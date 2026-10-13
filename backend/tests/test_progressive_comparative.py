"""Business immutability and trusted-input comparative generation."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock,patch
from uuid import uuid4
import httpx
from app.services import comparative_analysis_service as analyses
from app.engines.assignment.engine import run_assignment_engine,SCENARIO_FOR_OBJECTIVE
from app.auth import require_upload_access
from main import app
from contextlib import asynccontextmanager
from app.services import decision_interpreter_service as interpreter


class ProgressiveEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data=Path(__file__).resolve().parents[2]/'sample_data/v3'
        cls.orders=(data/'orders.csv').read_bytes();cls.fleet=(data/'fleet.csv').read_bytes()
        cls.options={'analysis_depth':'essential','solve_time_limit_s':.1,'deterministic_limit':.001,'total_time_limit_s':15}

    def test_missing_references_are_generated_without_reoptimizing_selected_plan(self):
        base=run_assignment_engine(self.orders,self.fleet,{'objective':'min_trips'},self.options)
        before=copy.deepcopy(base)
        with patch('app.engines.assignment.engine.solve',wraps=__import__('app.engines.assignment.engine',fromlist=['solve']).solve) as solver:
            derived=run_assignment_engine(self.orders,self.fleet,{k:v for k,v in base['configuration'].items() if k!='options'},
                {**base['configuration']['options'],'analysis_depth':'comparative'},reference_result=base)
        self.assertEqual(base,before)
        self.assertEqual(derived['scenarios']['selected'],base['scenarios']['selected'])
        self.assertTrue(analyses.references_available(derived));self.assertFalse(analyses.references_available(base))
        self.assertEqual(solver.call_count,len(analyses.expected_references(base)-set(base['scenarios'])))
        self.assertEqual(derived['scenarios']['min_trips'],base['scenarios']['min_trips'])

    def test_balanced_essential_reuses_all_persisted_references(self):
        base=run_assignment_engine(self.orders,self.fleet,{'objective':'balanced'},self.options)
        self.assertTrue(analyses.references_available(base))
        with patch('app.engines.assignment.engine.solve',side_effect=AssertionError('Unexpected recalculation')):
            derived=run_assignment_engine(self.orders,self.fleet,{k:v for k,v in base['configuration'].items() if k!='options'},
                {**base['configuration']['options'],'analysis_depth':'comparative'},reference_result=base)
        self.assertEqual(derived['scenarios'],base['scenarios'])

    def test_mismatched_configuration_cannot_anchor_another_decision(self):
        base=run_assignment_engine(self.orders,self.fleet,{'objective':'min_trips'},self.options)
        with self.assertRaisesRegex(ValueError,'configuración'):
            run_assignment_engine(self.orders,self.fleet,{'objective':'balanced'},
                {**base['configuration']['options'],'analysis_depth':'comparative'},reference_result=base)

    def test_progressive_runtime_reapplies_original_scope_and_resource_policy(self):
        from app.engines.assignment import run_assignment_engine as runtime
        options={**self.options,'resource_mode':'own'}
        base=runtime(self.orders,self.fleet,{'objective':'min_trips','scope':{'filters':[{'column':'quantity_units','type':'number','operator':'between','value':[1,100]}]}},options)
        derived=runtime(self.orders,self.fleet,{k:v for k,v in base['configuration'].items() if k!='options'},
            {**base['configuration']['options'],'analysis_depth':'comparative'},base['inputs'],reference_result=base)
        self.assertEqual(derived['inputs'],base['inputs']);self.assertEqual(derived['scope'],base['scope'])
        self.assertEqual(derived['resource_policy'],base['resource_policy'])
        self.assertEqual(derived['scenarios']['selected'],base['scenarios']['selected'])


class ProgressiveServiceTests(unittest.IsolatedAsyncioTestCase):
    def base(self,depth='essential'):
        row=json.loads((Path(__file__).parent/'browser/fixtures.json').read_text())['runs']['assignment']
        row['id']=str(uuid4());row['result_json']['analysis']['depth']=depth
        row['result_json']['configuration']['options']['analysis_depth']=depth
        return row

    async def test_endpoint_requires_auth_and_rejects_unknown_unfinished_and_unsupported_base(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
            run_id=str(uuid4())
            self.assertEqual((await c.post('/api/runs/'+run_id+'/comparative')).status_code,401)
            app.dependency_overrides[require_upload_access]=lambda:'dation'
            try:
                for row,status in [(None,404),({'status':'running'},409),({'status':'completed','schema_version':'scheduling_v1'},422)]:
                    with patch.object(analyses,'get_run',AsyncMock(return_value=row)),patch.object(analyses.dispatch,'db',AsyncMock()) as db:
                        for method in ['GET','POST']:
                            r=await c.request(method,'/api/runs/'+run_id+'/comparative')
                            self.assertEqual(r.status_code,status,r.text)
                        db.assert_not_awaited()
            finally:app.dependency_overrides.clear()

    async def test_admission_reconstructs_configuration_and_only_depth_changes(self):
        base=self.base();before=copy.deepcopy(base)
        artifact={'id':str(uuid4()),'base_run_id':base['id'],'status':'completed'}
        with patch.object(analyses,'get_run',AsyncMock(return_value=base)),patch.object(analyses.dispatch,'db',AsyncMock(return_value=[artifact])) as db:
            await analyses.generate_analysis(base['id'])
        body=db.call_args.kwargs['body'];request=body['job_request']
        self.assertEqual(request['configuration'],{k:v for k,v in base['result_json']['configuration'].items() if k!='options'})
        self.assertEqual(request['options'],{**base['result_json']['configuration']['options'],'analysis_depth':'comparative'})
        self.assertEqual(body['existing_result'],base['result_json']);self.assertEqual(base,before)
        self.assertFalse(any('decision_runs'==call.args[1] for call in db.await_args_list))

    async def test_existing_comparative_does_not_create_another_artifact(self):
        base=self.base('comparative')
        with patch.object(analyses,'get_run',AsyncMock(return_value=base)),patch.object(analyses.dispatch,'db',AsyncMock(return_value=[])) as db:
            result=await analyses.generate_analysis(base['id'])
        self.assertEqual(result['status'],'completed');self.assertEqual(result['source_mode'],'original')
        self.assertTrue(all(call.args[0]=='GET' for call in db.await_args_list))

    async def test_enriched_evidence_is_copied_and_never_changes_primary_result(self):
        base=self.base();before=copy.deepcopy(base)
        derived=copy.deepcopy(base['result_json']);derived.setdefault('sensitivity',{}).setdefault('frontier',[]).append({'scenario':'additional','metrics':{'total_trips':3}})
        with patch.object(analyses.dispatch,'db',AsyncMock(return_value=[{'id':'evidence','result_json':derived}])):
            result,identifier=await analyses.completed_evidence(base)
        self.assertEqual(identifier,'evidence');self.assertEqual(base,before)
        self.assertEqual(result['scenarios']['selected'],base['result_json']['scenarios']['selected'])
        self.assertEqual(result['sensitivity'],derived['sensitivity'])

    async def test_invalid_companion_cannot_redefine_primary_selection(self):
        base=self.base();derived=copy.deepcopy(base['result_json']);derived['scenarios']['selected']['name']='Different decision'
        with patch.object(analyses.dispatch,'db',AsyncMock(return_value=[{'id':'evidence','result_json':derived}])):
            with self.assertRaises(RuntimeError):await analyses.completed_evidence(base)

    async def test_chat_uses_persisted_comparative_and_records_scope_captured_before_provider(self):
        base=self.base();before=copy.deepcopy(base);artifact=copy.deepcopy(base['result_json'])
        artifact.setdefault('sensitivity',{})['frontier']=[{'scenario':'persisted-new-reference','label':'Referencia guardada','metrics':{'total_trips':3}}]
        evidence_id=str(uuid4());turn=str(uuid4())
        response={'provider':'qa','model':'qa','content':'La recomendación original se conserva.','usage':{}}
        with patch.object(interpreter.dispatch,'db',AsyncMock(side_effect=[None,[{'id':evidence_id,'result_json':artifact}],{'answer':response['content'],'evidence_analysis_id':evidence_id}])) as db,\
             patch.object(interpreter,'_load_completed_run',AsyncMock(return_value=base)),\
             patch.object(interpreter,'_recent_messages',AsyncMock(return_value=[])),\
             patch.object(interpreter,'chat_completion',AsyncMock(return_value=response)) as provider:
            result=await interpreter.answer_question(run_id=base['id'],question='¿Qué muestran las referencias?',turn_id=turn)
        self.assertIn('persisted-new-reference',provider.call_args.kwargs['messages'][0]['content'])
        self.assertEqual(db.call_args.kwargs['body']['evidence_analysis_id'],evidence_id)
        self.assertEqual(result['evidence_analysis_id'],evidence_id);self.assertEqual(base,before)

    async def test_saved_original_explanation_is_marked_until_enriched_scope_is_generated(self):
        run_id=str(uuid4());evidence_id=str(uuid4());explanation_id=str(uuid4());turn_id=str(uuid4())
        source_id=None
        async def handle(request):
            if request.url.path.endswith('/current_decision_explanation'):
                return httpx.Response(200,json=[{'id':explanation_id,'response_json':{'summary':'original'}}])
            if request.url.path.endswith('/decision_messages'):
                return httpx.Response(200,json=[{'turn_id':turn_id,'role':'assistant','content':'original'}])
            if request.url.path.endswith('/decision_interpretation_sources'):
                return httpx.Response(200,json=[{'explanation_id':explanation_id,'analysis_id':source_id},{'chat_turn_id':turn_id,'analysis_id':None}])
            return httpx.Response(200,json=[{'id':evidence_id,'source_mode':'computed'}])
        @asynccontextmanager
        async def client():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handle),base_url='https://qa.test') as http:yield http
        with patch.object(interpreter,'SUPABASE_URL','https://qa.test'),patch.object(interpreter,'http_client',client):
            original=await interpreter.get_saved_interpretation(run_id)
            self.assertFalse(original['explanation_is_current']);self.assertEqual(original['current_evidence_analysis_id'],evidence_id)
            source_id=evidence_id
            enriched=await interpreter.get_saved_interpretation(run_id)
            self.assertTrue(enriched['explanation_is_current']);self.assertIsNone(enriched['messages'][0]['evidence_analysis_id'])
