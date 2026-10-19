"""First run and demo use real tenant data, Storage, SQL, API and worker."""
import hashlib,json,os,subprocess,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
import httpx
from auth_fixture import USER_A,USER_B,VIEWER
from sandbox import Sandbox
import test_workflow as workflow

class OnboardingTests(unittest.TestCase):
 checked=workflow.WorkflowTests.checked
 upload=workflow.WorkflowTests.upload
 body=workflow.WorkflowTests.body
 admit=workflow.WorkflowTests.admit
 finish=workflow.WorkflowTests.finish
 approve=workflow.WorkflowTests.approve
 @classmethod
 def setUpClass(cls):
  cls.s=Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
 def setUp(self):
  self.s.stop(self.s.worker);self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,dation_private.workspace_onboarding,audit_events,dation_private.dataset_uploads,dation_private.dataset_deletions CASCADE;')
  self.s.sql("UPDATE workspace_ddas SET status='enabled' WHERE dda_id='logistics';")
  self.a=self.s.api_client
 def progress(self,client=None):return self.checked((client or self.a).get('/api/platform/onboarding'))
 def sample(self):return self.checked(self.a.post('/api/platform/onboarding/demo',json={}))
 def make_case(self,data):
  cid=str(uuid4());self.checked(self.a.post('/api/decision-cases',json={'id':cid,'orders_dataset_id':data['orders']['id'],'fleet_dataset_id':data['fleet']['id']}));return cid
 def test_01_personal_exploration_is_idempotent_and_tenant_authorized(self):
  data=self.progress();self.assertTrue(data['workspace_created']);self.assertFalse(data['data_ready']);self.assertFalse(data['first_decision_completed']);self.assertIsNone(data['explored_at'])
  before=self.s.sql("SELECT count(*) FROM audit_events;");self.progress();self.assertEqual(self.s.sql('SELECT count(*) FROM dation_private.workspace_onboarding;'),'0');self.assertEqual(self.s.sql('SELECT count(*) FROM audit_events;'),before)
  first=self.checked(self.a.post('/api/platform/onboarding/explore',json={}));second=self.checked(self.a.post('/api/platform/onboarding/explore',json={}));self.assertEqual(first['explored_at'],second['explored_at'])
  self.assertEqual(self.a.post('/api/platform/onboarding/explore',json={'actor_user_id':USER_B}).status_code,422)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
   self.assertIsNone(self.progress(viewer)['explored_at']);self.checked(viewer.post('/api/platform/onboarding/explore',json={}));self.assertEqual(viewer.post('/api/platform/onboarding/demo',json={}).status_code,403)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as other:self.assertIsNone(self.progress(other)['explored_at'])
  self.assertEqual(self.a.get('/api/platform/onboarding',headers={'X-Dation-Workspace-Id':self.s.workspace_b}).status_code,403)
  self.assertEqual(self.s.db.post('rpc/platform_onboarding',json={'target_workspace_id':self.s.workspace_b,'actor_user_id':USER_A}).status_code,403)
  for name in ['platform_onboarding','platform_onboarding_explore']:
   for token in [self.s.anon_token,self.s.user_tokens[USER_A]]:self.assertIn(self.s.http.post(self.s.rest_url+'/rpc/'+name,headers={'Authorization':'Bearer '+token},json={}).status_code,(401,403,404))
  self.assertEqual(self.s.sql("SELECT has_table_privilege('service_role','dation_private.workspace_onboarding','SELECT');"),'f')
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  self.assertFalse(self.progress()['logistics_enabled']);self.checked(self.a.post('/api/platform/onboarding/explore',json={}))
  self.assertEqual(self.a.post('/api/platform/onboarding/demo',json={}).status_code,403)
 def test_02_sample_concurrency_preserves_default_and_existing_file_origin(self):
  default=self.upload('fleet');self.checked(self.a.post('/api/datasets/'+default['id']+'/default'))
  root=Path(__file__).resolve().parents[3];raw=(root/'sample_data/onboarding-v1/orders.csv').read_bytes()
  original=self.checked(self.a.post('/api/datasets/upload?dataset_type=orders',files={'file':('mis-pedidos.csv',raw,'text/csv')}))['dataset'];self.assertFalse(original['is_sample'])
  with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:self.a.post('/api/platform/onboarding/demo',json={}),range(2)))
  self.assertTrue(all(r.status_code in (200,409) for r in responses),[(r.status_code,r.text[:300]) for r in responses]);data=self.sample()
  self.assertEqual(data['orders']['id'],original['id']);self.assertFalse(data['orders']['is_sample']);self.assertEqual(data['orders']['original_filename'],'mis-pedidos.csv');self.assertTrue(data['fleet']['is_sample']);self.assertFalse(data['fleet']['is_default'])
  self.assertEqual(self.s.sql("SELECT id FROM datasets WHERE is_default;"),default['id']);self.assertEqual(self.s.sql('SELECT count(*) FROM datasets;'),'3')
  counts=self.s.sql("SELECT (SELECT count(*) FROM audit_events)||':'||(SELECT count(*) FROM datasets);");self.sample();self.assertEqual(self.s.sql("SELECT (SELECT count(*) FROM audit_events)||':'||(SELECT count(*) FROM datasets);"),counts)
  self.assertEqual(self.s.sql("SELECT count(*) FROM dation_private.dataset_uploads WHERE status IN('pending','failed','discarding');"),'0')
  self.assertEqual(sum(path.is_file() for path in self.s.storage.rglob('*')),3)
  self.assertEqual(data['orders']['row_count'],4);self.assertEqual(data['fleet']['row_count'],2);self.assertEqual(data['orders']['sha256'],hashlib.sha256(raw).hexdigest())
  cid=self.make_case(data);detail=self.checked(self.a.get('/api/platform/decisions/'+cid));self.assertTrue(detail['is_demo']);self.assertTrue(detail['fleet']['is_demo']);self.assertFalse(detail['orders']['is_demo'])
  home=self.checked(self.a.get('/api/platform/home'));self.assertTrue(home['recent_cases'][0]['is_demo']);self.assertTrue(home['activity']['items'][0]['is_demo']);self.assertTrue(home['onboarding']['data_ready']);self.assertFalse(home['onboarding']['first_decision_completed'])
  self.checked(self.a.post('/api/datasets/'+data['orders']['id']+'/archive'));self.assertEqual(self.a.post('/api/platform/onboarding/demo',json={}).status_code,409)
  self.assertEqual(self.s.sql("SELECT count(*) FROM datasets WHERE id='"+original['id']+"' AND archived_at IS NOT NULL;"),'1')
 def test_03_golden_pack_runs_both_real_decisions_and_remains_demo(self):
  data=self.sample();cid=self.make_case(data);self.s.start_worker();rid=self.admit(self.body(cid,data['orders'],data['fleet']));self.finish(rid);self.approve(rid,cid)
  sid=self.admit(self.body(cid,data['orders'],data['fleet'],node='logistics_scheduling',source=rid));self.finish(sid);self.approve(sid,cid,'logistics_scheduling');self.s.stop(self.s.worker)
  progress=self.progress();self.assertTrue(progress['first_decision_completed']);self.assertTrue(progress['first_decision_demo']);self.assertTrue(progress['data_includes_demo'])
  self.assertTrue(self.checked(self.a.get('/api/platform/decisions/'+cid))['is_demo']);self.assertEqual(self.s.sql('SELECT count(*) FROM decision_approval_events;'),'2')
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  progress=self.progress();self.assertFalse(progress['logistics_enabled']);self.assertFalse(progress['data_ready']);self.assertFalse(progress['first_decision_completed']);self.assertEqual(self.a.post('/api/platform/onboarding/demo',json={}).status_code,403)
 def test_04_browser_first_run_empty_states_demo_and_recovery(self):
  root=Path(__file__).resolve().parents[2]
  r=subprocess.run([str(root/'.browser-venv/bin/python'),str(root/'tests/e2e/onboarding_journey.py')],cwd=root,env={**self.s.env,'DATION_E2E_URL':self.s.api_url},capture_output=True,text=True,timeout=180)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
