import copy
from datetime import date, datetime, timezone
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path
import unittest
from uuid import UUID

from pydantic import ValidationError
from app.domain.logistics.base import MAX_SCALED_INTEGER
from app.domain.logistics.contracts import CasePolicy, NodePolicy, TransportResource, Demand
from app.domain.logistics.costs import trip_cost
from app.domain.logistics.units import CurrencyPolicy, Money, QuantityVector, scaled_integer
from app.results import contracts as c
from app.results import canonical as h
from app.results import registry as registry
from app.results.metrics import METRICS, MetricDescriptor, make_catalog, DaySchedulingMetrics
from app.results.reason_codes import REASON_CODES, ReasonEmission
from tests.ultimate_fixtures import core, evidence, package, context, ai_context, WS, RUN1, RUN2, ZERO

ROOT=Path(__file__).resolve().parents[1]


def repackage(data):
    data=copy.deepcopy(data)
    data['fingerprints']['result_fingerprint']=h.result_fingerprint(data)
    return c.DecisionResultPackageV1.model_validate(data)


def resource(source='EXTERNAL', model='PER_KM', rate='1', basis='ONE_WAY', **changes):
    value=dict(resource_id='REC-1',source=source,guaranteed_capacity={'pallets':'26'},lanes=[['ORI-1','DST-1']])
    value.update(dict(units_available=1,base_origin_id='ORI-1',operating_cost_per_km=rate) if source=='OWN' else dict(
        services_available=1,availability_source='CONFIRMED',external_cost=dict(cost_model=model,rate=rate,billing_basis=basis)))
    value.update(changes)
    return TransportResource.model_validate(value)


