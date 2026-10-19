"""Activity must describe committed actions, including the real worker and exports."""
import hashlib,json,os,subprocess,unittest
from pathlib import Path
from uuid import uuid4
import httpx
from auth_fixture import USER_A,USER_B,VIEWER
from sandbox import Sandbox
import test_workflow as workflow

class ActivityTests(unittest.TestCase):
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
  self.s.stop(self.s.worker);self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,dation_private.dataset_uploads,dation_private.dataset_deletions,audit_events CASCADE;')
  self.s.sql("UPDATE workspace_ddas SET status='enabled' WHERE dda_id='logistics';")
  self.a=self.s.api_client
 def activity(self,**params):return self.checked(self.a.get('/api/platform/activity',params=params))
 def test_01_committed_data_events_immutable_isolated_and_keyset(self):
  case,orders,fleet=self.case();events=self.activity(limit=50)['items'];kinds=[e['event_type'] for e in events]
  self.assertEqual(kinds.count('dataset.uploaded'),2);self.assertEqual(kinds.count('dataset.validated'),2);self.assertEqual(kinds.count('decision_case.created'),1)
  self.assertTrue(all(e['actor']['id']==USER_A for e in events));self.assertTrue(all(e['case_id']==case for e in self.activity(case_id=case)['items']))
  first=self.activity(limit=2);cursor=first['next_cursor'];self.assertIsNotNone(cursor)
  self.checked(self.a.post('/api/platform/data/datasets/'+orders['id']+'/archive',headers={'X-Dation-Actor-Id':USER_B}))
  archived=self.activity()['items'][0];self.assertEqual(archived['event_type'],'dataset.archived');self.assertEqual(archived['actor']['id'],USER_A)
  self.checked(self.a.post('/api/platform/data/datasets/'+orders['id']+'/archive'))
  self.assertEqual(sum(e['event_type']=='dataset.archived' for e in self.activity(limit=50)['items']),1)
  next=self.activity(limit=2,**cursor);self.assertFalse({e['id'] for e in first['items']} & {e['id'] for e in next['items']})
  self.assertEqual(self.a.delete('/api/platform/data/datasets/'+orders['id']).status_code,409)
  self.assertNotIn('dataset.deleted',[e['event_type'] for e in self.activity(limit=50)['items']])
  version=self.checked(self.a.get('/api/platform/decisions/'+case))['updated_at'];self.checked(self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':version,'archived':True}))
  self.assertEqual(self.activity(case_id=case)['items'][0]['event_type'],'decision_case.archived');self.assertEqual(self.activity(case_id=case)['items'][0]['actor']['id'],USER_A)
  stamp=self.s.sql("SELECT count(*)||':'||md5(string_agg(to_jsonb(e)::text,'' ORDER BY id)) FROM audit_events e;")
  self.activity();self.checked(self.a.get('/api/platform/home'));self.checked(self.a.get('/api/platform/decisions/'+case))
  self.assertEqual(self.s.sql("SELECT count(*)||':'||md5(string_agg(to_jsonb(e)::text,'' ORDER BY id)) FROM audit_events e;"),stamp)
  for method in ['patch','delete']:
   r=getattr(self.s.db,method)('audit_events',params={'id':'eq.'+events[0]['id']},**({'json':{'event_type':'forged'}} if method=='patch' else {}));self.assertGreaterEqual(r.status_code,400)
  self.assertEqual(self.s.sql("SELECT has_table_privilege('service_role','audit_events','TRUNCATE');"),'f')
  for token in [self.s.anon_token,self.s.user_tokens[USER_A]]:self.assertIn(self.s.http.post(self.s.rest_url+'/rpc/platform_activity',headers={'Authorization':'Bearer '+token},json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_A}).status_code,(401,403,404))
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as b:
   self.assertEqual(self.checked(b.get('/api/platform/activity'))['items'],[]);self.assertEqual(b.get('/api/platform/activity',params={'case_id':case}).status_code,404)
  self.assertEqual(self.a.get('/api/platform/activity?before_id='+str(uuid4())).status_code,422)
  self.s.sql(f"INSERT INTO audit_events(workspace_id,actor_user_id,event_type,metadata_json) VALUES('{self.s.workspace_a}','{USER_A}','workspace.settings_updated','{{\"secret\":\"do-not-disclose\",\"csv\":\"FULL-CSV\",\"section\":\"general\"}}');")
  self.assertNotIn('do-not-disclose',json.dumps(self.activity()));self.assertNotIn('FULL-CSV',json.dumps(self.activity()))
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  self.assertTrue(all(e['event_type'].startswith(('workspace.','member.')) for e in self.activity(limit=50)['items']))
  self.assertEqual(self.activity(case_id=case)['items'][0]['event_type'],'decision_case.archived')
 def test_02_real_worker_approval_and_generated_exports(self):
  case,orders,fleet=self.case();self.s.start_worker();rid=self.admit(self.body(case,orders,fleet));run=self.finish(rid);self.approve(rid,case);self.approve(rid,case)
  events=self.activity(case_id=case,limit=50)['items'];kinds=[e['event_type'] for e in events]
  for kind in ['run.queued','run.started','run.completed','decision.submitted','decision.approved']:self.assertEqual(kinds.count(kind),1,(kind,kinds))
  for e in events:
   if e['event_type'] in ['run.started','run.completed','decision.submitted']:self.assertIsNone(e['actor']);self.assertTrue(e['label'].startswith('El sistema '))
   else:self.assertEqual(e['actor']['id'],USER_A)
  old=str(uuid4());self.s.sql(f"ALTER TABLE audit_events DISABLE TRIGGER activity_enrich; INSERT INTO audit_events(id,workspace_id,actor_user_id,event_type,metadata_json,created_at) VALUES('{old}','{self.s.workspace_a}','{USER_A}','decision.approved','{{\"case_id\":\"{case}\",\"node_id\":\"logistics_assignment\",\"run_id\":\"{rid}\"}}','2025-01-01'); ALTER TABLE audit_events ENABLE TRIGGER activity_enrich;")
  old_hash=self.s.sql(f"SELECT md5(to_jsonb(e)::text) FROM audit_events e WHERE id='{old}';")
  legacy=next(e for e in self.activity(case_id=case,limit=50)['items'] if e['id']==old);self.assertEqual(legacy['object_id'],rid);self.assertEqual(legacy['case_id'],case);self.assertEqual(legacy['actor']['id'],USER_A)
  self.assertEqual(self.s.sql(f"SELECT md5(to_jsonb(e)::text) FROM audit_events e WHERE id='{old}';"),old_hash)
  before=self.s.sql("SELECT md5(string_agg(to_jsonb(r)::text,'' ORDER BY id)) FROM decision_runs r;")
  payload={'run_id':rid,'format':'csv','operation_id':str(uuid4())};r=self.a.post('/api/platform/activity/exports',json=payload);self.assertEqual(r.status_code,200,r.text[:200]);self.assertIn('assignment-recomendada.csv',r.headers['content-disposition']);self.assertTrue(r.content.startswith(b'\xef\xbb\xbf'))
  e=self.activity(case_id=case)['items'][0];self.assertEqual(e['event_type'],'export.generated');self.assertEqual(e['metadata']['sha256'],hashlib.sha256(r.content).hexdigest());self.assertEqual(e['metadata']['bytes'],len(r.content));self.assertNotIn('result_json',e['metadata'])
  self.assertEqual(self.a.post('/api/platform/activity/exports',json=payload).status_code,200)
  self.assertEqual(sum(e['event_type']=='export.generated' for e in self.activity(case_id=case,limit=50)['items']),1)
  self.assertEqual(self.a.post('/api/platform/activity/exports',json={**payload,'format':'json'}).status_code,409)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
   r=viewer.post('/api/platform/activity/exports',json={**payload,'format':'json','operation_id':str(uuid4())});self.assertEqual(r.status_code,200,r.text[:200]);self.assertEqual(r.json(),self.finish(rid)['result_json'])
   self.assertEqual(viewer.get('/api/platform/activity').status_code,200)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as b:self.assertEqual(b.post('/api/platform/activity/exports',json=payload).status_code,404)
  self.assertEqual(self.s.sql("SELECT md5(string_agg(to_jsonb(r)::text,'' ORDER BY id)) FROM decision_runs r;"),before)
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  self.assertEqual(self.a.post('/api/platform/activity/exports',json=payload).status_code,403)
 def test_03_browser_real_home_case_events_and_exports(self):
  case,orders,fleet=self.case();self.s.start_worker();rid=self.admit(self.body(case,orders,fleet));self.finish(rid);self.approve(rid,case);self.s.stop(self.s.worker)
  self.checked(self.a.patch('/api/platform/profile',json={'first_name':'Equipo <img src=x onerror=window.__bad=1>','last_name':'Auditoría'}))
  for i in range(6):
   detail=self.checked(self.a.get('/api/platform/decisions/'+case));self.checked(self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':detail['updated_at'],'label':'Caso de auditoría '+str(i)}))
  root=Path(__file__).resolve().parents[2]
  r=subprocess.run([str(root/'.browser-venv/bin/python'),str(root/'tests/e2e/activity_journey.py')],cwd=root,env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_ACTIVITY_CASE':case,'DATION_ACTIVITY_RUN':rid},capture_output=True,text=True,timeout=180)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)

 def test_04_failed_execution_is_system_event_without_error_contents(self):
  case,orders,fleet=self.case();file=self.s.storage/orders['storage_bucket']/orders['storage_path'];file.write_bytes(file.read_bytes()+b'\ncorrupted')
  rid=self.admit(self.body(case,orders,fleet));self.s.start_worker();self.finish(rid,status='error')
  events=self.activity(case_id=case,limit=50)['items'];failed=[e for e in events if e['event_type']=='run.failed'];self.assertEqual(len(failed),1);self.assertIsNone(failed[0]['actor']);self.assertEqual(failed[0]['metadata'],{'source':'system'})
  self.assertNotIn('decision.submitted',[e['event_type'] for e in events])
  response=self.a.post('/api/platform/activity/exports',json={'run_id':rid,'format':'csv','operation_id':str(uuid4())});self.assertEqual(response.status_code,422)
  self.assertNotIn('export.generated',[e['event_type'] for e in self.activity(case_id=case,limit=50)['items']])

 def test_05_deletion_and_new_workspace_are_real_audited_actions(self):
  row=self.upload('orders');self.checked(self.a.post('/api/platform/data/datasets/'+row['id']+'/archive'))
  self.checked(self.a.delete('/api/platform/data/datasets/'+row['id']));self.checked(self.a.delete('/api/platform/data/datasets/'+row['id']))
  events=self.activity(limit=50)['items'];deleted=[e for e in events if e['event_type']=='dataset.deleted'];self.assertEqual(len(deleted),1);self.assertEqual(deleted[0]['object_id'],row['id']);self.assertEqual(deleted[0]['actor']['id'],USER_A)
  self.assertFalse((self.s.storage/row['storage_bucket']/row['storage_path']).exists())
  uid=str(uuid4());self.s.sql(f"INSERT INTO auth.users VALUES('{uid}','activity-new@example.test',now());")
  new=self.checked(self.s.db.post('rpc/platform_create_workspace',json={'actor_user_id':uid,'workspace_name':'Nuevo workspace','workspace_country':'AR','workspace_timezone':'UTC','workspace_currency':'ARS'}))
  feed=self.checked(self.s.db.post('rpc/platform_activity',json={'target_workspace_id':new['workspace_id'],'actor_user_id':uid}))
  self.assertEqual([e['event_type'] for e in feed['items']],['workspace.created']);self.assertEqual(feed['items'][0]['actor']['id'],uid)
