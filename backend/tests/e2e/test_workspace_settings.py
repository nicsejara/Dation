"""Settings and universal Free policy over the final schema and real API/worker."""
import json,os,subprocess,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from auth_fixture import USER_A,USER_B,VIEWER,DISABLED
from sandbox import Sandbox
import test_workflow as workflow

class WorkspaceSettingsTests(unittest.TestCase):
 checked=workflow.WorkflowTests.checked
 upload=workflow.WorkflowTests.upload
 case=workflow.WorkflowTests.case
 body=workflow.WorkflowTests.body
 admit=workflow.WorkflowTests.admit
 finish=workflow.WorkflowTests.finish
 approve=workflow.WorkflowTests.approve
 @classmethod
 def setUpClass(cls):
  cls.s=Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
 def setUp(self):
  self.s.stop(self.s.worker);self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events CASCADE;')
  self.s.sql(f"UPDATE workspace_members SET access_role='viewer',status='active' WHERE user_id='{VIEWER}'; UPDATE workspaces SET name=CASE WHEN id='{self.s.workspace_a}' THEN 'Dation' ELSE 'Workspace B' END,country='AR',language='es',timezone='UTC',currency='ARS',weight_unit='kg',distance_unit='km',logistics_unit='units',updated_at=clock_timestamp(); UPDATE workspace_ddas SET status='enabled' WHERE dda_id='logistics';")
  self.a=self.s.api_client
  self.b=httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False,timeout=30);self.addCleanup(self.b.close)
 def settings(self,client=None):return self.checked((client or self.a).get('/api/platform/settings'))
 def change(self,section='general',client=None,version=None,**changes):
  row=self.settings(client)['workspace'];fields=['name','country','language','timezone'] if section=='general' else ['currency','weight_unit','distance_unit','logistics_unit']
  return (client or self.a).patch('/api/platform/settings',json={'section':section,'expected_updated_at':version or row['updated_at'],**{key:row[key] for key in fields},**changes})
 def test_01_free_for_existing_and_new_workspaces_secure_validation_and_reads(self):
  a,b=self.settings(),self.settings(self.b)
  for data in (a,b):
   self.assertEqual(data['plan'],{'code':'free','name':'Free','status':'active','price_amount':0,'billing_mode':'free','requires_payment_method':False,'trial_ends_at':None,'member_limit':None})
  self.assertEqual(a['members']['active'],2);self.assertEqual(a['members']['total'],3)
  before=self.s.sql("SELECT md5(string_agg(to_jsonb(w)::text,'' ORDER BY id)) FROM workspaces w;")
  self.settings();self.assertEqual(self.s.sql("SELECT md5(string_agg(to_jsonb(w)::text,'' ORDER BY id)) FROM workspaces w;"),before)
  version=a['workspace']['updated_at'];self.checked(self.change(name='  Equipo Chile  ',country='CL',language='en',timezone='America/Santiago'))
  current=self.settings()['workspace'];self.assertEqual(current['name'],'Equipo Chile');self.assertEqual(current['currency'],'ARS');self.assertEqual(self.settings(self.b)['workspace'],b['workspace'])
  self.assertEqual(self.change(version=version,name='Stale').status_code,409)
  self.checked(self.change('operation',currency='CLP',weight_unit='t',distance_unit='mi',logistics_unit='pallets'))
  self.assertEqual(self.settings()['workspace']['name'],'Equipo Chile');self.assertEqual(self.settings()['plan'],a['plan'])
  for fields in [{'country':'ZZ'},{'timezone':'invalid/zone'},{'name':' '},{'language':'xx'},{'plan_code':'paid'},{'workspace_id':self.s.workspace_b}]:self.assertEqual(self.change(**fields).status_code,422)
  for fields in [{'currency':'XXX'},{'weight_unit':'lb'},{'distance_unit':'lightyear'},{'logistics_unit':'invalid'}]:self.assertEqual(self.change('operation',**fields).status_code,422)
  for rpc in ['platform_workspace_settings','platform_update_workspace']:
   for credential in [self.s.anon_token,self.s.user_tokens[USER_A]]:
    response=self.s.http.post(self.s.rest_url+'/rpc/'+rpc,headers={'Authorization':'Bearer '+credential},json={});self.assertIn(response.status_code,(401,403,404))
  response=self.s.db.post('rpc/platform_update_workspace',json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_A,'expected_updated_at':self.settings()['workspace']['updated_at'],'section_name':'plan','changes':{'code':'paid'}});self.assertEqual(response.status_code,400)
  self.assertEqual(self.a.get('/api/platform/settings',headers={'X-Dation-Workspace-Id':self.s.workspace_b}).status_code,403)
  self.assertEqual(self.s.sql(f"SELECT count(*) FROM audit_events WHERE event_type='workspace.settings_updated' AND workspace_id='{self.s.workspace_a}';"),'2')
 def test_02_admin_browser_preferences_free_plan_and_historical_evidence(self):
  case,orders,fleet=self.case();self.s.start_worker();run=self.admit(self.body(case,orders,fleet));self.finish(run);self.approve(run,case);self.s.stop(self.s.worker)
  sql="SELECT jsonb_build_object('runs',(SELECT md5(string_agg(to_jsonb(t)::text,'' ORDER BY id)) FROM decision_runs t),'datasets',(SELECT md5(string_agg(to_jsonb(t)::text,'' ORDER BY id)) FROM datasets t),'approvals',(SELECT md5(string_agg(to_jsonb(t)::text,'' ORDER BY id)) FROM decision_approval_events t));"
  before=self.s.sql(sql);root=Path(__file__).resolve().parents[2]
  result=subprocess.run([str(root/'.browser-venv/bin/python'),str(root/'tests/e2e/workspace_settings_journey.py')],cwd=root,env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_SETTINGS_CASE':case,'DATION_SETTINGS_RUN':run},capture_output=True,text=True,timeout=180)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(self.s.sql(sql),before)
  after=self.settings();self.assertEqual(after['workspace']['currency'],'CLP');self.assertEqual(after['workspace']['country'],'CL');self.assertEqual(after['plan']['code'],'free')
 def test_03_roles_concurrency_and_dda_status_are_independent_of_free(self):
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
   self.assertEqual(viewer.get('/api/platform/settings').status_code,200);self.assertEqual(self.change(client=viewer,name='No').status_code,403)
   self.s.sql(f"UPDATE workspace_members SET access_role='operator' WHERE user_id='{VIEWER}';")
   self.assertEqual(viewer.get('/api/platform/settings').status_code,200);self.assertEqual(self.change(client=viewer,name='No').status_code,403)
  version=self.settings()['workspace']['updated_at']
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(lambda name:self.change(version=version,name=name).status_code,['Primero','Segundo']))
  self.assertEqual(sorted(statuses),[200,409])
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics'; UPDATE workspace_ddas SET status='enabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='production';")
  self.assertEqual(self.a.get('/api/datasets').status_code,403);self.assertEqual(self.settings()['plan']['code'],'free');self.checked(self.change(name='Sin grant'))
  self.assertEqual(self.s.db.post('rpc/platform_workspace_settings',json={'target_workspace_id':self.s.workspace_b,'actor_user_id':VIEWER}).status_code,403)
  self.s.sql(f"UPDATE workspace_members SET status='disabled' WHERE user_id='{VIEWER}';")
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:self.assertEqual(viewer.get('/api/platform/settings').status_code,403)