class UltimateDomainTests(unittest.TestCase):
    def test_money_zero_is_known_and_precision_is_pinned(self):
        policy=CurrencyPolicy(currency='ARS',minor_units=2)
        zero=Money(amount='0',currency='ARS').validate_policy(policy)
        self.assertEqual(zero.amount,D(0))
        for amount in ['.001','1.234']:
            with self.assertRaises(ValueError):Money(amount=amount,currency='ARS').validate_policy(policy)
        self.assertEqual(policy.rounded(D('1.005')),D('1.01'))
        self.assertEqual(CurrencyPolicy(currency='CLP',minor_units=0).rounded(D('1.5')),D(2))

    def test_no_fx_or_live_workspace_currency_inference(self):
        with self.assertRaises(ValueError):Money(amount='1',currency='USD').validate_policy(CurrencyPolicy(currency='ARS',minor_units=2))
        with self.assertRaises(ValueError):CurrencyPolicy(currency='ARS')
        with self.assertRaises(ValueError):Money(amount=None,currency='ARS')

    def test_scaled_integer_precision_and_overflow(self):
        self.assertEqual(scaled_integer(D('12.345'),3),12345)
        with self.assertRaises(ValueError):scaled_integer(D('1.0001'),3)
        with self.assertRaises(ValueError):scaled_integer(D(MAX_SCALED_INTEGER)+1,0)

    def test_dimensions_are_not_interchangeable_or_unlimited(self):
        vector=QuantityVector(pallets='2',weight_kg=None)
        vector.require(('pallets',),positive=True)
        with self.assertRaises(ValueError):vector.require(('weight_kg',),positive=True)
        with self.assertRaises(ValueError):QuantityVector(pallets='.0001')
        with self.assertRaises(ValueError):QuantityVector()

    def test_unknown_external_availability_is_not_confirmed(self):
        unknown=resource(services_available=None,availability_source='UNKNOWN')
        self.assertIsNone(unknown.services_available)
        for source in ['CONFIRMED','ASSUMED']:
            with self.assertRaises(ValueError):resource(services_available=None,availability_source=source)
        zero=resource(services_available=0)
        self.assertEqual(zero.services_available,0)

    def test_maximum_capacity_cannot_replace_guaranteed(self):
        with self.assertRaises(ValueError):resource(guaranteed_capacity={'pallets':'0'},maximum_capacity={'pallets':'30'})
        r=resource(maximum_capacity={'pallets':'30'})
        self.assertEqual(r.guaranteed_capacity.pallets,D(26))
        with self.assertRaises(ValueError):resource(maximum_capacity={'pallets':'20'})

    def test_cost_models_and_billing_basis_are_explicit(self):
        currency=CurrencyPolicy(currency='ARS',minor_units=2)
        cases=[(resource(model='PER_TRIP',rate='100',basis=None),'100'),
               (resource(rate='2',basis='ONE_WAY'),'960'),(resource(rate='2',basis='ROUND_TRIP'),'1920'),
               (resource(source='OWN',rate='2'),'1920')]
        for r,expected in cases:self.assertEqual(trip_cost(r,480,currency).amount,D(expected))
        with self.assertRaises(ValueError):resource(model='PER_KM',basis=None)
        with self.assertRaises(ValueError):resource(model='PER_TRIP',basis='ROUND_TRIP')

    def test_unknown_cost_is_never_manufactured_zero(self):
        policy=CurrencyPolicy(currency='ARS',minor_units=2)
        self.assertIsNone(trip_cost(resource(rate=None),480,policy))
        self.assertEqual(trip_cost(resource(rate='0'),480,policy).amount,D(0))

    def test_cost_rounding_does_not_depend_on_decimal_context(self):
        for precision in (2,28,60):
            with localcontext() as ctx:
                ctx.prec=precision
                self.assertEqual(trip_cost(resource(source='OWN',rate='1.005'),'1',CurrencyPolicy(currency='ARS',minor_units=2)).amount,D('2.01'))

    def test_override_is_explicit_and_cannot_relax_hard_guardrails(self):
        case=CasePolicy(primary_goal='MINIMIZE_COST',guardrails=[dict(kind='MAXIMUM_EXTERNAL_SHARE',limit='.5')])
        for limit in ['.6','1']:
            with self.assertRaises(ValueError):NodePolicy(primary_goal='MINIMIZE_TRIPS',override=True,override_reason='Cambio',guardrails=[dict(kind='MAXIMUM_EXTERNAL_SHARE',limit=limit)]).validate_case_policy(case)
        NodePolicy(primary_goal='MINIMIZE_TRIPS',override=True,override_reason='Cambio',guardrails=[dict(kind='MAXIMUM_EXTERNAL_SHARE',limit='.4')]).validate_case_policy(case)
        with self.assertRaises(ValueError):NodePolicy(primary_goal='MINIMIZE_COST',override=True)
        with self.assertRaises(ValueError):NodePolicy(primary_goal='MINIMIZE_TRIPS').validate_case_policy(case)

    def test_contracts_are_deeply_immutable(self):
        frozen=context()
        with self.assertRaises((ValueError,TypeError)):frozen.case_name='Changed'
        with self.assertRaises(TypeError):frozen.display_metadata['owner']='New owner'
        with self.assertRaises(TypeError):frozen.active_dimensions[0]='units'

    def test_nonfinite_floats_negative_quantities_and_timestamps_are_rejected(self):
        for value in [float('nan'),float('inf'),1.5,True,'NaN','Infinity','-1']:
            with self.subTest(value=str(value)),self.assertRaises(ValueError):QuantityVector(pallets=value)
        data=context().model_dump();data['planning_start']=datetime(2026,11,2,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):type(context()).model_validate(data)


