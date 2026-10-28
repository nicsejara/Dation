"""U5 controlled graph transitions, approvals, read sets and orthogonal gates."""
import copy,unittest
from app.domain.logistics.definitions import DEFINITIONS,definition_hash,definition_snapshot,validate_definitions
from app.domain.logistics.graph import resolve_case_graph,NODE_STATES
from app.domain.logistics.data_contracts import compile_contract,NORMALIZER_VERSION
from tests.test_ultimate_data_contracts import model

D1='logistics_assignment';D2='logistics_scheduling'
CID='10000000-0000-4000-8000-000000000001'

def fixture():
    version=model();ctx={'id':CID,'workflow_version':2,'graph_definition_version':'ULTIMATE_FOUNDATION_V1',
        'logistics_model_version_id':version['id'],'case_policy_hash':'a'*64,
        'case_policy_jsonb':{'primary_goal':'MINIMIZE_COST'},'planning_start':'2026-11-02','planning_end':'2026-11-08','status':'active'}
    entries=[{'slot_key':e,'contract_hash':compile_contract(version,e).contract_hash,'normalizer_version':NORMALIZER_VERSION,
        'model_version_id':version['id'],'record_count':5,'canonical_sha256':('b' if e=='transport_demand' else 'c')*64,
        'summary':{'unknown_availability_count':0,'unknown_cost_count':0}} for e in ['transport_demand','transport_resources']]
    responsibilities={'gates_enforced':True,'stages':{key:{'owner_eligible':True,'can_execute':True,'owner':{'id':CID}} for key in ['data_owner',D1,D2]}}
    return dict(context=ctx,model=version,pack={'entries':entries},run_history=[],responsibilities=responsibilities,runtime_capabilities={},permissions={'can_write':True})

def nodes(f):return {n['id']:n for n in resolve_case_graph(**f)['nodes']}

def run(f,node=D1,status='completed',approved=False,id='20000000-0000-4000-8000-000000000001',trips=2):
    n=nodes(f)[node]
    return {'id':id,'node_id':node,'status':status,'logistics_model_version_id':f['context']['logistics_model_version_id'],
        'case_policy_hash':f['context']['case_policy_hash'],'approved_at':'2026-11-02T00:00:00Z' if approved else None,
        'upstream_run_id':n['upstream_run_id'],'result_published':status=='completed','trip_count':trips,
        'graph_snapshot':{'definition_hash':definition_hash(),'read_set':n['read_set']}}

