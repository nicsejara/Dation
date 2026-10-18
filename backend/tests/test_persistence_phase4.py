"""Application contract: full summaries, pure history and explicit approval conflicts."""
from unittest.mock import AsyncMock, patch
import unittest
from platform_fixtures import TenantTestCase, WORKSPACE
import httpx
from app.services import decision_case_service as cases
from app.services.dispatch_job_service import RunConflict
from app.auth import require_upload_access
from main import app
from test_decision_run_history_v2 import CASE_ID,ORDERS_ID,FLEET_ID,ASSIGNMENT_1,ASSIGNMENT_2,SCHEDULING_1,run_row


class PersistenceTests(TenantTestCase):
    async def test_history_rpc_uses_only_a_read_request_and_omits_null_node(self):
        requests=[]
        def respond(request):
            requests.append(request)
            return httpx.Response(200,json=self.snapshot())
        client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch.object(cases.httpx,'AsyncClient',return_value=client), \
             patch.object(cases,'SUPABASE_URL','https://qa.invalid'):
            snapshot=await cases.history_snapshot(CASE_ID)
        self.assertEqual([r.method for r in requests],['POST'])
        import json
        self.assertNotIn('target_node_id',json.loads(requests[0].content)['arguments'])
        self.assertEqual(snapshot['summaries']['logistics_assignment']['run_count'],1501)

    async def test_private_api_requires_credentials(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.get(f'/api/decision-cases/{CASE_ID}/runs')
        self.assertEqual(response.status_code,401)

    async def test_approval_body_cannot_claim_a_person(self):
        app.dependency_overrides[require_upload_access]=lambda:'dation'
        try:
            with patch.object(cases,'approve_run_version',AsyncMock()) as approve:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                    response=await client.post(f'/api/runs/{ASSIGNMENT_1}/approve',json={
                        'case_id':CASE_ID,'node_id':'logistics_assignment','approved_by':'person'})
            self.assertEqual(response.status_code,422)
            approve.assert_not_awaited()
        finally:app.dependency_overrides.clear()

    def snapshot(self):
        a=run_row(ASSIGNMENT_1,'logistics_assignment',created_at='2020-01-01',approved_at='2020-01-02')
        b=run_row(ASSIGNMENT_2,'logistics_assignment',created_at='2026-10-10')
        s=run_row(SCHEDULING_1,'logistics_scheduling',created_at='2026-10-10',upstream=ASSIGNMENT_1,approved_at='2026-10-10')
        return {'summaries':{'logistics_assignment':{'run_count':1501,'latest':b,'approved':a},
                'logistics_scheduling':{'run_count':1,'latest':s,'approved':s},
                'logistics_final_assignment':{'run_count':0,'latest':None,'approved':None}},'runs':[s]}

    def row(self):
        return {'id':CASE_ID,'orders_dataset_id':ORDERS_ID,'fleet_dataset_id':FLEET_ID,'state_json':{}}

    async def test_history_does_not_slice_page_or_drop_other_node_approvals(self):
        with patch.object(cases,'get_case_row',AsyncMock(return_value=self.row())), \
             patch.object(cases,'history_snapshot',AsyncMock(return_value=self.snapshot())) as read, \
             patch.object(cases,'list_case_runs',AsyncMock()) as legacy:
            history=await cases.get_run_history(CASE_ID,node_id='logistics_scheduling',limit=1,offset=1000)
        read.assert_awaited_once_with(CASE_ID,node_id='logistics_scheduling',limit=1,offset=1000)
        legacy.assert_not_awaited()
        self.assertEqual(history['runs'][0]['id'],SCHEDULING_1)
        self.assertEqual(history['summary']['status'],'approved')
        self.assertEqual(history['total'],1)

    async def test_case_and_projection_use_full_counts_without_history_window(self):
        data={'orders':{'dataset_type':'orders'},'fleet':{'dataset_type':'fleet'}}
        async def dataset(identifier):return data['orders' if identifier==ORDERS_ID else 'fleet']
        with patch.object(cases,'get_case_row',AsyncMock(return_value=self.row())), \
             patch.object(cases,'get_dataset',dataset), \
             patch.object(cases,'history_snapshot',AsyncMock(return_value=self.snapshot())), \
             patch.object(cases,'update_case',AsyncMock()) as write:
            result=await cases.get_case(CASE_ID)
            write.assert_not_awaited()
            await cases.sync_case_history(CASE_ID)
        node=result['decision_case']['nodes']['logistics_assignment']
        self.assertEqual(node['run_count'],1501)
        self.assertEqual(node['approved_run_id'],ASSIGNMENT_1)
        self.assertEqual(write.await_args.kwargs['state']['nodes']['logistics_assignment']['run_count'],1501)

    async def test_stale_approval_is_not_labeled_current(self):
        snapshot=self.snapshot()
        snapshot['summaries']['logistics_assignment']['approved']=snapshot['summaries']['logistics_assignment']['latest']
        snapshot['summaries']['logistics_assignment']['approved']['approved_at']='2026-10-10'
        with patch.object(cases,'get_case_row',AsyncMock(return_value=self.row())), \
             patch.object(cases,'history_snapshot',AsyncMock(return_value=snapshot)):
            history=await cases.get_run_history(CASE_ID,node_id='logistics_scheduling')
        self.assertEqual(history['runs'][0]['decision_state'],'stale')
        self.assertFalse(history['runs'][0]['is_current_approved'])

    async def test_atomic_conflict_is_a_business_conflict(self):
        target=self.snapshot()['summaries']['logistics_assignment']['latest']
        response=httpx.Response(400,json={'code':'22023'},request=httpx.Request('POST','https://qa.invalid'))
        error=httpx.HTTPStatusError('conflict',request=response.request,response=response)
        with patch.object(cases,'get_run',AsyncMock(return_value=target)), \
             patch.object(cases,'_db',AsyncMock(side_effect=error)):
            with self.assertRaises(RunConflict):
                await cases.approve_run_version(ASSIGNMENT_2,case_id=CASE_ID,node_id='logistics_assignment')

    async def test_case_creation_race_preserves_binding(self):
        response=httpx.Response(409,request=httpx.Request('POST','https://qa.invalid'))
        error=httpx.HTTPStatusError('race',request=response.request,response=response)
        with patch.object(cases,'get_case_row',AsyncMock(side_effect=[None,self.row()])), \
             patch.object(cases,'_validate_data_pack',AsyncMock()), \
             patch.object(cases,'_db',AsyncMock(side_effect=error)):
            self.assertEqual((await cases.ensure_case(CASE_ID,ORDERS_ID,FLEET_ID))['id'],CASE_ID)
