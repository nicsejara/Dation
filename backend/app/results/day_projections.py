"""D2 projections copy certified fields. No Transit, solver or date arithmetic."""
from . import contracts as c

def day_gantt(result):
    core=result.output.core
    return c.GanttProjection(planning_start=core.context.planning_start,planning_end=core.context.planning_end,
        rows=tuple(c.GanttRow(resource_id=r.resource_id,label=r.resource_id,source=r.resource_source) for r in result.resource_timeline),
        items=tuple(c.GanttItem(trip_id=t.trip_id,resource_id=t.resource_id,dispatch_date=t.dispatch_date,arrival_date=t.expected_arrival_date,
            occupancy_start=t.dispatch_date if t.resource_source=='OWN' else None,occupancy_end=t.available_again,status=t.status) for t in core.schedule.trips if t.dispatch_date is not None))

def day_summary(result):
    core=result.output.core;m=core.metrics;s=m.service_level
    facts=next(e.facts for e in result.output.evidence.entities if e.entity_type=='CASE')
    return c.ExecutiveSummary(template_id='ultimate.day_schedule.certified_v1',facts={
        'total_trips':m.scheduled_trips.total,'scheduled_trips':m.scheduled_trips.scheduled,'scheduled_ratio':m.scheduled_trips.ratio,
        'on_time':s.on_time,'at_risk':s.at_risk,'late':s.late,'pre_horizon':s.pre_horizon,'unscheduled':s.unscheduled,
        'expected_delivery_compliance':m.on_time_ratio,'strict_on_time_ratio':facts['strict_on_time_ratio'],'strict_on_time_numerator':s.on_time,'strict_on_time_denominator':m.scheduled_trips.total,
        'average_schedule_margin_days':m.average_schedule_margin_days,'margin_known_count':facts['margin_known_count'],
        'peak_dispatch_day':m.peak_dispatch_day.date if m.peak_dispatch_day else None,'peak_dispatch_trip_count':m.peak_dispatch_day.trip_count if m.peak_dispatch_day else None,
        'exception_count':m.exception_count,'source_run_id':str(core.source_transport_plan.run_id),'upstream_result_fingerprint':core.source_transport_plan.result_fingerprint})

def trip_facts(result):
    timing={t.trip_id:t for t in result.output.core.schedule.trips};values=[]
    for t in result.source.source_core.transport_plan.trips:
        facts={**timing[t.trip_id].model_dump(),'origin_id':t.origin_id,'destination_id':t.destination_id,'distance_km':t.distance_km,
            'order_ids':tuple(a.order_id for a in t.orders),'upstream_result_fingerprint':result.source.source_transport_plan.result_fingerprint}
        facts.pop('reason_codes')
        for dim in result.output.core.context.active_dimensions:
            facts['total_load_'+dim]=getattr(t.total_load,dim);facts['guaranteed_capacity_'+dim]=getattr(t.guaranteed_capacity,dim)
        for index,a in enumerate(t.orders):
            facts['allocation_fraction_'+str(index)]=a.allocation_fraction
            for dim in result.output.core.context.active_dimensions:facts['allocation_'+str(index)+'_load_'+dim]=getattr(a.load,dim)
        values.append(c.EntityEvidence(entity_type='TRIP',entity_id=t.trip_id,facts=facts,reason_refs=tuple(r.emission_id for r in result.output.evidence.reasons if r.entity_id==t.trip_id)))
    return tuple(sorted(values,key=lambda r:r.entity_id))

def day_export_rows(core):
    return tuple({**t.model_dump(exclude={'reason_codes'}),'reason_codes':t.reason_codes,
        'source_run_id':str(core.source_transport_plan.run_id),'upstream_result_fingerprint':core.source_transport_plan.result_fingerprint} for t in core.schedule.trips)

def day_exceptions(result):
    exceptions=[]
    code_by_status={'AT_RISK':'ZERO_MARGIN','PRE_HORIZON_DISPATCH_REQUIRED':'PRE_HORIZON_DISPATCH_REQUIRED','UNSCHEDULED':'UNSCHEDULED'}
    for t in result.output.core.schedule.trips:
        code=code_by_status.get(t.status)
        if code is None:continue
        reason=next(r for r in result.output.evidence.reasons if r.entity_id==t.trip_id and r.code==code)
        exceptions.append(c.ExceptionDescriptor(exception_id='D2-EX-'+t.trip_id,category='BUSINESS' if t.status=='AT_RISK' else 'FEASIBILITY',severity='ATTENTION' if t.status=='AT_RISK' else 'BLOCKING',
            code=code,entity_type='TRIP',entity_ids=(t.trip_id,),message_key='ultimate.exception.'+code.lower(),facts=reason.facts,reason_ref=reason.emission_id))
    return tuple(exceptions)

def day_review(result,exceptions):
    core=result.output.core;m=core.metrics;ready=core.feasibility.solution_found and core.feasibility.hard_constraints_satisfied is True and core.feasibility.policy_feasible is True
    items=[c.ReviewItem(priority=2,type='SERVICE_RISK' if e.code=='ZERO_MARGIN' else 'HARD_CONSTRAINT',code=e.code,entity=c.EntityRef(type='TRIP',id=e.entity_ids[0]),evidence_refs=(e.reason_ref,)) for e in exceptions]
    if not ready:items.insert(0,c.ReviewItem(priority=1,type='HARD_CONSTRAINT',code='SCHEDULE_NOT_CERTIFIED',entity=None,evidence_refs=('D2-POLICY-CERTIFICATE',)))
    return c.ApprovalReview(decision_ready_for_review=ready,hard_constraints_satisfied=core.feasibility.hard_constraints_satisfied,
        coverage_status='FULL' if m.scheduled_trips.scheduled==m.scheduled_trips.total else 'PARTIAL' if m.scheduled_trips.scheduled else 'NONE',
        exception_count=len(exceptions),assumption_count=0,review_items=tuple(items),scheduled_ratio=m.scheduled_trips.ratio,expected_delivery_compliance=m.on_time_ratio,
        at_risk_count=m.service_level.at_risk,late_count=m.service_level.late,pre_horizon_count=m.service_level.pre_horizon)
