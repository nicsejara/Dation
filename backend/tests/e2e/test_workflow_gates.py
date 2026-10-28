"""New-case ownership gates against real SQL, API, worker and tenant identity."""
import json
import unittest
from uuid import uuid4
import httpx
from auth_fixture import USER_A,USER_B,VIEWER
from sandbox import Sandbox
from workflow_fixture import prepare_stage,apply_attributes
import test_workflow as workflow

class WorkflowMigrationCompatibilityTests(unittest.TestCase):
    def test_existing_case_is_unchanged_and_legacy_actions_remain_available(self):
        cid,orders,fleet=map(str,(uuid4(),uuid4(),uuid4()));captured={}
        wid='00000000-0000-4000-8000-00000000da71'
        def seed(s,name):
            if name!='20261021010000_platform_workflow_gates.sql':return
            for identifier,kind in ((orders,'orders'),(fleet,'fleet')):
                s.sql(f"INSERT INTO datasets(id,workspace_id,original_filename,storage_path,dataset_type,profile_json) VALUES('{identifier}','{wid}','legacy-{kind}.csv','{wid}/{identifier}/input.csv','{kind}','{{\"valid\":true,\"counts\":{{\"errors\":0}}}}');")
            s.sql(f"INSERT INTO decision_cases(id,workspace_id,orders_dataset_id,fleet_dataset_id,input_signature) VALUES('{cid}','{wid}','{orders}','{fleet}','{orders}:{fleet}');")
            captured['case']=s.sql(f"SELECT to_jsonb(c)::text FROM decision_cases c WHERE id='{cid}';")
            captured['events']=s.sql(f"SELECT count(*) FROM audit_events WHERE decision_case_id='{cid}';")
        with Sandbox(migration_hook=seed) as s:
            original=json.loads(captured['case'])
            current=json.loads(s.sql(f"SELECT to_jsonb(c)::text FROM decision_cases c WHERE id='{cid}';"))
            # Expand migrations add nullable Ultimate columns/default cohort.
            # Every column that existed at the checkpoint must remain exact.
            self.assertEqual({key:current[key] for key in original},original)
            self.assertEqual(current['workflow_version'],1)
            self.assertIsNone(json.loads(s.sql(f"SELECT to_jsonb(c)::text FROM decision_cases c WHERE id='{cid}';"))['attributes_applied_at'])
            self.assertEqual(s.sql(f"SELECT workflow_policy_version FROM decision_cases WHERE id='{cid}';"),'0')
            self.assertEqual(s.sql(f"SELECT count(*) FROM audit_events WHERE decision_case_id='{cid}';"),captured['events'])
            response=s.api_client.get(f'/api/platform/decisions/{cid}/responsibilities')
            self.assertEqual(response.status_code,200,response.text);self.assertTrue(response.json()['gates_enforced'])
            self.assertEqual(response.json()['policy_version'],0)
            self.assertTrue(all(not stage['owner'] for stage in response.json()['stages'].values()))
            response=s.api_client.post('/api/runs',params={'run_id':str(uuid4())},json={'orders_dataset_id':orders,'fleet_dataset_id':fleet,'decision_case':{'case_id':cid,'node_id':'logistics_assignment'},'configuration':{'objective':'balanced'}})
            self.assertEqual(response.status_code,409,response.text)
            self.assertIn('atributos',response.json()['detail'])
            self.assertEqual(s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{cid}';"),'0')
            prepare_stage(s.api_client,cid,'logistics_assignment')
            response=s.api_client.post('/api/runs',params={'run_id':str(uuid4())},json={'orders_dataset_id':orders,'fleet_dataset_id':fleet,'decision_case':{'case_id':cid,'node_id':'logistics_assignment'},'configuration':{'objective':'balanced'}})
            self.assertEqual(response.status_code,202,response.text)
            other=str(uuid4())
            s.sql(f"INSERT INTO decision_cases(id,workspace_id,orders_dataset_id,fleet_dataset_id,input_signature,workflow_policy_version) VALUES('{other}','{wid}','{orders}','{fleet}','{orders}:{fleet}',0);")
            self.assertEqual(s.sql(f"SELECT workflow_policy_version FROM decision_cases WHERE id='{other}';"),'1')
            s.sql('UPDATE dation_private.platform_release SET workflow_gates_enabled=false;')
            self.assertFalse(s.api_client.get(f'/api/platform/decisions/{other}/responsibilities').json()['gates_enforced'])
            s.sql('UPDATE dation_private.platform_release SET workflow_gates_enabled=true;')
            self.assertTrue(s.api_client.get(f'/api/platform/decisions/{other}/responsibilities').json()['gates_enforced'])
            self.assertEqual(s.sql(f"SELECT workflow_policy_version FROM decision_cases WHERE id='{other}';"),'1')
            self.assertEqual(s.sql(f"SELECT workflow_policy_version FROM decision_cases WHERE id='{cid}';"),'0')


class WorkflowGateTests(unittest.TestCase):
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
        self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,audit_events CASCADE; DELETE FROM dation_private.member_responsibilities;')
        self.s.sql(f"UPDATE workspace_members SET business_role=NULL,access_role=CASE WHEN user_id IN('{USER_A}','{USER_B}') THEN 'admin' WHEN user_id='{VIEWER}' THEN 'viewer' ELSE 'operator' END; UPDATE auth.users SET email_confirmed_at=now();")
        self.a=self.s.api_client

    def roles(self,uid,roles):
        member=next(m for m in self.checked(self.a.get('/api/platform/team'))['members'] if m['user_id']==uid)
        return self.checked(self.a.patch('/api/platform/team/members/'+uid+'/responsibilities',json={'expected_updated_at':member['updated_at'],'business_roles':roles}))

    def snapshot(self,case):return self.checked(self.a.get(f'/api/platform/decisions/{case}/responsibilities'))

    def assign(self,case,stage,owner,approver=None):
        current=self.snapshot(case)['stages'][stage]
        return self.checked(self.a.put(f'/api/platform/decisions/{case}/responsibilities/{stage}',json={
            'expected_updated_at':current['updated_at'],'owner_user_id':owner,'approver_user_id':approver}))

    def rejected_run(self,body,phrase):
        before=self.s.sql('SELECT count(*) FROM dispatch_run_jobs;')
        response=self.a.post('/api/runs',params={'run_id':str(uuid4())},json=body)
        self.assertEqual(response.status_code,409,response.text);self.assertIn(phrase,response.json()['detail'])
        self.assertIn(response.headers.get('X-Dation-Workflow-Gate'),{'attributes','data','decision_owner'})
        self.assertEqual(self.s.sql('SELECT count(*) FROM dispatch_run_jobs;'),before)

    def test_new_cases_require_data_owner_and_approver_but_replays_keep_their_result(self):
        case,orders,fleet=self.case();body=self.body(case,orders,fleet)
        snapshot=self.snapshot(case);self.assertTrue(snapshot['gates_enforced']);self.assertEqual(snapshot['policy_version'],1)
        self.assertEqual(self.a.get(f'/api/platform/decisions/{case}/workflow-readiness').status_code,409)
        self.rejected_run(body,'atributos')
        apply_attributes(self.a,case)
        self.rejected_run(body,'Data Owner')
        self.roles(USER_A,['data_owner','decision_owner'])
        self.assign(case,'data_preparation',USER_A)
        self.checked(self.a.get(f'/api/platform/decisions/{case}/workflow-readiness'))
        self.rejected_run(body,'Decision Owner')
        self.assign(case,'logistics_assignment',USER_A)
        self.s.start_worker();run=self.admit(body);finished=self.finish(run)
        self.assertEqual(finished['created_by_user_id'],USER_A)
        self.roles(USER_A,[])
        self.assertEqual(self.admit(body,run),run)
        self.assertEqual(self.a.post('/api/runs/'+run+'/approve',json={'case_id':case,'node_id':'logistics_assignment'}).status_code,409)
        self.roles(USER_A,['decision_owner']);self.assign(case,'logistics_assignment',USER_A)
        approved=self.approve(run,case)
        self.roles(USER_A,[])
        self.assertEqual(self.approve(run,case)['approved_at'],approved['approved_at'])
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE run_id='{run}' AND action='approved';"),'1')

    def test_d1_d2_gates_are_independent_and_assigned_approver_is_not_actual_actor(self):
        self.roles(USER_A,['data_owner','decision_owner'])
        self.s.sql(f"UPDATE workspace_members SET access_role='operator' WHERE user_id='{VIEWER}';")
        self.roles(VIEWER,['decision_owner'])
        case,orders,fleet=self.case();apply_attributes(self.a,case)
        self.assign(case,'data_preparation',USER_A);self.assign(case,'logistics_assignment',VIEWER)
        self.s.start_worker();d1=self.admit(self.body(case,orders,fleet));self.finish(d1);self.approve(d1,case)
        queued=json.loads(self.s.sql(f"SELECT metadata_json FROM audit_events WHERE event_type='run.queued' AND object_id='{d1}';"))
        self.assertEqual(queued['decision_owner_user_id'],VIEWER);self.assertEqual(queued['data_responsible_user_id'],USER_A)
        self.assertEqual(self.checked(self.a.get('/api/runs/'+d1))['created_by_user_id'],USER_A)
        self.assign(case,'logistics_assignment',USER_A)
        self.assertEqual(json.loads(self.s.sql(f"SELECT metadata_json FROM audit_events WHERE event_type='run.queued' AND object_id='{d1}';")),queued)
        d2_body=self.body(case,orders,fleet,'logistics_scheduling',d1)
        self.rejected_run(d2_body,'Decision Owner')
        self.assign(case,'logistics_scheduling',USER_A)
        d2=self.admit(d2_body);self.finish(d2)
        self.roles(USER_A,['data_owner'])
        self.assertEqual(self.a.post('/api/runs/'+d2+'/approve',json={'case_id':case,'node_id':'logistics_scheduling'}).status_code,409)
        self.roles(USER_A,['data_owner','decision_owner'])
        self.assign(case,'logistics_scheduling',VIEWER)
        self.assertEqual(self.approve(d2,case,'logistics_scheduling')['approved_by_user_id'],USER_A)
        snapshot=self.snapshot(case)
        for node,owner in (('logistics_assignment',USER_A),('logistics_scheduling',VIEWER)):
            self.assertEqual(snapshot['stages'][node]['owner']['id'],owner)
            self.assertEqual(snapshot['stages'][node]['approver']['id'],owner)
        event=json.loads(self.s.sql(f"SELECT metadata_json FROM audit_events WHERE event_type='decision.approved' AND object_id='{d2}';"))
        self.assertTrue(event['admin_override']);self.assertEqual(event['assigned_decision_owner_user_id'],VIEWER)

    def test_role_loss_cross_workspace_forgery_and_policy_changes_do_not_bypass_gates(self):
        self.roles(USER_A,['data_owner','decision_owner'])
        case,orders,fleet=self.case();apply_attributes(self.a,case)
        self.assign(case,'data_preparation',USER_A);self.assign(case,'logistics_assignment',USER_A)
        self.roles(USER_A,['data_owner'])
        self.assertEqual(self.snapshot(case)['stages']['logistics_assignment']['owner']['id'],USER_A)
        self.assertFalse(self.snapshot(case)['stages']['logistics_assignment']['owner_eligible'])
        self.rejected_run(self.body(case,orders,fleet),'Decision Owner')
        self.assertEqual(self.s.db.patch('decision_cases',params={'id':'eq.'+case},json={'workflow_policy_version':0}).status_code,403)
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as other:
            for suffix in ('responsibilities','workflow-readiness'):
                self.assertEqual(other.get(f'/api/platform/decisions/{case}/'+suffix).status_code,404)
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
            self.assertEqual(viewer.put(f'/api/platform/decisions/{case}/responsibilities/data_preparation',json={'expected_updated_at':None,'owner_user_id':VIEWER}).status_code,403)

    def test_atomic_team_edit_keeps_multiple_roles_and_rolls_back_invalid_access(self):
        member=next(m for m in self.checked(self.a.get('/api/platform/team'))['members'] if m['user_id']==USER_A)
        payload={'expected_updated_at':member['updated_at'],'access_role':'admin','status':'active','business_roles':['data_owner','decision_owner']}
        result=self.checked(self.a.patch('/api/platform/team/members/'+USER_A,json=payload))
        self.assertEqual(set(result['business_roles']),set(payload['business_roles']))
        self.assertEqual(self.a.patch('/api/platform/team/members/'+USER_A,json=payload).status_code,409)
        payload.update(expected_updated_at=result['updated_at'],access_role='viewer',business_roles=[])
        self.assertEqual(self.a.patch('/api/platform/team/members/'+USER_A,json=payload).status_code,409)
        fresh=next(m for m in self.checked(self.a.get('/api/platform/team'))['members'] if m['user_id']==USER_A)
        self.assertEqual(fresh['access_role'],'admin');self.assertEqual(set(fresh['business_roles']),{'data_owner','decision_owner'})
        # A valid self-demotion updates the role set and technical access in one
        # transaction; a second active Admin is required and remains in control.
        other=next(m for m in self.checked(self.a.get('/api/platform/team'))['members'] if m['user_id']==VIEWER)
        self.checked(self.a.patch('/api/platform/team/members/'+VIEWER,json={'expected_updated_at':other['updated_at'],'access_role':'admin','status':'active','business_roles':[]}))
        self.checked(self.a.patch('/api/platform/team/members/'+USER_A,json={'expected_updated_at':fresh['updated_at'],'access_role':'operator','status':'active','business_roles':fresh['business_roles']}))
        me=next(m for m in self.checked(self.a.get('/api/platform/team'))['members'] if m['user_id']==USER_A)
        self.assertEqual(me['access_role'],'operator');self.assertEqual(set(me['business_roles']),set(fresh['business_roles']))
        for rpc in ('platform_validate_data_stage','platform_update_member_foundation'):
            response=self.s.http.post(self.s.rest_url+'/rpc/'+rpc,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_A]},json={})
            self.assertIn(response.status_code,(401,403,404))
