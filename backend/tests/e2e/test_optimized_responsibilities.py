"""Localized acceptance for split data roles, node assignments and archive persistence."""
import json
import unittest
from uuid import uuid4
import httpx
from auth_fixture import USER_A,USER_B,VIEWER,DISABLED
from sandbox import Sandbox
import test_workflow_gates as gates


class OptimizedResponsibilityTests(unittest.TestCase):
    setUpClass=classmethod(gates.WorkflowGateTests.setUpClass.__func__)
    setUp=gates.WorkflowGateTests.setUp
    checked=gates.WorkflowGateTests.checked
    upload=gates.WorkflowGateTests.upload
    case=gates.WorkflowGateTests.case
    body=gates.WorkflowGateTests.body
    admit=gates.WorkflowGateTests.admit
    finish=gates.WorkflowGateTests.finish
    roles=gates.WorkflowGateTests.roles
    snapshot=gates.WorkflowGateTests.snapshot
    assign=gates.WorkflowGateTests.assign

    def test_split_roles_reload_independent_node_assignments_and_actual_approval(self):
        self.s.sql("UPDATE workspace_members SET status='active' WHERE user_id='"+DISABLED+"';")
        self.roles(USER_A,['data_owner','decision_owner'])
        self.roles(DISABLED,['data_steward','approver'])
        cid,orders,fleet=self.case()
        for group,uid in [('data_owner',USER_A),('data_steward',DISABLED)]:
            members=self.checked(self.a.get('/api/platform/team',params={'candidates':'true','responsibility':group}))['members']
            self.assertEqual([m['user_id'] for m in members],[uid])
        self.assign(cid,'data_owner',USER_A)
        saved=self.assign(cid,'data_steward',DISABLED)
        self.assertEqual(saved['stages']['data_owner']['owner']['id'],USER_A)
        self.assertEqual(saved['stages']['data_steward']['owner']['id'],DISABLED)
        self.checked(self.a.get('/api/platform/decisions/'+cid+'/workflow-readiness'))
        stale=self.a.put('/api/platform/decisions/'+cid+'/responsibilities/data_steward',json={
            'expected_updated_at':None,'owner_user_id':None,'approver_user_id':None})
        self.assertEqual(stale.status_code,409)
        current=self.snapshot(cid)['stages']['data_owner']
        denied=self.a.put('/api/platform/decisions/'+cid+'/responsibilities/data_owner',json={
            'expected_updated_at':current['updated_at'],'owner_user_id':DISABLED,'approver_user_id':None})
        self.assertEqual(denied.status_code,409)
        self.assertEqual(self.snapshot(cid)['stages'],saved['stages'])
        self.assign(cid,'logistics_assignment',USER_A,DISABLED)
        self.assign(cid,'logistics_scheduling',USER_A,None)
        self.assertIsNone(self.snapshot(cid)['stages']['logistics_scheduling']['approver'])
        self.s.start_worker();run=self.admit(self.body(cid,orders,fleet));self.finish(run)
        with httpx.Client(base_url=self.s.api_url,trust_env=False,headers={'Authorization':'Bearer '+self.s.user_tokens[DISABLED]}) as approver:
            result=self.checked(approver.post('/api/runs/'+run+'/approve',json={'case_id':cid,'node_id':'logistics_assignment'}))
        self.assertEqual(result['created_by_user_id'],USER_A)
        self.assertEqual(result['approved_by_user_id'],DISABLED)
        detail=self.checked(self.a.get('/api/platform/decisions/'+cid))
        actual=detail['nodes'][0]['approved_run']
        self.assertEqual(actual['created_by']['id'],USER_A);self.assertEqual(actual['approved_by']['id'],DISABLED)
        trace=self.checked(self.a.get('/api/platform/decisions/'+cid+'/runs',params={'node_id':'logistics_assignment','run_id':run,'limit':1}))
        self.assertEqual(trace['total'],1);self.assertEqual(trace['items'][0]['created_by']['id'],USER_A)
        self.assertEqual(trace['items'][0]['approved_by']['id'],DISABLED)
        self.assertEqual(self.checked(self.a.get('/api/platform/decisions/'+cid+'/runs',params={'node_id':'logistics_assignment','run_id':str(uuid4()),'limit':1}))['total'],0)
        snapshot=self.snapshot(cid)
        with httpx.Client(base_url=self.s.api_url,trust_env=False,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]}) as viewer:
            self.assertEqual(viewer.put('/api/platform/decisions/'+cid+'/responsibilities/data_owner',json={
                'expected_updated_at':snapshot['stages']['data_owner']['updated_at'],'owner_user_id':None}).status_code,403)
        with httpx.Client(base_url=self.s.api_url,trust_env=False,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]}) as other:
            self.assertEqual(other.get('/api/platform/decisions/'+cid+'/responsibilities').status_code,404)
        self.assign(cid,'data_owner',None)
        self.assertTrue(self.snapshot(cid)['stages']['data_preparation']['owner_eligible'])
        self.assertEqual(self.snapshot(cid)['stages']['data_preparation']['owner']['id'],DISABLED)

    def test_legacy_assignment_projects_to_its_explicit_role_without_ambiguous_overwrite(self):
        self.roles(USER_A,['data_steward'])
        cid,orders,fleet=self.case()
        result=self.assign(cid,'data_preparation',USER_A)
        self.assertEqual(result['stages']['data_steward']['owner']['id'],USER_A)
        legacy=result['stages']['data_preparation']
        stale=self.a.put('/api/platform/decisions/'+cid+'/responsibilities/data_preparation',json={
            'expected_updated_at':legacy['updated_at'],'owner_user_id':None,'approver_user_id':None})
        self.assertEqual(stale.status_code,409)
        self.assertEqual(self.snapshot(cid)['stages']['data_steward']['owner']['id'],USER_A)

    def test_archive_persists_reloads_and_preserves_case_history_and_assignments(self):
        self.roles(USER_A,['data_owner'])
        cid,orders,fleet=self.case();self.assign(cid,'data_owner',USER_A)
        before=self.s.sql("SELECT jsonb_build_object('state',state_json,'orders',orders_dataset_id,'fleet',fleet_dataset_id)::text FROM decision_cases WHERE id='"+cid+"';")
        previous=self.snapshot(cid)['stages']
        case=self.checked(self.a.get('/api/platform/decisions/'+cid))
        self.checked(self.a.patch('/api/platform/decisions/'+cid,json={'expected_updated_at':case['updated_at'],'archived':True}))
        with httpx.Client(base_url=self.s.api_url,trust_env=False,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_A]}) as fresh:
            detail=self.checked(fresh.get('/api/platform/decisions/'+cid))
            self.assertEqual(detail['status'],'archived');self.assertEqual(detail['display_status'],'archived')
            self.assertEqual(self.checked(fresh.get('/api/platform/decisions?filter=archived'))['items'][0]['id'],cid)
            self.assertEqual(self.checked(fresh.get('/api/platform/decisions?filter=all'))['total'],0)
            self.assertEqual(self.checked(fresh.get('/api/platform/decisions?filter=in_progress'))['total'],0)
            self.assertEqual(self.snapshot(cid)['stages'],previous)
            self.assertEqual(self.s.sql("SELECT jsonb_build_object('state',state_json,'orders',orders_dataset_id,'fleet',fleet_dataset_id)::text FROM decision_cases WHERE id='"+cid+"';"),before)
            restored=self.checked(fresh.patch('/api/platform/decisions/'+cid,json={'expected_updated_at':detail['updated_at'],'archived':False}))
            self.assertEqual(restored['status'],'active')
            self.assertEqual(self.checked(fresh.get('/api/platform/decisions?filter=archived'))['total'],0)


