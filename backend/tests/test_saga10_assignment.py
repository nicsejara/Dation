"""Physical oracles and adversarial independent certification for D1 v2."""
from dataclasses import replace
from decimal import Decimal as D
from itertools import permutations
import unittest
from app.engines.assignment.cargo_inputs import run_cargo_policy,IDENTITY
from app.engines.assignment.cargo_model import CargoSearchLimit
from app.engines.assignment.transport_contracts import EngineCertificationError
from app.engines.assignment.transport_policy_validator import certify_policy_result
from app.results import contracts as c,registry
from app.results.canonical import core_result_fingerprint
from tests.saga10_fixtures import cargo_request,catalog_config,direct_config,bulk_config
from tests.test_transport_plan_core import resource,order


def solve(req):return run_cargo_policy(req,alternative_budget=0).recommended

def truck(rid='E1', pallets='26', weight='30000', volume='60', units='30000', services=1, **kw):
    return resource(rid,services=services,guaranteed_capacity={'pallets':pallets,'weight_kg':weight,'volume_m3':volume,'units':units},**kw)


class Saga10AssignmentTests(unittest.TestCase):
    def test_A_exact_mixed_order_and_product_conservation(self):
        core=solve(cargo_request()).output.core;trip=core.transport_plan.trips[0]
        self.assertEqual((trip.total_load.pallets,trip.total_load.weight_kg,trip.total_load.volume_m3,trip.total_load.units),(12,13140,D('27.24'),11520))
        self.assertEqual(core.engine.engine_version,'3.0.0');self.assertEqual(core.engine.solver_status,'OPTIMAL')
        self.assertEqual(core.metrics.total_cost.amount,100)
        self.assertEqual({x.presentation_id:(x.requested,x.assigned,x.unserved) for x in core.transport_plan.cargo.lines},{'PAL-JUICE':(5,5,0),'PAL-WATER':(4,4,0),'PAL-SODA':(3,3,0)})
        self.assertEqual(sum(p.product_units for a in core.transport_plan.cargo.allocations for p in a.products),11520)

    def test_B_20_physical_pallets(self):
        trip=solve(cargo_request(specifications=[('B',[('PAL-JUICE','20')],True)])).output.core.transport_plan.trips[0]
        self.assertEqual((trip.total_load.weight_kg,trip.total_load.volume_m3,trip.total_load.units),(19700,D('43.2'),19200))

    def test_discrete_three_pallets_cannot_split_into_halves(self):
        cfg=catalog_config();cfg['active_dimensions']=['pallets']
        core=solve(cargo_request(cfg,[('O',[('PAL-JUICE','3')],True)],[resource(cap='1.5',services=2)])).output.core
        self.assertEqual(core.metrics.demand_coverage.assigned,2)
        self.assertEqual(sorted(x.quantity for x in core.transport_plan.cargo.allocations),[1,1])
        cfg=direct_config(split_permitted=True,homogeneous_loads_declared=True,cargo={'input_mode':'direct','split_policy':'DISCRETE','compatibility_policy':'UNIFORM_DECLARED'})
        core=solve(cargo_request(cfg,[order(pallets='3')],[resource(cap='1.5',services=2)])).output.core
        self.assertEqual(core.metrics.demand_coverage.assigned,2);self.assertIsNone(core.transport_plan.cargo)

    def test_line_resource_eligibility_distinct_from_coload(self):
        cfg=catalog_config();cfg['cargo']['compatibility_policy']='CATEGORIZED';cfg['homogeneous_loads_declared']=False
        for p in cfg['cargo']['products']:p['compatibility_groups']=['COLD' if p['product_id']=='JUICE' else 'DRY']
        specs=[('O',[('PAL-JUICE','1'),('PAL-WATER','1')],True)]
        core=solve(cargo_request(cfg,specs,[truck('C',compatibility_groups=['COLD']),truck('D',compatibility_groups=['DRY'])])).output.core
        self.assertEqual(core.metrics.demand_coverage.assigned,2);self.assertEqual(len(core.transport_plan.trips),2)
        self.assertEqual({a.presentation_id:next(t.resource_id for t in core.transport_plan.trips if t.trip_id==a.trip_id) for a in core.transport_plan.cargo.allocations},{'PAL-JUICE':'C','PAL-WATER':'D'})
        core=solve(cargo_request(cfg,specs,[truck('BOTH',services=2,compatibility_groups=['COLD','DRY'])])).output.core
        self.assertEqual(len(core.transport_plan.trips),2)
        cfg['cargo']['co_load_pairs']=[['COLD','DRY']]
        core=solve(cargo_request(cfg,specs,[truck('BOTH',compatibility_groups=['COLD','DRY'])])).output.core
        self.assertEqual(core.metrics.trip_count,1)

    def test_indivisible_order_not_subset_of_lines(self):
        cfg=catalog_config();cfg['split_permitted']=False;cfg['cargo']['split_policy']='INDIVISIBLE'
        core=solve(cargo_request(cfg,[('O',[('PAL-JUICE','2'),('PAL-WATER','1')],False)],[truck(pallets='2',services=2)])).output.core
        self.assertEqual(core.metrics.demand_coverage.assigned,0);self.assertFalse(core.transport_plan.trips)
        self.assertTrue(all(x.assigned==0 for x in core.transport_plan.cargo.lines))

    def test_consolidation_flag_is_independent_of_split(self):
        for consolidate,count in [(True,1),(False,2)]:
            cfg=catalog_config();cfg['consolidation_permitted']=consolidate
            core=solve(cargo_request(cfg,[('A',[('PAL-JUICE','1')],False),('B',[('PAL-WATER','1')],False)],[truck(services=2)])).output.core
            self.assertEqual(core.metrics.trip_count,count);self.assertEqual(core.metrics.demand_coverage.assigned,2)

    def test_weight_capacity_binds_even_when_pallets_fit(self):
        core=solve(cargo_request(specifications=[('O',[('PAL-JUICE','20')],True)],resources=[truck(weight='12000')])).output.core
        self.assertEqual(core.metrics.demand_coverage.assigned,12)
        self.assertEqual(core.transport_plan.trips[0].total_load.weight_kg,11820)

    def test_continuous_bulk_uses_explicit_density_and_quantum(self):
        r=resource(guaranteed_capacity={'weight_kg':'8500','volume_m3':'10'},services=2)
        core=solve(cargo_request(bulk_config(),[('B',[('BULK','12.125')],True)],[r])).output.core
        self.assertEqual(core.metrics.demand_coverage.assigned,D('12.125'))
        self.assertEqual(sum(t.total_load.weight_kg for t in core.transport_plan.trips),D('10306.25'))
        self.assertEqual(sum(x.quantity for x in core.transport_plan.cargo.allocations),D('12.125'))

    def test_permutation_and_boundaries(self):
        fingerprints=[core_result_fingerprint(solve(cargo_request(specifications=[('O',lines,True)])).output.core) for lines in permutations([('PAL-JUICE','1'),('PAL-WATER','1'),('PAL-SODA','1')])]
        self.assertEqual(len(set(fingerprints)),1)
        with self.assertRaises(CargoSearchLimit):solve(cargo_request(resources=[truck(services=3)],options={'max_slots':1}))
        with self.assertRaises(CargoSearchLimit):solve(cargo_request(options={'max_variables':2}))
        self.assertIs(registry.resolve_test_policy(IDENTITY),run_cargo_policy)
        with self.assertRaises(registry.RuntimeUnavailable):registry.resolve_runtime(IDENTITY,require_available=True)

    def test_independent_certificate_rejects_rebound_quantity_and_hidden_line(self):
        req=cargo_request();result=solve(req)
        for mutate in ('quantity','hide','resolution','product'):
            data=result.structural.model_dump(mode='python');detail=data['output']['core']['transport_plan']['cargo']
            if mutate=='quantity':detail['allocations'][0]['quantity']+=1
            elif mutate=='hide':detail['allocations']=detail['allocations'][1:]
            elif mutate=='resolution':detail['lines'][0]['assigned']-=1;detail['lines'][0]['unserved']+=1
            else:detail['allocations'][0]['products'][0]['product_units']+=1
            data['output']['evidence']['core_result_fingerprint']=core_result_fingerprint(c.EngineCoreResult.model_validate(data['output']['core']))
            bad=type(result.structural).model_validate(data)
            with self.subTest(mutate=mutate),self.assertRaises(EngineCertificationError):certify_policy_result(req,replace(result,structural=bad))
        data=result.output.core.model_dump();data['transport_plan']['cargo']['allocations']=()
        core=c.EngineCoreResult.model_validate(data);ev=c.EngineEvidence.model_validate({**result.output.evidence.model_dump(),'core_result_fingerprint':core_result_fingerprint(core)})
        with self.assertRaises(EngineCertificationError):certify_policy_result(req,replace(result,output=c.EngineOutput(core=core,evidence=ev)))

    def test_zero_budget_and_hard_coverage_not_relaxed(self):
        core=solve(cargo_request(options={'deterministic_budget':0})).output.core
        self.assertEqual(core.engine.solver_status,'UNKNOWN');self.assertFalse(core.transport_plan.trips)
        core=solve(cargo_request(resources=[truck(pallets='1')],guards=[{'kind':'MINIMUM_DEMAND_COVERAGE','limit':'1'}])).output.core
        self.assertEqual(core.engine.solver_status,'INFEASIBLE');self.assertFalse(core.transport_plan.trips)

    def test_small_independent_integer_line_oracle(self):
        from itertools import product
        cfg=catalog_config();cfg['active_dimensions']=['pallets']
        for first,second in product(range(1,4),repeat=2):
            expected=None
            for placement in product(range(-1,2),repeat=first+second):
                loads=[placement.count(0),placement.count(1)]
                if loads[0]>2 or loads[1]>3:continue
                assigned=sum(p>=0 for p in placement);cost=sum(price for price,load in zip([100,150],loads) if load)
                score=(assigned,-cost)
                if expected is None or score>expected:expected=score
            result=solve(cargo_request(cfg,[('O',[('PAL-JUICE',str(first)),('PAL-WATER',str(second))],True)],
                [resource('A',cap='2',services=1),resource('B',cap='3',services=1,external_cost={'cost_model':'PER_TRIP','rate':'150','billing_basis':None})]))
            self.assertEqual((result.output.core.metrics.demand_coverage.assigned,-result.output.core.metrics.total_cost.amount),expected)

    def test_all_goals_preserve_line_quantities_and_OWN_cycle_price(self):
        for goal in ['MINIMIZE_COST','MAXIMIZE_SERVICE','MAXIMIZE_OWN_CAPACITY','MINIMIZE_TRIPS','BALANCED']:
            core=solve(cargo_request(goal=goal,resources=[truck('EXT'),truck('OWN',source='OWN',operating_cost_per_km='1')])).output.core
            self.assertEqual(core.metrics.demand_coverage.assigned,12)
            for trip in core.transport_plan.trips:
                self.assertEqual(trip.estimated_cost.amount,trip.distance_km*2 if trip.resource_source=='OWN' else 100)
            self.assertEqual(sum(row.quantity for row in core.transport_plan.cargo.allocations),12)

    def test_direct_multicategory_load_needs_explicit_coload_pair(self):
        from pydantic import ValidationError
        cfg=direct_config()
        with self.assertRaises(ValidationError):cargo_request(cfg,[order(split=False,compatibility_groups=['FOOD','CHEMICAL'])],[resource(compatibility_groups=['FOOD','CHEMICAL'])])
        cfg['cargo']['co_load_pairs']=[['FOOD','CHEMICAL']]
        result=solve(cargo_request(cfg,[order(pallets='1',split=False,compatibility_groups=['FOOD','CHEMICAL'])],[resource(compatibility_groups=['FOOD','CHEMICAL'])]))
        self.assertEqual(result.output.core.metrics.demand_coverage.assigned,1)

    def test_v1_runtime_cannot_silently_accept_v2_line_dtos(self):
        from pydantic import ValidationError
        from tests.test_transport_plan_core import request
        from app.engines.assignment.transport_contracts import TransportPlanInput
        old=request().model_dump();new=cargo_request().demands[0].model_dump()
        # Preserve the v1 physical vector/context while adding a v2-only line.
        old['demands'][0]['lines']=new['lines']
        with self.assertRaises(ValidationError):TransportPlanInput.model_validate(old)

    def test_CUSTOM_preferences_and_hard_guards_keep_same_policy_hierarchy(self):
        req=cargo_request(resources=[truck('EXT'),truck('OWN',source='OWN',operating_cost_per_km='1')]).model_dump()
        policy={'primary_goal':'CUSTOM','preferences':[{'kind':'COST','weight':'.5'},{'kind':'TRIPS','weight':'.5'}],
            'guardrails':[{'kind':'MINIMUM_DEMAND_COVERAGE','limit':'1'},{'kind':'MINIMUM_OWN_SHARE','limit':'.5'},{'kind':'MAXIMUM_EXTERNAL_SHARE','limit':'.5'}]}
        req['context']['case_policy']=req['context']['node_policy']=policy
        core=solve(req).output.core
        self.assertEqual(core.metrics.demand_coverage.assigned,12);self.assertGreaterEqual(core.metrics.resource_mix.own_trip_ratio,D('.5'))
        self.assertLessEqual(core.metrics.resource_mix.external_trip_ratio,D('.5'))
        cfg=catalog_config();cfg['active_dimensions']=['pallets']
        req=cargo_request(cfg,[('HIGH',[('PAL-JUICE','3')],True),('MED',[('PAL-WATER','3')],True)],[resource(cap='5',services=1)]).model_dump()
        req['demands'][0]['priority']='HIGH'
        result=solve(req);self.assertEqual({r.order_id:r.assigned.pallets for r in result.demand_resolution},{'HIGH':3,'MED':2})
