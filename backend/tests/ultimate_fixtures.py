"""Literal hypothetical ABI fixtures; no Ultimate engine/assembler is implemented."""
from datetime import date, datetime, timezone
from decimal import Decimal as D
from uuid import UUID

from app.domain.logistics.contracts import FrozenCaseContext
from app.results import contracts as c
from app.results.canonical import (canonical_tree, core_result_fingerprint, input_context_hash,
                                  policy_hash, result_fingerprint, decision_context_hash)

WS, CASE, MODEL, MV, PACK = [UUID(int=i) for i in range(1, 6)]
RUN1, RUN2 = UUID(int=101), UUID(int=102)
ZERO = '0' * 64


def context():
    return FrozenCaseContext.model_validate(dict(workspace_id=WS, case_id=CASE, case_name='Semana 45',
        operating_role='SHIPPER', logistics_model_id=MODEL, logistics_model_version_id=MV,
        logistics_model_version=1, data_pack_version_id=PACK, data_pack_version=1,
        model_hash='1'*64, pack_manifest_hash='2'*64, graph_version='ULTIMATE_GRAPH_V1',
        contract_hash='3'*64, planning_start='2026-11-02', planning_end='2026-11-08',
        case_policy={'primary_goal':'MINIMIZE_COST'}, node_policy={'primary_goal':'MINIMIZE_COST'},
        currency_policy={'currency':'ARS','minor_units':2}, primary_dimension='pallets',
        active_dimensions=['pallets'], read_set=[
            dict(slot='transport_demand',canonical_sha256='4'*64,contract_hash='5'*64,normalizer_version='demand_v1'),
            dict(slot='transport_resources',canonical_sha256='6'*64,contract_hash='7'*64,normalizer_version='resources_v1')]))


def core(kind='d1', source_fingerprint='c'*64):
    d1 = kind == 'd1'
    schema = 'transport_plan_v1' if d1 else 'day_scheduling_v1'
    engine = c.EngineHeader(engine_name='transport_plan' if d1 else 'day_scheduling', engine_version='2.0.0',
        runtime_profile=schema, solver='OR_TOOLS_CP_SAT', solver_status='FEASIBLE',
        result_generated_at=datetime(2026,11,2,tzinfo=timezone.utc))
    identity=c.RuntimeIdentity(engine_name=engine.engine_name, engine_version=engine.engine_version,
        runtime_profile=schema,result_schema=schema,result_schema_version=1)
    frozen=context();upstream=None if d1 else c.ResultBinding(run_id=RUN1,result_fingerprint=source_fingerprint)
    metrics = dict(total_cost={'amount':'10','currency':'ARS'}, cost_completeness='COMPLETE', trip_count=1,
        demand_coverage=dict(primary_dimension='pallets',requested='1',assigned='1',unassigned='0',ratio='1'),
        capacity_utilization=dict(primary_dimension='pallets',weighted_ratio='.5'),
        resource_mix=dict(own_trip_ratio='1',external_trip_ratio='0'), resources_used=1,
        coverage_by_priority=[dict(priority='HIGH',coverage_ratio='1')]) if d1 else dict(
        scheduled_trips=dict(scheduled=1,total=1,ratio='1'),
        service_level=dict(on_time=1,at_risk=0,late=0,pre_horizon=0,unscheduled=0),
        on_time_ratio='1',average_schedule_margin_days='3',peak_dispatch_day=dict(date='2026-11-02',trip_count=1),exception_count=0)
    trip = dict(trip_id='VIA-001',origin_id='ORI-01',destination_id='DST-01',distance_km='480',resource_id='REC-01',resource_source='OWN',
        orders=[dict(order_id='ORD-01',allocation_fraction='1',load={'pallets':'1'})],total_load={'pallets':'1'},guaranteed_capacity={'pallets':'2'},
        utilization={'pallets':'.5'},estimated_cost=dict(amount='10',currency='ARS',cost_model='OWN_OPERATING_CYCLE'),ready_date='2026-11-02',delivery_due_date='2026-11-05')
    schedule = dict(trip_id='VIA-001',resource_id='REC-01',resource_source='OWN',ready_date='2026-11-02',delivery_due_date='2026-11-05',
        dispatch_date='2026-11-02',expected_arrival_date='2026-11-02',outbound_days=1,cycle_days=2,
        resource_busy_until='2026-11-04',available_again='2026-11-04',schedule_margin_days=3,status='ON_TIME')
    return c.EngineCoreResult.model_validate(dict(result_schema=schema,
        decision=dict(node_id='logistics_assignment' if d1 else 'logistics_scheduling',decision_type='TRANSPORT_PLAN' if d1 else 'DAY_SCHEDULING',decision_label='Fixture',run_id=RUN1 if d1 else RUN2),
        context=frozen,engine=engine,input_context_hash=input_context_hash(frozen,identity,upstream),
        feasibility=dict(solution_found=True,policy_feasible=True,hard_constraints_satisfied=True,full_demand_coverage=True),metrics=metrics,
        transport_plan=dict(trips=[trip],unassigned_demand=[],capacity_gap=None) if d1 else None,
        schedule=dict(trips=[schedule]) if not d1 else None,source_transport_plan=upstream))


