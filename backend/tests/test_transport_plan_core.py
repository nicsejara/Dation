"""U6: structural invariants, adversarial certification and independent oracles."""
from datetime import date
from decimal import Decimal as D, localcontext
from fractions import Fraction
from itertools import product, permutations
import json
from pathlib import Path
import unittest

from app.engines.assignment.transport_contracts import TransportPlanInput, EngineCertificationError
from app.engines.assignment.transport_plan import run_transport_plan, IDENTITY
from app.engines.assignment.transport_validator import certify_transport_plan
from app.engines.common.day_resource_feasibility import day_resource_feasibility
from app.results import registry
from app.results.canonical import core_result_fingerprint, canonical_bytes
from app.results.contracts import EngineCoreResult
from tests.ultimate_fixtures import context, RUN1


def order(oid='O1', pallets='70', *, split=True, **changes):
    value=dict(order_id=oid,origin_id='A',destination_id='B',distance_km='480',
        ready_date='2026-11-02',delivery_due_date='2026-11-08',priority='MEDIUM',
        split_allowed=split,requested={'pallets':pallets},compatibility_groups=['DRY'])
    value.update(changes)
    return value


def resource(rid='E1', cap='26', services=2, *, source='EXTERNAL', **changes):
    value=dict(resource_id=rid,source=source,guaranteed_capacity={'pallets':cap},
        lanes=[['A','B']],compatibility_groups=['DRY'])
    if source=='EXTERNAL':value.update(services_available=services,availability_source='CONFIRMED',
        external_cost={'cost_model':'PER_TRIP','rate':'100','billing_basis':None})
    else:value.update(units_available=services,base_origin_id='A',operating_cost_per_km=None)
    value.update(changes)
    return value


def request(orders=None, resources=None, *, dims=('pallets',), options=None, model_changes=None, context_changes=None):
    data=context().model_dump(mode='python')
    data.update(active_dimensions=list(dims),primary_dimension=dims[0],
        case_policy={'primary_goal':'MAXIMIZE_SERVICE'},node_policy={'primary_goal':'MAXIMIZE_SERVICE'})
    data.update(context_changes or {})
    model=dict(workspace_id=data['workspace_id'],model_id=data['logistics_model_id'],version_id=data['logistics_model_version_id'],
        version=data['logistics_model_version'],configuration_hash=data['model_hash'],operating_role=data['operating_role'],
        primary_dimension=data['primary_dimension'],active_dimensions=list(dims),allowed_sources=['OWN','EXTERNAL'],
        homogeneous_loads_declared=False,split_permitted=True,currency_policy=data['currency_policy'],contract_registry_version='ULTIMATE_CONTRACTS_V1')
    model.update(model_changes or {})
    return TransportPlanInput.model_validate(dict(model=model,context=data,demands=[order()] if orders is None else orders,
        resources=[resource()] if resources is None else resources,run_id=RUN1,result_generated_at='2026-11-02T00:00:00Z',options=options or {}))


def coverage(result):
    v=result.output.core.metrics.demand_coverage
    return v.assigned,v.unassigned


def external_oracle(quantities, capacities):
    """Brute force whole orders into finite services, no engine helpers/objective."""
    best=0
    for placements in product(range(-1,len(capacities)),repeat=len(quantities)):
        loads=[0]*len(capacities)
        for amount,target in zip(quantities,placements):
            if target>=0:loads[target]+=amount
        if all(load<=cap for load,cap in zip(loads,capacities)):
            best=max(best,sum(q for q,p in zip(quantities,placements) if p>=0))
    return best


def temporal_oracle(windows, cycles, units):
    """Exhaustive day/unit placements. No CP-SAT or TransitEstimator call."""
    domains=[[(day,unit) for day in range(first,last+1) for unit in range(units)] for first,last in windows]
    for placements in product(*domains):
        if all(ui!=uj or di+cycles[i]<=dj or dj+cycles[j]<=di
               for i,(di,ui) in enumerate(placements) for j,(dj,uj) in enumerate(placements) if i<j):
            return True
    return False


def rebind_mutant_core(data):
    """Keep the T1 envelope valid so adversarial tests reach the certifier."""
    data['output']['evidence']['core_result_fingerprint']=core_result_fingerprint(EngineCoreResult.model_validate(data['output']['core']))
    return data


