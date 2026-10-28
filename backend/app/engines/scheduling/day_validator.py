"""Independent D2 certifier: dates, membership, occupancy and metric facts."""
from app.domain.logistics.transit import TransitEstimator
from app.results import contracts as c
from app.results.canonical import canonical_bytes
from .day_metrics import schedule_metrics,rounded

def require(ok,message):
    if not ok:raise ValueError('D2 certification: '+message)

def certify_schedule(result):
    core=result.output.core;request=result.source;source=request.source_core
    c.EngineOutput.model_validate(result.output);c.validate_schedule_source(source,core,request.source_transport_plan.result_fingerprint)
    original={t.trip_id:t for t in source.transport_plan.trips};rows={t.trip_id:t for t in core.schedule.trips};resources={r.resource_id:r for r in request.resources}
    require(core.context==request.context,'Frozen context changed')
    for tid,t in rows.items():
        s=original[tid];estimate=TransitEstimator.estimate(s.distance_km,t.resource_source)
        require((t.ready_date,t.delivery_due_date,t.outbound_days,t.cycle_days)==(s.ready_date,s.delivery_due_date,estimate.outbound_days,estimate.cycle_days),'Source windows/Transit changed')
        if t.dispatch_date is not None:
            dates=TransitEstimator.dates(t.dispatch_date,s.distance_km,t.resource_source)
            require(request.context.planning_start<=t.dispatch_date<=request.context.planning_end,'Departure outside horizon')
            require(t.dispatch_date>=s.ready_date,'Departure before ready')
            require((t.expected_arrival_date,t.available_again,t.resource_busy_until)==(dates.arrival,dates.available_again,dates.available_again),'Dates/occupancy contradict Transit')
            require(t.schedule_margin_days==(s.delivery_due_date-dates.arrival).days,'Margin differs')
            require(t.status!='LATE','No certified lateness policy exists in this release')
        elif t.status=='PRE_HORIZON_DISPATCH_REQUIRED':require(s.delivery_due_date.toordinal()-estimate.outbound_days+1<request.context.planning_start.toordinal(),'False PRE_HORIZON')
    for rid,r in resources.items():
        selected=[t for t in rows.values() if t.resource_id==rid and t.dispatch_date is not None]
        if r.source=='EXTERNAL':require(r.services_available is not None and len(selected)<=r.services_available,'External horizon services exceeded')
        else:
            events={d for t in selected for d in [t.dispatch_date,t.available_again]}
            for day in events:require(sum(t.dispatch_date<=day<t.available_again for t in selected)<=r.units_available,'OWN overlap exceeds available units')
    require(canonical_bytes(core.metrics)==canonical_bytes(schedule_metrics(tuple(rows.values()))),'Metrics differ from all source Trips')
    require(core.metrics.scheduled_trips.total==len(original),'Trips disappeared from denominator')
    evidence=result.output.evidence
    facts=next(e.facts for e in evidence.entities if e.entity_type=='CASE')
    require(canonical_bytes(facts['strict_on_time_ratio'])==canonical_bytes(rounded(core.metrics.service_level.on_time,len(rows))),'Strict ON_TIME differs')
    require(facts['margin_known_count']==sum(t.schedule_margin_days is not None for t in rows.values()),'Known-margin denominator differs')
    timelines={t.resource_id:t for t in result.resource_timeline}
    require(set(timelines)=={t.resource_id for t in rows.values()},'Resource timeline membership differs')
    for rid,timeline in timelines.items():
        r=resources[rid];selected=[t for t in rows.values() if t.resource_id==rid and t.dispatch_date is not None]
        require(timeline.resource_source==r.source and timeline.units_available==(r.units_available if r.source=='OWN' else None),'Resource timeline source/units differ')
        require({(v.trip_id,v.dispatch_date,v.busy_until) for v in timeline.occupancy}==({(v.trip_id,v.dispatch_date,v.available_again) for v in selected} if r.source=='OWN' else set()),'Resource occupancy differs')
        require({(v.trip_id,v.dispatch_date,v.arrival_date) for v in timeline.dispatch_events}=={(v.trip_id,v.dispatch_date,v.expected_arrival_date) for v in selected},'Dispatch events differ')
    require(len(result.service_analysis)==len(rows),'Service dataset omits Trips')
    for v in result.service_analysis:
        t=rows[v.trip_id];require((v.dispatch_date,v.arrival_date,v.delivery_due_date,v.margin_days,v.status)==(t.dispatch_date,t.expected_arrival_date,t.delivery_due_date,t.schedule_margin_days,t.status),'Service timing differs')
    require([v.trip_id for v in result.service_analysis]==[v.trip_id for v in sorted(core.schedule.trips,key=lambda t:(t.schedule_margin_days is None,t.schedule_margin_days or 0,t.trip_id))],'Service margin order differs')
    return True
