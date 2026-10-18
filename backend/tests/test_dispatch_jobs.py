import asyncio
import hashlib
import json
from pathlib import Path
import unittest
from platform_fixtures import TenantTestCase, WORKSPACE
from unittest.mock import AsyncMock, patch

import httpx

from app.auth import require_upload_access
from app.services import dispatch_job_service as jobs
from app.services import dispatch_service as dispatch
from main import app

O = '00000000-0000-4000-8000-000000000001'
F = '00000000-0000-4000-8000-000000000002'
R = '00000000-0000-4000-8000-000000000003'
C = '00000000-0000-4000-8000-000000000004'


def request_data(case=None):
    name, version, schema = jobs.engine_identity((case or {}).get('node_id'))
    return dict(workspace_id=WORKSPACE,orders_id=O, fleet_id=F, configuration={'objective':'balanced'}, options={},
                decision_case=case, source_run_id=None, engine_name=name, engine_version=version, schema_version=schema)


def fingerprint(request):
    return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def http_error(code, status=400):
    response = httpx.Response(status,json={'code':code},request=httpx.Request('POST','https://qa.invalid'))
    return httpx.HTTPStatusError('QA provider error',request=response.request,response=response)


class JobAdmissionTests(TenantTestCase):
    async def test_same_intention_replays_before_mutable_upstream_validation(self):
        case = {'case_id':C,'node_id':'logistics_scheduling'}
        request = request_data(case)
        with patch.object(dispatch,'db',AsyncMock(return_value=[{'request_fingerprint':fingerprint(request)}])) as db, \
             patch.object(jobs,'get_run',AsyncMock(return_value={'id':R,'status':'completed'})), \
             patch.object(jobs.cases,'validate_upstream_run',AsyncMock(side_effect=ValueError('superseded'))) as validate:
            result = await jobs.enqueue(O,F,request['configuration'],{},R,case)
        self.assertEqual(result['status'],'completed')
        validate.assert_not_awaited()
        self.assertEqual([call.args[0] for call in db.await_args_list],['GET'])

    async def test_same_id_with_different_intention_conflicts(self):
        with patch.object(dispatch,'db',AsyncMock(return_value=[{'request_fingerprint':'another-intention'}])):
            with self.assertRaises(jobs.RunConflict):
                await jobs.enqueue(O,F,{'objective':'balanced'},{},R)

    async def test_case_admission_uses_single_atomic_rpc(self):
        case = {'case_id':C,'node_id':'logistics_assignment'}
        with patch.object(dispatch,'db',AsyncMock(side_effect=[[],[{'id':R,'status':'queued'}]])) as db, \
             patch.object(jobs.cases,'ensure_case',AsyncMock()) as ensure:
            result = await jobs.enqueue(O,F,{'objective':'balanced'},{},R,case)
        self.assertEqual(result['status'],'queued')
        ensure.assert_awaited_once_with(C,O,F)
        command = db.await_args_list[-1]
        self.assertEqual(command.args,('POST','rpc/enqueue_dispatch_run'))
        self.assertEqual(command.kwargs['body']['run_payload']['node_id'],'logistics_assignment')
        self.assertEqual(len(command.kwargs['body']['intent_fingerprint']),64)
        self.assertFalse(any(call.args[0] == 'PATCH' for call in db.await_args_list))

    async def test_wrong_dataset_types_never_enter_queue(self):
        with patch.object(dispatch,'db',AsyncMock(return_value=[])) as db, \
             patch.object(jobs,'get_dataset',AsyncMock(return_value={'dataset_type':'orders'})):
            with self.assertRaisesRegex(ValueError,'tipos'):
                await jobs.enqueue(O,F,{}, {},R)
        self.assertEqual(db.await_count,1)

    async def test_rpc_capacity_and_conflict_errors_are_explicit(self):
        for code, expected in [('53300',jobs.QueueFull),('22023',jobs.RunConflict),('23505',jobs.RunConflict)]:
            with self.subTest(code=code), patch.object(dispatch,'db',AsyncMock(side_effect=[[],http_error(code)])), \
                 patch.object(jobs.cases,'ensure_case',AsyncMock()):
                with self.assertRaises(expected):
                    await jobs.enqueue(O,F,{}, {},R,{'case_id':C,'node_id':'logistics_assignment'})


