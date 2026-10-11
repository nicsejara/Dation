"""Correlation isolation, safe logs, deadlines and atomic chat admission."""
import asyncio
from contextlib import asynccontextmanager
import json
import logging
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import httpx
from fastapi import FastAPI
from main import app
from app.auth import require_upload_access
from app import observability as telemetry
from app.services import llm_service as llm, decision_interpreter_service as interpreter
from app.services import dispatch_job_service as jobs, operations_service as operations


class TelemetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_requests_keep_correlation_and_registered_route_labels(self):
        api=FastAPI();api.add_middleware(telemetry.RequestTelemetry)
        @api.get('/things/{identifier}')
        async def things(identifier:str):
            before=dict(telemetry.context.get());await asyncio.sleep(.001)
            self.assertEqual(before,telemetry.context.get())
            return before
        with patch.object(telemetry,'metrics',telemetry.Metrics()) as metrics:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),base_url='http://test') as client:
                ids=[str(uuid4()) for _ in range(12)]
                results=await asyncio.gather(*(client.get('/things/'+str(i),headers={'X-Request-ID':rid}) for i,rid in enumerate(ids)))
                self.assertEqual([r.headers['x-request-id'] for r in results],ids)
                self.assertEqual([r.json()['request_id'] for r in results],ids)
            self.assertIn('route="/things/{identifier}"',metrics.render())
            self.assertNotIn(ids[0],metrics.render())
            self.assertEqual(telemetry.context.get(),{})

    async def test_errors_auth_validation_and_invalid_inbound_headers_are_correlated(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            for path in ['/ready','/metrics','/api/system/operations']:
                result=await client.get(path,headers={'X-Request-ID':'private input','traceparent':'00-'+'0'*32+'-'+'1'*16+'-01'})
                self.assertEqual(result.status_code,401)
                self.assertIsNotNone(telemetry.uuid_value(result.headers['x-request-id']))
                self.assertNotIn('0'*32,result.headers['traceparent'])
            app.dependency_overrides[require_upload_access]=lambda:'dation'
            try:
                for question in ['x', '   ']:
                    bad=await client.post('/api/runs/'+str(uuid4())+'/chat',json={'question':question})
                    self.assertEqual(bad.status_code,422);self.assertIn('x-request-id',bad.headers)
            finally:app.dependency_overrides.clear()

    async def test_unhandled_error_returns_safe_response_and_headers(self):
        api=FastAPI();api.add_middleware(telemetry.RequestTelemetry)
        @api.get('/failure')
        async def failure():raise RuntimeError('secret prompt body')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),base_url='http://test') as client:
            result=await client.get('/failure')
        self.assertEqual(result.status_code,500);self.assertIn('x-request-id',result.headers)
        self.assertNotIn('secret',result.text)

    def test_formatter_discards_bodies_urls_exception_text_and_nonfinite_values(self):
        record=logging.LogRecord('private',logging.ERROR,'',1,'https://host?apikey=secret',(),None)
        record.telemetry={'body':'prompt secret','question':'private','duration_ms':float('nan'),'request_id':'bad'}
        result=telemetry.JSONFormatter().format(record)
        self.assertNotIn('secret',result);self.assertNotIn('private',result.replace('"logger":"private"',''))
        self.assertNotIn('duration_ms',json.loads(result));self.assertNotIn('request_id',json.loads(result))

    async def test_dependency_instrumentation_preserves_identity_headers_and_timeout(self):
        captured=[]
        async def respond(request):captured.append(request);return httpx.Response(200,json={})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            self.assertIs(telemetry.instrument_http(client),client)
            self.assertIs(telemetry.instrument_http(client),client)
            with telemetry.bind_context() as data:
                await client.get('https://host/rest/v1/datasets?private=secret',headers={'Authorization':'Bearer fake'},timeout=7)
            self.assertEqual(captured[0].headers['x-request-id'],data['request_id'])
            self.assertEqual(captured[0].headers['authorization'],'Bearer fake')
            self.assertEqual(captured[0].extensions['timeout']['read'],7)

    async def test_cancelled_dependency_is_measured_without_swallowing_cancellation(self):
        async def respond(request):raise asyncio.CancelledError()
        with patch.object(telemetry,'metrics',telemetry.Metrics()) as metrics:
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                telemetry.instrument_http(client)
                with self.assertRaises(asyncio.CancelledError):await client.get('https://host/storage/v1/object')
            self.assertIn('outcome="cancelled"',metrics.render())

    async def test_admission_identity_does_not_change_replay_fingerprint(self):
        run,case,orders,fleet=[str(uuid4()) for _ in range(4)]
        async def db(method,path,**kw):
            if method=='GET':return []
            self.body=kw['body'];return [{'id':run}]
        with patch.object(jobs.dispatch,'db',side_effect=db),patch.object(jobs.cases,'ensure_case',AsyncMock()):
            with telemetry.bind_context() as data:
                await jobs.enqueue(orders,fleet,{}, {},run,{'case_id':case,'node_id':'logistics_assignment'})
        import hashlib
        request=self.body['job_request'];self.assertEqual(request.pop('_observability')['request_id'],data['request_id'])
        self.assertEqual(self.body['intent_fingerprint'],hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest())


class LLMTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def client(self,handler):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url='https://synthetic.local') as client:
            telemetry.instrument_http(client);yield client

    async def test_retry_is_capped_once_and_usage_is_sanitized(self):
        calls=[]
        async def provider(request):
            calls.append(request)
            if len(calls)==1:return httpx.Response(429,headers={'Retry-After':'999999999'})
            return httpx.Response(200,json={'choices':[{'message':{'content':'answer'}}],
                'usage':{'total_tokens':9,'prompt_tokens':5,'completion_tokens':4,'raw_prompt':'private','negative':-1}})
        with patch.object(llm,'LLM_API_KEY','synthetic'),patch.object(llm,'http_client',lambda:self.client(provider)),patch.object(llm.asyncio,'sleep',AsyncMock()) as pause:
            result=await llm.chat_completion(messages=[{'role':'user','content':'private question'}])
        self.assertEqual(len(calls),2);pause.assert_awaited_once_with(5)
        self.assertEqual(result['usage'],{'total_tokens':9,'prompt_tokens':5,'completion_tokens':4})

    async def test_provider_retry_and_io_share_one_deadline(self):
        calls=[]
        async def provider(request):
            calls.append(request)
            return httpx.Response(429,headers={'Retry-After':'5'})
        with patch.object(llm,'LLM_API_KEY','synthetic'),patch.object(llm,'TOTAL_DEADLINE_SECONDS',.02),patch.object(llm,'http_client',lambda:self.client(provider)):
            with self.assertRaises(TimeoutError):await llm.chat_completion(messages=[])
        self.assertEqual(len(calls),1)

    def test_retry_delay_handles_invalid_nonfinite_and_negative_inputs(self):
        for value,expected in [('nan',3),('inf',3),('-2',0),('99999',5),('bad',3)]:
            self.assertEqual(llm._retry_delay(httpx.Response(429,headers={'Retry-After':value})),expected)
        self.assertEqual(llm.safe_usage({'total_tokens':True,'prompt_tokens':-1,'completion_tokens':10**11}),{})

    async def test_completed_turn_replay_avoids_provider_and_retains_audit_identity(self):
        saved={'answer':'saved','prompt_version':'v1'}
        with patch.object(interpreter.dispatch,'db',AsyncMock(return_value=saved)),patch.object(interpreter,'chat_completion',AsyncMock()) as provider:
            result=await interpreter.answer_question(run_id=str(uuid4()),question='Why?',turn_id=str(uuid4()))
        self.assertEqual(result,saved);provider.assert_not_awaited()

    async def test_turn_is_persisted_with_one_atomic_rpc_and_usage(self):
        run,turn=str(uuid4()),str(uuid4())
        response={'provider':'fake','model':'synthetic','content':'answer','usage':{'total_tokens':9}}
        with patch.object(interpreter.dispatch,'db',AsyncMock(side_effect=[None,{'answer':'answer'}])) as db,\
             patch.object(interpreter,'_load_completed_run',AsyncMock(return_value={'result_json':{}})),\
             patch.object(interpreter,'build_decision_context',return_value={}),\
             patch.object(interpreter,'load_logistics_knowledge_for_question',return_value={'version':'qa','content':''}),\
             patch.object(interpreter,'_recent_messages',AsyncMock(return_value=[])),\
             patch.object(interpreter,'chat_completion',AsyncMock(return_value=response)):
            await interpreter.answer_question(run_id=run,question='Why?',turn_id=turn)
        self.assertEqual(db.await_count,2)
        self.assertEqual(db.call_args.args[1],'rpc/record_decision_chat_turn')
        body=db.call_args.kwargs['body'];self.assertEqual(body['question_text'],'Why?')
        self.assertEqual(body['metadata']['usage'],{'total_tokens':9});self.assertEqual(body['target_turn_id'],turn)

    async def test_history_uses_latest_window_and_exposes_older_page(self):
        async def respond(request):
            if 'decision_messages' in request.url.path:
                self.params=request.url.params
                return httpx.Response(200,json=[{'content':str(i)} for i in range(3)])
            return httpx.Response(200,json=[])
        with patch.object(interpreter,'http_client',lambda:self.client(respond)):
            result=await interpreter.get_saved_interpretation(str(uuid4()),limit=2,offset=4)
        self.assertEqual([r['content'] for r in result['messages']],['1','0'])
        self.assertTrue(result['pagination']['has_more']);self.assertEqual(self.params['offset'],'4')
        self.assertEqual(self.params['order'],'created_at.desc,id.desc')

    async def test_whole_turn_deadline_also_bounds_database_waits(self):
        async def blocked(*args,**kwargs):await asyncio.sleep(1)
        with patch.object(interpreter,'TURN_DEADLINE_SECONDS',.01),patch.object(interpreter.dispatch,'db',side_effect=blocked):
            with self.assertRaises(TimeoutError):await interpreter.answer_question(run_id=str(uuid4()),question='Why?')


class OperationsTests(unittest.IsolatedAsyncioTestCase):
    async def test_probe_failure_and_healthy_database_without_worker_are_distinct(self):
        with patch.object(operations.dispatch,'db',side_effect=httpx.ConnectError('secret host')):
            result=await operations.operational_snapshot()
        self.assertEqual(result['database'],'unavailable');self.assertFalse(result['ready']);self.assertNotIn('host',json.dumps(result))
        snapshot={'workers':{'healthy':0},'queue':{'queued':1,'oldest_queued_seconds':31,'expired_leases':1,'past_deadline':1},'reconciliation':{'oldest_pending_seconds':61}}
        with patch.object(operations.dispatch,'db',AsyncMock(return_value=snapshot)):
            result=await operations.operational_snapshot()
        self.assertEqual(result['database'],'available');self.assertFalse(result['ready'])
        self.assertIn('queue_without_worker',result['alerts']);self.assertIn('reconciliation_over_60s',result['alerts'])
