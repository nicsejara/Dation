"""Decision Center across real tenant SQL/REST, API, worker and browser."""
import json,os,subprocess,unittest
from pathlib import Path
from uuid import uuid4
import httpx
from sandbox import Sandbox
from auth_fixture import USER_A,USER_B,VIEWER
import test_workflow as workflow

class DecisionCenterTests(unittest.TestCase):
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
  self.s.stop(self.s.worker)
  self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,dation_private.dataset_uploads,dation_private.dataset_deletions CASCADE;')
  self.s.sql("UPDATE workspace_ddas SET status='enabled' WHERE dda_id='logistics';")
  self.a=self.s.api_client
 def center(self,case=None):return self.checked(self.a.get('/api/platform/decisions'+('/'+case if case else '')))

 def test_01_case_library_labels_pagination_identity_and_isolation(self):
  case,orders,fleet=self.case();detail=self.center(case)
  self.assertEqual(detail['created_by']['id'],USER_A);self.assertIsNone(detail['owner']);self.assertEqual(detail['status'],'active')
  self.assertEqual(detail['nodes'][2]['status'],'coming_soon');self.assertIsNone(detail['nodes'][2]['target'])
  label='Despachos · <img src=x onerror=window.__bad=1>'
  result=self.checked(self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':detail['updated_at'],'label':label}))
  self.assertEqual(self.center(case)['label'],label)
  self.assertEqual(self.checked(self.a.get('/api/platform/home'))['recent_cases'][0]['label'],label)
  for q,expected in [('Despachos',1),('DC-'+case[:8],1),(case,1),("' OR true --",0),('%',0)]:
   self.assertEqual(self.checked(self.a.get('/api/platform/decisions',params={'q':q}))['total'],expected)
  stale=self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':detail['updated_at'],'archived':True})
  self.assertEqual(stale.status_code,409);self.assertEqual(self.center(case)['status'],'active')
  extra=self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':result['updated_at'],'owner_user_id':USER_B})
  self.assertEqual(extra.status_code,422)
  other=str(uuid4());self.checked(self.a.post('/api/decision-cases',json={'id':other,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}))
  page=self.checked(self.a.get('/api/platform/decisions?limit=1'));second=self.checked(self.a.get('/api/platform/decisions?limit=1&offset=1'))
  self.assertEqual(page['total'],2);self.assertNotEqual(page['items'][0]['id'],second['items'][0]['id'])
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as b:
   self.assertEqual(self.checked(b.get('/api/platform/decisions'))['total'],0)
   for suffix in ['', '/runs?node_id=logistics_assignment']:self.assertEqual(b.get('/api/platform/decisions/'+case+suffix).status_code,404)
   self.assertEqual(b.patch('/api/platform/decisions/'+case,json={'expected_updated_at':result['updated_at'],'archived':True}).status_code,404)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
   self.assertEqual(viewer.get('/api/platform/decisions/'+case).status_code,200)
   self.assertEqual(viewer.patch('/api/platform/decisions/'+case,json={'expected_updated_at':result['updated_at'],'label':'No'}).status_code,403)
  for credential in (self.s.anon_token,self.s.user_tokens[USER_A]):
   for rpc,body in [('platform_decision_center',{}),('platform_update_case',{'target_case_id':case,'expected_updated_at':result['updated_at'],'archive':True})]:
    response=self.s.http.post(self.s.rest_url+'/rpc/'+rpc,headers={'Authorization':'Bearer '+credential},json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_A,**body})
    self.assertIn(response.status_code,(401,403))
  self.assertGreaterEqual(self.s.db.patch('decision_cases',params={'id':'eq.'+case},json={'created_by_user_id':USER_B}).status_code,400)
  self.assertEqual(self.s.db.post('rpc/platform_decision_center',json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_B}).status_code,403)
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  self.assertEqual(self.a.get('/api/decision-cases/'+case).status_code,403)
  self.assertEqual(self.a.get('/api/platform/decisions/'+case).status_code,200)
  self.checked(self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':self.center(case)['updated_at'],'archived':True}))
  self.assertEqual(self.center()['total'],1);self.assertEqual(self.checked(self.a.get('/api/platform/decisions?filter=archived'))['items'][0]['id'],case)
  self.checked(self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':self.center(case)['updated_at'],'archived':False,'label':None}))
  self.assertIsNone(self.center(case)['label'])

 def test_02_live_workflow_completion_review_lineage_history_and_read_purity(self):
  case,orders,fleet=self.case();self.s.start_worker()
  assignment=self.admit(self.body(case,orders,fleet));self.finish(assignment);self.approve(assignment,case)
  detail=self.center(case)
  self.assertEqual(detail['resume'],{'view':'logistics-config','node_id':'logistics_scheduling','run_id':None})
  self.assertEqual(detail['nodes'][0]['approved_run']['created_by']['id'],USER_A)
  self.assertEqual(detail['nodes'][0]['approved_run']['approved_by']['id'],USER_A)
  self.browser(case,assignment,'available')
  scheduling=self.admit(self.body(case,orders,fleet,'logistics_scheduling',assignment));self.finish(scheduling)
  detail=self.center(case);self.assertTrue(detail['in_review']);self.assertEqual(detail['status'],'active')
  self.assertEqual(detail['resume']['run_id'],scheduling);self.assertEqual(detail['resume']['node_id'],'logistics_scheduling')
  self.assertEqual(self.checked(self.a.get('/api/platform/decisions?filter=review'))['total'],1)
  # A real browser sees the same approved D1 and current D2 review. No fixtures
  # can invent the target run, create authors or change the approval lineage.
  self.browser(case,assignment,scheduling)
  self.approve(scheduling,case,'logistics_scheduling')
  self.assertEqual(self.center(case)['status'],'completed');self.assertEqual(self.checked(self.a.get('/api/platform/decisions?filter=completed'))['total'],1)
  replacement=self.admit(self.body(case,orders,fleet));self.finish(replacement)
  detail=self.center(case);self.assertEqual(detail['status'],'active');self.assertTrue(detail['in_review'])
  self.assertEqual(detail['nodes'][0]['approved_run']['id'],assignment);self.assertEqual(detail['nodes'][0]['latest_run']['id'],replacement)
  before=self.s.sql("SELECT md5(string_agg(to_jsonb(c)::text,'' ORDER BY id)) FROM decision_cases c;")
  self.center(case);history=self.checked(self.a.get('/api/platform/decisions/'+case+'/runs?node_id=logistics_assignment&limit=1&offset=1'))
  self.assertEqual(history['total'],2);self.assertEqual(history['items'][0]['id'],assignment)
  self.assertEqual(history['items'][0]['objective'],'balanced');self.assertIsInstance(history['items'][0]['duration_ms'],int)
  self.assertEqual(history['items'][0]['created_by']['id'],USER_A);self.assertNotIn('result_json',json.dumps(history));self.assertNotIn('configuration_json',json.dumps(history))
  self.assertEqual(self.s.sql("SELECT md5(string_agg(to_jsonb(c)::text,'' ORDER BY id)) FROM decision_cases c;"),before)
  self.approve(replacement,case)
  detail=self.center(case);self.assertEqual(detail['status'],'active');self.assertEqual(detail['nodes'][1]['status'],'stale');self.assertFalse(detail['nodes'][1]['approval_current'])

 def test_03_historical_attribution_is_unknown_and_inactive_members_cannot_read(self):
  case,_,_=self.case()
  self.s.sql('ALTER TABLE decision_cases DISABLE TRIGGER center_provenance_guard;')
  try:self.s.sql(f"UPDATE decision_cases SET created_by_user_id=NULL WHERE id='{case}';")
  finally:self.s.sql('ALTER TABLE decision_cases ENABLE TRIGGER center_provenance_guard;')
  detail=self.center(case);self.assertIsNone(detail['created_by']);self.assertIsNone(detail['owner'])
  self.s.sql(f"UPDATE decision_cases SET state_json='{{\"nodes\":{{\"logistics_assignment\":{{\"status\":\"obsolete-cache\"}}}}}}'::jsonb WHERE id='{case}';")
  before=self.s.sql(f"SELECT state_json::text FROM decision_cases WHERE id='{case}';")
  self.assertEqual(self.center(case)['nodes'][0]['status'],'available')
  self.assertEqual(self.s.sql(f"SELECT state_json::text FROM decision_cases WHERE id='{case}';"),before)
  self.assertTrue(all(n['owner'] is None and n['approver'] is None for n in detail['nodes']))
  self.assertEqual(self.a.get('/api/platform/decisions?limit=51').status_code,422)
  self.assertEqual(self.a.get('/api/platform/decisions/'+case+'/runs?node_id=other').status_code,422)
  self.s.sql(f"UPDATE workspace_members SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_A}';")
  try:self.assertEqual(self.a.get('/api/platform/decisions/'+case).status_code,403)
  finally:self.s.sql(f"UPDATE workspace_members SET status='active' WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_A}';")

 def browser(self,case,assignment,scheduling):
  root=Path(__file__).resolve().parents[2]
  result=subprocess.run([str(root/'.browser-venv/bin/python'),str(root/'tests/e2e/decision_center_journey.py')],cwd=root,
   env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_CENTER_CASE':case,'DATION_CENTER_ASSIGNMENT':assignment,'DATION_CENTER_SCHEDULING':scheduling},capture_output=True,text=True,timeout=150)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)

 def test_04_portfolio_summary_is_global_actionable_and_read_only(self):
  case,orders,fleet=self.case()
  for _ in range(26):self.checked(self.a.post('/api/decision-cases',json={'id':str(uuid4()),'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}))
  def portfolio(client=None,**params):return self.checked((client or self.a).get('/api/platform/decisions',params={'limit':1,**params}))
  initial=portfolio();self.assertEqual(initial['summary'],{'active_cases':27,'in_review':0,'pending_approval':0,'approved':0});self.assertEqual(len(initial['items']),1)
  self.s.start_worker();run=self.admit(self.body(case,orders,fleet));self.finish(run)
  summary=portfolio()['summary'];self.assertEqual(summary,{'active_cases':27,'in_review':1,'pending_approval':1,'approved':0})
  self.assertEqual(portfolio(q='does-not-exist')['summary'],summary);self.assertEqual(portfolio(offset=27)['summary'],summary)
  self.assertEqual(portfolio(dda='production')['total'],0);self.assertEqual(portfolio(dda='production')['summary'],summary)
  self.assertEqual(portfolio(filter='pending_approval')['total'],1)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
   result=portfolio(viewer);self.assertEqual(result['summary']['in_review'],1);self.assertEqual(result['summary']['pending_approval'],0);self.assertEqual(portfolio(viewer,filter='pending_approval')['total'],0)
  member=next(m for m in self.checked(self.a.get('/api/platform/team'))['members'] if m['user_id']==USER_A)
  self.checked(self.a.patch('/api/platform/team/members/'+USER_A+'/responsibilities',json={'expected_updated_at':member['updated_at'],'business_roles':['data_owner','decision_owner','approver']}))
  stage=self.center(case)['responsibilities']['stages']['data_preparation']
  self.checked(self.a.put('/api/platform/decisions/'+case+'/responsibilities/data_preparation',json={'expected_updated_at':stage['updated_at'],'owner_user_id':USER_A}))
  self.assertEqual(portfolio(owner='me')['total'],1);self.assertEqual(portfolio(owner=USER_A)['total'],1);self.assertEqual(portfolio(owner='unassigned')['total'],26);self.assertEqual(portfolio(owner=USER_B)['total'],0)
  detail=self.center(case);self.assertEqual(detail['responsibilities']['stages']['data_preparation']['owner']['id'],USER_A)
  self.assertEqual(detail['current_objective']['id'],'balanced');self.assertEqual(detail['current_objective']['source'],'latest_run')
  download=self.a.get('/api/platform/data/datasets/'+orders['id']+'/download');self.assertEqual(download.status_code,200);self.assertIn('attachment;',download.headers['content-disposition'])
  before=self.s.sql("SELECT md5(string_agg(to_jsonb(t)::text,'' ORDER BY id)) FROM audit_events t;")
  portfolio();self.center(case);self.assertEqual(self.s.sql("SELECT md5(string_agg(to_jsonb(t)::text,'' ORDER BY id)) FROM audit_events t;"),before)
  self.s.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  try:self.assertEqual(portfolio()['summary']['pending_approval'],0);self.assertEqual(portfolio()['summary']['in_review'],1)
  finally:self.s.sql(f"UPDATE workspace_ddas SET status='enabled' WHERE workspace_id='{self.s.workspace_a}' AND dda_id='logistics';")
  self.approve(run,case);self.assertEqual(portfolio()['summary']['approved'],1)
  d2=self.admit(self.body(case,orders,fleet,'logistics_scheduling',run));self.finish(d2);self.approve(d2,case,'logistics_scheduling')
  result=portfolio();self.assertEqual(result['summary']['active_cases'],26);self.assertEqual(result['summary']['approved'],2)
  replacement_body=self.body(case,orders,fleet);replacement_body['configuration']={'mode':'preset','objective':'min_cost','dimensions':['trips','cost','own_fleet','co2']}
  replacement=self.admit(replacement_body);self.finish(replacement);detail=self.center(case)
  self.assertEqual(detail['current_objective']['id'],'balanced');self.assertEqual(detail['current_objective']['run_id'],run)
  self.assertEqual(detail['nodes'][0]['latest_objective']['id'],'min_cost');self.assertEqual(detail['nodes'][0]['latest_run']['id'],replacement)
  result=portfolio();self.assertEqual(result['summary'],{'active_cases':27,'in_review':1,'pending_approval':1,'approved':2})
  self.approve(replacement,case);self.assertEqual(portfolio()['summary']['approved'],1);self.assertFalse(self.center(case)['nodes'][1]['approval_current'])
  self.checked(self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':self.center(case)['updated_at'],'archived':True}))
  self.assertEqual(portfolio()['summary'],{'active_cases':26,'in_review':0,'pending_approval':0,'approved':0})
  for credential in [self.s.anon_token,self.s.user_tokens[USER_A]]:
   self.assertIn(self.s.http.post(self.s.rest_url+'/rpc/platform_decision_portfolio',headers={'Authorization':'Bearer '+credential},json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_A}).status_code,(401,403))
  self.assertEqual(self.s.db.post('rpc/platform_decision_portfolio',json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_B}).status_code,403)

 def test_05_portfolio_five_thousand_cases_remains_bounded(self):
  case,orders,fleet=self.case()
  # Synthetic rows exist only in the owned disposable stack; preserve real foreign keys and triggers.
  self.s.sql(f"INSERT INTO decision_cases(id,workspace_id,domain,orders_dataset_id,fleet_dataset_id,input_signature,state_json,status) SELECT gen_random_uuid(),workspace_id,domain,orders_dataset_id,fleet_dataset_id,input_signature,'{{}}'::jsonb,'active' FROM decision_cases c CROSS JOIN generate_series(1,4999) WHERE c.id='{case}';")
  import time
  started=time.monotonic();result=self.checked(self.a.get('/api/platform/decisions?limit=25'));elapsed=time.monotonic()-started
  self.assertEqual(result['total'],5000);self.assertEqual(result['summary']['active_cases'],5000);self.assertEqual(len(result['items']),25)
  self.assertLess(len(json.dumps(result)),100000);self.assertLess(elapsed,12,'Portfolio exceeded the existing service timeout budget')
  second=self.checked(self.a.get('/api/platform/decisions?limit=25&offset=25'));self.assertTrue(set(x['id'] for x in result['items']).isdisjoint(x['id'] for x in second['items']))
