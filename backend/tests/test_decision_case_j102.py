"""J1.02 contracts and real CP-SAT guarantees; no production resources."""
from copy import deepcopy
from decimal import Decimal
import unittest
from uuid import uuid4

from pydantic import ValidationError
from app.models.decision_case_v2 import DecisionCaseDefinitionV2, UltimateCaseCreateV2
from app.domain.logistics.case_policy_v2 import CaseExecutionBindingV2
from app.domain.logistics.case_acceptance import evaluate_acceptance
from app.results.canonical import canonical_tree, canonical_bytes, content_sha256
from tests.test_transport_plan_policies import policy_request, solve
from tests.test_transport_plan_core import order, resource


def definition(**changes):
    value=dict(schema_version='decision_case_definition_v2',case_work_id=str(uuid4()),
        identity={'name':'Distribución QA','description':None},
        model_binding=dict(model_id=str(uuid4()),model_version_id=str(uuid4()),configuration_hash='a'*64,contract_hash='b'*64),
        decision_context=dict(planning_start='2026-11-02',planning_end='2026-11-08',horizon_type='WEEKLY',operating_mode='OPERATIONAL'),
        case_policy={'primary_goal':'MINIMIZE_COST','guardrails':[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]},
        business_rules={'prefer_own_fleet_on_cost_tie':True},acceptance_policy={'threshold':'.98'},
        approval_policy={'kind':'MANUAL_DECISION_OWNER'},provenance=None)
    value.update(changes)
    return DecisionCaseDefinitionV2.model_validate(value)


def binding(req, tie=True):
    return CaseExecutionBindingV2(definition_revision_id=uuid4(),definition_hash='d'*64,
        business_rules={'prefer_own_fleet_on_cost_tie':tie},acceptance_policy={'threshold':'.98'})


def bound(req,tie=True):
    data=req.model_dump(mode='python');data['context']['decision_definition']=binding(req,tie)
    return type(req).model_validate(data)


class DecisionCaseV2ContractTests(unittest.TestCase):
    def test_definition_is_versioned_strict_and_canonical(self):
        d=definition();self.assertEqual(DecisionCaseDefinitionV2.model_validate(canonical_tree(d)),d)
        self.assertEqual(content_sha256(canonical_bytes(d)),content_sha256(canonical_bytes(deepcopy(d))))
        for changes in [{'identity':{'name':' '*3}}, {'identity':{'name':'x'*121}},
                {'identity':{'name':'x','description':'x'*1001}}, {'schema_version':'decision_case_definition_v1'},
                {'unknown':'must not silently ignore'}, {'acceptance_policy':{'threshold':'1.01'}},
                {'approval_policy':{'kind':'AUTO'}}]:
            with self.subTest(changes=changes),self.assertRaises(ValidationError):definition(**changes)

    def test_rule_only_with_minimum_cost_and_one_hard_critical_guardrail(self):
        for policy in [{'primary_goal':'MAXIMIZE_SERVICE','guardrails':[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]},
                {'primary_goal':'MINIMIZE_COST','guardrails':[]},
                {'primary_goal':'MINIMIZE_COST','guardrails':[{'kind':'MINIMUM_OWN_SHARE','limit':'1'}]}]:
            with self.assertRaises(ValidationError):definition(case_policy=policy)
        for goal in ['MAXIMIZE_SERVICE','MAXIMIZE_OWN_CAPACITY','MINIMIZE_TRIPS','BALANCED','CUSTOM']:
            policy={'primary_goal':goal,'guardrails':[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'.5'}]}
            if goal=='CUSTOM':policy['preferences']=[{'kind':'COST','weight':'.5'},{'kind':'SERVICE','weight':'.5'}]
            definition(case_policy=policy,business_rules={'prefer_own_fleet_on_cost_tie':False})

    def test_create_envelope_cannot_substitute_model_or_policy(self):
        d=definition();c=dict(id=uuid4(),name=d.identity.name,logistics_model_version_id=d.model_binding.model_version_id,
            **d.decision_context.model_dump(),case_policy=d.case_policy,definition_v2=d)
        UltimateCaseCreateV2(**c)
        for key,value in [('name','Other'),('logistics_model_version_id',uuid4()),('planning_start','2026-11-01')]:
            with self.assertRaises(ValidationError):UltimateCaseCreateV2(**{**c,key:value})


