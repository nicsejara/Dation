"""Independent T7 price/metric/policy certifier; no policy optimizer import."""
from decimal import Decimal,localcontext
from app.domain.logistics.base import Priority
from app.results.canonical import core_result_fingerprint
from app.engines.common.day_resource_feasibility import FixedTrip,day_resource_feasibility
from .transport_validator import certify_transport_plan
from .transport_contracts import EngineCertificationError


def certify_policy_result(request,result):
    try:
        certify_transport_plan(request,result.structural)
        with localcontext() as ctx:
            ctx.prec=60;_check(request,result)
    except (ValueError,AssertionError,KeyError,TypeError,ArithmeticError) as exc:
        raise EngineCertificationError('Independent policy certification failed: '+str(exc)) from exc
    return True


def _check(request,result):
    def require(ok,message):
        if not ok:raise ValueError(message)
    def price(resource,distance):
        if resource.source=='OWN':
            rate=resource.operating_cost_per_km
            value=None if rate is None else rate*distance*2
        else:
            v=resource.external_cost;value=v.rate
            if value is not None and v.cost_model=='PER_KM':value*=distance*(2 if v.billing_basis=='ROUND_TRIP' else 1)
        return None if value is None else request.context.currency_policy.rounded(value)
    core=result.output.core;evidence=result.output.evidence
    old=result.structural.output.core
    require(core.context==old.context and core.input_context_hash==old.input_context_hash,'Context changed')
    require(evidence.core_result_fingerprint==core_result_fingerprint(core),'Policy fingerprint differs')
    require(result.residuals==result.structural.residuals,'Policy changed residual')
    resources={r.resource_id:r for r in request.resources}
    expected=[]
    require(len(core.transport_plan.trips)==len(old.transport_plan.trips),'Policy wrapper changed Trip count')
    for trip,previous in zip(core.transport_plan.trips,old.transport_plan.trips):
        a=trip.model_dump();b=previous.model_dump()
        for key in ['estimated_cost','reason_codes']:a.pop(key);b.pop(key)
        require(a==b,'Policy wrapper changed assignments')
        amount=price(resources[trip.resource_id],trip.distance_km);expected.append(amount)
        require((trip.estimated_cost.amount if trip.estimated_cost else None)==amount,'Trip price differs')
        if amount is not None:require(trip.estimated_cost.currency==request.context.currency_policy.currency,'Wrong currency')
    complete=core.feasibility.solution_found and all(v is not None for v in expected)
    expected_total=sum(expected,Decimal(0)) if complete else None
    require((core.metrics.total_cost.amount if core.metrics.total_cost else None)==expected_total,'Total cost differs')
    require(core.metrics.cost_completeness==('COMPLETE' if complete else 'PARTIAL' if any(v is not None for v in expected) else 'UNKNOWN'),'Cost completeness differs')
    a=core.metrics.model_dump();b=old.metrics.model_dump()
    for key in ['total_cost','cost_completeness']:a.pop(key);b.pop(key)
    require(a==b,'Structural metric changed')
    for usage,previous in zip(result.resource_usage,result.structural.resource_usage):
        a=usage.model_dump();b=previous.model_dump();a.pop('total_cost');b.pop('total_cost')
        require(a==b,'Resource usage changed')
        values=[price(resources[t.resource_id],t.distance_km) for t in core.transport_plan.trips if t.resource_id==usage.resource_id]
        amount=sum(values,Decimal(0)) if core.feasibility.solution_found and all(v is not None for v in values) else None
        require((usage.total_cost.amount if usage.total_cost else None)==amount,'Resource cost differs')
    for r,p in zip(result.demand_resolution,result.structural.demand_resolution):
        a=r.model_dump();b=p.model_dump();a.pop('reason_codes');b.pop('reason_codes');require(a==b,'Resolution changed')
    if core.feasibility.solution_found:
        require(core.feasibility.policy_feasible is True and core.feasibility.hard_constraints_satisfied is True,'Uncertified policy')
        trips=core.transport_plan.trips;primary=request.model.primary_dimension
        for guard in request.context.node_policy.guardrails:
            if guard.kind=='MINIMUM_DEMAND_COVERAGE':n,d=core.metrics.demand_coverage.assigned,core.metrics.demand_coverage.requested
            elif guard.kind=='CRITICAL_DEMAND_COVERAGE':n=sum(getattr(r.assigned,primary) for r in result.demand_resolution if r.priority=='HIGH');d=sum(getattr(r.requested,primary) for r in result.demand_resolution if r.priority=='HIGH')
            elif guard.kind=='MAXIMUM_EXTERNAL_SHARE':n,d=sum(t.resource_source=='EXTERNAL' for t in trips),len(trips)
            else:n,d=sum(t.resource_source=='OWN' for t in trips),len(trips)
            require(d==0 or (n<=guard.limit*d if guard.kind=='MAXIMUM_EXTERNAL_SHARE' else n>=guard.limit*d),'Hard guardrail relaxed')
    proof=next(c for c in evidence.constraints if c.code=='POLICY_CERTIFICATE')
    require(proof.facts['goal']==result.exploration_goal,'Wrong exploration policy')
    if core.engine.solver_status=='OPTIMAL':
        require(result.structural.search.candidate_set_complete,'Incomplete candidate-set optimum')
        states=[v for k,v in proof.facts.items() if k.endswith('_status')]
        require(bool(states) and all(v=='OPTIMAL' for v in states),'False optimality')
    trips=core.transport_plan.trips;trip_map={t.trip_id:t for t in trips}
    constraint_ids={c.evidence_id for c in evidence.constraints}
    comparisons={}
    for reason in evidence.reasons:
        require(set(reason.evidence_refs)<=constraint_ids,'Reason certificate missing')
        if reason.code=='SELECTED_PRIORITY_PROTECTION':
            row=next(r for r in result.demand_resolution if r.order_id==reason.entity_id)
            require(row.priority=='HIGH' and reason.facts['assigned_quantity']==getattr(row.assigned,request.model.primary_dimension),'False priority facts')
            require(proof.facts['candidate_set_complete'] and any(v=='COVERAGE_HIGH' and proof.facts[k.replace('_name','_status')]=='OPTIMAL' for k,v in proof.facts.items() if k.endswith('_name')),'Priority trace missing')
        if reason.code not in ('SELECTED_LOWEST_COST_FEASIBLE','SELECTED_ONLY_FEASIBLE_RESOURCE','SELECTED_OWN_COST_ADVANTAGE'):continue
        trip=trip_map[reason.entity_id];feasible=[]
        orders=[o for o in request.demands if o.order_id in {a.order_id for a in trip.orders}]
        for resource in (resources.values() if trip.trip_id not in comparisons else []):
            if resource.source not in request.model.allowed_sources or (trip.origin_id,trip.destination_id) not in resource.lanes:continue
            if resource.source=='OWN' and resource.base_origin_id!=trip.origin_id:continue
            if any(not set(o.compatibility_groups).issubset(resource.compatibility_groups) for o in orders):continue
            if any(getattr(trip.total_load,d)>getattr(resource.guaranteed_capacity,d) for d in request.model.active_dimensions):continue
            certificate=day_resource_feasibility([FixedTrip(trip_id=t.trip_id,resource_id=resource.resource_id if t.trip_id==trip.trip_id else t.resource_id,
                distance_km=t.distance_km,ready_date=t.ready_date,delivery_due_date=t.delivery_due_date) for t in trips],request.resources,
                {'planning_start':request.context.planning_start,'planning_end':request.context.planning_end},deterministic_budget=float(result.comparison_budget))
            require(certificate.status!='UNKNOWN','Selection comparison is unproved')
            if certificate.status=='FEASIBLE':feasible.append((resource,price(resource,trip.distance_km)))
        if trip.trip_id not in comparisons:comparisons[trip.trip_id]=feasible
        else:feasible=comparisons[trip.trip_id]
        if reason.code=='SELECTED_ONLY_FEASIBLE_RESOURCE':require(len(feasible)==1 and feasible[0][0].resource_id==trip.resource_id,'False unique feasible resource')
        else:
            require(all(value is not None for _,value in feasible),'Unknown comparison cost')
            if reason.code=='SELECTED_LOWEST_COST_FEASIBLE':require(trip.estimated_cost.amount==min(value for _,value in feasible)==reason.facts['minimum_feasible_cost'],'False least-cost claim')
            else:require(trip.resource_source=='OWN' and trip.estimated_cost.amount<min(value for r,value in feasible if r.source=='EXTERNAL'),'False OWN advantage')
