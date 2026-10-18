"""Request budgets, live approvals and HTTP pool ownership."""
import asyncio
import copy
import unittest
from platform_fixtures import TenantTestCase, WORKSPACE
from unittest.mock import AsyncMock, patch

import httpx
from app.services import decision_case_service as cases, http_service, run_service
from main import app


class CaseListTests(TenantTestCase):
    def bundle(self, identifier=0):
        return {'case_row':{'id':str(identifier),'orders_dataset_id':'orders',
                'fleet_dataset_id':'fleet','state_json':{}},
                'orders':{'id':'orders','dataset_type':'orders','label':'Orders'},
                'fleet':{'id':'fleet','dataset_type':'fleet','label':'Fleet'},
                'summaries':{n:{'run_count':0,'latest':None,'approved':None} for n in cases.NODE_IDS}}

    async def test_case_page_has_one_database_request_at_every_size(self):
        for size in (0,3,100):
            with self.subTest(size=size), \
                 patch.object(cases,'_db',AsyncMock(return_value=[self.bundle(i) for i in range(size)])) as db, \
                 patch.object(cases,'get_dataset',AsyncMock()) as datasets, \
                 patch.object(cases,'history_snapshot',AsyncMock()) as history:
                result=await cases.list_cases(status=None,limit=100,offset=7,summary=True)
                self.assertEqual(len(result),size)
                db.assert_awaited_once_with('POST','rpc/list_decision_cases',body={
                    'case_status':None,'page_limit':100,'page_offset':7,'summary_only':True})
                datasets.assert_not_awaited();history.assert_not_awaited()

    async def test_next_read_observes_replacement_and_stale_downstream(self):
        first=self.bundle();second=copy.deepcopy(first)
        a={'id':'a','node_id':'logistics_assignment','status':'completed','approved_at':'2026-10-10'}
        b={**a,'id':'b','approved_at':None}
        s={'id':'s','node_id':'logistics_scheduling','status':'completed',
           'upstream_run_id':'a','approved_at':'2026-10-10'}
        for bundle,approved in [(first,a),(second,{**b,'approved_at':'2026-10-10'})]:
            bundle['summaries']['logistics_assignment']={'run_count':1501,'latest':b if bundle is first else approved,'approved':approved}
            bundle['summaries']['logistics_scheduling']={'run_count':1,'latest':s,'approved':s}
        with patch.object(cases,'_db',AsyncMock(side_effect=[[first],[second]])) as db:
            before=(await cases.list_cases())[0]['decision_case']['nodes']
            after=(await cases.list_cases())[0]['decision_case']['nodes']
        self.assertEqual(db.await_count,2)
        self.assertEqual(before['logistics_scheduling']['status'],'approved')
        self.assertEqual(after['logistics_scheduling']['status'],'stale')
        self.assertEqual(after['logistics_assignment']['run_count'],1501)
        self.assertEqual(after['logistics_assignment']['approved_run_id'],'b')

    async def test_invalid_pagination_and_dataset_types_fail_before_hydration(self):
        with patch.object(cases,'_db',AsyncMock()) as db:
            for kwargs in [{'limit':0},{'limit':101},{'offset':-1},{'status':'unknown'}]:
                with self.assertRaises(ValueError):await cases.list_cases(**kwargs)
            db.assert_not_awaited()
        bundle=self.bundle();bundle['fleet']['dataset_type']='orders'
        with patch.object(cases,'_db',AsyncMock(return_value=[bundle])):
            with self.assertRaises(ValueError):await cases.list_cases()


class PoolTests(TenantTestCase):
    async def test_lifespan_shares_client_with_parallel_tasks_and_closes_on_shutdown(self):
        requests=[]
        async def respond(request):
            requests.append(request)
            await asyncio.sleep(0)
            return httpx.Response(200,json=[{'id':str(request.url.params['id'])}])
        client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch.object(http_service.httpx,'AsyncClient',return_value=client) as factory, \
             patch.object(run_service,'SUPABASE_URL','https://qa.invalid'):
            async with app.router.lifespan_context(app):
                await asyncio.gather(*(run_service.get_dataset(str(i)) for i in range(20)))
                async with http_service.http_client() as shared:self.assertIs(shared,client)
                self.assertFalse(client.is_closed)
                factory.assert_called_once()
            self.assertTrue(client.is_closed)
        self.assertEqual(len(requests),20)
        self.assertTrue(all(r.extensions['timeout']['read']==15 for r in requests))
        self.assertNotIn(asyncio.get_running_loop(),http_service._clients)

    async def test_headers_and_timeouts_are_request_local_even_when_pool_is_shared(self):
        seen=[]
        client=httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request:(seen.append(request) or httpx.Response(200,json={}))))
        with patch.object(http_service.httpx,'AsyncClient',return_value=client):
            async with http_service.http_pool():
                async with http_service.http_client() as first, http_service.http_client() as second:
                    await asyncio.gather(first.get('https://qa.invalid',headers={'X-Test':'a'},timeout=10),
                                         second.get('https://qa.invalid',headers={'X-Test':'b'},timeout=30))
        self.assertEqual({(r.headers['X-Test'],r.extensions['timeout']['read']) for r in seen},{('a',10),('b',30)})

    async def test_error_and_cancellation_release_pool_and_standalone_client(self):
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200)))
        with patch.object(http_service.httpx,'AsyncClient',return_value=client):
            with self.assertRaises(asyncio.CancelledError):
                async with http_service.http_pool():raise asyncio.CancelledError()
        self.assertTrue(client.is_closed)
        self.assertNotIn(asyncio.get_running_loop(),http_service._clients)
        temporary=httpx.AsyncClient()
        with patch.object(http_service.httpx,'AsyncClient',return_value=temporary):
            with self.assertRaises(ValueError):
                async with http_service.http_client():raise ValueError('fixture')
        self.assertTrue(temporary.is_closed)
