"""Real isolated API/PostgreSQL/Storage/worker D1 -> human approval -> D2."""
import json,sys,unittest
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from ultimate_result_fixture import ResultSandbox
from ultimate_result_helpers import ok,submit,wait_run,row,endpoint,approval,intention
from test_ultimate_d2_lineage import day_submit
from auth_fixture import USER_A
from app.domain.logistics.data_contracts import compile_contract
from app.results.canonical import core_result_fingerprint
from app.results.contracts import EngineCoreResult
from tests.saga10_fixtures import catalog_config
from tests.test_saga10_data_contracts import csv_bytes,sample_rows


class Saga10ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=ResultSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
        cls.s.sql('UPDATE dation_private.platform_release SET saga10_schema_enabled=true,saga10_ui_enabled=true,saga10_optimization_enabled=true,ultimate_scheduling_admissions_enabled=true;')
    def tearDown(self):
        self.s.stop(self.s.worker,kill=True)
        error=self.s.storage/'t8-rpc-errors.jsonl'
        if error.exists():Path('/tmp/saga10-g4-rpc-errors.log').write_text(error.read_text())
    def setup_case(self):
        a=self.s.api_client
        m=ok(a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'Catálogo ejecución local','configuration':catalog_config()}))['model']
        v=ok(a.post('/api/platform/logistics-models/'+m['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))['version']
        case=ok(a.post('/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'Case ejecución local','logistics_model_version_id':v['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}))['case'];cid=case['id'];base='/api/platform/logistics-cases/'+cid
        ok(a.put('/api/platform/decisions/'+cid+'/responsibilities/data_owner',json={'expected_updated_at':None,'owner_user_id':USER_A}))
        state=ok(a.get(base+'/data'));selection=[]
        for entity in ['transport_demand','order_lines','transport_resources']:
            contract=compile_contract(v,entity);rows=sample_rows(contract)[:1]
            if entity=='order_lines':rows=[{'order_id':'ORD-001','presentation_id':'PAL-JUICE','quantity':'20'}]
            elif entity=='transport_resources':
                rows[0].update(guaranteed_pallets='26',guaranteed_weight_kg='30000',guaranteed_volume_m3='60',guaranteed_units='30000')
            upload=ok(a.post(base+'/data/uploads/'+entity,params={'upload_id':str(uuid4()),'contract_hash':contract.contract_hash},files={'file':('local.csv',csv_bytes(contract,rows),'text/csv')}))
            selection.append({'slot_key':entity,'upload_id':upload['id']})
        ok(a.post(base+'/data/publish',json={'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':selection}))
        return cid
    def test_01_exact_runtime_read_set_worker_publication_approval_and_D2(self):
        cid=self.setup_case();a=self.s.api_client;ctx=ok(a.get('/api/platform/logistics-cases/'+cid+'/run-context'))
        self.assertEqual(ctx['runtime_profile'],'transport_plan_cargo_v2');self.assertEqual(len(ctx['context']['read_set']),3)
        rid,body,response=submit(self.s,cid);ok(response)
        job=json.loads(self.s.sql("SELECT request_json FROM dispatch_run_jobs WHERE run_id='"+rid+"';"))
        self.assertEqual((job['engine_version'],job['runtime_profile']),('3.0.0','transport_plan_cargo_v2'))
        self.assertEqual(len(job['entries']),3);self.assertEqual(len(job['input']['demands'][0]['lines']),1)
        self.s.start_worker();done=wait_run(self.s,rid)
        self.assertEqual(done['result_json']['metrics']['demand_coverage']['assigned'],'20')
        self.assertEqual(ok(endpoint(self.s,rid,'approval-review'))['approval_overlay']['approval_allowed'],True)
        ok(approval(self.s,cid,rid));before=row(self.s,rid)
        child,_,response=day_submit(self.s,cid);ok(response);downstream=wait_run(self.s,child)
        self.assertEqual(downstream['upstream_run_id'],rid);self.assertEqual(row(self.s,rid),before)
        parent_core=self.read_core(rid);child_core=self.read_core(child)
        self.assertEqual(child_core['schedule']['cargo'],parent_core['transport_plan']['cargo'])
        self.assertEqual(parent_core['transport_plan']['cargo']['lines'][0]['assigned'],'20')
        self.assertEqual(self.s.sql("SELECT dation_private.t9_core_hash('"+json.dumps(parent_core).replace("'","''")+"'::jsonb);"),core_result_fingerprint(EngineCoreResult.model_validate(parent_core)))
        graph=ok(a.get('/api/platform/logistics-cases/'+cid+'/graph'))['graph'];self.assertEqual(graph['nodes'][0]['node_state'],'APPROVED')
        self.assertIn('order_lines',graph['nodes'][0]['read_set'])
    def read_core(self,rid):
        run=row(self.s,rid);ref=next(x for x in run['result_json']['artifact_manifest']['artifacts'] if x['kind']=='CORE')
        return json.loads((self.s.storage/'dda-inputs'/self.s.workspace_a/'runs'/rid/'core'/ref['part_key']/(ref['content_sha256']+'.json')).read_text())['rows'][0]
    def test_02_independent_optimization_gate_blocks_admission_and_worker(self):
        cid=self.setup_case();rid,_,response=submit(self.s,cid);ok(response)
        self.s.sql('UPDATE dation_private.platform_release SET saga10_optimization_enabled=false;')
        try:
            ctx=ok(self.s.api_client.get('/api/platform/logistics-cases/'+cid+'/run-context'));self.assertFalse(ctx['admission_available'])
            _,_,response=submit(self.s,cid);self.assertEqual(response.status_code,403,response.text)
            # Preserve worker's NULL actor contract, but reject this closed v2
            # before producing or publishing any result.
            response=self.s.db.post('rpc/platform_ultimate_execution',json={'target_workspace_id':self.s.workspace_a,'actor_user_id':None,'operation':'prepared','arguments':{'run_id':rid,'worker_token':str(uuid4())}})
            self.assertEqual(response.status_code,403,response.text);self.assertIn('Saga10 optimization closed',response.text)
            self.assertEqual(self.s.sql("SELECT count(*) FROM decision_result_artifacts WHERE run_id='"+rid+"';"),'0')
        finally:self.s.sql('UPDATE dation_private.platform_release SET saga10_optimization_enabled=true;')
    def test_03_migration_idempotence_and_private_permissions(self):
        migration=next((Path(__file__).resolve().parents[3]/'supabase/migrations').glob('*_saga10_cargo_execution.sql'));self.s.sql(migration.read_text())
        self.assertEqual(self.s.sql("SELECT has_function_privilege('service_role','dation_private.saga10_execution_v1(uuid,uuid,text,jsonb)','EXECUTE');"),'f')
        self.assertEqual(self.s.sql("SELECT has_function_privilege('authenticated','public.platform_ultimate_execution(uuid,uuid,text,jsonb)','EXECUTE');"),'f')
