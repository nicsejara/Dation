"""U7 engine: independent price/packing oracles, policy and proof boundaries."""
from dataclasses import replace
from decimal import Decimal as D
from itertools import product,permutations
import json
from pathlib import Path
import unittest

from app.engines.assignment.transport_policy_result import run_transport_policy,plan_signature
from app.engines.assignment.transport_policies import PolicyRequirementsError
from app.engines.assignment.transport_policy_validator import certify_policy_result
from app.engines.assignment.transport_plan import IDENTITY
from app.engines.assignment.transport_contracts import EngineCertificationError
from app.results.canonical import canonical_bytes,core_result_fingerprint
from app.results import contracts as c,registry
from tests.test_transport_plan_core import request,order,resource

FIXTURES=json.loads((Path(__file__).parent/'fixtures/ultimate/t7-fixtures.json').read_text())['cases']


def policy_request(orders=None,resources=None,*,goal='MINIMIZE_COST',guards=(),preferences=(),**kwargs):
    policy={'primary_goal':goal,'guardrails':list(guards),'preferences':list(preferences)}
    return request(orders,resources,context_changes={'case_policy':policy,'node_policy':policy},**kwargs)


def solve(req,**options):return run_transport_policy(req,alternative_budget=0,**options).recommended


def independent_oracle(orders,capacities,prices):
    """Enumerate finite single-service bins with integer fixture quantities.

    No production cost function, objective builder, candidate helper or CP-SAT.
    """
    best=None
    for positions in product(range(-1,len(capacities)),repeat=len(orders)):
        loads=[0]*len(capacities);covered=[0,0,0]
        for (amount,priority),target in zip(orders,positions):
            if target>=0:loads[target]+=amount;covered[priority]+=amount
        if any(q>cap for q,cap in zip(loads,capacities)):continue
        cost=sum(price for price,load in zip(prices,loads) if load)
        score=(*covered,-cost)
        if best is None or score>best[0]:best=(score,cost)
    return best


