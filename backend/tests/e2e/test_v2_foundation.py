"""Foundation domain against owned PostgreSQL, actual RPC/API and worker."""
import json
import unittest
from uuid import uuid4
import httpx
from auth_fixture import USER_A,USER_B,VIEWER,DISABLED
from sandbox import Sandbox
from workflow_fixture import apply_attributes
import test_workflow as workflow

class MigrationCompatibilityTests(unittest.TestCase):
    def test_legacy_member_is_backfilled_without_rewriting_the_membership(self):
        legacy='10000000-0000-4000-8000-000000000005';captured={}
        def seed(s,name):
            if name!='20261020010000_platform_v2_foundation.sql':return
            s.sql(f"INSERT INTO auth.users VALUES('{legacy}','legacy@example.test',now()); INSERT INTO workspace_members(workspace_id,user_id,access_role,business_role,status) VALUES('00000000-0000-4000-8000-00000000da71','{legacy}','operator','data_steward','active');")
            captured['row']=s.sql(f"SELECT to_jsonb(m)::text FROM workspace_members m WHERE user_id='{legacy}';")
        with Sandbox(migration_hook=seed) as s:
            self.assertEqual(s.sql(f"SELECT to_jsonb(m)::text FROM workspace_members m WHERE user_id='{legacy}';"),captured['row'])
            roles=json.loads(s.sql(f"SELECT jsonb_agg(responsibility ORDER BY responsibility) FROM dation_private.member_responsibilities WHERE user_id='{legacy}';"))
            self.assertEqual(roles,['data_owner','data_steward'])