class WorkerTests(TenantTestCase):
    def job(self):
        return {'workspace_id':WORKSPACE,'run_id':R,'lease_token':C,'attempts':1,'request_json':request_data()}

    async def test_completed_result_is_written_once_with_lease_and_progress_is_nonblocking(self):
        async def execute(*args,execution_writer,progress_handler):
            for index in range(200):
                await asyncio.to_thread(progress_handler,str(index))
            return (await execution_writer({'status':'completed','result_json':{'fingerprint':'same'}}))[0]
        with patch.object(dispatch,'execute',execute), patch.object(dispatch,'db',AsyncMock(return_value=[{'id':R,'status':'completed'}])) as db:
            result = await jobs.process_job(self.job())
        self.assertEqual(result['status'],'completed')
        db.assert_awaited_once()
        command=db.await_args
        self.assertEqual(command.args,('POST','rpc/finish_dispatch_job'))
        self.assertEqual(command.kwargs['body']['worker_token'],C)

    async def test_stale_worker_cannot_overwrite_new_owner(self):
        async def execute(*args,execution_writer,progress_handler):
            await execution_writer({'status':'completed','result_json':{}})
        with patch.object(dispatch,'execute',execute), patch.object(dispatch,'db',AsyncMock(return_value=[])) as db:
            self.assertIsNone(await jobs.process_job(self.job()))
        self.assertEqual(db.await_count,1)

    async def test_dependency_outage_leaves_job_for_lease_recovery(self):
        with patch.object(dispatch,'execute',AsyncMock(side_effect=httpx.ConnectError('offline'))), \
             patch.object(dispatch,'db',AsyncMock()) as db:
            await jobs.process_job(self.job())
        db.assert_not_awaited()

    async def test_invalid_engine_version_is_terminal_without_running_solver(self):
        job=self.job();job['request_json']['engine_version']='unavailable-version'
        with patch.object(dispatch,'execute',AsyncMock()) as execute, patch.object(dispatch,'db',AsyncMock(return_value=[{'id':R}])) as db:
            await jobs.process_job(job)
        execute.assert_not_awaited()
        self.assertEqual(db.await_args.kwargs['body']['terminal_values']['status'],'error')

    async def test_projection_failure_only_reschedules_observed_outbox_version(self):
        with patch.object(dispatch,'db',AsyncMock(side_effect=[[{'workspace_id':WORKSPACE,'case_id':C,'version':7,'attempts':2}],[]])) as db, \
             patch.object(jobs.cases,'sync_case_history',AsyncMock(side_effect=httpx.ConnectError('offline'))):
            await jobs.reconcile_cases()
        command=db.await_args_list[-1]
        self.assertEqual(command.args,('PATCH','decision_case_reconciliations'))
        self.assertEqual(command.kwargs['params']['version'],'eq.7')
        self.assertEqual(command.kwargs['body']['attempts'],3)
        self.assertFalse(any(call.args[1]=='decision_runs' for call in db.await_args_list))

    async def test_projection_acknowledges_only_observed_version(self):
        with patch.object(dispatch,'db',AsyncMock(side_effect=[[{'workspace_id':WORKSPACE,'case_id':C,'version':8,'attempts':0}],None])) as db, \
             patch.object(jobs.cases,'sync_case_history',AsyncMock()):
            await jobs.reconcile_cases()
        self.assertEqual(db.await_args.kwargs['body'],{'target_case_id':C,'observed_version':8})

    async def test_real_assignment_engine_uses_leased_writer_without_duplicate_insert(self):
        root=Path(__file__).resolve().parents[2]/'sample_data/v3'
        datasets=({'id':O,'original_filename':'orders.csv','created_at':'2026-10-10'},
                  {'id':F,'original_filename':'fleet.csv','created_at':'2026-10-10'})
        writer=AsyncMock(return_value=[{'id':R,'status':'completed'}])
        with patch.object(dispatch,'load_inputs',AsyncMock(return_value=(*datasets,(root/'orders.csv').read_bytes(),(root/'fleet.csv').read_bytes()))), \
             patch.object(dispatch,'_insert_run',AsyncMock()) as insert, patch.object(dispatch,'db',AsyncMock()) as db:
            result=await dispatch.execute(O,F,{'objective':'balanced'},{},R,
                {'case_id':C,'node_id':'logistics_assignment'},execution_writer=writer,progress_handler=lambda stage:None)
        self.assertEqual(result['status'],'completed')
        insert.assert_not_awaited();db.assert_not_awaited()
        payload=writer.await_args.args[0]
        self.assertEqual(payload['status'],'completed')
        self.assertEqual(payload['result_json']['schema_version'],'assignment_v1')
        self.assertTrue(payload['input_fingerprint'])


class DurableHTTPTests(TenantTestCase):
    async def asyncSetUp(self):
        app.dependency_overrides[require_upload_access]=lambda:'dation'
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://qa')

    async def asyncTearDown(self):
        app.dependency_overrides.clear();await self.client.aclose()

    async def test_conflict_and_capacity_statuses(self):
        for exc, status in [(jobs.RunConflict('different'),409),(jobs.QueueFull('full'),429)]:
            with self.subTest(status=status), patch.object(dispatch,'available',AsyncMock(return_value=True)), \
                 patch.object(jobs,'enqueue',AsyncMock(side_effect=exc)):
                response=await self.client.post('/api/runs?run_id='+R,json={'orders_dataset_id':O,'fleet_dataset_id':F})
                self.assertEqual(response.status_code,status)
                if status==429:self.assertEqual(response.headers['Retry-After'],'5')

    async def test_persisted_approval_succeeds_when_projection_is_unavailable(self):
        with patch.object(jobs.cases,'approve_run_version',AsyncMock(return_value={'id':R,'approved_at':'2026-10-10'})), \
             patch.object(jobs.cases,'sync_case_history',AsyncMock(side_effect=httpx.ConnectError('offline'))):
            response=await self.client.post('/api/runs/'+R+'/approve',json={'case_id':C,'node_id':'logistics_assignment'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['approved_at'],'2026-10-10')
        self.assertTrue(response.json()['projection_pending'])

    async def test_explicit_cancel_command(self):
        with patch.object(jobs,'cancel',AsyncMock(return_value={'id':R,'status':'error'})) as cancel:
            response=await self.client.post('/api/runs/'+R+'/cancel')
        self.assertEqual(response.status_code,200);cancel.assert_awaited_once_with(R)
