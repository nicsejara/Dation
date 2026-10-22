"""Saga 3: current Runs, immutable input identity and unified ownership."""
import json
import unittest
from uuid import uuid4
from auth_fixture import USER_A,USER_B,VIEWER,DISABLED
from sandbox import Sandbox
import test_workflow as workflow
from workflow_fixture import set_roles

class Saga3Tests(unittest.TestCase):
    checked=workflow.WorkflowTests.checked
    upload=workflow.WorkflowTests.upload
    body=workflow.WorkflowTests.body
    finish=workflow.WorkflowTests.finish

    @classmethod
    def setUpClass(cls):
        cls.s=Sandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)

    def setUp(self):
        self.s.stop(self.s.worker)
        self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events CASCADE;')
        set_roles(self.s.api_client,USER_A,['data_owner','decision_owner'])

    def case(self):
        orders,fleet=self.upload('orders'),self.upload('fleet');cid=str(uuid4())
        self.checked(self.s.api_client.post('/api/decision-cases',json={'id':cid,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id'],'label':'SEMANA 43','category':'weekly'}))
        for stage in ('data_owner','logistics_assignment','logistics_scheduling'):
            self.checked(self.s.api_client.put(f'/api/platform/decisions/{cid}/responsibilities/{stage}',json={'expected_updated_at':None,'owner_user_id':USER_A,'approver_user_id':None if stage=='data_owner' else USER_A}))
        return cid,orders,fleet

    def admit(self,body):
        rid=str(uuid4());self.checked(self.s.api_client.post('/api/runs',params={'run_id':rid},json=body),202);return rid

    def approve(self,rid,cid,node='logistics_assignment'):
        return self.checked(self.s.api_client.post('/api/runs/'+rid+'/approve',json={'case_id':cid,'node_id':node}))

    def nodes(self,cid):return self.checked(self.s.api_client.get('/api/decision-cases/'+cid))['decision_case']['nodes']

    def scheduling(self,cid,orders,fleet,source):
        return self.body(cid,orders,fleet,node='logistics_scheduling',source=source)

    def test_multiple_runs_reopen_current_and_downstream_without_destroying_evidence(self):
        cid,orders,fleet=self.case();self.s.start_worker();body=self.body(cid,orders,fleet)
        r1=self.finish(self.admit(body));r2=self.finish(self.admit(body));a=self.approve(r2['id'],cid)
        self.assertEqual(self.nodes(cid)['logistics_assignment']['approved_run_id'],r2['id'])
        s1=self.finish(self.admit(self.scheduling(cid,orders,fleet,r2['id'])));s1a=self.approve(s1['id'],cid,'logistics_scheduling')
        people=self.s.sql(f"SELECT md5(string_agg(to_jsonb(a)::text,'' ORDER BY node_id)) FROM decision_assignments a WHERE decision_case_id='{cid}';")
        s2id=self.admit(self.scheduling(cid,orders,fleet,r2['id']));nodes=self.nodes(cid)
        self.assertEqual(nodes['logistics_assignment']['status'],'approved');self.assertIsNone(nodes['logistics_scheduling']['approved_run_id'])
        self.assertEqual(nodes['logistics_scheduling']['latest_run_id'],s2id)
        self.finish(s2id);self.approve(s2id,cid,'logistics_scheduling')
        r3id=self.admit(body);nodes=self.nodes(cid)
        self.assertIsNone(nodes['logistics_assignment']['approved_run_id']);self.assertEqual(nodes['logistics_scheduling']['status'],'stale')
        self.assertEqual(self.s.api_client.post('/api/runs/'+s2id+'/approve',json={'case_id':cid,'node_id':'logistics_scheduling'}).status_code,409)
        self.finish(r3id);self.approve(r3id,cid)
        s3=self.finish(self.admit(self.scheduling(cid,orders,fleet,r3id)));self.approve(s3['id'],cid,'logistics_scheduling')
        self.assertTrue(all(self.nodes(cid)[n]['status']=='approved' for n in ('logistics_assignment','logistics_scheduling')))
        for original in (a,s1a):
            saved=self.checked(self.s.api_client.get('/api/runs/'+original['id']))
            for key in ('result_fingerprint','input_fingerprint','approved_at','approved_by_user_id','result_json'):
                self.assertEqual(saved[key],original[key],key)
            self.assertIsNotNone(saved['superseded_at'])
        self.assertEqual(self.s.sql(f"SELECT md5(string_agg(to_jsonb(a)::text,'' ORDER BY node_id)) FROM decision_assignments a WHERE decision_case_id='{cid}';"),people)
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_runs;'),'6')
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_cases;'),'1')
        # Attribute/governance edits do not retire approvals or create another Case.
        detail=self.checked(self.s.api_client.get('/api/platform/decisions/'+cid))
        self.checked(self.s.api_client.patch('/api/platform/decisions/'+cid,json={'expected_updated_at':detail['updated_at'],'label':'SEMANA 44','category':'monthly'}))
        data=self.checked(self.s.api_client.get(f'/api/platform/decisions/{cid}/responsibilities'))['stages']['data_owner']
        self.checked(self.s.api_client.put(f'/api/platform/decisions/{cid}/responsibilities/data_owner',json={'expected_updated_at':data['updated_at'],'owner_user_id':None}))
        self.assertTrue(all(self.nodes(cid)[n]['status']=='approved' for n in ('logistics_assignment','logistics_scheduling')))
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_cases;'),'1')

    def test_readiness_requires_applied_attributes_and_each_canonical_owner(self):
        orders,fleet=self.upload('orders'),self.upload('fleet');cid=str(uuid4());client=self.s.api_client
        self.checked(client.post('/api/decision-cases',json={'id':cid,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}))
        path=f'/api/platform/decisions/{cid}'
        self.assertEqual(client.get(path+'/workflow-readiness').status_code,409)
        detail=self.checked(client.get(path))
        self.checked(client.patch(path,json={'expected_updated_at':detail['updated_at'],'label':'Atributos aplicados','category':'weekly'}))
        self.assertEqual(client.get(path+'/workflow-readiness').status_code,409)
        self.checked(client.put(path+'/responsibilities/data_owner',json={'expected_updated_at':None,'owner_user_id':USER_A}))
        self.assertTrue(self.checked(client.get(path+'/workflow-readiness'))['ready'])
        self.assertEqual(client.get(path+'/workflow-readiness?node_id=logistics_assignment').status_code,409)
        snapshot=self.checked(client.get(path+'/responsibilities'));self.assertNotIn('data_steward',snapshot['stages'])
        self.checked(client.put(path+'/responsibilities/logistics_assignment',json={'expected_updated_at':None,'owner_user_id':USER_A}))
        self.assertTrue(self.checked(client.get(path+'/workflow-readiness?node_id=logistics_assignment'))['ready'])
        self.assertEqual(client.put(path+'/responsibilities/data_steward',json={'expected_updated_at':None,'owner_user_id':USER_A}).status_code,422)
        import httpx
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
            self.assertEqual(viewer.put(path+'/responsibilities/logistics_assignment',json={'expected_updated_at':None,'owner_user_id':VIEWER}).status_code,403)
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as other:
            self.assertEqual(other.get(path+'/responsibilities').status_code,404)

    def test_legacy_steward_remains_historical_but_is_operationally_a_data_owner(self):
        cid,_,_=self.case()
        self.s.sql(f"DELETE FROM dation_private.member_responsibilities WHERE user_id='{USER_A}' AND responsibility='data_owner'; INSERT INTO dation_private.member_responsibilities VALUES('{self.s.workspace_a}','{USER_A}','data_steward');")
        candidates=self.checked(self.s.api_client.get('/api/platform/team?candidates=true&responsibility=data_owner'))
        self.assertIn(USER_A,[m['user_id'] for m in candidates['members']])
        snapshot=self.checked(self.s.api_client.get(f'/api/platform/decisions/{cid}/responsibilities'))
        self.assertTrue(snapshot['stages']['data_owner']['owner_eligible'])
        self.assertNotIn('data_steward',snapshot['stages'])
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM dation_private.member_responsibilities WHERE user_id='{USER_A}' AND responsibility='data_steward';"),'1')

    def test_another_operator_cannot_execute_or_approve_the_assigned_owners_decision(self):
        import httpx
        cid,orders,fleet=self.case()
        self.s.sql(f"UPDATE workspace_members SET status='active',access_role='operator' WHERE user_id='{DISABLED}';")
        set_roles(self.s.api_client,DISABLED,['decision_owner'])
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[DISABLED]},trust_env=False,timeout=30) as other:
            self.assertEqual(other.post('/api/runs',params={'run_id':str(uuid4())},json=self.body(cid,orders,fleet)).status_code,403)
            self.assertEqual(self.s.sql('SELECT count(*) FROM decision_runs;'),'0')
            self.s.start_worker();run=self.finish(self.admit(self.body(cid,orders,fleet)))
            self.assertEqual(other.post('/api/runs/'+run['id']+'/approve',json={'case_id':cid,'node_id':'logistics_assignment'}).status_code,403)
            self.assertIsNone(self.checked(self.s.api_client.get('/api/runs/'+run['id']))['approved_at'])

    def test_upgrade_reopening_preserves_a_run_selected_after_other_candidates(self):
        cid,orders,fleet=self.case();self.s.start_worker();body=self.body(cid,orders,fleet)
        first=self.finish(self.admit(body));self.finish(self.admit(body));approved=self.approve(first['id'],cid)
        from pathlib import Path
        migration=(Path(__file__).parents[3]/'supabase/migrations/20261022020000_decision_run_reopening.sql').read_text()
        reconcile=migration.split('-- Existing candidates become current under the same rule; no evidence is rewritten.',1)[1].split('-- A persisted Case',1)[0]
        self.s.sql(reconcile)
        self.assertEqual(self.nodes(cid)['logistics_assignment']['approved_run_id'],first['id'])
        # Reproduce an admission from the old policy, then apply the upgrade reconciliation.
        self.s.sql('ALTER TABLE decision_runs DISABLE TRIGGER decision_runs_reopen;')
        try:latest=self.admit(body)
        finally:self.s.sql('ALTER TABLE decision_runs ENABLE TRIGGER decision_runs_reopen;')
        self.s.sql(reconcile)
        node=self.nodes(cid)['logistics_assignment'];self.assertIsNone(node['approved_run_id']);self.assertEqual(node['latest_run_id'],latest)
        historical=self.checked(self.s.api_client.get('/api/runs/'+first['id']))
        self.assertEqual(historical['approved_at'],approved['approved_at']);self.assertEqual(historical['result_json'],approved['result_json'])
        self.assertEqual(historical['superseded_by_run_id'],latest)

    def test_attributes_keep_case_but_different_data_pack_forks_idempotently(self):
        cid,orders,fleet=self.case();old=self.checked(self.s.api_client.get('/api/platform/decisions/'+cid))
        changed=self.checked(self.s.api_client.patch('/api/platform/decisions/'+cid,json={'expected_updated_at':old['updated_at'],'label':'SEMANA 44','category':'monthly','description':'Revisión de atributos'}))
        self.assertEqual(changed['id'],cid)
        original=self.s.sql(f"SELECT to_jsonb(c)::text FROM decision_cases c WHERE id='{cid}';")
        from fixtures import csv_input
        other=self.checked(self.s.api_client.post('/api/datasets/upload',params={'dataset_type':'orders'},files={'file':('orders-new.csv',csv_input('orders')+b'\n','text/csv')}))['dataset']
        pack={'expected_updated_at':changed['updated_at'],'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}
        self.assertEqual(self.checked(self.s.api_client.put(f'/api/platform/decisions/{cid}/data-pack',json=pack))['id'],cid)
        pack['orders_dataset_id']=other['id']
        fork=self.checked(self.s.api_client.put(f'/api/platform/decisions/{cid}/data-pack',json=pack))
        self.assertNotEqual(fork['id'],cid)
        self.assertEqual(self.checked(self.s.api_client.put(f'/api/platform/decisions/{cid}/data-pack',json=pack))['id'],fork['id'])
        self.assertEqual(self.s.sql(f"SELECT to_jsonb(c)::text FROM decision_cases c WHERE id='{cid}';"),original)
        self.assertEqual(self.s.sql('SELECT count(*) FROM decision_cases;'),'2')
        self.assertEqual(self.s.api_client.put(f'/api/platform/decisions/{cid}/data-pack',json={**pack,'expected_updated_at':old['updated_at']}).status_code,409)