class UltimateRegistryTests(unittest.TestCase):
    def test_three_legacy_identities_match_existing_dispatcher(self):
        from app.services.dispatch_job_service import engine_identity
        for node,schema in [('logistics_assignment','assignment_v1'),('logistics_scheduling','scheduling_v1'),(None,'dispatch_v2')]:
            name,version,old_schema=engine_identity(node)
            value=registry.resolve_persisted_runtime(dict(engine_name=name,engine_version=version,schema_version=old_schema),require_available=True)
            self.assertEqual(value.result_schema,schema)
            self.assertTrue(value.implemented and value.available)

    def test_known_ultimate_is_not_implemented_or_available(self):
        for schema in ['transport_plan_v1','day_scheduling_v1']:
            self.assertEqual(registry.resolve_schema(schema,1).cohort,'ULTIMATE')
            identity=core('d1' if schema=='transport_plan_v1' else 'd2').runtime_identity
            entry=registry.resolve_runtime(identity)
            self.assertFalse(entry.implemented or entry.available)
            with self.assertRaises(registry.RuntimeUnavailable):registry.resolve_runtime(identity,require_available=True)

    def test_persisted_identity_not_node_determines_resolution(self):
        row=dict(engine_name='logistics-assignment-engine',engine_version='1.0.0',schema_version='assignment_v1',node_id='logistics_scheduling')
        self.assertEqual(registry.resolve_persisted_runtime(row).result_schema,'assignment_v1')
        for key,value in [('engine_version','9.0.0'),('engine_name','other'),('schema_version','unknown')]:
            with self.assertRaises(ValueError):registry.resolve_persisted_runtime({**row,key:value})
        with self.assertRaises(ValueError):registry.resolve_persisted_runtime({'node_id':'logistics_assignment'})

    def test_ultimate_identity_requires_all_persisted_versions(self):
        row=dict(engine_name='transport_plan',engine_version='2.0.0',schema_version='transport_plan_v1',runtime_profile='transport_plan_v1',result_schema_version=1)
        self.assertFalse(registry.resolve_persisted_runtime(row).available)
        for key in ['runtime_profile','result_schema_version']:
            bad=dict(row);bad.pop(key)
            with self.assertRaises(ValueError):registry.resolve_persisted_runtime(bad)
        with self.assertRaises(ValueError):registry.resolve_persisted_runtime({**row,'result_schema_version':True})

    def test_unknown_schema_or_version_never_falls_back_to_dispatch(self):
        for payload in [{},{'schema_version':'unknown'},{'result_schema':'unknown','result_schema_version':1},
                        {'result_schema':'transport_plan_v1','result_schema_version':2}]:
            with self.assertRaises(registry.UnsupportedResultSchema):registry.resolve_result_header(payload)
        with self.assertRaises(ValueError):registry.resolve_schema('transport_plan_v1',True)

    def test_legacy_and_ultimate_headers_are_unambiguous(self):
        self.assertEqual(registry.resolve_result_header({'schema_version':'assignment_v1'}).cohort,'LEGACY')
        self.assertEqual(registry.resolve_result_header({'result_schema':'transport_plan_v1','result_schema_version':1}).cohort,'ULTIMATE')
        with self.assertRaises(ValueError):registry.resolve_result_header({'result_schema':'transport_plan_v1','result_schema_version':1,'schema_version':'assignment_v1'})
        with self.assertRaises(ValueError):registry.resolve_result_header({'schema_version':'assignment_v1'},dict(engine_name='logistics-scheduling-engine',engine_version='1.0.0',schema_version='scheduling_v1'))

    def test_lifecycle_adapter_does_not_rename_persisted_error(self):
        self.assertEqual(registry.lifecycle_status('error'),'FAILED')
        with self.assertRaises(ValueError):registry.lifecycle_status('unrecognized')

    def test_static_metadata_matches_authority_and_references_resolve(self):
        metadata=json.loads((ROOT/'app/static/contracts/result-contracts-v1.json').read_text())
        self.assertEqual(metadata,registry.contract_metadata())
        self.assertEqual(set(metadata['json_schemas']) & {'EngineCoreResult','EngineEvidence','DecisionResultPackageV1','DecisionContextV1','ApprovalReview'},
            {'EngineCoreResult','EngineEvidence','DecisionResultPackageV1','DecisionContextV1','ApprovalReview'})
        def refs(value):
            if isinstance(value,dict):
                if '$ref' in value:self.assertIn(value['$ref'].split('/')[-1],metadata['$defs'])
                for child in value.values():refs(child)
            elif isinstance(value,list):
                for child in value:refs(child)
        refs(metadata)
        self.assertTrue(all(not e['implemented'] for e in metadata['api']))


