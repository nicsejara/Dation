"""Independent post-solve certifier: reads immutable inputs and output only.

No import of the candidate generator, CP model, extraction, or metric producer.
An inconsistency is a technical engine error; never repair the candidate here.
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction

from app.domain.logistics.base import Dimension, Priority
from app.domain.logistics.transit import TransitEstimator
from app.results.canonical import core_result_fingerprint
from .transport_contracts import TransportPlanInput, TransportPlanComputation, EngineCertificationError


def certify_transport_plan(request, result):
    try:
        request=TransportPlanInput.model_validate(request)
        result=TransportPlanComputation.model_validate(result)
        with localcontext() as ctx:
            ctx.prec=60
            _certify(request,result)
    except (ValueError, AssertionError, KeyError, TypeError, ArithmeticError) as exc:
        raise EngineCertificationError('Independent D1 certification failed: '+str(exc)) from exc
    return True


def _certify(request,result):
    def check(value,message):
        if not value:raise ValueError(message)
    def rounded(n,d,scale=4):
        return None if not d else (Decimal(n)/Decimal(d)).quantize(Decimal(1).scaleb(-scale),rounding=ROUND_HALF_UP)
    m,context=request.model,request.context
    core,evidence=result.output.core,result.output.evidence
    check(core.context==context and core.decision.run_id==request.run_id,'Pinned context/Run changed')
    check(core.engine.engine_name=='transport_plan' and core.engine.engine_version=='2.0.0' and core.engine.runtime_profile=='transport_plan_v1','Wrong runtime identity')
    check(core.feasibility.policy_feasible is None,'T6 cannot certify T7 policy')
    check(evidence.core_result_fingerprint==core_result_fingerprint(core),'Core fingerprint changed')
    trips=core.transport_plan.trips
    dims=m.active_dimensions
    orders={o.order_id:o for o in request.demands}
    resources={r.resource_id:r for r in request.resources}
    totals={oid:{d:Decimal(0) for d in dims} for oid in orders}
    refs=defaultdict(list)
    per_resource=defaultdict(list)
    trip_map={t.trip_id:t for t in trips}
    check(len(trip_map)==len(trips),'Duplicate Trip IDs')
    allowed_entities={('ORDER',oid) for oid in orders}|{('RESOURCE',rid) for rid in resources}|{('TRIP',tid) for tid in trip_map}
    entities={(e.entity_type,e.entity_id):e for e in evidence.entities}
    check(len(entities)==len(evidence.entities) and set(entities)==allowed_entities,'Entity evidence set differs')
    for trip in trips:
        check(trip.resource_id in resources,'Unknown resource reference')
        resource=resources[trip.resource_id]
        check(trip.resource_source==resource.source and resource.source in m.allowed_sources,'Resource source mismatch')
        check((trip.origin_id,trip.destination_id) in resource.lanes,'Ineligible resource lane')
        check(resource.source!='OWN' or resource.base_origin_id==trip.origin_id,'OWN base differs')
        per_resource[resource.resource_id].append(trip)
        rows=[]
        for allocation in trip.orders:
            check(allocation.order_id in orders,'Unknown Order reference')
            order=orders[allocation.order_id];rows.append(order)
            check((trip.origin_id,trip.destination_id,trip.distance_km)==(order.origin_id,order.destination_id,order.distance_km),'Route/distance modified')
            check(set(order.compatibility_groups).issubset(resource.compatibility_groups) if order.compatibility_groups else m.homogeneous_loads_declared,'Incompatible resource/cargo')
            fraction=None
            for d in dims:
                q,load=getattr(order.requested,d),getattr(allocation.load,d)
                check(load is not None,'Missing active dimension')
                if q:
                    current=Fraction(load)/Fraction(q)
                    check(fraction is None or current==fraction,'Split vector loses proportionality')
                    fraction=current
                else:check(load==0,'Demand created in a zero dimension')
                totals[order.order_id][d]+=load
            check(fraction is not None and 0<fraction<=1,'Invalid allocation fraction')
            check(allocation.allocation_fraction==rounded(fraction.numerator,fraction.denominator,6),'Fraction display differs from exact vector')
            if not(order.split_allowed and m.split_permitted):
                check(fraction==1,'Non-split demand divided')
            refs[order.order_id].append(trip.trip_id)
        check(len({tuple(sorted(o.compatibility_groups)) for o in rows})==1,'Unsafe heterogeneous consolidation')
        check(trip.ready_date==max(o.ready_date for o in rows) and trip.delivery_due_date==min(o.delivery_due_date for o in rows),'Trip window modified')
        for d in Dimension:
            if d not in dims:
                check(getattr(trip.total_load,d) is None and getattr(trip.guaranteed_capacity,d) is None,'Inactive dimension presented as certified')
                continue
            load=sum(getattr(a.load,d) for a in trip.orders)
            cap=getattr(resource.guaranteed_capacity,d)
            check(trip.guaranteed_capacity.model_dump()[d]==cap,'Guaranteed capacity changed')
            check(getattr(trip.total_load,d)==load and load<=cap,'Trip capacity exceeded or load not conserved')
            check(getattr(trip.utilization,d)==rounded(load,cap),'Utilization differs')
        check(trip.estimated_cost is None,'T6 fabricated a cost policy output')
    resolutions={r.order_id:r for r in result.demand_resolution}
    check(len(resolutions)==len(result.demand_resolution) and set(resolutions)==set(orders)==set(result.residuals),'Missing demand resolution/residual')
    residual_rows=[]
    gap={d:Decimal(0) for d in dims}
    for oid,order in orders.items():
        resolution=resolutions[oid]
        check(resolution.priority==order.priority,'Priority changed')
        check(tuple(sorted(refs[oid]))==resolution.trip_ids,'Order Trip references differ')
        if not(order.split_allowed and m.split_permitted):check(len(refs[oid])<=1,'Non-split assigned across Trips')
        entity=entities['ORDER',oid]
        check(entity.facts['priority']==order.priority,'Order evidence priority changed')
        for d in dims:
            requested,assigned=getattr(order.requested,d),totals[oid][d]
            residual=getattr(result.residuals[oid],d)
            check(assigned+residual==requested and residual>=0,'Conservation violated')
            check(getattr(resolution.requested,d)==requested and getattr(resolution.assigned,d)==assigned,'Demand DTO differs from allocations')
            check(Decimal(entity.facts['requested_'+d])==requested and Decimal(entity.facts['assigned_'+d])==assigned and Decimal(entity.facts['residual_'+d])==residual,'Order evidence differs from conservation')
            gap[d]+=residual
        any_gap=any(getattr(result.residuals[oid],d)>0 for d in dims)
        any_assigned=any(totals[oid][d]>0 for d in dims)
        expected='COVERED' if not any_gap else 'PARTIALLY_COVERED' if any_assigned else 'UNASSIGNED'
        check(resolution.status==expected,'False structural coverage status')
        check(resolution.coverage_ratio==rounded(totals[oid][m.primary_dimension],getattr(order.requested,m.primary_dimension)),'Order coverage ratio differs')
        if any_gap:residual_rows.append(resolution)
    check(tuple(sorted(residual_rows,key=lambda o:o.order_id))==core.transport_plan.unassigned_demand,'Residual rows missing')
    if any(gap.values()):
        check(core.transport_plan.capacity_gap is not None,'Gap hidden')
        for d in dims:check(getattr(core.transport_plan.capacity_gap,d)==gap[d],'Gap total changed')
    else:check(core.transport_plan.capacity_gap is None,'False gap')
    cert=result.temporal_certificate
    witnesses={w.trip_id:w for w in cert.witness}
    check(len(witnesses)==len(cert.witness),'Duplicate witness')
    if core.feasibility.solution_found:
        check(core.engine.solver_status in ('OPTIMAL','FEASIBLE','UNKNOWN') and cert.status=='FEASIBLE' and set(witnesses)==set(trip_map),'Uncertified candidate exposed')
        check(core.feasibility.hard_constraints_satisfied is True,'Missing structural certification')
        check(core.feasibility.full_demand_coverage==(not any(gap.values())),'False full coverage')
    else:
        check(not trips and not witnesses and core.engine.solver_status in ('UNKNOWN','INFEASIBLE'),'Unusable result contains Trips')
        check(core.feasibility.hard_constraints_satisfied is None and core.feasibility.full_demand_coverage is None,'No-solution claims certainty')
    occupancy=defaultdict(list)
    usage={u.resource_id:u for u in result.resource_usage}
    check(len(usage)==len(result.resource_usage) and set(usage)==set(resources),'Missing resource usage')
    for rid,resource in resources.items():
        used=per_resource[rid]
        u=usage[rid]
        check(u.resource_source==resource.source and u.trip_count==len(used) and u.trip_ids==tuple(t.trip_id for t in used),'Resource usage identity/count differs')
        check(u.total_distance_km==sum((t.distance_km for t in used),Decimal(0)),'Resource distance differs')
        check(u.total_cost is None,'Uncertified cost')
        if resource.source=='EXTERNAL':
            check(u.services_available==resource.services_available and u.services_used==len(used) and u.services_remaining==(resource.services_available-len(used) if resource.services_available is not None else None),'External quota facts differ')
            check(u.availability_source==resource.availability_source,'Availability assumption changed')
            check(not used or resource.services_available is not None and len(used)<=resource.services_available,'Finite horizon service quota exceeded')
        else:
            check(u.units_available==resource.units_available and u.services_used is None,'OWN units changed')
        for d in dims:
            total=sum((getattr(t.total_load,d) for t in used),Decimal(0))
            check(getattr(u.total_load,d)==total and getattr(u.weighted_utilization,d)==rounded(total,len(used)*getattr(resource.guaranteed_capacity,d)),'Resource utilization differs')
        for trip in used:
            w=witnesses[trip.trip_id]
            check(w.resource_id==rid and context.planning_start<=w.dispatch<=context.planning_end and w.dispatch>=trip.ready_date,'Temporal witness references/window invalid')
            dates=TransitEstimator.dates(w.dispatch,trip.distance_km,resource.source)
            check(w.arrival==dates.arrival and w.arrival<=trip.delivery_due_date and w.available_again==dates.available_again,'Temporal witness violates T1 transit/due')
            if resource.source=='EXTERNAL':check(w.unit_index is None and w.available_again is None,'Invented external cycle')
            else:
                check(w.unit_index is not None and 0<=w.unit_index<resource.units_available,'Invalid OWN unit index')
                occupancy[rid,w.unit_index].append((w.dispatch,w.available_again))
    for periods in occupancy.values():
        ordered=sorted(periods)
        check(all(a[1]<=b[0] for a,b in zip(ordered,ordered[1:])),'OWN unit overlaps')
    metric=core.metrics
    primary=m.primary_dimension
    requested=sum((getattr(o.requested,primary) for o in orders.values()),Decimal(0))
    assigned=sum((totals[oid][primary] for oid in orders),Decimal(0))
    check((metric.demand_coverage.requested,metric.demand_coverage.assigned,metric.demand_coverage.unassigned,metric.demand_coverage.ratio)==(requested,assigned,requested-assigned,rounded(assigned,requested)),'Coverage metrics differ')
    check(metric.trip_count==len(trips) and metric.resources_used==len({t.resource_id for t in trips}),'Count metrics differ')
    own=sum(t.resource_source=='OWN' for t in trips)
    check((metric.resource_mix.own_trip_ratio,metric.resource_mix.external_trip_ratio)==(rounded(own,len(trips)),rounded(len(trips)-own,len(trips))),'Resource mix differs')
    check(metric.capacity_utilization.weighted_ratio==rounded(sum((getattr(t.total_load,primary) for t in trips),Decimal(0)),sum((getattr(t.guaranteed_capacity,primary) for t in trips),Decimal(0))),'Weighted utilization differs')
    check(metric.total_cost is None and metric.cost_completeness=='UNKNOWN','T7 economic claim in T6')
    coverage={v.priority:v.coverage_ratio for v in metric.coverage_by_priority}
    check(set(coverage)==set(Priority),'Missing priority strata')
    for priority in Priority:
        check(coverage[priority]==rounded(sum((totals[oid][primary] for oid,o in orders.items() if o.priority==priority),Decimal(0)),sum((getattr(o.requested,primary) for o in orders.values() if o.priority==priority),Decimal(0))),'Priority coverage differs')
    constraint_ids={e.evidence_id for e in evidence.constraints}
    check(len(constraint_ids)==len(evidence.constraints),'Duplicate constraint evidence')
    pair_evidence={}
    for constraint in evidence.constraints:
        if constraint.code!='CANDIDATE_ELIGIBILITY':continue
        f=constraint.facts
        o,r=orders[f['order_id']],resources[f['resource_id']]
        key=(o.order_id,r.resource_id)
        check(key not in pair_evidence,'Duplicate candidate pair evidence')
        pair_evidence[key]=constraint
        rejected=[]
        eligible=r.source in m.allowed_sources and (o.origin_id,o.destination_id) in r.lanes and (r.source!='OWN' or r.base_origin_id==o.origin_id) and (set(o.compatibility_groups).issubset(r.compatibility_groups) if o.compatibility_groups else m.homogeneous_loads_declared)
        if not eligible:rejected.append('RESOURCE_INCOMPATIBLE')
        first=max(context.planning_start,o.ready_date).toordinal()
        last=min(context.planning_end.toordinal(),o.delivery_due_date.toordinal()-TransitEstimator.estimate(o.distance_km,r.source).outbound_days+1)
        if first>last:rejected.append('DATE_WINDOW_INCOMPATIBLE')
        if not(o.split_allowed and m.split_permitted) and any(getattr(o.requested,d)>getattr(r.guaranteed_capacity,d) for d in dims):rejected.append('NON_SPLIT_CAPACITY')
        available=r.units_available if r.source=='OWN' else r.services_available
        if available==0:rejected.append('ZERO_AVAILABILITY')
        check(tuple(rejected)==f['rejected_by'] and constraint.status==('VIOLATED' if rejected else 'SATISFIED') and not constraint.hard,'Candidate rejection facts differ')
        check((f['earliest_dispatch_ordinal'],f['latest_dispatch_ordinal'],f['availability'])==(first,last,available),'Candidate window/availability differs')
        for d in dims:check(Decimal(f['requested_'+d])==getattr(o.requested,d) and Decimal(f['guaranteed_'+d])==getattr(r.guaranteed_capacity,d),'Candidate vector facts differ')
    check(set(pair_evidence)=={(o,r) for o in orders for r in resources},'Missing pair evidence')
    for reason in evidence.reasons:
        check((reason.entity_type,reason.entity_id) in allowed_entities,'Reason entity missing')
        check(set(reason.evidence_refs).issubset(constraint_ids),'Reason certificate missing')
        f=reason.facts
        if reason.code=='CAPACITY_GAP':
            check(core.feasibility.solution_found and f['unassigned_quantity']==getattr(result.residuals[reason.entity_id],f['dimension']),'Unsupported gap reason')
        elif reason.code=='GUARANTEED_CAPACITY_USED_FOR_FEASIBILITY':
            trip=trip_map[reason.entity_id]
            check(f['guaranteed_capacity']==getattr(trip.guaranteed_capacity,f['dimension']) and f['load']==getattr(trip.total_load,f['dimension']),'Capacity reason differs')
        elif reason.code=='CONSOLIDATED_COMPATIBLE_DEMAND':
            trip=trip_map[reason.entity_id]
            check(set(f['order_ids'])=={a.order_id for a in trip.orders} and f['compatibility_certificate_ref'] in constraint_ids,'Consolidation proof missing')
        elif reason.code in ('ASSUMED_EXTERNAL_AVAILABILITY','RESOURCE_SERVICE_LIMIT_REACHED'):
            r=resources[reason.entity_id]
            check(r.source=='EXTERNAL' and f['services_available']==r.services_available,'External reason differs')
            if reason.code=='ASSUMED_EXTERNAL_AVAILABILITY':check(r.availability_source=='ASSUMED','False assumption')
            else:check(f['services_used']==len(per_resource[r.resource_id])==r.services_available,'False service saturation')
        elif reason.code=='NO_COMPATIBLE_RESOURCE':
            o=orders[reason.entity_id]
            eligible=[r for r in resources.values() if r.source in m.allowed_sources and (o.origin_id,o.destination_id) in r.lanes and (r.source!='OWN' or r.base_origin_id==o.origin_id) and (set(o.compatibility_groups).issubset(r.compatibility_groups) if o.compatibility_groups else m.homogeneous_loads_declared)]
            check(not eligible and f['certificate_ref'] in constraint_ids,'False compatibility exhaustion')
        elif reason.code=='NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY':
            o=orders[reason.entity_id]
            check(not(o.split_allowed and m.split_permitted) and f['requested']==getattr(o.requested,f['dimension']),'False non-split proof')
            eligible=[r for r in resources.values() if r.source in m.allowed_sources and (o.origin_id,o.destination_id) in r.lanes and (r.source!='OWN' or r.base_origin_id==o.origin_id) and (set(o.compatibility_groups).issubset(r.compatibility_groups) if o.compatibility_groups else m.homogeneous_loads_declared)]
            check(bool(eligible) and max(getattr(r.guaranteed_capacity,f['dimension']) for r in eligible)==f['maximum_guaranteed_capacity'],'Non-split bound omitted resource')
        elif reason.code=='DATE_WINDOW_INCOMPATIBLE':
            o=orders[reason.entity_id]
            eligible=[r for r in resources.values() if r.source in m.allowed_sources and (o.origin_id,o.destination_id) in r.lanes and (r.source!='OWN' or r.base_origin_id==o.origin_id) and (set(o.compatibility_groups).issubset(r.compatibility_groups) if o.compatibility_groups else m.homogeneous_loads_declared)]
            latest=[min(context.planning_end.toordinal(),o.delivery_due_date.toordinal()-TransitEstimator.estimate(o.distance_km,r.source).outbound_days+1) for r in eligible]
            check(bool(latest) and f['earliest_dispatch']==max(context.planning_start,o.ready_date) and f['latest_dispatch'].toordinal()==max(latest) and f['earliest_dispatch']>f['latest_dispatch'],'Invalid date contradiction')
        else:
            raise ValueError('Unsupported T6 reason claim: '+reason.code)
    reason_map={r.emission_id:r for r in evidence.reasons}
    for key,entity in entities.items():
        for ref in entity.reason_refs:
            check((reason_map[ref].entity_type,reason_map[ref].entity_id)==key,'Cross-entity reason reference')
        if entity.entity_type=='ORDER':
            candidates={c.resource_id:c for c in entity.candidate_summary}
            check(len(candidates)==len(entity.candidate_summary) and set(candidates)==set(resources),'Incomplete static candidate set')
            for rid,candidate in candidates.items():
                selected=any(t.resource_id==rid and any(a.order_id==entity.entity_id for a in t.orders) for t in trips)
                check((candidate.status=='SELECTED')==selected,'False candidate selection')
                rejected=pair_evidence[entity.entity_id,rid].status=='VIOLATED'
                check(candidate.status==('SELECTED' if selected else 'INFEASIBLE' if rejected else 'UNKNOWN'),'Unsupported candidate feasibility claim')
                check(candidate.estimated_cost is None,'Uncertified candidate cost')
    check(core.engine.solver_status!='OPTIMAL','T6 producer must not claim a T7/global optimum')
