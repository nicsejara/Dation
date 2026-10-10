import unittest
from unittest.mock import AsyncMock, patch
import httpx
from app.services import dispatch_service as dispatch
from app.services import run_service


class ReadPurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_stale_run_never_writes(self):
        methods=[]
        async def handler(request):
            methods.append(request.method)
            return httpx.Response(200,json=[{'id':'qa','status':'running','started_at':'2000-01-01T00:00:00Z'}])
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch.object(run_service.httpx,'AsyncClient',return_value=client), patch.object(run_service,'SUPABASE_URL','https://qa.invalid'):
            run=await run_service.get_run('qa')
        self.assertEqual(run['status'],'running');self.assertEqual(methods,['GET'])

    async def test_profile_read_derives_metadata_without_persisting(self):
        dataset={'id':'qa','dataset_type':'orders','profile_json':{},'original_filename':'orders.csv'}
        report={'valid':True,'rows':3,'columns':10,'profile':{'profile_version':3},'records':[]}
        with patch.object(dispatch,'download_dataset',AsyncMock(return_value=b'qa')), \
             patch.dict(dispatch.REPORT_VALIDATORS,{'orders':lambda contents:report}), patch.object(dispatch,'db',AsyncMock()) as db:
            result=await dispatch._ensure_profile(dataset)
        self.assertEqual(result['row_count'],3);db.assert_not_awaited();self.assertEqual(dataset['profile_json'],{})

    async def test_explicit_profile_refresh_persists(self):
        dataset={'id':'qa','dataset_type':'orders','profile_json':{},'label':'QA'}
        report={'valid':True,'rows':3,'columns':10,'profile':{'profile_version':3},'records':[]}
        with patch.object(dispatch,'download_dataset',AsyncMock(return_value=b'qa')), \
             patch.dict(dispatch.REPORT_VALIDATORS,{'orders':lambda contents:report}), patch.object(dispatch,'db',AsyncMock(return_value=[dataset])) as db:
            await dispatch._ensure_profile(dataset,persist=True)
        self.assertEqual(db.await_args.args,('PATCH','datasets'))

    async def probe(self,status,paths=None):
        methods=[]
        async def handler(request):
            methods.append(request.method)
            return httpx.Response(status,json={'paths':paths or {}})
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch.object(dispatch,'supabase_configured',return_value=True), patch.object(dispatch,'SUPABASE_URL','https://qa.invalid'), \
             patch.object(dispatch.httpx,'AsyncClient',return_value=client):
            result=await dispatch._probe_default_rpc()
        self.assertEqual(methods,['GET'])
        return result

    async def test_401_403_and_provider_errors_are_never_rpc_success(self):
        for status in [401,403,500]:
            with self.subTest(status=status):self.assertFalse((await self.probe(status))[0])

    async def test_rpc_diagnostics_use_authorized_catalog_without_execution(self):
        self.assertTrue((await self.probe(200,{'/rpc/set_default_fleet':{'post':{}}}))[0])
        self.assertFalse((await self.probe(200))[0])

    async def test_missing_queue_schema_blocks_execution_availability(self):
        async def rest(path,params):return (path!='dispatch_run_jobs','missing queue' if path=='dispatch_run_jobs' else None)
        with patch.object(dispatch,'supabase_configured',return_value=True), patch.object(dispatch,'_probe_rest',rest), \
             patch.object(dispatch,'_probe_rpc_catalog',AsyncMock(return_value=(True,None))), \
             patch.object(dispatch,'_probe_bucket',AsyncMock(return_value=(True,None))):
            result=await dispatch.system_status()
        self.assertFalse(result['available'])
        self.assertFalse(next(check for check in result['checks'] if check['id']=='durable_queue')['ok'])