class UltimateReasonMetricTests(unittest.TestCase):
    def test_all_source_reason_codes_require_facts_and_provenance(self):
        self.assertEqual(len(REASON_CODES),24)
        for definition in REASON_CODES.values():
            self.assertTrue(definition.required_facts)
            with self.subTest(code=definition.stable_id),self.assertRaises(ValueError):
                ReasonEmission(emission_id='R1',code=definition.stable_id,entity_type=definition.entity_scope[0],entity_id='E1',
                    producer=definition.producer,claim_strength=definition.claim_strength,facts={},evidence_refs=['F1'])

    def test_non_split_reason_has_a_numerical_witness(self):
        args=dict(emission_id='R1',code='NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY',entity_type='ORDER',entity_id='ORD1',producer='transport_plan',
            claim_strength='CERTIFIED_INFEASIBILITY',facts=dict(split_allowed=False,dimension='pallets',requested='28',maximum_guaranteed_capacity='26'),evidence_refs=['CAP1'])
        valid=ReasonEmission(**args);self.assertEqual(valid.facts['requested'],D(28))
        for changes in [dict(requested='26'),dict(split_allowed=True),dict(requested=None),dict(maximum_guaranteed_capacity=26.0),dict(dimension='widgets')]:
            with self.assertRaises(ValueError):ReasonEmission(**{**args,'facts':{**args['facts'],**changes}})
        with self.assertRaises(ValueError):ReasonEmission(**{**args,'entity_type':'TRIP'})
        with self.assertRaises(ValueError):ReasonEmission(**{**args,'producer':'day_scheduling'})
        with self.assertRaises(ValueError):ReasonEmission(**{**args,'evidence_refs':[]})

    def test_global_comparison_requires_complete_candidate_certificate(self):
        args=dict(emission_id='R1',code='SELECTED_LOWEST_COST_FEASIBLE',entity_type='TRIP',entity_id='VIA1',producer='transport_plan',
            claim_strength='CERTIFIED_COMPARISON',facts=dict(selected_resource_id='REC1',selected_cost='10',currency='ARS',minimum_feasible_cost='10',candidate_set_complete=True,certificate_ref='C1'),evidence_refs=['C1'])
        ReasonEmission(**args)
        for changes in [dict(candidate_set_complete=False),dict(selected_cost='11'),dict(certificate_ref=''),dict(currency='implicit')]:
            with self.assertRaises(ValueError):ReasonEmission(**{**args,'facts':{**args['facts'],**changes}})

    def test_optimal_requires_proof_not_a_display_label(self):
        with self.assertRaises(ValueError):c.SolverEvidence(status='OPTIMAL',objective_value='10',best_bound='9',certificate=dict(kind='GLOBAL_OPTIMUM',evidence_ref='S1'))
        with self.assertRaises(ValueError):c.SolverEvidence(status='OPTIMAL',objective_value='10',best_bound='10',certificate=None)
        c.SolverEvidence(status='OPTIMAL',objective_value='10',best_bound='10',certificate=dict(kind='GLOBAL_OPTIMUM',evidence_ref='S1'))
        with self.assertRaises(ValueError):c.SolverEvidence(status='FEASIBLE',objective_value='10',best_bound='10',certificate=dict(kind='GLOBAL_OPTIMUM',evidence_ref='S1'))

    def test_unknown_solver_is_not_global_infeasibility_but_keeps_local_witnesses(self):
        data=evidence(core()).model_dump();data['solver']=dict(status='UNKNOWN',objective_value=None,best_bound=None,certificate=None)
        local=ReasonEmission(emission_id='R1',code='NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY',entity_type='ORDER',entity_id='ORD2',producer='transport_plan',
            claim_strength='CERTIFIED_INFEASIBILITY',facts=dict(split_allowed=False,dimension='pallets',requested='28',maximum_guaranteed_capacity='26'),evidence_refs=['CAP1'])
        data['reasons']=[local];c.EngineEvidence.model_validate(data)
        global_claim=ReasonEmission(emission_id='R2',code='HORIZON_CAPACITY_LIMIT',entity_type='CASE',entity_id=str(context().case_id),producer='transport_plan',
            claim_strength='CERTIFIED_INFEASIBILITY',facts=dict(planning_start='2026-11-02',planning_end='2026-11-08',feasibility_certificate_ref='H1'),evidence_refs=['H1'])
        data['reasons']=[global_claim]
        with self.assertRaises(ValueError):c.EngineEvidence.model_validate(data)

    def test_metric_producer_is_unique(self):
        item=next(iter(METRICS.values()));bad=item.model_dump();bad['producer']='day_scheduling'
        with self.assertRaises(ValueError):make_catalog([item,MetricDescriptor.model_validate(bad)])
        with self.assertRaises(ValueError):make_catalog([MetricDescriptor.model_validate(bad)])
        self.assertTrue(all(m.null_semantics and m.version==1 for m in METRICS.values()))

    def test_service_categories_and_expected_compliance_are_distinct(self):
        data=core('d2').metrics.model_dump()
        data.update(scheduled_trips=dict(scheduled=8,total=10,ratio='.8'),service_level=dict(on_time=6,at_risk=2,late=0,pre_horizon=1,unscheduled=1),on_time_ratio='.8')
        metric=DaySchedulingMetrics.model_validate(data)
        self.assertEqual(metric.service_level.on_time,6)
        self.assertEqual(metric.on_time_ratio,D('.8'))
        with self.assertRaises(ValueError):DaySchedulingMetrics.model_validate({**data,'on_time_ratio':'.6'})
        with self.assertRaises(ValueError):DaySchedulingMetrics.model_validate({**data,'service_level':{**data['service_level'],'late':1}})

    def test_zero_denominator_is_not_a_fabricated_ratio(self):
        data=core('d2').metrics.model_dump()
        data.update(scheduled_trips=dict(scheduled=0,total=0,ratio=None),service_level=dict(on_time=0,at_risk=0,late=0,pre_horizon=0,unscheduled=0),
            on_time_ratio=None,peak_dispatch_day=None,average_schedule_margin_days=None)
        DaySchedulingMetrics.model_validate(data)
        with self.assertRaises(ValueError):DaySchedulingMetrics.model_validate({**data,'on_time_ratio':'0'})