class TransportPlanPolicyTests(unittest.TestCase):
    def test_B_C_independent_literal_cost_oracles(self):
        for name in ['B','C']:
            f=FIXTURES[name]
            with self.subTest(name=name):
                r=solve(policy_request([order(pallets='1',distance_km=f['distance_km'])],[resource('OWN','2',1,source='OWN',operating_cost_per_km=f['own_rate']),
                    resource('EXT','2',1,external_cost={'cost_model':'PER_TRIP','rate':f['external_per_trip'],'billing_basis':None})]))
                self.assertEqual(r.output.core.metrics.total_cost.amount,D(f['expected_cost']))
                self.assertEqual(r.output.core.transport_plan.trips[0].resource_source,f['expected_source'])
                self.assertEqual(r.output.core.engine.solver_status,'OPTIMAL')

    def test_N_mileage_basis_changes_real_choice(self):
        for name in ['N_ONE_WAY','N_ROUND_TRIP']:
            f=FIXTURES[name]
            r=solve(policy_request([order(pallets='1',distance_km=f['distance_km'])],[resource('KM','2',1,external_cost={'cost_model':'PER_KM','rate':'1','billing_basis':f['basis']}),resource('TRIP','2',1,external_cost={'cost_model':'PER_TRIP','rate':'150','billing_basis':None})]))
            self.assertEqual(r.output.core.metrics.total_cost.amount,D(f['expected_cost']))
            self.assertEqual(r.output.core.transport_plan.trips[0].resource_id,f['expected_resource'])

    def test_A_F_partial_gap_and_min_cost_never_prefers_empty(self):
        for resources,assigned,residual,cost in [([resource()],52,18,200),([resource('E1'),resource('E2','30',1,external_cost={'cost_model':'PER_TRIP','rate':'150','billing_basis':None})],70,0,350)]:
            r=solve(policy_request(resources=resources));m=r.output.core.metrics
            self.assertEqual((m.demand_coverage.assigned,m.demand_coverage.unassigned,m.total_cost.amount),(assigned,residual,cost))
            self.assertTrue(r.output.core.feasibility.solution_found and r.output.core.feasibility.policy_feasible)

    def test_G_priority_precedes_cost_and_csv_order(self):
        signatures=[]
        for rows in permutations([order('HIGH','30',priority='HIGH'),order('MEDIUM','30')]):
            r=solve(policy_request(list(rows),[resource(cap='40',services=1)]))
            self.assertEqual({o.order_id:o.assigned.pallets for o in r.demand_resolution},{'HIGH':30,'MEDIUM':10})
            signatures.append(core_result_fingerprint(r.output.core))
            self.assertIn('SELECTED_PRIORITY_PROTECTION',{p.code for p in r.output.evidence.reasons})
        self.assertEqual(len(set(signatures)),1)

    def test_all_goals_supported_without_relaxing_capacity(self):
        for goal in ['MINIMIZE_COST','MAXIMIZE_SERVICE','MAXIMIZE_OWN_CAPACITY','MINIMIZE_TRIPS','BALANCED','CUSTOM']:
            with self.subTest(goal=goal):
                prefs=[{'kind':'COST','weight':'.5'},{'kind':'TRIPS','weight':'.5'}] if goal=='CUSTOM' else []
                r=solve(policy_request([order(pallets='5')],[resource('E','5',1),resource('OWN','5',1,source='OWN',operating_cost_per_km='1')],goal=goal,preferences=prefs))
                self.assertEqual(r.output.core.metrics.demand_coverage.assigned,5)
                self.assertTrue(r.output.core.feasibility.hard_constraints_satisfied)

    def test_hard_coverage_guardrail_impossible_is_not_relaxed(self):
        r=solve(policy_request(guards=[{'kind':'MINIMUM_DEMAND_COVERAGE','limit':'1'}]))
        self.assertEqual(r.output.core.engine.solver_status,'INFEASIBLE')
        self.assertFalse(r.output.core.feasibility.solution_found)
        self.assertFalse(r.output.core.feasibility.policy_feasible)
        self.assertEqual(r.output.core.transport_plan.trips,())

    def test_hard_critical_coverage_and_source_mix_guardrails(self):
        guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'},{'kind':'MAXIMUM_EXTERNAL_SHARE','limit':'.5'},{'kind':'MINIMUM_OWN_SHARE','limit':'.5'}]
        r=solve(policy_request([order('HIGH','1',priority='HIGH'),order('OTHER','1',destination_id='C')],
            [resource('EXT','1',2,lanes=[['A','B'],['A','C']]),resource('OWN','1',1,source='OWN',operating_cost_per_km='10',lanes=[['A','B'],['A','C']])],guards=guards))
        self.assertEqual(r.output.core.metrics.demand_coverage.assigned,2)
        self.assertGreaterEqual(r.output.core.metrics.resource_mix.own_trip_ratio,D('.5'))
        self.assertEqual(next(o for o in r.demand_resolution if o.priority=='HIGH').assigned.pallets,1)

    def test_unknown_cost_blocks_dependent_goal_not_invented_zero(self):
        with self.assertRaises(PolicyRequirementsError):solve(policy_request(resources=[resource(external_cost={'cost_model':'PER_TRIP','rate':None,'billing_basis':None})]))
        r=solve(policy_request(resources=[resource(external_cost={'cost_model':'PER_TRIP','rate':None,'billing_basis':None})],goal='MAXIMIZE_SERVICE'))
        self.assertIsNone(r.output.core.metrics.total_cost)
        self.assertEqual(r.output.core.metrics.cost_completeness,'UNKNOWN')
        self.assertTrue(all(t.estimated_cost is None for t in r.output.core.transport_plan.trips))

    def test_partial_known_cost_is_not_a_total(self):
        r=solve(policy_request([order(pallets='4')],[resource('A','2',1),resource('B','2',1,external_cost={'cost_model':'PER_TRIP','rate':None,'billing_basis':None})],goal='MAXIMIZE_SERVICE'))
        self.assertEqual(r.output.core.metrics.cost_completeness,'PARTIAL')
        self.assertIsNone(r.output.core.metrics.total_cost)
        self.assertEqual(r.output.core.metrics.demand_coverage.assigned,4)

    def test_false_lowest_cost_or_only_resource_claims_are_omitted(self):
        r=solve(policy_request([order(pallets='1')],[resource('A','2',1),resource('OWN','2',1,source='OWN',operating_cost_per_km='100')],goal='MAXIMIZE_OWN_CAPACITY'))
        codes={p.code for p in r.output.evidence.reasons}
        self.assertNotIn('SELECTED_LOWEST_COST_FEASIBLE',codes)
        self.assertNotIn('SELECTED_ONLY_FEASIBLE_RESOURCE',codes)
        self.assertNotIn('SELECTED_OWN_COST_ADVANTAGE',codes)

    def test_cost_claim_has_complete_local_comparison_not_just_goal(self):
        r=solve(policy_request([order(pallets='1')],[resource('A','2',1),resource('B','2',1,external_cost={'cost_model':'PER_TRIP','rate':'300','billing_basis':None})]))
        reason=next(p for p in r.output.evidence.reasons if p.code=='SELECTED_LOWEST_COST_FEASIBLE')
        proof=next(p for p in r.output.evidence.constraints if p.evidence_id==reason.facts['certificate_ref'])
        self.assertEqual(proof.facts['scope'],'FIXED_OTHER_TRIPS')
        self.assertEqual(set(proof.facts['feasible_resource_ids']),{'A','B'})

    def test_budget_incomplete_never_claims_global_optimum_or_inevitability(self):
        r=solve(policy_request(options={'max_slots':1}))
        self.assertEqual(r.output.core.engine.solver_status,'FEASIBLE')
        self.assertEqual(r.output.evidence.solver.certificate.kind,'FEASIBILITY')
        self.assertTrue(all(p.claim_strength!='CERTIFIED_INFEASIBILITY' or p.entity_type!='CASE' for p in r.output.evidence.reasons))

    def test_zero_solver_budget_unknown_with_no_fake_recommendation(self):
        r=solve(policy_request(options={'deterministic_budget':0}))
        self.assertEqual(r.output.core.engine.solver_status,'UNKNOWN')
        self.assertIsNone(r.output.core.feasibility.policy_feasible)

    def test_alternatives_are_material_bounded_same_input_and_recoverable(self):
        req=policy_request([order(pallets='1')],[resource('E','2',1),resource('OWN','2',1,source='OWN',operating_cost_per_km='10')])
        r=run_transport_policy(req)
        self.assertTrue(1<=len(r.alternatives)<=3)
        self.assertEqual(len({plan_signature(p) for p in (r.recommended,*r.alternatives)}),1+len(r.alternatives))
        self.assertTrue(all(p.output.core.context==req.context and p.output.core.feasibility.policy_feasible for p in r.alternatives))

    def test_alternative_states_distinguish_not_computed_from_none(self):
        req=policy_request([order(pallets='1')],[resource(services=1)])
        self.assertEqual(run_transport_policy(req,alternative_budget=0).alternatives_status,'BUDGET_LIMIT')
        self.assertEqual(run_transport_policy(req).alternatives_status,'NO_MATERIAL_ALTERNATIVE')

    def test_policy_certifier_detects_forged_cost_with_valid_rebinding(self):
        req=policy_request([order(pallets='1')],[resource(services=1)])
        r=solve(req);data=r.output.core.model_dump();data['transport_plan']['trips'][0]['estimated_cost']['amount']=D('1')
        core=c.EngineCoreResult.model_validate(data)
        evidence=c.EngineEvidence.model_validate({**r.output.evidence.model_dump(),'core_result_fingerprint':core_result_fingerprint(core)})
        bad=replace(r,output=c.EngineOutput(core=core,evidence=evidence))
        with self.assertRaises(EngineCertificationError):certify_policy_result(req,bad)

    def test_small_independent_oracle_varied_quantities_and_prices(self):
        for amounts,prices in product([(1,2),(2,3),(1,3)],[(1,5),(8,2),(3,3)]):
            demands=[(amounts[0],0),(amounts[1],1)]
            expected=independent_oracle(demands,[2,3],prices)
            r=solve(policy_request([order('HIGH',str(amounts[0]),split=False,priority='HIGH'),order('MED',str(amounts[1]),split=False)],
                [resource('A','2',1,external_cost={'cost_model':'PER_TRIP','rate':str(prices[0]),'billing_basis':None}),resource('B','3',1,external_cost={'cost_model':'PER_TRIP','rate':str(prices[1]),'billing_basis':None})]))
            self.assertEqual(r.output.core.metrics.total_cost.amount,expected[1])
            self.assertEqual(tuple(sum(o.assigned.pallets for o in r.demand_resolution if o.priority==p) for p in ['HIGH','MEDIUM','LOW']),expected[0][:3])

    def test_registry_policy_is_test_only(self):
        self.assertIs(registry.resolve_test_policy(IDENTITY),run_transport_policy)
        with self.assertRaises(registry.RuntimeUnavailable):registry.resolve_runtime(IDENTITY,require_available=True)

    def test_explicit_Node_override_uses_snapshot_and_preserves_Case_guardrails(self):
        base={'primary_goal':'MINIMIZE_COST','guardrails':[{'kind':'MINIMUM_DEMAND_COVERAGE','limit':'1'}]}
        node={'primary_goal':'MAXIMIZE_OWN_CAPACITY','guardrails':base['guardrails'],'override':True,'override_reason':'Use internal capacity'}
        req=request([order(pallets='1')],[resource('E','2',1),resource('OWN','2',1,source='OWN',operating_cost_per_km='10')],context_changes={'case_policy':base,'node_policy':node})
        r=solve(req)
        self.assertEqual(r.output.core.transport_plan.trips[0].resource_source,'OWN')
        self.assertEqual(r.output.evidence.policy.case_goal,'MINIMIZE_COST')
        self.assertEqual(r.output.evidence.policy.effective_node_policy,'MAXIMIZE_OWN_CAPACITY')
        self.assertEqual(r.output.evidence.policy.override_reason,'Use internal capacity')

    def test_BALANCED_CUSTOM_preferences_have_bounded_explicit_normalization(self):
        for goal,prefs in [('BALANCED',()),('CUSTOM',[{'kind':'COST','weight':'.6'},{'kind':'OWN_CAPACITY','weight':'.4'}])]:
            r=solve(policy_request([order(pallets='1')],[resource('E','2',1),resource('OWN','2',1,source='OWN',operating_cost_per_km='1')],goal=goal,preferences=prefs))
            proof=next(p for p in r.output.evidence.constraints if p.code=='POLICY_CERTIFICATE')
            self.assertEqual(proof.facts['normalized_scale'],10000)
            self.assertGreater(int(proof.facts['bound_COST']),0)
            self.assertEqual(proof.facts['goal'],goal)


if __name__=='__main__':unittest.main()
