"""D2 chooses WHEN on fixed D1 Trips, using the T6 model and T1 Transit."""
from collections import defaultdict
from datetime import date
from decimal import Decimal,localcontext
from app.domain.logistics.transit import TransitEstimator
from app.engines.common.day_resource_feasibility import FixedTrip,dispatch_window,day_resource_feasibility
from app.results import contracts as c
from app.results.canonical import input_context_hash,core_result_fingerprint
from app.results.reason_codes import ReasonEmission,reason_definition
from .day_contracts import DaySchedulingInput,DaySchedulingResult,UpstreamCertificationConflict,SchedulingNotCertified
from .day_metrics import schedule_metrics,rounded

IDENTITY=c.RuntimeIdentity(engine_name='day_scheduling',engine_version='2.0.0',runtime_profile='day_scheduling_v1',result_schema='day_scheduling_v1',result_schema_version=1)

def run_day_scheduling(input_,*,deterministic_budget=2.0):
    request=DaySchedulingInput.model_validate(input_);source=request.source_core;context=request.context
    original=tuple(sorted(source.transport_plan.trips,key=lambda t:t.trip_id))
    if not original:raise ValueError('D2 is NOT_APPLICABLE when approved D1 has no Trips')
    resources={r.resource_id:r for r in request.resources};horizon={'planning_start':context.planning_start,'planning_end':context.planning_end}
    fixed={t.trip_id:FixedTrip(trip_id=t.trip_id,resource_id=t.resource_id,distance_km=t.distance_km,ready_date=t.ready_date,delivery_due_date=t.delivery_due_date) for t in original}
    windows={t.trip_id:dispatch_window(fixed[t.trip_id],resources[t.resource_id],context) for t in original}
    pre={t.trip_id for t in original if windows[t.trip_id][1]<context.planning_start.toordinal()}
    candidates=[fixed[t.trip_id] for t in original if t.trip_id not in pre and windows[t.trip_id][0]<=windows[t.trip_id][1]]
    cert=day_resource_feasibility(candidates,request.resources,horizon,deterministic_budget=deterministic_budget,select_earliest=True)
    if cert.status=='UNKNOWN':raise SchedulingNotCertified('Scheduling selection is not certified: '+str(cert.cause or cert.native_status))
    impossible=bool(pre) or len(candidates)!=len(original) or cert.status=='INFEASIBLE'
    if impossible and request.source_temporal_certified:
        raise UpstreamCertificationConflict('STOP: T6-certified D1 Trips are not feasible under the identical frozen inputs')
    witness={w.trip_id:w for w in cert.witness} if cert.status=='FEASIBLE' else {}
    reasons=[];constraints=[];entities=[];rows=[];window_entities=[]
    conflicts={}
    if cert.status=='INFEASIBLE':
        for rid,r in resources.items():
            if r.source!='OWN' or r.units_available is None:continue
            group=[t for t in candidates if t.resource_id==rid]
            for day in range(context.planning_start.toordinal(),context.planning_end.toordinal()+1):
                mandatory=[t for t in group if windows[t.trip_id][1]<=day<windows[t.trip_id][0]+windows[t.trip_id][2].cycle_days]
                if len(mandatory)>r.units_available:
                    for t in mandatory:conflicts[t.trip_id]={'resource_id':rid,'concurrent_trips':len(mandatory),'units_available':r.units_available,'conflict_date':date.fromordinal(day)}
                    break
    def emit(code,tid,facts,ref):
        reason=ReasonEmission(emission_id='D2-'+code+'-'+tid,code=code,entity_type='TRIP',entity_id=tid,producer='day_scheduling',
            claim_strength=reason_definition(code).claim_strength,facts=facts,evidence_refs=(ref,));reasons.append(reason);return reason
    for trip in original:
        tid=trip.trip_id;r=resources[trip.resource_id];earliest,latest,estimate=windows[tid];ref='WINDOW-'+tid
        constraints.append(c.ConstraintEvidence(evidence_id=ref,code='DISPATCH_WINDOW',status='SATISFIED' if earliest<=latest else 'VIOLATED',hard=True,
            facts={'trip_id':tid,'earliest_dispatch':date.fromordinal(earliest),'latest_dispatch_ordinal':latest,'outbound_days':estimate.outbound_days,
                   'planning_start':context.planning_start,'planning_end':context.planning_end,'delivery_due_date':trip.delivery_due_date}))
        w=witness.get(tid);margin=None;status='UNSCHEDULED'
        if tid in pre:
            status='PRE_HORIZON_DISPATCH_REQUIRED';emit(status,tid,{'latest_dispatch':date.fromordinal(latest),'planning_start':context.planning_start},ref)
        elif w is not None:
            margin=(trip.delivery_due_date-w.arrival).days;status='ON_TIME' if margin>0 else 'AT_RISK' if margin==0 else 'LATE'
            emit('SCHEDULED_WITHIN_FEASIBLE_WINDOW',tid,{'earliest_dispatch':date.fromordinal(earliest),'latest_dispatch':date.fromordinal(latest),'selected_dispatch':w.dispatch},ref)
            if w.dispatch.toordinal()==earliest:emit('SCHEDULED_EARLIEST_FEASIBLE',tid,{'earliest_dispatch':w.dispatch,'selected_dispatch':w.dispatch},ref)
            emit('SCHEDULED_TO_PROTECT_DUE_DATE',tid,{'arrival_date':w.arrival,'delivery_due_date':trip.delivery_due_date,'schedule_evidence_ref':'SCHEDULE-CERTIFICATE'},ref)
            if trip.ready_date>context.planning_start:emit('DELAYED_BY_READY_DATE',tid,{'unconstrained_dispatch':context.planning_start,'ready_date':trip.ready_date,'selected_dispatch':w.dispatch},ref)
            if margin==0:emit('ZERO_MARGIN',tid,{'margin_days':0,'arrival_date':w.arrival,'delivery_due_date':trip.delivery_due_date},ref)
            if r.source=='OWN' and w.dispatch.toordinal()>earliest:
                blocked=[v for v in witness.values() if v.resource_id==r.resource_id and v.trip_id!=tid and v.dispatch.toordinal()<=earliest<v.available_again.toordinal()]
                if len(blocked)>=r.units_available and min(v.available_again for v in blocked)==w.dispatch:
                    emit('DELAYED_BY_RESOURCE_OCCUPANCY',tid,{'resource_id':r.resource_id,'desired_dispatch':date.fromordinal(earliest),'resource_busy_until':w.dispatch,'selected_dispatch':w.dispatch},'SCHEDULE-CERTIFICATE')
        elif cert.status!='UNKNOWN':
            proof='SCHEDULE-CERTIFICATE'
            if tid in conflicts:emit('RESOURCE_CAPACITY_CONFLICT',tid,conflicts[tid],proof)
            emit('NO_FEASIBLE_DISPATCH_DAY',tid,{'feasible_day_count':0,'feasibility_certificate_ref':proof},proof)
            emit('UNSCHEDULED',tid,{'cause_code':'NO_FEASIBLE_DISPATCH_DAY','cause_evidence_ref':proof},proof)
        codes=tuple(sorted({v.code for v in reasons if v.entity_id==tid}))
        row=c.ScheduleTrip(trip_id=tid,resource_id=trip.resource_id,resource_source=trip.resource_source,ready_date=trip.ready_date,delivery_due_date=trip.delivery_due_date,
            dispatch_date=w.dispatch if w else None,expected_arrival_date=w.arrival if w else None,outbound_days=estimate.outbound_days,cycle_days=estimate.cycle_days,
            resource_busy_until=w.available_again if w else None,available_again=w.available_again if w else None,schedule_margin_days=margin,status=status,reason_codes=codes)
        rows.append(row)
        facts={**row.model_dump(),'resource_slot':w.unit_index if w else None,'selection_rule':'LEXICOGRAPHIC_TRIP_ID_EARLIEST_V1','earliest_dispatch':date.fromordinal(earliest),'latest_dispatch_ordinal':latest,
               'order_ids':tuple(a.order_id for a in trip.orders),'origin_id':trip.origin_id,'destination_id':trip.destination_id,'distance_km':trip.distance_km}
        facts.pop('reason_codes')
        e=c.EntityEvidence(entity_type='TRIP',entity_id=tid,facts=facts,reason_refs=tuple(v.emission_id for v in reasons if v.entity_id==tid));entities.append(e);window_entities.append(e)
    all_scheduled=all(t.dispatch_date is not None for t in rows);usable=any(t.dispatch_date is not None for t in rows)
    known=cert.status!='UNKNOWN';status='FEASIBLE' if usable else 'INFEASIBLE' if known else 'UNKNOWN'
    policy_ok=all_scheduled
    for guard in context.node_policy.guardrails:
        metric=source.metrics
        if guard.kind=='MINIMUM_DEMAND_COVERAGE':n,d=metric.demand_coverage.assigned,metric.demand_coverage.requested
        elif guard.kind=='CRITICAL_DEMAND_COVERAGE':
            selected=[v.facts for v in request.source_evidence.entities if v.entity_type=='ORDER' and v.facts['priority']=='HIGH'];dim=context.primary_dimension
            with localcontext() as arithmetic:
                arithmetic.prec=60
                n=sum((Decimal(v['assigned_'+dim]) for v in selected),Decimal(0));d=sum((Decimal(v['requested_'+dim]) for v in selected),Decimal(0))
        elif guard.kind=='MAXIMUM_EXTERNAL_SHARE':n,d=sum(t.resource_source=='EXTERNAL' for t in original),len(original)
        else:n,d=sum(t.resource_source=='OWN' for t in original),len(original)
        with localcontext() as arithmetic:
            arithmetic.prec=60;ok=d==0 or (Decimal(n)<=guard.limit*Decimal(d) if guard.kind=='MAXIMUM_EXTERNAL_SHARE' else Decimal(n)>=guard.limit*Decimal(d))
        policy_ok=policy_ok and ok
        constraints.append(c.ConstraintEvidence(evidence_id='D2-GUARD-'+guard.kind,code=guard.kind,status='SATISFIED' if ok else 'VIOLATED',hard=True,
            facts={'numerator':n,'denominator':d,'limit':guard.limit,'scope':'UNCHANGED_APPROVED_D1_FACTS'}))
    constraints.extend([c.ConstraintEvidence(evidence_id=key,code=code,status='SATISFIED' if satisfied else 'VIOLATED' if known else 'UNKNOWN',hard=True,
        facts={'selection_rule':'LEXICOGRAPHIC_TRIP_ID_EARLIEST_V1','fixed_trip_count':len(original),'scheduled_trip_count':sum(t.dispatch_date is not None for t in rows),'kernel_status':cert.status,'native_status':cert.native_status})
        for key,code,satisfied in [('SCHEDULE-CERTIFICATE','SCHEDULE_FEASIBILITY',all_scheduled),('D2-POLICY-CERTIFICATE','POLICY_CERTIFICATE',policy_ok)]])
    timeline=[]
    for rid in sorted({t.resource_id for t in original}):
        r=resources[rid];used=[t for t in rows if t.resource_id==rid and t.dispatch_date is not None]
        timeline.append(c.ResourceTimeline(resource_id=rid,resource_source=r.source,units_available=r.units_available if r.source=='OWN' else None,
            occupancy=tuple(c.Occupancy(trip_id=t.trip_id,dispatch_date=t.dispatch_date,busy_until=t.available_again) for t in used) if r.source=='OWN' else (),
            dispatch_events=tuple(c.DispatchEvent(trip_id=t.trip_id,dispatch_date=t.dispatch_date,arrival_date=t.expected_arrival_date) for t in used)))
        entities.append(c.EntityEvidence(entity_type='RESOURCE',entity_id=rid,facts={'source':r.source,'units_available':r.units_available,'services_available':r.services_available,'scheduled_trip_count':len(used)},reason_refs=()))
    input_hash=input_context_hash(context,IDENTITY,request.source_transport_plan)
    core=c.EngineCoreResult(result_schema='day_scheduling_v1',decision=c.Decision(node_id='logistics_scheduling',decision_type='DAY_SCHEDULING',decision_label='Day Scheduling',run_id=request.run_id),
        context=context,engine=c.EngineHeader(engine_name=IDENTITY.engine_name,engine_version=IDENTITY.engine_version,runtime_profile=IDENTITY.runtime_profile,solver='OR_TOOLS_CP_SAT',solver_status=status,result_generated_at=request.result_generated_at),
        input_context_hash=input_hash,feasibility=c.Feasibility(solution_found=usable,policy_feasible=policy_ok if known else None,hard_constraints_satisfied=policy_ok if known else None,full_demand_coverage=None),
        metrics=schedule_metrics(rows),schedule=c.DaySchedule(trips=tuple(rows)),source_transport_plan=request.source_transport_plan)
    entities.append(c.EntityEvidence(entity_type='CASE',entity_id=str(context.case_id),facts={
        'strict_on_time_ratio':rounded(core.metrics.service_level.on_time,len(rows)),'margin_known_count':sum(t.schedule_margin_days is not None for t in rows),
        'source_run_id':str(request.source_transport_plan.run_id),'upstream_result_fingerprint':request.source_transport_plan.result_fingerprint},reason_refs=()))
    evidence=c.EngineEvidence(result_schema='day_scheduling_v1',workspace_id=context.workspace_id,run_id=request.run_id,input_context_hash=input_hash,core_result_fingerprint=core_result_fingerprint(core),
        policy=c.PolicyEvidence(case_goal=context.case_policy.primary_goal,effective_node_policy=context.node_policy.primary_goal,override=context.node_policy.override,override_reason=context.node_policy.override_reason,evidence_id='D2-POLICY-CERTIFICATE'),
        constraints=tuple(constraints),solver=c.SolverEvidence(status=status,objective_value=None,best_bound=None,certificate=c.SolverCertificate(kind='FEASIBILITY' if usable else 'INFEASIBILITY',evidence_ref='SCHEDULE-CERTIFICATE') if known else None),
        reasons=tuple(reasons),entities=tuple(sorted(entities,key=lambda e:(e.entity_type,e.entity_id))))
    result=DaySchedulingResult(c.EngineOutput(core=core,evidence=evidence),request,tuple(timeline),
        tuple(c.ServiceAnalysis(trip_id=t.trip_id,dispatch_date=t.dispatch_date,arrival_date=t.expected_arrival_date,delivery_due_date=t.delivery_due_date,margin_days=t.schedule_margin_days,status=t.status) for t in sorted(rows,key=lambda t:(t.schedule_margin_days is None,t.schedule_margin_days or 0,t.trip_id))),tuple(window_entities))
    from .day_validator import certify_schedule
    certify_schedule(result)
    return result