class UltimateResultContractTests(unittest.TestCase):
    def test_both_specialized_packages_and_engine_outputs_validate(self):
        for kind in ['d1','d2']:
            result=core(kind);c.EngineOutput(core=result,evidence=evidence(result));p=package(kind)
            self.assertEqual(c.DecisionResultPackageV1.model_validate_json(p.model_dump_json()),p)
            self.assertFalse(registry.resolve_runtime(result.runtime_identity).available)
            c.ResultContractBundle(core=result,evidence=evidence(result),package=p)

    def test_bundle_rejects_a_well_hashed_package_for_other_mathematics(self):
        result=core();data=package().model_dump()
        data['metrics']['total_cost']['amount']=D(20)
        data['transport_plan']['trips']['rows'][0]['estimated_cost']['amount']=D(20)
        altered=repackage(data)
        with self.assertRaises(ValueError):c.ResultContractBundle(core=result,evidence=evidence(result),package=altered)

    def test_review_and_policy_evidence_are_exact_copies_of_certified_facts(self):
        for kind in ['d1','d2']:
            data=package(kind).model_dump();data['approval_review']['hard_constraints_satisfied']=False
            with self.assertRaises(ValueError):repackage(data)
            data=package(kind).model_dump();data['evidence']['policy']['effective_node_policy']='MINIMIZE_TRIPS'
            with self.assertRaises(ValueError):repackage(data)
        data=package('d2').model_dump();data['approval_review']['at_risk_count']=2
        with self.assertRaises(ValueError):repackage(data)

    def test_versions_are_not_booleans_and_decimal_wire_is_lossless(self):
        data=package().model_dump();data['result_schema_version']=True
        with self.assertRaises(ValueError):repackage(data)
        self.assertEqual(Money(amount='1e3',currency='ARS').model_dump_json(),'{"amount":"1000","currency":"ARS"}')

    def test_context_cannot_switch_decision_metrics_or_current_overlay_run(self):
        ctx=ai_context();data=ctx.model_dump();data['decision_definition']['node_id']='logistics_scheduling'
        data['context_hash']=h.decision_context_hash(data)
        with self.assertRaises(ValueError):c.DecisionContextV1.model_validate(data)
        with self.assertRaises(ValueError):c.DecisionContextResponse(context=ctx,approval_overlay=dict(run_id=RUN2,result_fingerprint=ctx.provenance.result_fingerprint,
            approval_allowed=False,freshness='CURRENT',approval_blockers=['OWNER_REQUIRED']))

    def test_inconsistent_schema_node_body_and_currency_are_rejected(self):
        data=package().model_dump()
        for change in [dict(result_schema='dispatch_v2'),dict(result_schema_version=2),dict(schedule=core('d2').schedule.model_dump()),
                       dict(decision={**data['decision'],'node_id':'logistics_scheduling'}),
                       dict(metrics={**data['metrics'],'total_cost':dict(amount='10',currency='USD')})]:
            with self.subTest(change=list(change)),self.assertRaises(ValueError):repackage({**data,**change})

    def test_core_reasons_cannot_be_published_without_engine_facts(self):
        result=core();data=result.model_dump();data['transport_plan']['trips'][0]['reason_codes']=('SELECTED_LOWEST_COST_FEASIBLE',)
        changed=c.EngineCoreResult.model_validate(data)
        with self.assertRaises(ValueError):c.EngineOutput(core=changed,evidence=evidence(changed))

    def test_empty_inline_is_not_missing_or_corrupt_artifact(self):
        empty=c.InlineDataset[c.Trip](dataset_id='empty',row_schema='transport_trip_v1',schema_version=1,row_count=0,rows=[])
        self.assertEqual(empty.rows,())
        with self.assertRaises(ValueError):c.ReferenceDataset(dataset_id='missing',row_schema='transport_trip_v1',schema_version=1,row_count=0,artifacts=[])
        missing=c.ArtifactReadError(status='UNAVAILABLE',artifact_id=UUID(int=900),expected_sha256=ZERO,code='ARTIFACT_MISSING')
        self.assertFalse(hasattr(missing,'rows'))
        with self.assertRaises(ValueError):c.ArtifactReadError(status='CORRUPT',artifact_id=UUID(int=900),expected_sha256=ZERO,code='ARTIFACT_MISSING')

    def test_reference_manifest_and_tenant_run_core_binding(self):
        data=package().model_dump();ref=dict(artifact_id=UUID(int=900),workspace_id=WS,run_id=RUN1,kind='DETAIL_DATASET',part_key='part-1',
            artifact_schema='transport_trip_v1',schema_version=1,content_sha256=h.content_sha256(b'[]'),size_bytes=2,media_type='application/json',
            core_fingerprint=data['fingerprints']['core_result_fingerprint'],assembler_version='RESULT_ASSEMBLER_V1')
        data['artifact_manifest']['artifacts']=(ref,)
        data['details'][0]['data']=dict(mode='REFERENCE',delivery_version=1,dataset_id='plan',row_schema='transport_trip_v1',schema_version=1,row_count=1,artifacts=(ref,))
        repackage(data)
        for key,value in [('workspace_id',UUID(int=55)),('run_id',RUN2),('core_fingerprint','f'*64)]:
            bad=copy.deepcopy(data);bad['details'][0]['data']['artifacts'][0][key]=value
            with self.assertRaises(ValueError):repackage(bad)
        bad=copy.deepcopy(data);bad['artifact_manifest']['artifacts']=()
        with self.assertRaises(ValueError):repackage(bad)

    def test_data_reference_cannot_masquerade_as_inline_empty(self):
        with self.assertRaises(ValueError):c.InlineDataset[c.Trip](dataset_id='x',row_schema='transport_trip_v1',schema_version=1,row_count=1,rows=[])
        data=package().model_dump();data['details'][0]['data']['dataset_id']='other'
        with self.assertRaises(ValueError):repackage(data)
        with self.assertRaises(ValueError):c.InlineDataset[c.Trip](dataset_id='x',row_schema='day_schedule_trip_v1',row_count=1,rows=core().transport_plan.trips)

    def test_review_does_not_grant_current_authority(self):
        p=package();binding=dict(run_id=RUN1,result_fingerprint=p.fingerprints.result_fingerprint)
        overlay=c.ApprovalOverlay(**binding,approval_allowed=False,freshness='CURRENT',approval_blockers=['OWNER_REQUIRED'])
        response=c.ResultResponse(package=p,provenance=binding,approval_overlay=overlay)
        self.assertTrue(response.package.approval_review.decision_ready_for_review)
        self.assertFalse(response.approval_overlay.approval_allowed)
        self.assertEqual(h.result_fingerprint(response),p.fingerprints.result_fingerprint)
        data=p.model_dump();data['approval_review']['approval_allowed']=True
        with self.assertRaises(ValueError):repackage(data)
        with self.assertRaises(ValueError):c.ApprovalOverlay(**binding,approval_allowed=True,freshness='STALE',approval_blockers=[])

    def test_hard_violation_no_solution_is_not_review_ready(self):
        data=package().model_dump();data['feasibility'].update(solution_found=False,policy_feasible=False,full_demand_coverage=False)
        with self.assertRaises(ValueError):repackage(data)
        data['approval_review']['decision_ready_for_review']=False
        with self.assertRaises(ValueError):repackage(data)  # FEASIBLE still claims a usable solution

    def test_no_alternatives_computed_is_not_no_alternatives_exist(self):
        p=package();self.assertEqual(p.alternatives_state,'NOT_COMPUTED')
        data=p.model_dump();data['alternatives_state']='COMPUTED'
        with self.assertRaises(ValueError):repackage(data)

    def test_d2_cannot_reassign_or_change_upstream_identity(self):
        d1=core();d2=core('d2');c.validate_schedule_source(d1,d2,'c'*64)
        data=d2.model_dump();data['schedule']['trips'][0]['resource_id']='OTHER'
        with self.assertRaises(ValueError):c.validate_schedule_source(d1,c.EngineCoreResult.model_validate(data),'c'*64)
        with self.assertRaises(ValueError):c.validate_schedule_source(d1,d2,'d'*64)
        data=d2.model_dump();data['schedule']['trips'][0]['orders']=[]
        with self.assertRaises(ValueError):c.EngineCoreResult.model_validate(data)

    def test_api_discriminator_does_not_accept_client_engine_or_graph(self):
        frozen=context()
        args=dict(case_id=frozen.case_id,node_id='logistics_assignment',expected_context_hash=ZERO,
            model_version_id=frozen.logistics_model_version_id,data_pack_version_id=frozen.data_pack_version_id,node_policy=frozen.node_policy)
        c.UltimateRunRequest(**args)
        for key in ['engine_name','dependency_closure','runtime_profile']:
            with self.assertRaises(ValueError):c.UltimateRunRequest(**args,**{key:'client-selected'})
        with self.assertRaises(ValueError):c.UltimateRunRequest(**{**args,'node_id':'logistics_scheduling'})

    def test_ai_context_is_exact_versioned_and_compare_is_not_invented(self):
        ctx=ai_context();data=ctx.model_dump();data['case_policy']['primary_goal']='MINIMIZE_TRIPS'
        data['context_hash']=h.decision_context_hash(data)
        with self.assertRaises(ValueError):c.DecisionContextV1.model_validate(data)
        data=ctx.model_dump();data.update(mode='COMPARE',selected_alternative_ids=('ALT-UNKNOWN',));data['context_hash']=h.decision_context_hash(data)
        with self.assertRaises(ValueError):c.DecisionContextV1.model_validate(data)