class FoundationDomainTests(unittest.TestCase):
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
        self.s.sql(f"UPDATE workspace_members SET business_role=NULL,access_role=CASE WHEN user_id IN('{USER_A}','{USER_B}') THEN 'admin' WHEN user_id='{VIEWER}' THEN 'viewer' ELSE 'operator' END,status=CASE WHEN user_id='{DISABLED}' THEN 'disabled' ELSE 'active' END; UPDATE auth.users SET email_confirmed_at=now();")
        self.a=self.s.api_client

    def client(self,uid):
        c=httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[uid]},trust_env=False,timeout=30)
        self.addCleanup(c.close);return c

    def member(self,uid):
        return next(r for r in self.checked(self.a.get('/api/platform/team'))['members'] if r['user_id']==uid)

    def roles(self,uid,roles,version=None):
        return self.a.patch('/api/platform/team/members/'+uid+'/responsibilities',json={'expected_updated_at':version or self.member(uid)['updated_at'],'business_roles':roles})

    def assign(self,case,stage,owner,approver=None,version=None):
        return self.a.put(f'/api/platform/decisions/{case}/responsibilities/{stage}',json={'expected_updated_at':version,'owner_user_id':owner,'approver_user_id':approver})

    def read(self,case):return self.checked(self.a.get(f'/api/platform/decisions/{case}/responsibilities'))

    def test_multi_responsibility_candidates_cas_and_legacy_compatibility(self):
        before=self.member(USER_A);self.checked(self.roles(USER_A,['data_owner','decision_owner']))
        self.assertEqual(set(self.member(USER_A)['business_roles']),{'data_owner','decision_owner'})
        self.assertEqual(self.member(USER_A)['access_role'],'admin')
        self.assertEqual(self.roles(USER_A,[],version=before['updated_at']).status_code,409)
        self.assertEqual(self.roles(USER_A,['decision_owner','decision_owner']).status_code,422)
        for retired in ('data_steward','approver'):
            self.assertEqual(self.roles(USER_A,[retired]).status_code,422)
        self.checked(self.roles(VIEWER,['data_owner','decision_owner']))
        self.checked(self.roles(DISABLED,['data_owner','decision_owner']))
        self.s.sql(f"UPDATE workspace_members SET status='active' WHERE user_id='{DISABLED}'; UPDATE auth.users SET email_confirmed_at=NULL WHERE id='{DISABLED}';")
        for group in ('data','data_owner','decision_owner'):
            response=self.checked(self.a.get('/api/platform/team',params={'candidates':'true','responsibility':group,'limit':1}))
            self.assertEqual(response['total'],1);self.assertEqual(response['members'][0]['user_id'],USER_A)
            self.assertEqual(self.checked(self.a.get('/api/platform/team',params={'candidates':'true','responsibility':group,'offset':1}))['members'],[])
        for retired in ('data_steward','approver'):
            result=self.checked(self.a.get('/api/platform/team',params={'candidates':'true','responsibility':retired}))
            self.assertEqual(result['total'],0)
            self.assertEqual(result['members'],[])
        self.assertEqual(self.a.get('/api/platform/team?responsibility=approver').status_code,422)
        b=self.client(USER_B)
        self.assertEqual(self.checked(b.get('/api/platform/team?candidates=true&responsibility=approver'))['total'],0)
        self.assertEqual(b.patch('/api/platform/team/members/'+USER_A+'/responsibilities',json={'expected_updated_at':self.member(USER_A)['updated_at'],'business_roles':['decision_owner']}).status_code,404)
        self.assertEqual(self.client(VIEWER).patch('/api/platform/team/members/'+VIEWER+'/responsibilities',json={'expected_updated_at':self.member(VIEWER)['updated_at'],'business_roles':[]}).status_code,403)
        # The single-value old contract replaces the canonical role set on change.
        member=self.member(USER_A)
        self.checked(self.a.patch('/api/platform/team/members/'+USER_A,json={'expected_updated_at':member['updated_at'],'access_role':'admin','business_role':'decision_owner','status':'active'}))
        self.assertEqual(self.member(USER_A)['business_roles'],['decision_owner'])
        member=self.member(USER_A)
        self.checked(self.a.patch('/api/platform/team/members/'+USER_A,json={'expected_updated_at':member['updated_at'],'access_role':'admin','business_role':'data_owner','status':'active'}))
        self.assertEqual(self.member(USER_A)['business_roles'],['data_owner'])
        self.assertEqual(self.checked(self.a.get('/api/platform/team?candidates=true&responsibility=approver'))['members'],[])

    def test_stage_assignments_enforce_eligibility_and_keep_get_read_only(self):
        case,_,_=self.case();self.checked(self.roles(USER_A,['data_owner','decision_owner']))
        self.checked(self.roles(VIEWER,['decision_owner']))
        original=self.read(case);self.assertTrue(original['gates_enforced'])
        self.assertTrue(all(s['owner'] is None for s in original['stages'].values()))
        self.assertEqual(self.assign(case,'data_preparation',VIEWER).status_code,409)
        self.assertEqual(self.assign(case,'logistics_assignment',USER_B).status_code,409)
        self.assertEqual(self.assign(case,'data_preparation',USER_A,USER_A).status_code,409)
        data=self.checked(self.assign(case,'data_preparation',USER_A));stage=data['stages']['data_preparation']
        self.assertTrue(stage['owner_eligible']);self.assertIsNone(stage['approver'])
        self.assertEqual(self.assign(case,'data_preparation',None).status_code,409)
        self.checked(self.assign(case,'logistics_assignment',USER_A,USER_A))
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_assignments WHERE decision_case_id='{case}';"),'1')
        snapshot=self.s.sql("SELECT md5(string_agg(to_jsonb(e)::text,'' ORDER BY id)) FROM audit_events e;")
        self.read(case);self.read(case)
        self.assertEqual(self.s.sql("SELECT md5(string_agg(to_jsonb(e)::text,'' ORDER BY id)) FROM audit_events e;"),snapshot)
        version=self.read(case)['stages']['logistics_assignment']['updated_at']
        self.checked(self.assign(case,'logistics_assignment',USER_A,USER_A,version))
        self.assertEqual(self.s.sql("SELECT md5(string_agg(to_jsonb(e)::text,'' ORDER BY id)) FROM audit_events e;"),snapshot)
        kinds=json.loads(self.s.sql("SELECT jsonb_agg(event_type) FROM audit_events;"))
        for kind in ('stage.responsible_changed','decision.owner_changed'):self.assertIn(kind,kinds)
        self.assertNotIn('decision.approver_assigned',kinds)
        self.checked(self.roles(USER_A,['decision_owner']))
        self.assertFalse(self.read(case)['stages']['data_preparation']['owner_eligible'])
        self.assertEqual(self.read(case)['stages']['data_preparation']['owner']['id'],USER_A)
        self.assertEqual(self.client(USER_B).get(f'/api/platform/decisions/{case}/responsibilities').status_code,404)
        detail=self.checked(self.a.get('/api/platform/decisions/'+case))
        self.checked(self.a.patch('/api/platform/decisions/'+case,json={'expected_updated_at':detail['updated_at'],'archived':True}))
        self.assertEqual(self.assign(case,'data_preparation',None,version=stage['updated_at']).status_code,409)

    def test_approved_precedence_actual_actor_and_explicit_candidate_access(self):
        row=self.member(VIEWER)
        self.checked(self.a.patch('/api/platform/team/members/'+VIEWER,json={'expected_updated_at':row['updated_at'],'access_role':'operator','business_role':'decision_owner','status':'active'}))
        self.checked(self.roles(USER_A,['data_owner','decision_owner']))
        case,orders,fleet=self.case();apply_attributes(self.a,case)
        self.checked(self.assign(case,'data_preparation',USER_A));self.checked(self.assign(case,'logistics_assignment',VIEWER))
        self.s.start_worker();first=self.finish(self.admit(self.body(case,orders,fleet)));approved=self.approve(first['id'],case)
        self.assertEqual(approved['approved_by_user_id'],USER_A)
        self.assertEqual(self.read(case)['stages']['logistics_assignment']['approver']['id'],VIEWER)
        current=self.checked(self.a.get('/api/platform/decisions/'+case))['nodes'][0]
        self.assertEqual(current['target']['run_id'],first['id']);self.assertTrue(current['approval_current'])
        second=self.finish(self.admit(self.body(case,orders,fleet)))
        detail=self.checked(self.a.get('/api/platform/decisions/'+case));node=detail['nodes'][0]
        self.assertEqual(node['target']['run_id'],second['id']);self.assertEqual(node['latest_run']['id'],second['id'])
        self.assertFalse(node['approval_current'])
        historical=self.checked(self.a.get('/api/runs/'+first['id']))
        self.assertEqual(historical['approved_at'],approved['approved_at']);self.assertIsNotNone(historical['superseded_at'])
        self.assertEqual(self.checked(self.a.get('/api/runs/'+second['id']))['id'],second['id'])
        self.assertEqual(detail['context']['caseId'],case)
        event=json.loads(self.s.sql(f"SELECT metadata_json FROM audit_events WHERE event_type='decision.approved' AND object_id='{first['id']}';"))
        self.assertTrue(event['admin_override']);self.assertEqual(event['assigned_decision_owner_user_id'],VIEWER)

    def test_private_relations_and_new_rpcs_are_not_direct_client_capabilities(self):
        for table in ('member_responsibilities','workflow_stage_assignments'):
            self.assertEqual(self.s.sql(f"SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE oid='dation_private.{table}'::regclass;"),'t')
            for role in ('anon','authenticated','service_role'):
                self.assertEqual(self.s.sql(f"SELECT has_table_privilege('{role}','dation_private.{table}','SELECT,INSERT,UPDATE,DELETE');"),'f')
        for rpc in ('platform_team_foundation','platform_set_member_responsibilities','platform_workflow_responsibilities'):
            for credential in (self.s.anon_token,self.s.user_tokens[USER_A]):
                r=self.s.http.post(self.s.rest_url+'/rpc/'+rpc,headers={'Authorization':'Bearer '+credential},json={})
                self.assertIn(r.status_code,(401,403,404))
