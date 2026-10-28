"""Focal HTTP proof for a SQL-seeded empty Ultimate Case, never a T3 creation API."""
import hashlib,json,os,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4

ROOT=Path('/workspace/Dation');OUT=Path('/workspace/work/dation-t2')
sys.path.insert(0,str(ROOT/'backend/tests/e2e'))
from sandbox import Sandbox
from auth_fixture import USER_A,USER_B,VIEWER


class EmptyUltimateAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
        cls.c,mid,mv,pack,version=[str(uuid4()) for _ in range(5)];w=cls.s.workspace_a;h='a'*64
        cls.s.sql(f"""BEGIN;
         INSERT INTO dation_private.decision_definition_versions(version,definition_hash,definition_jsonb) VALUES('ULTIMATE_GRAPH_V1','{h}','{{}}');
         INSERT INTO logistics_models(id,workspace_id,name,created_by) VALUES('{mid}','{w}','Fixture SQL','{USER_A}');
         INSERT INTO logistics_model_versions(id,workspace_id,model_id,version,graph_definition_version,config_schema_version,
          config_jsonb,contract_descriptor_jsonb,config_hash,contract_hash,contract_registry_version,published_by)
          VALUES('{mv}','{w}','{mid}',1,'ULTIMATE_GRAPH_V1','logistics_model_v1','{{}}','{{}}','{h}','{h}','SEMANTIC_FIELDS_V1','{USER_A}');
         INSERT INTO decision_cases(id,workspace_id,workflow_version,logistics_model_version_id,planning_start,planning_end,
          operating_mode,case_policy_schema_version,case_policy_jsonb,case_policy_hash,graph_definition_version,label)
          VALUES('{cls.c}','{w}',2,'{mv}','2026-11-02','2026-11-08','OPERATIONAL','case_policy_v1',
          '{{"version":1,"primary_goal":"MINIMIZE_COST"}}','{h}','ULTIMATE_GRAPH_V1','Case vacío T2');
         INSERT INTO case_data_packs(id,workspace_id,case_id) VALUES('{pack}','{w}','{cls.c}');
         INSERT INTO case_data_pack_versions(id,workspace_id,case_id,pack_id,version,manifest_hash,contract_set_hash,created_by)
          VALUES('{version}','{w}','{cls.c}','{pack}',1,'{h}','{h}','{USER_A}');
         UPDATE case_data_packs SET current_version_id='{version}' WHERE id='{pack}';
         COMMIT;""")

    def checked(self,path):
        response=self.s.api_client.get(path)
        self.assertEqual(response.status_code,200,response.text[:2000]);return response.json()

    def test_case_detail_list_and_history_accept_real_null_references(self):
        before=self.s.sql(f"SELECT md5(to_jsonb(c)::text) FROM decision_cases c WHERE id='{self.c}';")
        detail=self.checked('/api/decision-cases/'+self.c)
        self.assertIsNone(detail['orders']);self.assertIsNone(detail['fleet'])
        self.assertIsNone(detail['decision_case']['signature'])
        self.assertEqual(detail['decision_case']['nodes']['logistics_assignment']['status'],'needs_data')
        for summary in ('false','true'):
            self.assertIn(self.c,[r['case']['id'] for r in self.checked('/api/decision-cases?summary='+summary)['cases']])
        self.assertEqual(self.checked('/api/decision-cases/'+self.c+'/runs')['runs'],[])
        self.assertEqual(self.s.sql(f"SELECT md5(to_jsonb(c)::text) FROM decision_cases c WHERE id='{self.c}';"),before)

    def test_home_center_and_hub_do_not_hide_or_simulate_the_case(self):
        self.assertIn(self.c,[r['case_id'] for r in self.checked('/api/platform/home')['recent_cases']])
        listing=self.checked('/api/platform/decisions')
        self.assertIn(self.c,[r['id'] for r in listing['items']])
        detail=self.checked('/api/platform/decisions/'+self.c)
        self.assertIsNone(detail['resume']);self.assertIsNone(detail['orders']);self.assertIsNone(detail['fleet'])
        self.assertEqual(detail['progress'],dict(approved=0,total=2))
        self.assertEqual(self.checked('/api/platform/data/packs')['items'],[])

    def test_tenant_and_viewer_boundaries_survive_empty_context(self):
        import httpx
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as other:
            self.assertEqual(other.get('/api/decision-cases/'+self.c).status_code,404)
            self.assertEqual(other.get('/api/platform/decisions/'+self.c).status_code,404)
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
            self.assertEqual(viewer.get('/api/decision-cases/'+self.c).status_code,200)
            self.assertEqual(viewer.patch('/api/decision-cases/'+self.c,json={'state':{}}).status_code,403)

    def test_legacy_writes_and_unimplemented_creation_stay_closed(self):
        before=self.s.sql(f"SELECT md5(to_jsonb(c)::text) FROM decision_cases c WHERE id='{self.c}';")
        response=self.s.api_client.patch('/api/decision-cases/'+self.c,json={'state':{'nodes':{}}})
        self.assertIn(response.status_code,(400,409,422),response.text[:1000])
        response=self.s.api_client.post('/api/decision-cases',json={'id':str(uuid4()),'workflow_version':2})
        self.assertEqual(response.status_code,422)
        self.assertEqual(self.s.sql(f"SELECT md5(to_jsonb(c)::text) FROM decision_cases c WHERE id='{self.c}';"),before)


if __name__=='__main__':
    for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:
        os.environ[key]=''
    for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:
        os.environ.pop(key,None)
    os.environ['DATION_E2E_ARTIFACTS']=str(OUT/'empty-case-api')
    started=datetime.now(timezone.utc).isoformat();begin=time.monotonic()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(EmptyUltimateAPI)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record=dict(suite='FOCAL-EMPTY-API',status='PASS' if result.wasSuccessful() and result.testsRun and not result.skipped else 'FAIL',
        tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),seconds=round(time.monotonic()-begin,3),
        command=[sys.executable,'-B','/tmp/dation-t2-empty-case-smoke.py'],cwd=str(ROOT),production_credentials_cleared=True,
        test_ids=[t.id() for t,_ in result.failures+result.errors],no_public_Ultimate_creation=True)
    (OUT/'FOCAL-EMPTY-API.result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record));sys.exit(0 if record['status']=='PASS' else 1)