class UltimateCanonicalTests(unittest.TestCase):
    def test_known_canonical_vectors_and_hashes(self):
        vectors=json.loads((ROOT/'tests/fixtures/ultimate/fingerprint-vectors-v1.json').read_text())
        for vector in vectors['canonical_vectors']:
            with self.subTest(vector=vector['name']):
                payload=vector['input']
                self.assertEqual(h.canonical_bytes(payload).decode(),vector['canonical_utf8'])
                self.assertEqual(h.content_sha256(h.canonical_bytes(payload)),vector['sha256'])
        self.assertEqual(h.canonical_bytes({'b':True,'a':D('1.2300')}),b'{"a":"1.23","b":true}')
        self.assertEqual(h.canonical_bytes(D('-0.000')),b'"0"')

    def test_unicode_dates_and_object_order_are_stable(self):
        self.assertEqual(h.canonical_bytes({'b':'e\u0301','a':date(2026,11,2)}),h.canonical_bytes({'a':'2026-11-02','b':'é'}))
        with self.assertRaises(ValueError):h.canonical_bytes({'é':1,'e\u0301':2})
        with self.assertRaises(ValueError):h.canonical_bytes(datetime(2026,11,2))

    def test_binary_floats_nonfinites_and_nonstring_keys_fail_closed(self):
        for value in [1.0,float('nan'),float('inf'),D('NaN'),{1:'x'}]:
            with self.subTest(value=str(value)),self.assertRaises(ValueError):h.canonical_bytes(value)

    def test_mathematical_hashes_exclude_run_display_clock_and_current_actor(self):
        original=core();data=original.model_dump();data['decision'].update(run_id=UUID(int=999),decision_label='Otro label')
        data['context'].update(case_name='Otra etiqueta',display_metadata={'owner_name':'Otra persona'})
        data['engine']['result_generated_at']=datetime(2026,11,3,tzinfo=timezone.utc)
        changed=c.EngineCoreResult.model_validate(data)
        self.assertEqual(changed.input_context_hash,original.input_context_hash)
        self.assertEqual(h.core_result_fingerprint(changed),h.core_result_fingerprint(original))

    def test_semantic_money_changes_mathematical_fingerprint(self):
        original=core();data=original.model_dump();data['metrics']['total_cost']['amount']=D(20)
        data['transport_plan']['trips'][0]['estimated_cost']['amount']=D(20)
        changed=c.EngineCoreResult.model_validate(data)
        self.assertNotEqual(h.core_result_fingerprint(changed),h.core_result_fingerprint(original))

    def test_artifacts_reject_future_hash_and_mutable_overlays(self):
        for value in [dict(result_fingerprint=ZERO),dict(fingerprints=dict(result_fingerprint=ZERO)),dict(signed_url='https://example.test/a'),dict(approval_allowed=True)]:
            with self.assertRaises(ValueError):h.artifact_bytes(value)
        content=h.artifact_bytes(dict(core_result_fingerprint=ZERO,source_transport_plan=dict(run_id=str(RUN1),result_fingerprint='c'*64),rows=[]))
        self.assertEqual(h.content_sha256(content),hashlib.sha256(content).hexdigest())

    def test_package_fingerprint_excludes_only_its_own_field(self):
        p=package();data=p.model_dump();data['fingerprints']['result_fingerprint']='f'*64
        self.assertEqual(h.result_fingerprint(data),p.fingerprints.result_fingerprint)
        with self.assertRaises(ValueError):c.DecisionResultPackageV1.model_validate(data)
        data=p.model_dump();data['decision']['run_id']=UUID(int=999)
        self.assertNotEqual(h.result_fingerprint(data),p.fingerprints.result_fingerprint)
        data=p.model_dump();data['context']['display_metadata']['signed_url']='https://example.test/private?token=x'
        with self.assertRaises(ValueError):repackage(data)

    def test_context_mode_selection_and_evidence_enter_v2_intent(self):
        ctx=ai_context();args=dict(provenance=ctx.provenance,context_hash=ctx.context_hash,mode='EXPLAIN',question=' ¿Por qué? ',selected_entity=None,evidence_hashes=[])
        first=c.DecisionIntentV2(**args);fingerprint=h.intent_hash_v2(first)
        for change in [dict(mode='REVIEW'),dict(selected_entity=dict(type='TRIP',id='VIA-001')),dict(evidence_hashes=['a'*64]),dict(provenance=dict(run_id=RUN2,result_fingerprint='b'*64))]:
            self.assertNotEqual(h.intent_hash_v2(c.DecisionIntentV2(**{**args,**change})),fingerprint)
        self.assertEqual(h.intent_hash_v2(c.DecisionIntentV2(**{**args,'question':'¿Por qué?'})),fingerprint)

    def test_pinned_core_package_context_vectors(self):
        vectors=json.loads((ROOT/'tests/fixtures/ultimate/fingerprint-vectors-v1.json').read_text())['typed_vectors']
        self.assertEqual(h.core_result_fingerprint(core()),vectors['d1_core'])
        self.assertEqual(package().fingerprints.result_fingerprint,vectors['d1_package'])
        self.assertEqual(package('d2').fingerprints.result_fingerprint,vectors['d2_package'])
        self.assertEqual(ai_context().context_hash,vectors['decision_context'])


if __name__=='__main__':unittest.main()