class DataRoleMigrationTests(unittest.TestCase):
    def test_existing_steward_assignment_keeps_person_actor_and_version(self):
        uid,cid,orders,fleet=map(str,(uuid4(),uuid4(),uuid4(),uuid4()))
        wid='00000000-0000-4000-8000-00000000da71';captured={}
        def seed(s,name):
            if name!='20261021020000_platform_data_responsibilities.sql':return
            s.sql("INSERT INTO auth.users VALUES('"+uid+"','legacy-steward@example.test',now()); INSERT INTO workspace_members(workspace_id,user_id,access_role,status,business_role) VALUES('"+wid+"','"+uid+"','operator','active','data_steward');")
            for identifier,kind in [(orders,'orders'),(fleet,'fleet')]:
                s.sql("INSERT INTO datasets(id,workspace_id,original_filename,storage_path,dataset_type) VALUES('"+identifier+"','"+wid+"','"+kind+".csv','"+wid+"/"+identifier+"/input.csv','"+kind+"');")
            s.sql("INSERT INTO decision_cases(id,workspace_id,orders_dataset_id,fleet_dataset_id,input_signature) VALUES('"+cid+"','"+wid+"','"+orders+"','"+fleet+"','"+orders+":"+fleet+"'); INSERT INTO dation_private.workflow_stage_assignments VALUES('"+wid+"','"+cid+"','data_preparation','"+uid+"','"+uid+"',clock_timestamp());")
            captured['assignment']=json.loads(s.sql("SELECT to_jsonb(a)-'stage_key' FROM dation_private.workflow_stage_assignments a WHERE decision_case_id='"+cid+"';"))
        with Sandbox(migration_hook=seed) as s:
            current=json.loads(s.sql("SELECT to_jsonb(a)-'stage_key' FROM dation_private.workflow_stage_assignments a WHERE decision_case_id='"+cid+"' AND stage_key='data_steward';"))
            self.assertEqual(current,captured['assignment'])
            response=s.api_client.get('/api/platform/decisions/'+cid+'/responsibilities')
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['stages']['data_steward']['owner']['id'],uid)
            self.assertEqual(response.json()['stages']['data_preparation']['owner']['id'],uid)