class TransportPlanCoreTests(unittest.TestCase):
    def test_A_70_pallets_finite_services_three_trips(self):
        result=run_transport_plan(request(resources=[resource('E1','26',2,maximum_capacity={'pallets':'30'}),resource('E2','30',1)]))
        self.assertEqual(coverage(result),(70,0))
        self.assertEqual(result.output.core.metrics.trip_count,3)
        self.assertEqual({u.resource_id:u.services_used for u in result.resource_usage},{'E1':2,'E2':1})
        self.assertIsNone(result.output.core.metrics.total_cost)

    def test_F_capacity_gap_is_valid_partial_business_result(self):
        result=run_transport_plan(request())
        self.assertEqual(coverage(result),(52,18))
        self.assertEqual(result.residuals['O1'].pallets,18)
        self.assertTrue(result.output.core.feasibility.solution_found)
        self.assertEqual(result.output.core.engine.solver_status,'FEASIBLE')
        self.assertEqual(result.output.core.metrics.trip_count,2)
        reasons=[r for r in result.output.evidence.reasons if r.code=='CAPACITY_GAP']
        self.assertEqual(len(reasons),1)
        self.assertEqual(reasons[0].claim_strength,'OBSERVED')

    def test_non_split_28_uses_guaranteed_30_only(self):
        result=run_transport_plan(request([order(pallets='28',split=False)],[resource('A','26',3,maximum_capacity={'pallets':'30'}),resource('B','30',1)]))
        self.assertEqual(coverage(result),(28,0))
        self.assertEqual([t.resource_id for t in result.output.core.transport_plan.trips],['B'])

    def test_non_split_cannot_use_maximum_or_26_plus_2(self):
        result=run_transport_plan(request([order(pallets='28',split=False)],[resource(maximum_capacity={'pallets':'30'})]))
        self.assertEqual(coverage(result),(0,28))
        self.assertEqual(result.output.core.transport_plan.trips,())
        self.assertIn('NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY',{r.code for r in result.output.evidence.reasons})

    def test_Model_disables_split_even_if_order_allows(self):
        result=run_transport_plan(request([order(pallets='28')],model_changes={'split_permitted':False}))
        self.assertEqual(coverage(result),(0,28))

    def test_M_all_vector_dimensions_constrain_non_split(self):
        resources=[resource('A',guaranteed_capacity={'pallets':'30','weight_kg':'20000'}),resource('B',guaranteed_capacity={'pallets':'30','weight_kg':'26000'})]
        for weight,expected in [('28000',0),('24000',28)]:
            with self.subTest(weight=weight):
                result=run_transport_plan(request([order(split=False,requested={'pallets':'28','weight_kg':weight})],resources,dims=('pallets','weight_kg')))
                self.assertEqual(coverage(result)[0],expected)
                if expected:self.assertEqual(result.output.core.transport_plan.trips[0].resource_id,'B')

    def test_split_preserves_exact_vector_and_fraction_display(self):
        result=run_transport_plan(request([order(requested={'pallets':'70','weight_kg':'140000','volume_m3':'7','units':'140'})],
            [resource(guaranteed_capacity={'pallets':'26','weight_kg':'52000','volume_m3':'2.6','units':'52'})],dims=('pallets','weight_kg','volume_m3','units')))
        self.assertEqual(result.residuals['O1'].model_dump(),{'pallets':D(18),'weight_kg':D(36000),'volume_m3':D('1.8'),'units':D(36)})
        for trip in result.output.core.transport_plan.trips:
            a=trip.orders[0]
            self.assertEqual(Fraction(a.load.pallets)/70,Fraction(a.load.weight_kg)/140000)
            self.assertEqual(a.allocation_fraction,D('.371429'))

    def test_precision_lattice_does_not_split_dimensions_independently(self):
        result=run_transport_plan(request([order(requested={'pallets':'.003','volume_m3':'.000002'})],
            [resource(guaranteed_capacity={'pallets':'.002','volume_m3':'.000001'})],dims=('pallets','volume_m3')))
        self.assertEqual(coverage(result),(0,D('.003')))

    def test_zero_primary_demand_still_preserves_other_active_dimension(self):
        result=run_transport_plan(request([order(requested={'pallets':'0','weight_kg':'100'})],
            [resource(guaranteed_capacity={'pallets':'1','weight_kg':'100'})],dims=('pallets','weight_kg')))
        self.assertEqual(result.residuals['O1'].weight_kg,0)
        self.assertIsNone(result.demand_resolution[0].coverage_ratio)

    def test_D_compatible_orders_consolidate_one_service(self):
        result=run_transport_plan(request([order('A','6',split=False),order('B','8',split=False)],[resource(services=1)]))
        self.assertEqual(coverage(result),(14,0))
        self.assertEqual(result.output.core.metrics.trip_count,1)
        self.assertIn('CONSOLIDATED_COMPATIBLE_DEMAND',{r.code for r in result.output.evidence.reasons})

    def test_D_disjoint_windows_do_not_consolidate(self):
        orders=[order('A','6',split=False,delivery_due_date='2026-11-03'),order('B','8',split=False,ready_date='2026-11-06')]
        one=run_transport_plan(request(orders,[resource(services=1)]))
        self.assertEqual(one.output.core.metrics.trip_count,1)
        self.assertGreater(coverage(one)[1],0)
        two=run_transport_plan(request(orders,[resource(services=2)]))
        self.assertEqual(coverage(two),(14,0))
        self.assertEqual(two.output.core.metrics.trip_count,2)

    def test_consolidation_requires_route_distance_and_cargo_compatibility(self):
        for changed in [dict(destination_id='C'),dict(distance_km='481'),dict(compatibility_groups=['CHILLED'])]:
            with self.subTest(changed=changed):
                resources=[resource(services=2,lanes=[['A','B'],['A','C']],compatibility_groups=['DRY','CHILLED'])]
                result=run_transport_plan(request([order('A','6',split=False),order('B','8',split=False,**changed)],resources))
                self.assertEqual(result.output.core.metrics.trip_count,2)

    def test_incompatible_resource_is_certified_without_fake_selection_reason(self):
        result=run_transport_plan(request(resources=[resource(compatibility_groups=['CHILLED'])]))
        self.assertEqual(coverage(result),(0,70))
        self.assertIn('NO_COMPATIBLE_RESOURCE',{r.code for r in result.output.evidence.reasons})
        self.assertFalse(any(r.code.startswith('SELECTED_') for r in result.output.evidence.reasons))

    def test_external_quota_shared_across_lanes_and_days(self):
        orders=[order(str(i),'20',split=False,destination_id=str(i),ready_date=f'2026-11-0{2+i}',delivery_due_date=f'2026-11-0{2+i}') for i in range(3)]
        result=run_transport_plan(request(orders,[resource(services=2,lanes=[['A',str(i)] for i in range(3)])]))
        self.assertEqual(result.output.core.metrics.trip_count,2)
        self.assertEqual(coverage(result),(40,20))

    def test_assumed_external_availability_is_not_confirmed(self):
        result=run_transport_plan(request(resources=[resource(services=1,availability_source='ASSUMED')]))
        self.assertEqual(coverage(result),(26,44))
        self.assertEqual(result.resource_usage[0].availability_source,'ASSUMED')
        self.assertIn('ASSUMED_EXTERNAL_AVAILABILITY',{r.code for r in result.output.evidence.reasons})

    def test_zero_services_and_zero_own_units_are_business_gaps(self):
        for resources in [[resource(services=0)],[resource('OWN',services=0,source='OWN')]]:
            with self.subTest(resources=resources):
                result=run_transport_plan(request(resources=resources))
                self.assertEqual(coverage(result),(0,70))
                self.assertTrue(result.output.core.feasibility.solution_found)

    def test_unknown_availability_fails_input_boundary_not_infinity(self):
        for resources in [[resource(services=None,availability_source='UNKNOWN')],[resource('OWN',services=None,source='OWN')]]:
            with self.subTest(resources=resources),self.assertRaises(ValueError):request(resources=resources)

    def test_own_units_do_not_multiply_per_trip_capacity(self):
        result=run_transport_plan(request([order(pallets='78',split=False)],[resource('OWN',source='OWN',services=3)]))
        self.assertEqual(coverage(result),(0,78))
        split=run_transport_plan(request([order(pallets='78')],[resource('OWN',source='OWN',services=3)],context_changes={'planning_end':'2026-11-02'}))
        self.assertEqual(coverage(split),(78,0))
        self.assertEqual(len({w.unit_index for w in split.temporal_certificate.witness}),3)

    def test_own_single_unit_cannot_cover_simultaneous_incompatible_cycles(self):
        result=run_transport_plan(request([order('A','26',split=False,delivery_due_date='2026-11-02'),order('B','26',split=False,delivery_due_date='2026-11-02')],
            [resource('OWN',source='OWN',services=1)]))
        self.assertEqual(coverage(result),(26,26))

    def test_own_reuse_uses_T1_cycle_and_exclusive_interval(self):
        result=run_transport_plan(request([order(pallets='78')],[resource('OWN',source='OWN',services=1)]))
        self.assertEqual(coverage(result),(78,0))
        witnesses=sorted(result.temporal_certificate.witness,key=lambda w:w.dispatch)
        self.assertEqual(len(witnesses),3)
        self.assertTrue(all((w.available_again-w.dispatch).days==2 for w in witnesses))
        self.assertTrue(all(a.available_again<=b.dispatch for a,b in zip(witnesses,witnesses[1:])))
        self.assertIsNone(result.output.core.schedule)
        self.assertFalse(any('SCHEDULED' in r.code for r in result.output.evidence.reasons))

    def test_horizon_bounds_departure_not_arrival_or_return(self):
        for source in ['OWN','EXTERNAL']:
            result=run_transport_plan(request([order(pallets='1',distance_km='1150',ready_date='2026-11-08',delivery_due_date='2026-11-10')],[resource(source,services=1,source=source)]))
            self.assertEqual(coverage(result),(1,0))
            witness=result.temporal_certificate.witness[0]
            self.assertEqual((witness.dispatch,witness.arrival),(date(2026,11,8),date(2026,11,10)))
            if source=='EXTERNAL':self.assertIsNone(witness.available_again)

    def test_impossible_window_has_certified_date_reason(self):
        result=run_transport_plan(request([order(distance_km='1150',ready_date='2026-11-08',delivery_due_date='2026-11-09')]))
        self.assertEqual(coverage(result),(0,70))
        self.assertIn('DATE_WINDOW_INCOMPATIBLE',{r.code for r in result.output.evidence.reasons})

    def test_source_model_filter_and_role_do_not_grant_resource_capacity(self):
        signatures=[]
        for role in ['SHIPPER','LOGISTICS_PROVIDER','HYBRID']:
            result=run_transport_plan(request(resources=[resource('E'),resource('OWN',source='OWN')],
                model_changes={'operating_role':role,'allowed_sources':['EXTERNAL']},context_changes={'operating_role':role}))
            self.assertTrue(all(t.resource_source=='EXTERNAL' for t in result.output.core.transport_plan.trips))
            signatures.append([(t.trip_id,t.total_load) for t in result.output.core.transport_plan.trips])
        self.assertEqual(signatures[0],signatures[1]);self.assertEqual(signatures[1],signatures[2])

    def test_duplicate_ids_and_missing_dimensions_rejected_before_solver(self):
        bad=[lambda:request([order(),order()]),lambda:request(resources=[resource(),resource()]),
             lambda:request(dims=('pallets','weight_kg')),lambda:request([order(requested={'pallets':'0'})]),
             lambda:request(model_changes={'version':2}),lambda:request(resources=[resource(guaranteed_capacity={'pallets':'0'})])]
        for fixture in bad:
            with self.subTest(fixture=fixture),self.assertRaises(ValueError):fixture()

    def test_empty_demand_zero_trips_no_false_percent_or_cost(self):
        result=run_transport_plan(request([]))
        self.assertEqual(coverage(result),(0,0));self.assertEqual(result.demand_resolution,())
        self.assertIsNone(result.output.core.metrics.resource_mix.own_trip_ratio)
        self.assertIsNone(result.output.core.metrics.demand_coverage.ratio)
        self.assertTrue(result.output.core.feasibility.full_demand_coverage)

    def test_no_resources_conserves_all_orders(self):
        result=run_transport_plan(request([order('A','5'),order('B','3')],[]))
        self.assertEqual(coverage(result),(0,8))
        self.assertEqual(len(result.demand_resolution),2)

    def test_zero_solver_budget_is_UNKNOWN_without_inevitability_claim(self):
        result=run_transport_plan(request(options={'deterministic_budget':0}))
        self.assertEqual(result.output.core.engine.solver_status,'UNKNOWN')
        self.assertFalse(result.output.core.feasibility.solution_found)
        self.assertIsNone(result.output.core.feasibility.full_demand_coverage)
        self.assertNotIn('CAPACITY_GAP',{r.code for r in result.output.evidence.reasons})
        self.assertIsNone(result.output.evidence.solver.certificate)

    def test_candidate_budget_is_bounded_and_does_not_prove_gap_inevitable(self):
        result=run_transport_plan(request(options={'max_slots':1,'max_variables':4}))
        self.assertEqual(result.search.candidate_slots,1)
        self.assertIn('CANDIDATE_MODEL_BUDGET',result.search.limits)
        self.assertEqual(coverage(result),(26,44))
        self.assertEqual(result.output.core.engine.solver_status,'FEASIBLE')
        self.assertFalse(result.search.candidate_set_complete)
        self.assertLessEqual(result.search.variable_count,4)

    def test_rational_coverage_budget_returns_unknown_instead_of_integer_overflow(self):
        orders=[order('O'+str(i),str(q),split=False) for i,q in enumerate([1009,1013,1019,1021,1031,1033])]
        result=run_transport_plan(request(orders,[resource(cap='10000',services=6)]))
        self.assertEqual(result.output.core.engine.solver_status,'UNKNOWN')
        self.assertIn('RATIONAL_COVERAGE_INTEGER_BUDGET',result.search.limits)

    def test_candidate_evidence_contains_checked_vector_rejection_facts(self):
        req=request([order(pallets='28',split=False)],[resource(maximum_capacity={'pallets':'30'})])
        good=run_transport_plan(req)
        pair=next(c for c in good.output.evidence.constraints if c.code=='CANDIDATE_ELIGIBILITY')
        self.assertEqual(pair.facts['requested_pallets'],'28')
        self.assertEqual(pair.facts['guaranteed_pallets'],'26')
        self.assertIn('NON_SPLIT_CAPACITY',pair.facts['rejected_by'])
        bad=good.model_dump(mode='python')
        pair=next(c for c in bad['output']['evidence']['constraints'] if c['code']=='CANDIDATE_ELIGIBILITY')
        pair['facts']['guaranteed_pallets']='30'
        with self.assertRaisesRegex(EngineCertificationError,'Candidate vector facts differ'):
            certify_transport_plan(req,bad)

    def test_native_optimal_is_scoped_not_presented_as_T7_global_optimum(self):
        result=run_transport_plan(request())
        self.assertIn('OPTIMAL',result.search.native_statuses)
        self.assertEqual(result.output.core.engine.solver_status,'FEASIBLE')
        self.assertEqual(result.output.evidence.solver.certificate.kind,'FEASIBILITY')
        self.assertIsNone(result.output.evidence.solver.best_bound)

    def test_independent_kernel_unknown_never_certifies_selected_own_plan(self):
        result=run_transport_plan(request(resources=[resource('OWN',source='OWN',services=1)],options={'kernel_budget':0}))
        self.assertEqual(result.output.core.engine.solver_status,'UNKNOWN')
        self.assertEqual(result.output.core.transport_plan.trips,())
        self.assertEqual(result.temporal_certificate.status,'UNKNOWN')

    def test_cost_facts_do_not_drive_T6_selection_or_positive_reason(self):
        results=[]
        for rate in ['1','10000']:
            resources=[resource('A','26',2,external_cost={'cost_model':'PER_TRIP','rate':rate,'billing_basis':None}),resource('B','26',2)]
            results.append(run_transport_plan(request(resources=resources)))
        self.assertEqual(results[0].output.core.transport_plan,results[1].output.core.transport_plan)
        self.assertTrue(all(r.code not in {'SELECTED_LOWEST_COST_FEASIBLE','SELECTED_ONLY_FEASIBLE_RESOURCE','SELECTED_OWN_COST_ADVANTAGE','SELECTED_PRIORITY_PROTECTION'} for r in results[0].output.evidence.reasons))

    def test_permuted_rows_are_deterministic_and_preserve_inputs(self):
        orders=[order('B','14'),order('A','20',priority='HIGH'),order('C','5',split=False)]
        resources=[resource('B','26',1),resource('A','26',1)]
        fingerprints=[];evidence=[]
        for rows in permutations(orders):
            req=request(list(rows),list(reversed(resources)))
            before=canonical_bytes(req)
            result=run_transport_plan(req)
            self.assertEqual(canonical_bytes(req),before)
            fingerprints.append(core_result_fingerprint(result.output.core))
            evidence.append(canonical_bytes(result.output.evidence))
        self.assertEqual(len(set(fingerprints)),1);self.assertEqual(len(set(evidence)),1)

    def test_decimal_context_does_not_change_math(self):
        outputs=[]
        req=request()
        for precision in [6,28,60]:
            with localcontext() as ctx:
                ctx.prec=precision;outputs.append(core_result_fingerprint(run_transport_plan(req).output.core))
        self.assertEqual(len(set(outputs)),1)

    def test_registry_test_profile_is_explicit_inactive_and_legacy_unchanged(self):
        self.assertIs(registry.resolve_test_core(IDENTITY),run_transport_plan)
        with self.assertRaises(registry.RuntimeUnavailable):registry.resolve_runtime(IDENTITY,require_available=True)
        legacy=registry.RUNTIMES[0]
        self.assertEqual((legacy.engine_name,legacy.engine_version,legacy.result_schema),('logistics-assignment-engine','1.0.0','assignment_v1'))
        with self.assertRaises(registry.RuntimeUnavailable):registry.resolve_test_core(legacy.identity)
        metadata=json.loads((Path(__file__).parents[1]/'app/static/contracts/result-contracts-v1.json').read_text())
        self.assertEqual(registry.contract_metadata(),metadata)

    def test_small_non_split_oracle_exhaustive_equal_demand_units(self):
        # Equal order quantities make the independent maximum-quantity oracle
        # comparable to the structural fractional-coverage objective.
        for amount,count,cap,services in product([1,2,3],[1,2,3],[2,3,4],[0,1,2]):
            with self.subTest(amount=amount,count=count,cap=cap,services=services):
                expected=external_oracle([amount]*count,[cap]*services)
                result=run_transport_plan(request([order('O'+str(i),str(amount),split=False) for i in range(count)],[resource(cap=str(cap),services=services)]))
                self.assertEqual(coverage(result)[0],expected)

    def test_kernel_against_independent_day_unit_enumeration(self):
        for units,narrow in product([1,2],[True,False]):
            windows=[(0,0),(0,0)] if narrow else [(0,2),(0,2),(0,2)]
            trips=[dict(trip_id='T'+str(i),resource_id='OWN',distance_km='480',ready_date='2026-11-02',delivery_due_date='2026-11-02' if narrow else '2026-11-04') for i in range(len(windows))]
            req=request(resources=[resource('OWN',cap='1',services=units,source='OWN')])
            result=day_resource_feasibility(trips,req.resources,{'planning_start':'2026-11-02','planning_end':'2026-11-04'})
            self.assertEqual(result.status=='FEASIBLE',temporal_oracle(windows,[2]*len(windows),units))

    def test_kernel_external_no_return_unknown_and_global_quota(self):
        trips=[dict(trip_id='T'+str(i),resource_id='E1',distance_km='1150',ready_date='2026-11-02',delivery_due_date='2026-11-04') for i in range(2)]
        horizon={'planning_start':'2026-11-02','planning_end':'2026-11-08'}
        req=request(resources=[resource(services=2)])
        result=day_resource_feasibility(trips,req.resources,horizon)
        self.assertEqual(result.status,'FEASIBLE')
        self.assertTrue(all(w.unit_index is None and w.available_again is None for w in result.witness))
        self.assertEqual(day_resource_feasibility(trips,request(resources=[resource(services=1)]).resources,horizon).status,'INFEASIBLE')
        unknown=resource(services=None,availability_source='UNKNOWN')
        self.assertEqual(day_resource_feasibility(trips,[unknown],horizon).status,'UNKNOWN')

    def test_certifier_rejects_wrong_residual_and_source_and_references(self):
        req=request();good=run_transport_plan(req)
        mutations=[]
        bad=good.model_dump(mode='python');bad['residuals']['O1']['pallets']+=1;mutations.append(bad)
        bad=good.model_dump(mode='python');bad['resource_usage'][0]['services_available']+=1;mutations.append(bad)
        bad=good.model_dump(mode='python');bad['demand_resolution'][0]['trip_ids']=();mutations.append(bad)
        bad=good.model_dump(mode='python');bad['output']['core']['transport_plan']['trips'][0]['orders'][0]['allocation_fraction']=D('.5');mutations.append(bad)
        for bad in mutations:
            with self.subTest(mutation=mutations.index(bad)),self.assertRaises(EngineCertificationError):certify_transport_plan(req,bad)

    def test_certifier_rejects_vector_capacity_and_non_split_mismatch(self):
        req=request([order(pallets='10',split=False)],[resource(cap='26',services=1)])
        good=run_transport_plan(req)
        for field,value in [('resource_source','OWN'),('distance_km',D('481')),('orders',[{'order_id':'O1','allocation_fraction':D('.5'),'load':{'pallets':D('10')}}])]:
            bad=good.model_dump(mode='python');bad['output']['core']['transport_plan']['trips'][0][field]=value
            rebind_mutant_core(bad)
            with self.subTest(field=field),self.assertRaisesRegex(EngineCertificationError,'source mismatch|Route/distance modified|Fraction display differs'):
                certify_transport_plan(req,bad)
        bad=good.model_dump(mode='python');trip=bad['output']['core']['transport_plan']['trips'][0]
        trip['guaranteed_capacity']['pallets']=D('30');trip['utilization']['pallets']=D('.3333')
        with self.assertRaisesRegex(EngineCertificationError,'Guaranteed capacity changed'):
            certify_transport_plan(req,rebind_mutant_core(bad))

    def test_certifier_rejects_original_solver_service_and_unit_overcommit(self):
        req=request();result=run_transport_plan(req)
        reduced=request(resources=[resource(services=1)])
        with self.assertRaisesRegex(EngineCertificationError,'quota facts differ'):
            certify_transport_plan(reduced,result)
        own=request([order(pallets='26')],[resource('OWN',source='OWN',services=1)])
        result=run_transport_plan(own)
        zero=request([order(pallets='26')],[resource('OWN',source='OWN',services=0)])
        with self.assertRaisesRegex(EngineCertificationError,'OWN units changed'):
            certify_transport_plan(zero,result)

    def test_structural_priority_is_explicit_and_not_an_economic_goal(self):
        result=run_transport_plan(request([order('HIGH','30',priority='HIGH'),order('MEDIUM','30',priority='MEDIUM')],[resource(cap='40',services=1)]))
        self.assertEqual({o.order_id:o.assigned.pallets for o in result.demand_resolution},{'HIGH':D('30'),'MEDIUM':D('10')})
        self.assertIsNone(result.output.core.feasibility.policy_feasible)
        self.assertEqual(result.search.version,'D1_STRUCTURAL_FRACTION_COVERAGE_V1')

    def test_kernel_zero_units_window_and_unknown_budget_are_distinct(self):
        fixed=[dict(trip_id='T1',resource_id='OWN',distance_km='480',ready_date='2026-11-02',delivery_due_date='2026-11-02')]
        horizon={'planning_start':'2026-11-02','planning_end':'2026-11-04'}
        self.assertEqual(day_resource_feasibility(fixed,[resource('OWN',source='OWN',services=0)],horizon).status,'INFEASIBLE')
        self.assertEqual(day_resource_feasibility(fixed,[resource('OWN',source='OWN',services=1)],horizon,deterministic_budget=0).status,'UNKNOWN')
        fixed[0]['distance_km']='1150'
        self.assertEqual(day_resource_feasibility(fixed,[resource('OWN',source='OWN',services=1)],horizon).status,'INFEASIBLE')

    def test_kernel_rejects_unstable_entity_references(self):
        fixed=[dict(trip_id='T1',resource_id='MISSING',distance_km='480',ready_date='2026-11-02',delivery_due_date='2026-11-04')]
        horizon={'planning_start':'2026-11-02','planning_end':'2026-11-04'}
        with self.assertRaises(ValueError):day_resource_feasibility(fixed,request().resources,horizon)
        fixed[0]['resource_id']='E1'
        with self.assertRaises(ValueError):day_resource_feasibility(fixed*2,request().resources,horizon)

    def test_certifier_rejects_own_overlap_and_invalid_unit_and_due(self):
        req=request([order(pallets='52')],[resource('OWN',source='OWN',services=1)])
        good=run_transport_plan(req)
        for mutate in ['unit','due','overlap']:
            bad=good.model_dump(mode='python');w=bad['temporal_certificate']['witness']
            if mutate=='unit':w[0]['unit_index']=1
            elif mutate=='due':w[0]['arrival']=date(2026,11,10)
            else:
                w[1]['dispatch']=w[0]['dispatch'];w[1]['arrival']=w[0]['arrival'];w[1]['available_again']=w[0]['available_again']
            with self.subTest(mutation=mutate),self.assertRaises(EngineCertificationError):certify_transport_plan(req,bad)

    def test_serialization_round_trip_still_certifies(self):
        req=request();good=run_transport_plan(req)
        self.assertTrue(certify_transport_plan(req,json.loads(good.model_dump_json())))


if __name__=='__main__':unittest.main()