class DecisionCaseV2SolverTests(unittest.TestCase):
    def test_incomplete_or_timeout_certificate_never_claims_acceptance(self):
        output=solve(self.tied()).output
        for patch in [{'candidate_set_complete':False},{'stage_0_status':'FEASIBLE'},{'stage_0_status':'UNKNOWN'}]:
            constraints=tuple(c.model_copy(update={'facts':{**c.facts,**patch}}) if c.code=='POLICY_CERTIFICATE' else c for c in output.evidence.constraints)
            evidence=output.evidence.model_copy(update={'constraints':constraints})
            self.assertEqual(evaluate_acceptance(output.model_copy(update={'evidence':evidence}))['status'],'NOT_EVALUABLE')

    def tied(self,own_rate='.50',**opts):
        return bound(policy_request([order('HIGH','10',priority='HIGH',distance_km='100')],
            [resource('A-EXTERNAL','10',1),resource('Z-OWN','10',1,source='OWN',operating_cost_per_km=own_rate)],
            guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}],**opts))

    def test_equal_proven_min_cost_prefers_own_with_exact_stage_evidence(self):
        r=solve(self.tied());self.assertEqual(r.output.core.engine.solver_status,'OPTIMAL')
        self.assertEqual(r.output.core.metrics.total_cost.amount,100)
        self.assertEqual(r.output.core.transport_plan.trips[0].resource_source,'OWN')
        proof=next(x for x in r.output.evidence.constraints if x.code=='POLICY_CERTIFICATE')
        self.assertIn('PREFER_OWN_FLEET_ON_COST_TIE',proof.facts.values())

    def test_secondary_never_pays_more_even_one_minor_unit(self):
        r=solve(self.tied('.50005'));self.assertEqual(r.output.core.metrics.total_cost.amount,100)
        self.assertEqual(r.output.core.transport_plan.trips[0].resource_source,'EXTERNAL')

    def test_hard_high_impossible_never_returns_80_percent_admissible(self):
        req=bound(policy_request([order('HIGH','100',priority='HIGH')],[resource(cap='80',services=1)],guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]),False)
        r=solve(req);self.assertEqual(r.output.core.engine.solver_status,'INFEASIBLE');self.assertFalse(r.output.core.feasibility.solution_found)

    def test_no_own_and_unknown_budget_are_honest(self):
        req=bound(policy_request([order(pallets='10')],[resource(cap='10',services=1)]))
        r=solve(req);self.assertEqual(r.output.core.metrics.resource_mix.own_trip_ratio,0)
        r=solve(self.tied(options={'deterministic_budget':0}));self.assertEqual(r.output.core.engine.solver_status,'UNKNOWN')
        self.assertNotEqual(evaluate_acceptance(r.output)['status'],'MEETS')

    def test_meets_misses_and_no_high_never_approve(self):
        for served,status in [('990','MEETS'),('960','MISSES')]:
            req=bound(policy_request([order('HIGH','200',priority='HIGH'),order('LOW','800',priority='LOW')],
                [resource(cap=served,services=1)],guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]),False)
            result=evaluate_acceptance(solve(req).output)
            self.assertEqual(result['status'],status);self.assertEqual(result['numerator'],served);self.assertEqual(result['denominator'],'1000')
            self.assertEqual(result['human_approval'],'SEPARATE_WORKFLOW');self.assertEqual(result['critical_coverage']['status'],'MEETS')
        req=bound(policy_request([order(pallets='10')],[resource(cap='10',services=1)],guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]),False)
        self.assertEqual(evaluate_acceptance(solve(req).output)['critical_coverage']['status'],'NOT_APPLICABLE')

    def test_legacy_and_mismatched_lineage_never_get_a_fake_kpi(self):
        legacy=solve(policy_request([order(pallets='1')],[resource(services=1)]))
        self.assertEqual(evaluate_acceptance(legacy.output)['status'],'NOT_CONFIGURED')
        result=solve(self.tied());self.assertEqual(evaluate_acceptance(result.output,expected_case_id=uuid4())['status'],'NOT_EVALUABLE')

    def test_zero_demands_and_infeasible_never_fake_success(self):
        empty=bound(policy_request([],[],guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]),False)
        self.assertEqual(evaluate_acceptance(solve(empty).output)['status'],'NOT_EVALUABLE')
        impossible=bound(policy_request([order('HIGH','100',priority='HIGH')],[resource(cap='80',services=1)],guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]),False)
        self.assertEqual(evaluate_acceptance(solve(impossible).output)['status'],'NOT_EVALUABLE')

    def test_mixed_catalog_metric_is_physical_primary_quantity_not_package_counts(self):
        from tests.saga10_fixtures import catalog_config,cargo_request
        from app.engines.assignment.cargo_inputs import run_cargo_policy
        cfg=catalog_config();cfg['primary_dimension']='weight_kg'
        req=bound(cargo_request(cfg,[('MIX',[('PAL-JUICE','1'),('PAL-WATER','1')],True)],guards=[{'kind':'CRITICAL_DEMAND_COVERAGE','limit':'1'}]),False)
        result=run_cargo_policy(req,alternative_budget=0).recommended
        evaluated=evaluate_acceptance(result.output)
        self.assertEqual(evaluated['unit'],'weight_kg');self.assertEqual(evaluated['denominator'],'2210');self.assertEqual(evaluated['numerator'],'2210');self.assertEqual(evaluated['status'],'MEETS')

    def test_node_override_cannot_bypass_tie_primary_or_hard_guardrail(self):
        data=self.tied().model_dump(mode='python')
        data['context']['node_policy'].update(primary_goal='MAXIMIZE_OWN_CAPACITY',override=True,override_reason='Forged override')
        with self.assertRaises(ValidationError):type(self.tied()).model_validate(data)
        data=self.tied().model_dump(mode='python');data['context']['node_policy']['guardrails'][0]['limit']='0.8'
        with self.assertRaises(ValidationError):type(self.tied()).model_validate(data)

