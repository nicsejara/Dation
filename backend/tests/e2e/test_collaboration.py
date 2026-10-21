"""Team, invitations, assignment/approval races against isolated real SQL and API."""
import json, os, subprocess, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
import httpx
from auth_fixture import USER_A, USER_B, VIEWER, DISABLED, token
from sandbox import Sandbox
from workflow_fixture import set_roles,prepare_stage
import test_workflow as workflow

class CollaborationTests(unittest.TestCase):
 auto_assign_workflow=False
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
  self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,workspace_invitations CASCADE;')
  self.s.sql(f"DELETE FROM workspace_members WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_B}'; UPDATE workspace_members SET access_role=CASE WHEN user_id='{USER_A}' THEN 'admin' WHEN user_id='{VIEWER}' THEN 'viewer' ELSE 'operator' END,status=CASE WHEN user_id='{DISABLED}' THEN 'disabled' ELSE 'active' END,business_role=NULL,updated_at=clock_timestamp() WHERE workspace_id='{self.s.workspace_a}'; UPDATE profiles SET active_workspace_id='{self.s.workspace_b}' WHERE id='{USER_B}'; UPDATE auth.users SET email_confirmed_at=now();")
  self.a=self.s.api_client
  set_roles(self.a,USER_A,['data_steward','decision_owner','approver'])
  self.b=httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False,timeout=30);self.addCleanup(self.b.close)
 def team(self):return self.checked(self.a.get('/api/platform/team'))
 def row(self,uid):return next(row for row in self.team()['members'] if row['user_id']==uid)
 def update(self,uid,role,status='active',business=None,client=None,version=None):
  row=self.row(uid)
  return (client or self.a).patch('/api/platform/team/members/'+uid,json={'expected_updated_at':version or row['updated_at'],'access_role':role,'business_role':business,'status':status})
 def invite(self,email='user-2@example.test',role='operator'):
  return self.checked(self.a.post('/api/platform/team/invitations',json={'email':email,'access_role':role,'business_role':'approver'}),201)
 def bff(self,uid=USER_B):
  c=httpx.Client(base_url=self.s.api_url,headers={'Origin':self.s.api_url},trust_env=False,timeout=30)
  c.cookies.set('dation_access',self.s.user_tokens[uid]);self.addCleanup(c.close);return c
 def join(self):
  invitation=self.invite();self.checked(self.bff().post('/auth/invitations/'+invitation['id']+'/accept'));set_roles(self.a,USER_B,['decision_owner','approver']);return invitation
 def assign(self,case,node='logistics_assignment',owner=USER_B,approver=USER_B,version=None):
  return self.a.put('/api/platform/decisions/'+case+'/assignments/'+node,json={'expected_updated_at':version,'owner_user_id':owner,'approver_user_id':approver})

 def test_01_team_browser_invitation_acceptance_assignments_and_access(self):
  case,_,_=self.case()
  root=Path(__file__).resolve().parents[2]
  result=subprocess.run([str(root/'.browser-venv/bin/python'),str(root/'tests/e2e/collaboration_journey.py')],cwd=root,env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_TEAM_CASE':case,'DATION_TEAM_USER_B':USER_B},capture_output=True,text=True,timeout=180)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  row=self.row(USER_B);self.assertEqual(row['access_role'],'operator');self.assertEqual(row['business_role'],'approver')
  c=self.checked(self.a.get('/api/platform/decisions/'+case));self.assertEqual(c['nodes'][0]['approver']['id'],USER_B)
  for field in ['owner_user_id','approver_user_id']:
   invalid={'expected_updated_at':c['nodes'][0]['assignment_updated_at'],'owner_user_id':USER_A,'approver_user_id':USER_A,field:DISABLED}
   self.assertEqual(self.a.put('/api/platform/decisions/'+case+'/assignments/logistics_assignment',json=invalid).status_code,409)
  other=self.checked(self.b.get('/api/platform/team'));self.assertEqual(other['invitations'],[])
  self.assertEqual(self.b.post('/api/platform/team/invitations',json={'email':'third@example.test','access_role':'admin'}).status_code,403)
  self.assertEqual(self.b.put('/api/platform/decisions/'+case+'/assignments/logistics_assignment',json={'expected_updated_at':None,'owner_user_id':USER_B,'approver_user_id':USER_B}).status_code,403)
  row=self.row(USER_B);self.checked(self.update(USER_B,'viewer',business='data_steward'));self.assertEqual(self.update(USER_B,'operator',version=row['updated_at']).status_code,409)
  self.assertFalse(any(m['user_id']==USER_B for m in self.checked(self.a.get('/api/platform/team?candidates=true'))['members']))
  self.assertEqual(self.b.get('/api/platform/team').status_code,200);self.assertEqual(self.b.patch('/api/platform/team/members/'+USER_A,json={}).status_code,403)
  for rpc in ['platform_team','platform_invite_member','platform_update_member','platform_assign_decision','platform_received_invitations','platform_case_collaboration']:
   r=self.s.http.post(self.s.rest_url+'/rpc/'+rpc,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_A]},json={})
   self.assertIn(r.status_code,(401,403,404))
  self.assertEqual(self.a.get('/api/platform/team?limit=51').status_code,422)
  self.assertEqual(self.a.post('/api/platform/team/invitations',json={'email':'valid@example.test','access_role':'owner'}).status_code,422)
  self.assertEqual(self.s.sql("SELECT count(*) FROM audit_events WHERE event_type='team.invitation_accepted';"),'1')
  activity=self.checked(self.a.get('/api/platform/activity?limit=50'))['items'];kinds=[e['event_type'] for e in activity]
  for kind in ['member.invited','member.joined','member.role_changed']:self.assertIn(kind,kinds)

 def test_02_assigned_approval_handoff_attribution_override_and_retry(self):
  self.join();self.checked(self.update(VIEWER,'operator'));case,orders,fleet=self.case()
  prepare_stage(self.a,case,'data_preparation')
  first=self.checked(self.assign(case));second=self.checked(self.assign(case,'logistics_scheduling',owner=USER_B,approver=USER_B))
  self.assertEqual(self.assign(case,version=None).status_code,409)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as operator:
   self.s.start_worker();d1=self.admit(self.body(case,orders,fleet));self.finish(d1)
   self.assertEqual(self.checked(operator.get('/api/platform/home'))['attention']['total'],0)
   self.assertEqual(self.checked(self.b.get('/api/platform/home'))['attention']['total'],1)
   self.assertFalse(self.checked(operator.get('/api/decision-cases/'+case))['collaboration']['logistics_assignment']['can_approve'])
   request={'case_id':case,'node_id':'logistics_assignment'}
   self.assertEqual(operator.post('/api/runs/'+d1+'/approve',json=request).status_code,403)
   root=Path(__file__).resolve().parents[2]
   browser=subprocess.run([str(root/'.browser-venv/bin/python'),str(root/'tests/e2e/collaboration_approval_journey.py')],cwd=root,env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_TEAM_CASE':case,'DATION_TEAM_RUN':d1,'DATION_TEAM_OTHER_TOKEN':self.s.user_tokens[VIEWER]},capture_output=True,text=True,timeout=100)
   self.assertEqual(browser.returncode,0,browser.stdout+browser.stderr)
   approved=self.checked(self.b.post('/api/runs/'+d1+'/approve',json=request));self.assertEqual(approved['approved_by'],'user:'+USER_B)
   self.assertEqual(self.checked(self.b.post('/api/runs/'+d1+'/approve',json=request))['approved_at'],approved['approved_at'])
   self.assertEqual(self.s.sql(f"SELECT count(*) FROM audit_events WHERE event_type='decision.approved' AND metadata_json->>'run_id'='{d1}';"),'1')
   detail=self.checked(self.a.get('/api/platform/decisions/'+case));self.assertEqual(detail['nodes'][1]['status'],'available');self.assertEqual(detail['nodes'][1]['owner']['id'],USER_B)
   handoff=self.checked(self.b.get('/api/platform/home'))['attention'];self.assertEqual(handoff['total'],1);self.assertEqual(handoff['items'][0]['kind'],'handoff');self.assertEqual(handoff['items'][0]['node_id'],'logistics_scheduling')
   d2=self.admit(self.body(case,orders,fleet,'logistics_scheduling',d1));self.finish(d2)
   self.assertEqual(operator.post('/api/runs/'+d2+'/approve',json={'case_id':case,'node_id':'logistics_scheduling'}).status_code,403)
   self.approve(d2,case,'logistics_scheduling')
   event=json.loads(self.s.sql(f"SELECT metadata_json FROM audit_events WHERE event_type='decision.approved' AND metadata_json->>'run_id'='{d2}';"));self.assertTrue(event['admin_override']);self.assertEqual(event['assigned_approver_user_id'],USER_B)
   before=self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE run_id='{d2}';");self.approve(d2,case,'logistics_scheduling');self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE run_id='{d2}';"),before)
   self.checked(self.update(USER_B,'operator','disabled'));detail=self.checked(self.a.get('/api/platform/decisions/'+case));self.assertFalse(detail['nodes'][0]['approver']['active'])
   self.assertEqual(self.b.get('/api/platform/team',headers={'X-Dation-Workspace-Id':self.s.workspace_a}).status_code,403)
   self.assertEqual(self.assign(case,version=first['updated_at']).status_code,409)
  # Composite FKs and RLS block cross-workspace assignments, even for a guessed ID.
  self.s.sql(f"UPDATE profiles SET active_workspace_id='{self.s.workspace_b}' WHERE id='{USER_B}';")
  self.assertEqual(self.b.get('/api/platform/decisions/'+case).status_code,404)
  self.assertEqual(self.b.put('/api/platform/decisions/'+case+'/assignments/logistics_assignment',json={'expected_updated_at':first['updated_at'],'owner_user_id':USER_B,'approver_user_id':USER_B}).status_code,404)
  response=self.s.http.get(self.s.rest_url+'/decision_assignments',headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]});self.assertEqual(response.json(),[])

 def test_03_invitation_confirmation_expiry_revocation_recipient_and_idempotency(self):
  self.assertEqual(self.a.post('/auth/invitations').status_code,403)
  invited=self.invite();self.assertEqual(self.a.post('/api/platform/team/invitations',json={'email':'USER-2@EXAMPLE.TEST','access_role':'viewer'}).status_code,409)
  self.assertEqual(self.bff(USER_A).post('/auth/invitations/'+invited['id']+'/accept').status_code,404)
  bff=self.bff();self.assertEqual(len(self.checked(bff.post('/auth/invitations'))['items']),1)
  self.s.sql(f"UPDATE auth.users SET email_confirmed_at=NULL WHERE id='{USER_B}';")
  self.assertEqual(bff.post('/auth/invitations/'+invited['id']+'/accept').status_code,403)
  self.s.sql(f"UPDATE auth.users SET email_confirmed_at=now() WHERE id='{USER_B}'; UPDATE workspace_invitations SET expires_at=now()-interval '1 second' WHERE id='{invited['id']}';")
  self.assertEqual(bff.post('/auth/invitations/'+invited['id']+'/accept').status_code,409)
  renewed=self.invite();self.checked(self.a.post('/api/platform/team/invitations/'+renewed['id']+'/revoke',json={'expected_updated_at':renewed['updated_at']}))
  self.assertEqual(bff.post('/auth/invitations/'+renewed['id']+'/accept').status_code,409)
  current=self.invite();self.checked(bff.post('/auth/invitations/'+current['id']+'/accept'));self.assertTrue(self.checked(bff.post('/auth/invitations/'+current['id']+'/accept'))['already_accepted'])
  self.checked(self.update(USER_B,'operator','disabled'))
  self.assertEqual(bff.post('/auth/invitations/'+current['id']+'/accept').status_code,403)
  self.assertEqual(self.a.post('/api/platform/team/invitations',json={'email':'user-2@example.test','access_role':'admin'}).status_code,409)
  self.assertEqual(self.a.post('/api/platform/team/invitations',json={'email':'user-4@example.test','access_role':'admin'}).status_code,409)
  new_user=str(uuid4());self.s.sql(f"INSERT INTO auth.users VALUES('{new_user}','fresh@example.test',now());")
  fresh_invitation=self.invite('fresh@example.test','viewer');root=Path(__file__).resolve().parents[2]
  new_token=token(self.s.auth_key,self.s.env['SUPABASE_URL'],new_user)
  self.checked(self.update(VIEWER,'admin'));self.checked(self.update(USER_A,'operator'))
  with httpx.Client(base_url=self.s.api_url,headers={'Origin':self.s.api_url},trust_env=False) as pending:
   pending.cookies.set('dation_access',new_token)
   self.assertEqual(pending.post('/auth/invitations/'+fresh_invitation['id']+'/accept').status_code,403)
  with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as other_admin:
   self.checked(self.update(USER_A,'admin',client=other_admin))
  journey=subprocess.run([str(root/'.browser-venv/bin/python'),str(root/'tests/e2e/collaboration_onboarding_journey.py')],cwd=root,env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_TEAM_NEW_TOKEN':new_token},capture_output=True,text=True,timeout=75)
  self.assertEqual(journey.returncode,0,journey.stdout+journey.stderr)
  self.assertEqual(self.row(new_user)['access_role'],'viewer')

 def test_04_last_admin_concurrency_and_assignment_races(self):
  self.assertEqual(self.update(USER_A,'operator').status_code,409)
  self.join();self.checked(self.update(USER_B,'admin'))
  versions={uid:self.row(uid)['updated_at'] for uid in (USER_A,USER_B)}
  def demote(uid):
   client=self.a if uid==USER_A else self.b
   return client.patch('/api/platform/team/members/'+uid,json={'expected_updated_at':versions[uid],'access_role':'operator','business_role':None,'status':'active'}).status_code
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(demote,[USER_A,USER_B]))
  self.assertEqual(sorted(results),[200,409]);self.assertEqual(self.s.sql(f"SELECT count(*) FROM workspace_members WHERE workspace_id='{self.s.workspace_a}' AND access_role='admin' AND status='active';"),'1')
  self.s.sql(f"UPDATE workspace_members SET access_role='admin' WHERE user_id='{USER_A}' AND workspace_id='{self.s.workspace_a}';")
  case,_,_=self.case()
  set_roles(self.a,USER_B,['decision_owner','approver'])
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.assign(case).status_code,range(2)))
  self.assertEqual(sorted(results),[200,409]);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_assignments WHERE decision_case_id='{case}';"),'1')
