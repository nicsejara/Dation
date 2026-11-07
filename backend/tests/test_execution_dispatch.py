"""Activation failures preserve accepted work; idle readiness has no worker requirement."""
import asyncio
from contextlib import asynccontextmanager
import copy
import os
import sys
import unittest
from unittest.mock import AsyncMock,patch
from uuid import uuid4
import httpx
from fastapi import HTTPException
from platform_fixtures import TenantTestCase
from app.services import execution_dispatch as runtime,operations_service
from app.cloud_identity import environment, PROJECT, REGION
import event_worker

class ExecutionDispatchTests(TenantTestCase):
    def setUp(self):
        super().setUp();mode=patch.dict(os.environ,{'DATION_EXECUTION_MODE':'jobs','DATION_CLOUD_EXECUTION_ENABLED':'false'})
        mode.start();self.addCleanup(mode.stop)
    def test_jobs_is_the_production_default_without_environment_override(self):
        with patch.dict(os.environ,{}):
            os.environ.pop('DATION_EXECUTION_MODE',None)
            self.assertTrue(runtime.jobs_mode())

    async def test_default_disabled_never_reserves_or_contacts_cloud(self):
        with patch.object(runtime,'runtime_rpc',AsyncMock()) as rpc:
            await runtime.nudge('dispatch',str(uuid4()))
            rpc.assert_not_awaited()
        with patch.object(runtime,'runtime_rpc',AsyncMock(return_value={'enabled':False})):
            with self.assertRaises(HTTPException) as caught:await runtime.ensure_admission()
            self.assertEqual(caught.exception.status_code,503)
    async def test_ambiguous_provider_timeout_preserves_same_fenced_delivery(self):
        identity={'id':str(uuid4()),'delivery_token':str(uuid4()),'kind':'dispatch','generation':1,'delivery_attempts':1}
        rpc=AsyncMock(side_effect=[[identity],True])
        provider=type('Provider',(),{'dispatch':AsyncMock(side_effect=httpx.ReadTimeout('lost ACK'))})()
        with runtime.use_transport(provider),patch.object(runtime,'runtime_rpc',rpc):
            self.assertEqual(await runtime.publish_pending(),['pending_recovery'])
        self.assertEqual(rpc.await_args_list[1].args[0],'defer')
        self.assertEqual(rpc.await_args_list[1].args[1]['delivery_token'],identity['delivery_token'])
    async def test_google_transport_requires_exact_resources_and_managed_identity(self):
        with patch.dict(os.environ,{**environment(),'DATION_CLOUD_EXECUTION_ENABLED':'true'}):
            provider=runtime.GoogleJobsTransport()
            with patch.dict(os.environ,{'DATION_CLOUD_PROJECT':'other-project'}):
                with self.assertRaises(runtime.DispatchConfigurationError):runtime.GoogleJobsTransport()
            client=AsyncMock();client.get.return_value=httpx.Response(200,json={'access_token':'synthetic'},request=httpx.Request('GET','http://metadata.google.internal'))
            self.assertEqual(await provider._token(client),'synthetic')
            self.assertEqual(client.get.call_args.kwargs['headers'],{'Metadata-Flavor':'Google'})
    async def test_missing_or_cross_project_config_fails_before_reservation_or_cloud(self):
        valid={**environment(),'DATION_CLOUD_EXECUTION_ENABLED':'true'}
        invalid=[]
        for key in environment():
            missing=dict(valid);missing.pop(key);invalid.append(missing)
        for key,value in [('DATION_CLOUD_PROJECT','dation-510100'),
                          ('DATION_CLOUD_PROJECT_NUMBER','469052310590'),
                          ('DATION_CLOUD_REGION','us-central1'),
                          ('DATION_CONTROL_JOB','projects/other-project/locations/us-west1/jobs/dation-recovery')]:
            invalid.append({**valid,key:value})
        for values in invalid:
            with self.subTest(values=values),patch.dict(os.environ,values,clear=True), \
                 patch.object(runtime,'runtime_rpc',AsyncMock()) as rpc,patch.object(runtime,'http_client') as cloud:
                with self.assertRaises(runtime.DispatchConfigurationError):await runtime.publish_pending()
                rpc.assert_not_awaited();cloud.assert_not_called()
    async def test_provider_and_iam_requests_are_scoped_to_v2_for_every_work_kind(self):
        client=AsyncMock()
        client.get.return_value=httpx.Response(200,json={'access_token':'synthetic'},request=httpx.Request('GET','http://metadata.google.internal'))
        operation=f'projects/{PROJECT}/locations/{REGION}/operations/owned'
        client.post.return_value=httpx.Response(200,json={'name':operation},request=httpx.Request('POST','https://run.googleapis.com'))
        @asynccontextmanager
        async def owned_client():yield client
        with patch.dict(os.environ,{**environment(),'DATION_CLOUD_EXECUTION_ENABLED':'true'}),patch.object(runtime,'http_client',owned_client):
            provider=runtime.GoogleJobsTransport()
            for kind,target in [('dispatch','compute'),('comparative','compute'),('reconciliation','control')]:
                intent={'id':str(uuid4()),'delivery_token':str(uuid4()),'kind':kind}
                self.assertEqual(await provider.dispatch(intent),operation)
                call=client.post.call_args
                self.assertEqual(call.args[0],'https://run.googleapis.com/v2/'+runtime.JOBS[target]+':run')
                overrides=call.kwargs['json']['overrides']
                self.assertEqual(overrides,{'taskCount':1,'containerOverrides':[{'name':'runtime','args':['--intent-id',intent['id'],'--delivery-token',intent['delivery_token']]}]})
            client.get.side_effect=[client.get.return_value,*[
                httpx.Response(200,json={'name':resource},request=httpx.Request('GET','https://run.googleapis.com')) for resource in runtime.JOBS.values()]]
            client.post.side_effect=[httpx.Response(200,json={'permissions':['run.jobs.run','run.jobs.runWithOverrides']},request=httpx.Request('POST','https://run.googleapis.com')) for _ in runtime.JOBS]
            client.post.reset_mock()
            self.assertTrue(await provider.healthy())
            self.assertEqual([c.args[0] for c in client.post.call_args_list],['https://run.googleapis.com/v2/'+resource+':testIamPermissions' for resource in runtime.JOBS.values()])
            client.post.side_effect=None
            client.get.side_effect=None
            client.post.return_value=httpx.Response(200,json={'name':'projects/dation-510100/locations/us-west1/operations/retired'},request=httpx.Request('POST','https://run.googleapis.com'))
            with self.assertRaises(runtime.DispatchConfigurationError):await provider.dispatch(intent)
    async def test_fake_transport_rejects_remote_hosts_and_cloud_runtime(self):
        for url in ['https://127.0.0.1','http://localhost','http://example.com','http://127.0.0.1/other']:
            with self.assertRaises(runtime.DispatchConfigurationError):runtime.LoopbackJobsTransport(url)
        with patch.dict(os.environ,{'CLOUD_RUN_JOB':'owned'}):
            with self.assertRaises(runtime.DispatchConfigurationError):runtime.LoopbackJobsTransport('http://127.0.0.1:1234')
    async def test_idle_readiness_reads_only_and_alerts_stale_work(self):
        base={'workers':{'healthy':0},'queue':{},'reconciliation':{}}
        policy=dict.fromkeys(['enabled','admissions_open','recovery_fresh','dispatch_budget_available'],True)
        provider=type('Provider',(),{'healthy':AsyncMock(return_value=True)})()
        for age,alerts in [(0,[]),(901,['execution_wait_over_recovery_interval'])]:
            rpc=AsyncMock(side_effect=[policy,{'pending':int(age>0),'oldest_pending_seconds':age}])
            with runtime.use_transport(provider),patch.object(runtime,'runtime_rpc',rpc),patch.object(operations_service.dispatch,'db',AsyncMock(side_effect=[copy.deepcopy(base),{}])):
                value=await operations_service.operational_snapshot()
            self.assertTrue(value['ready']);self.assertEqual(value['alerts'],alerts)
            self.assertEqual([c.args[0] for c in rpc.await_args_list],['policy','snapshot'])
    async def test_supervisor_kills_cpu_process_group_on_stop(self):
        from datetime import datetime,timedelta,timezone
        claim={'job':{},'intent':{'deadline_at':(datetime.now(timezone.utc)+timedelta(seconds=20)).isoformat(),'kind':'dispatch','id':str(uuid4())}}
        real_create=asyncio.create_subprocess_exec;children=[]
        async def owned_child(*args,**kwargs):
            child=await real_create(sys.executable,'-c','import sys,time;sys.stdin.read();time.sleep(60)',**kwargs)
            children.append(child);return child
        stop=asyncio.Event();stop.set()
        with patch.object(event_worker.asyncio,'create_subprocess_exec',owned_child):
            self.assertFalse(await event_worker.supervise(claim,{},stop))
        self.assertIsNotNone(children[0].returncode)
        self.assertLess(children[0].returncode,0)

    async def test_database_loss_during_child_work_terminates_process_before_exit(self):
        from datetime import datetime,timedelta,timezone
        claim={'job':{},'intent':{'deadline_at':(datetime.now(timezone.utc)+timedelta(seconds=20)).isoformat(),'kind':'dispatch','id':str(uuid4())}}
        real_create=asyncio.create_subprocess_exec;children=[]
        async def owned_child(*args,**kwargs):
            child=await real_create(sys.executable,'-c','import sys,time;sys.stdin.read();time.sleep(60)',**kwargs)
            children.append(child);return child
        with patch.object(event_worker.asyncio,'create_subprocess_exec',owned_child),patch.object(runtime,'runtime_rpc',AsyncMock(side_effect=httpx.ConnectError('DB offline'))):
            with self.assertRaises(httpx.ConnectError):await event_worker.supervise(claim,{},asyncio.Event())
        self.assertIsNotNone(children[0].returncode);self.assertLess(children[0].returncode,0)
