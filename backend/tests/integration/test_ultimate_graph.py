"""S5: real API/RPC projection, tenant/permissions, lifecycle and immutable lineage."""
import json,sys,unittest
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from ultimate_graph_fixture import GraphSandbox
from ultimate_graph_state import install_run
from auth_fixture import USER_A,USER_B,VIEWER
from tests.test_ultimate_data_contracts import model

D1='logistics_assignment';D2='logistics_scheduling'

class UltimateGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=GraphSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def ok(self,r):self.assertTrue(r.is_success,r.text);return r.json()
    def setUp(self):
        self.a=self.s.api_client
        m=self.ok(self.a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'T5 graph','configuration':model()['config_jsonb']}))
        self.v=self.ok(self.a.post('/api/platform/logistics-models/'+m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))
        self.c=self.new_case();self.cid=self.c['case']['id'];self.base='/api/platform/logistics-cases/'+self.cid
    def new_case(self):return self.ok(self.a.post('/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'T5 sin CSV','logistics_model_version_id':self.v['version']['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}))
    def graph(self):return self.ok(self.a.get(self.base+'/graph'))
    def nodes(self):return {n['id']:n for n in self.graph()['graph']['nodes']}
    def publish(self,entity='transport_demand',raw=None):
        state=self.ok(self.a.get(self.base+'/data'));raw=raw or self.a.get(self.base+'/data/templates/'+entity).content
        j=self.ok(self.a.post(self.base+'/data/uploads/'+entity,params={'upload_id':str(uuid4()),'contract_hash':state['contracts'][entity]['contract_hash']},files={'file':('T5.csv',raw,'text/csv')}))
        return self.ok(self.a.post(self.base+'/data/publish',json={'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':[{'slot_key':entity,'upload_id':j['id']}]}))
    def full(self):self.publish();self.publish('transport_resources')
    def owner(self):
        return self.ok(self.a.put('/api/platform/decisions/'+self.cid+'/responsibilities/data_owner',json={'expected_updated_at':None,'owner_user_id':USER_A}))
    def test_01_empty_case_snapshot_and_versioned_definitions(self):
        g=self.graph();self.assertEqual([n['node_state'] for n in g['graph']['nodes']],['DATA_REQUIRED','LOCKED']);self.assertFalse(g['graph']['runtime_execution_available']);self.assertEqual(g['case']['id'],self.cid)
    def test_02_demand_then_full_pack_and_contextual_config(self):
        self.publish();self.assertEqual(self.nodes()[D1]['node_state'],'DATA_REQUIRED');self.publish('transport_resources');self.owner();n=self.nodes()[D1];self.assertEqual(n['node_state'],'READY');self.assertFalse(n['runtime_available']);r=self.ok(self.a.get(self.base+'/graph/config/'+D1));self.assertEqual(r['configuration_context']['case_id'],self.cid);self.assertFalse(r['configuration_context']['admission_available'])
    def test_03_candidates_are_not_ready(self):
        state=self.ok(self.a.get(self.base+'/data'));raw=self.a.get(self.base+'/data/templates/transport_demand').content
        self.ok(self.a.post(self.base+'/data/uploads/transport_demand',params={'upload_id':str(uuid4()),'contract_hash':state['contracts']['transport_demand']['contract_hash']},files={'file':('T5.csv',raw,'text/csv')}));self.assertEqual(self.nodes()[D1]['node_state'],'DATA_REQUIRED')
    def test_04_cross_tenant_and_forged_nodes_denied(self):
        self.assertEqual(self.a.get(self.base+'/graph/config/future').status_code,422)
        import httpx
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as b:self.assertIn(b.get(self.base+'/graph').status_code,[403,404])
    def test_05_viewer_and_missing_owners_do_not_change_ready_state(self):
        self.full();self.assertEqual(self.nodes()[D1]['node_state'],'READY');self.assertEqual(self.a.get(self.base+'/graph/config/'+D1).status_code,409)
        import httpx
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as v:
            n=self.ok(v.get(self.base+'/graph'))['graph']['nodes'][0];self.assertEqual(n['node_state'],'READY');self.assertFalse(n['actions']['configure']['allowed'])
    def test_06_sql_rpc_not_publicly_executable(self):
        for role in ['anon','authenticated']:
            with self.assertRaises(AssertionError):self.s.sql(f"SET ROLE {role}; SELECT platform_ultimate_graph('{self.s.workspace_a}','{USER_A}','{self.cid}');")
    def test_07_in_progress_completed_approved_are_controlled_metadata(self):
        self.full();rid=install_run(self.s,self.a,self.cid,status='queued');self.assertEqual(self.nodes()[D1]['node_state'],'IN_PROGRESS')
        self.s.sql(f"UPDATE decision_runs SET status='error',error_message='T5 controlled failure' WHERE id='{rid}';")
        # A fresh Case for the completed publication, not a fake solver transition.
        self.c=self.new_case();self.cid=self.c['case']['id'];self.base='/api/platform/logistics-cases/'+self.cid;self.full();install_run(self.s,self.a,self.cid)
        self.assertEqual(self.nodes()[D1]['node_state'],'COMPLETED');self.assertEqual(self.nodes()[D2]['node_state'],'LOCKED')
    def test_08_approved_upstream_unlocks_d2_without_extra_csv(self):
        self.full();self.owner();rid=install_run(self.s,self.a,self.cid,approved=True);n=self.nodes();self.assertEqual(n[D1]['node_state'],'APPROVED');self.assertEqual(n[D2]['node_state'],'READY');self.assertEqual(n[D2]['requirements'],[]);self.assertEqual(n[D2]['upstream_run_id'],rid);self.assertEqual(self.ok(self.a.get(self.base+'/graph/config/'+D2))['configuration_context']['upstream_run_id'],rid)
    def test_09_historical_run_selection_does_not_move_graph(self):
        self.full();old=install_run(self.s,self.a,self.cid,approved=True);new=install_run(self.s,self.a,self.cid,status='queued');before=self.graph()['graph'];selected=self.ok(self.a.get(self.base+'/graph',params={'node_id':D1,'run_id':old}));self.assertEqual(selected['selected_run']['id'],old);self.assertEqual(selected['graph'],before);self.assertEqual(self.nodes()[D1]['run_id'],new)
    def test_10_freshness_changes_do_not_delete_history(self):
        self.full();rid=install_run(self.s,self.a,self.cid,approved=True);raw=self.a.get(self.base+'/data/templates/transport_demand').content.replace(b'ORD-001',b'ORD-999');self.publish(raw=raw);n=self.nodes();self.assertEqual(n[D1]['freshness'],'STALE');self.assertEqual(n[D2]['node_state'],'LOCKED');self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE id='{rid}' AND approved_at IS NOT NULL;"),'1')
    def test_11_zero_trips_not_applicable_and_history_is_paged(self):
        self.full();rid=install_run(self.s,self.a,self.cid,approved=True,trip_count=0);self.assertEqual(self.nodes()[D2]['node_state'],'NOT_APPLICABLE');h=self.ok(self.a.get(self.base+'/graph/history/'+D1));self.assertEqual(h['total'],1);self.assertEqual(h['items'][0]['id'],rid);self.assertEqual(self.a.get(self.base+'/graph/history/'+D1+'?limit=0').status_code,422)
    def test_12_new_d2_preserves_upstream_and_config_read_is_pure(self):
        self.full();self.owner();up=install_run(self.s,self.a,self.cid,approved=True);install_run(self.s,self.a,self.cid,D2,approved=True)
        before=self.s.sql(f"SELECT jsonb_agg(to_jsonb(r) ORDER BY id) FROM decision_runs r WHERE decision_case_id='{self.cid}';")
        for _ in range(2):self.assertEqual(self.ok(self.a.get(self.base+'/graph/config/'+D2))['configuration_context']['upstream_run_id'],up)
        self.assertEqual(before,self.s.sql(f"SELECT jsonb_agg(to_jsonb(r) ORDER BY id) FROM decision_runs r WHERE decision_case_id='{self.cid}';"))
    def test_13_map_center_context_home_share_one_projection(self):
        self.full();self.owner();g=self.graph()['graph'];context=self.ok(self.a.get(self.base+'/context'));self.assertEqual(context['graph'],g)
        center=self.ok(self.a.get('/api/platform/decisions/'+self.cid));self.assertEqual(center['graph'],g);self.assertEqual(center['display_status'],'READY')
        home=self.ok(self.a.get('/api/platform/home'));item=next(x for x in home['recent_cases'] if x['case_id']==self.cid);self.assertEqual(item['graph'],g);self.assertEqual(item['resume']['view'],'logistics-map')
    def test_14_archived_case_is_readable_but_not_configurable(self):
        self.full();self.owner();row=self.ok(self.a.get(self.base+'/context'))['case'];self.ok(self.a.patch('/api/platform/decisions/'+self.cid,json={'expected_updated_at':row['updated_at'],'archived':True}))
        self.assertEqual(self.nodes()[D1]['node_state'],'READY');self.assertFalse(self.nodes()[D1]['actions']['configure']['allowed']);self.assertEqual(self.ok(self.a.get('/api/platform/decisions/'+self.cid))['display_status'],'archived')
    def test_15_wrong_case_or_node_run_binding_is_not_selected(self):
        self.full();rid=install_run(self.s,self.a,self.cid,approved=True);self.assertEqual(self.a.get(self.base+'/graph',params={'node_id':D2,'run_id':rid}).status_code,404)
        other=self.new_case()['case']['id'];self.assertEqual(self.a.get('/api/platform/logistics-cases/'+other+'/graph',params={'run_id':rid}).status_code,404)
    def test_16_approval_and_snapshot_definitions_are_not_mutated_by_reads(self):
        self.full();rid=install_run(self.s,self.a,self.cid,approved=True);before=self.s.sql(f"SELECT to_jsonb(r) FROM decision_runs r WHERE id='{rid}';")
        for _ in range(3):self.graph()
        self.assertEqual(before,self.s.sql(f"SELECT to_jsonb(r) FROM decision_runs r WHERE id='{rid}';"))
        with self.assertRaises(AssertionError):self.s.sql("UPDATE dation_private.decision_definition_versions SET definition_jsonb='{}' WHERE version='ULTIMATE_DECISION_GRAPH_V1';")
    def test_17_runtime_and_admission_stay_closed_with_complete_inputs(self):
        self.full();self.owner();before=self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{self.cid}';")
        for node in [D1,D2]:self.assertFalse(self.nodes()[node]['actions']['execute']['allowed']);self.assertFalse(self.nodes()[node]['runtime_available'])
        self.ok(self.a.get(self.base+'/graph/config/'+D1));self.assertEqual(before,self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{self.cid}';"))
    def test_18_superseded_downstream_keeps_count_history_actors_and_upstream(self):
        self.full();up=install_run(self.s,self.a,self.cid,approved=True);child=install_run(self.s,self.a,self.cid,D2,approved=True);install_run(self.s,self.a,self.cid,status='queued')
        n=self.nodes()[D2];self.assertEqual(n['node_state'],'LOCKED');self.assertEqual(n['history_count'],1)
        h=self.ok(self.a.get(self.base+'/graph/history/'+D2));self.assertEqual(h['items'][0]['id'],child);self.assertEqual(h['items'][0]['upstream_run_id'],up);self.assertTrue(h['items'][0]['superseded_at']);self.assertTrue(h['items'][0]['approval_actor'])
    def test_19_home_attention_outside_recent_cases_uses_current_graph(self):
        self.full();install_run(self.s,self.a,self.cid,approved=True)
        for _ in range(3):self.new_case()
        home=self.ok(self.a.get('/api/platform/home'));self.assertNotIn(self.cid,[c['case_id'] for c in home['recent_cases']])
        attention=next(i for i in home['attention']['items'] if i['case_id']==self.cid);self.assertEqual(attention['graph']['nodes'][1]['node_state'],'READY')
        raw=self.a.get(self.base+'/data/templates/transport_demand').content.replace(b'ORD-001',b'ORD-997');self.publish(raw=raw)
        home=self.ok(self.a.get('/api/platform/home'));self.assertNotIn(self.cid,[i['case_id'] for i in home['attention']['items']])

if __name__=='__main__':unittest.main()