def evidence(result):
    return c.EngineEvidence.model_validate(dict(result_schema=result.result_schema,workspace_id=WS,run_id=result.decision.run_id,
        input_context_hash=result.input_context_hash,core_result_fingerprint=core_result_fingerprint(result),
        policy=dict(case_goal='MINIMIZE_COST',effective_node_policy='MINIMIZE_COST',override=False,override_reason=None,evidence_id='POLICY-01'),
        constraints=[dict(evidence_id='CAP-01',code='CAPACITY',status='SATISFIED',hard=True,facts={'guaranteed_pallets':D('2')})],
        solver=dict(status='FEASIBLE',objective_value='10',best_bound='0',certificate=dict(kind='FEASIBILITY',evidence_ref='CERT-01')),
        reasons=[],entities=[dict(entity_type='TRIP',entity_id='VIA-001',facts={'load_pallets':D('1')},reason_refs=[])]))


def inline(schema, dataset_id, rows, row_type):
    return c.InlineDataset[row_type](dataset_id=dataset_id,row_schema=schema,schema_version=1,row_count=len(rows),rows=tuple(rows))


def package(kind='d1', source_fingerprint='c'*64):
    result=core(kind,source_fingerprint);proof=evidence(result);d1=kind=='d1'
    trip=result.transport_plan.trips[0] if d1 else result.schedule.trips[0]
    trips=inline('transport_trip_v1' if d1 else 'day_schedule_trip_v1','plan' if d1 else 'schedule',[trip],c.Trip if d1 else c.ScheduleTrip)
    visual=c.SankeyProjection(value_dimension='pallets',nodes=(
        c.SankeyNode(id='DST-01',type='DESTINATION',label='Destino'),c.SankeyNode(id='VIA-001',type='TRIP',label='VIA-001'),
        c.SankeyNode(id='REC-01',type='RESOURCE',label='Recurso')),
        links=(c.SankeyLink(source='DST-01',target='VIA-001',value='1',order_ids=('ORD-01',)),c.SankeyLink(source='VIA-001',target='REC-01',value='1'))) if d1 else c.GanttProjection(
        planning_start='2026-11-02',planning_end='2026-11-08',rows=(c.GanttRow(resource_id='REC-01',label='Recurso',source='OWN'),),
        items=(c.GanttItem(trip_id='VIA-001',resource_id='REC-01',dispatch_date='2026-11-02',arrival_date='2026-11-02',occupancy_start='2026-11-02',occupancy_end='2026-11-04',status='ON_TIME'),))
    columns=(c.DetailColumn(key='trip_id',unit=None,format='ID'),)
    detail=c.DetailDatasetDescriptor(dataset_id=trips.dataset_id,dataset_type='PLAN' if d1 else 'SCHEDULE',columns=columns,
        primary_key=('trip_id',),stable_order=('trip_id',),data=trips)
    review=c.ApprovalReview(decision_ready_for_review=True,hard_constraints_satisfied=True,coverage_status='FULL',exception_count=0,assumption_count=0,
        review_items=(),**({} if d1 else dict(scheduled_ratio='1',expected_delivery_compliance='1',at_risk_count=0,late_count=0,pre_horizon_count=0)))
    fingerprints=c.FingerprintSet(input_context_hash=result.input_context_hash,core_result_fingerprint=proof.core_result_fingerprint,result_fingerprint=ZERO,
        model_version=1,data_pack_version=1,case_policy_hash=policy_hash(result.context.case_policy),node_policy_hash=policy_hash(result.context.node_policy),
        contract_hash=result.context.contract_hash,engine_version='2.0.0',upstream_result_fingerprint=None if d1 else source_fingerprint)
    rows=inline('export_rows_v1','csv',[{'trip_id':'VIA-001','estimated_cost':D('10') if d1 else None}],dict[str,c.FactValue])
    fields=dict(result_schema=result.result_schema,assembler_version='RESULT_ASSEMBLER_V1',decision=result.decision,context=result.context,engine=result.engine,
        feasibility=result.feasibility,transport_plan=c.PublishedTransportPlan(trips=trips,
            unassigned_demand=inline('demand_resolution_v1','unassigned',[],c.DemandResolution),capacity_gap=None) if d1 else None,
        schedule=c.PublishedSchedule(trips=trips) if not d1 else None,source_transport_plan=result.source_transport_plan,
        summary=c.ExecutiveSummary(template_id='ultimate.fixture.summary',facts={'trips':1}),metrics=result.metrics,
        primary_visual=c.PrimaryVisual(type='SANKEY' if d1 else 'DAY_GANTT',projection=visual),details=(detail,),alternatives=(),alternatives_state='NOT_COMPUTED',
        exceptions=(),assumptions=(),evidence=c.EvidenceSummary(solver=proof.solver,policy=proof.policy,constraints=proof.constraints,
            reason_emissions=inline('reason_emission_v1','reasons',[],c.ReasonEmission)),approval_review=review,
        exports=c.Exports.model_validate(dict(csv=dict(available=True,type='TRANSPORT_PLAN' if d1 else 'DAY_SCHEDULE',
            granularity='TRIP_ORDER' if d1 else 'TRIP',cost_scope='TRIP_ONCE' if d1 else None,rows=rows),
            json=dict(available=True,type='DECISION_RESULT_PACKAGE',granularity='PACKAGE'))),
        ai_context=c.AIContextReference(base_context=None),artifact_manifest=c.ArtifactManifest(artifacts=()),fingerprints=fingerprints)
    # Two-phase fixture only: hash the typed draft, then validate the entire
    # published DTO. No application producer uses model_construct.
    draft=c.DecisionResultPackageV1.model_construct(**fields)
    data=draft.model_dump(mode='python',by_alias=True)
    data['fingerprints']['result_fingerprint']=result_fingerprint(draft)
    return c.DecisionResultPackageV1.model_validate(data)


def ai_context():
    p=package();case=p.context
    fields=dict(provenance=c.ResultBinding(run_id=p.decision.run_id,result_fingerprint=p.fingerprints.result_fingerprint),mode='EXPLAIN',case=case,
        logistics_model=c.ModelContext(id=case.logistics_model_id,version_id=case.logistics_model_version_id,version=1,model_hash=case.model_hash),
        case_policy=case.case_policy,node_policy=case.node_policy,
        decision_definition=c.DecisionDefinitionContext(node_id='logistics_assignment',version='ULTIMATE_GRAPH_V1',decision_type='TRANSPORT_PLAN'),
        input_summary=c.InputSummary(orders=1,demand={'pallets':'1'},priority_distribution={'HIGH':1},own_resources=1,external_resources=0),
        result_summary=p.summary,metrics=p.metrics,exceptions=(),assumptions=(),evidence_summary=p.evidence,alternatives_summary=(),
        approval_review=p.approval_review,selected_entity=None,context_hash=ZERO)
    draft=c.DecisionContextV1.model_construct(**fields);data=draft.model_dump(mode='python',by_alias=True)
    data['context_hash']=decision_context_hash(draft)
    return c.DecisionContextV1.model_validate(data)