class UltimateGraphTests(unittest.TestCase):
    def test_empty_case_has_data_required_and_locked(self):
        f=fixture();f['pack']['entries']=[];n=nodes(f);self.assertEqual(n[D1]['node_state'],'DATA_REQUIRED');self.assertEqual(n[D2]['node_state'],'LOCKED');self.assertEqual(n[D1]['primary_action']['target']['case_id'],CID)
    def test_demand_only_is_not_ready(self):
        f=fixture();f['pack']['entries']=f['pack']['entries'][:1];self.assertEqual(nodes(f)[D1]['requirements'][0]['slot'],'transport_resources')
    def test_complete_pack_is_ready_with_runtime_unavailable(self):
        n=nodes(fixture());self.assertEqual(n[D1]['node_state'],'READY');self.assertFalse(n[D1]['runtime_available']);self.assertTrue(n[D1]['actions']['configure']['allowed']);self.assertFalse(n[D1]['actions']['execute']['allowed'])
    def test_exact_eight_states_are_closed(self):self.assertEqual(set(NODE_STATES),{'LOCKED','DATA_REQUIRED','READY','IN_PROGRESS','COMPLETED','APPROVED','COMING_SOON','NOT_APPLICABLE'})
    def test_d1_controlled_lifecycle(self):
        f=fixture()
        for status,approved,expected in [('queued',False,'IN_PROGRESS'),('running',False,'IN_PROGRESS'),('completed',False,'COMPLETED'),('completed',True,'APPROVED')]:
            f['run_history']=[run(f,status=status,approved=approved)];self.assertEqual(nodes(f)[D1]['node_state'],expected)
    def test_completed_d1_does_not_unlock_d2_but_approved_does(self):
        f=fixture();f['run_history']=[run(f)];self.assertEqual(nodes(f)[D2]['node_state'],'LOCKED');f['run_history'][0]['approved_at']='now';self.assertEqual(nodes(f)[D2]['node_state'],'READY');self.assertEqual(nodes(f)[D2]['requirements'],[])
    def test_approval_authority_beats_created_at(self):
        f=fixture();a=run(f,approved=True);b=run(f,id='later');b['created_at']='2099';f['run_history']=[b,a];self.assertEqual(nodes(f)[D1]['approved_run_id'],a['id'])
    def test_superseded_approval_is_historical_only(self):
        f=fixture();a=run(f,approved=True);a['superseded_at']='now';f['run_history']=[a];self.assertIsNone(nodes(f)[D1]['approved_run_id']);self.assertEqual(nodes(f)[D2]['node_state'],'LOCKED')
    def test_consumed_demand_change_makes_approval_stale_without_mutating_it(self):
        f=fixture();a=run(f,approved=True);f['run_history']=[a];before=copy.deepcopy(a);f['pack']['entries'][0]['canonical_sha256']='d'*64;n=nodes(f);self.assertEqual(n[D1]['freshness'],'STALE');self.assertEqual(n[D1]['node_state'],'READY');self.assertEqual(n[D2]['node_state'],'LOCKED');self.assertEqual(a,before)
    def test_irrelevant_enrichment_does_not_invalidate_d1_or_d2(self):
        f=fixture();f['run_history']=[run(f,approved=True)];f['run_history'].append(run(f,D2,approved=True,id='child'));before=nodes(f);f['pack']['entries'].append({'slot_key':'scheduling_enrichment','canonical_sha256':'f'*64});self.assertEqual(nodes(f),before)
    def test_d2_pins_exact_approved_upstream(self):
        f=fixture();f['run_history']=[run(f,approved=True)];child=run(f,D2,approved=True,id='child');child['upstream_run_id']='another';f['run_history'].append(child);self.assertEqual(nodes(f)[D2]['freshness'],'STALE');self.assertIsNone(nodes(f)[D2]['approved_run_id'])
    def test_zero_trips_is_not_applicable_and_creates_no_run(self):
        f=fixture();f['run_history']=[run(f,approved=True,trips=0)];n=nodes(f)[D2];self.assertEqual(n['node_state'],'NOT_APPLICABLE');self.assertIsNone(n['run_id']);self.assertFalse(n['actions']['configure']['allowed'])
    def test_unknown_trip_count_does_not_mean_zero(self):
        f=fixture();f['run_history']=[run(f,approved=True,trips=None)];self.assertEqual(nodes(f)[D2]['node_state'],'READY')
    def test_future_definition_never_executable(self):
        f=fixture();future=DEFINITIONS[0].model_copy(update={'id':'future_capacity','implemented':False});f['definitions']=(*DEFINITIONS,future);n=nodes(f)['future_capacity'];self.assertEqual(n['node_state'],'COMING_SOON');self.assertFalse(any(a['allowed'] for a in n['actions'].values()))
    def test_cycle_and_unknown_dependency_fail_closed(self):
        for defs in [(DEFINITIONS[0].model_copy(update={'dependencies':(D2,)}),DEFINITIONS[1]),(DEFINITIONS[0].model_copy(update={'dependencies':('unknown',)}),)]:
            with self.assertRaises(ValueError):validate_definitions(defs)
    def test_definition_snapshot_has_required_metadata_and_closure(self):
        s=definition_snapshot();self.assertEqual(s['dependency_closure'][D2],[D1]);self.assertEqual(s['nodes'][1]['required_inputs'],[]);self.assertEqual(len(definition_hash()),64)
    def test_technical_error_is_orthogonal_to_data(self):
        f=fixture();f['run_history']=[run(f,status='error')];n=nodes(f)[D1];self.assertEqual(n['node_state'],'READY');self.assertTrue(n['technical_failure']);self.assertFalse(n['actions']['configure']['allowed'])
    def test_viewer_owner_missing_archived_leave_ready_business_state(self):
        for kind in ['viewer','data_owner','owner','archived']:
            f=fixture()
            if kind=='viewer':f['permissions']['can_write']=False
            elif kind=='archived':f['context']['status']='archived'
            else:f['responsibilities']['stages']['data_owner' if kind=='data_owner' else D1]['owner_eligible']=False
            n=nodes(f)[D1];self.assertEqual(n['node_state'],'READY');self.assertFalse(n['actions']['configure']['allowed'])
    def test_incomplete_publication_is_not_completed_or_approved(self):
        f=fixture();r=run(f,approved=True);r['result_published']=False;f['run_history']=[r];self.assertEqual(nodes(f)[D1]['node_state'],'READY');self.assertEqual(nodes(f)[D2]['node_state'],'LOCKED')
    def test_contract_normalizer_and_unknowns_are_requirements(self):
        for key,value in [('contract_hash','bad'),('normalizer_version','unknown'),('summary',{'unknown_cost_count':1}),('summary',{'unknown_availability_count':1})]:
            f=fixture();f['pack']['entries'][1][key]=value;self.assertEqual(nodes(f)[D1]['node_state'],'DATA_REQUIRED')
    def test_new_run_targets_config_d1_d2_without_upload(self):
        f=fixture();f['run_history']=[run(f,approved=True)]
        for node in [D1,D2]:
            action=nodes(f)[node]['actions']['new_run'];self.assertEqual(action['target']['view'],'logistics-config');self.assertEqual(action['target']['node_id'],node);self.assertEqual(action['target']['case_id'],CID)
    def test_registry_order_does_not_change_dependencies(self):
        f=fixture();a=nodes(f);f['definitions']=tuple(reversed(DEFINITIONS));self.assertEqual(nodes(f),a)
    def test_unknown_graph_binding_never_falls_back_to_legacy(self):
        f=fixture();f['context']['graph_definition_version']='unknown'
        with self.assertRaises(ValueError):nodes(f)

if __name__=='__main__':unittest.main()
