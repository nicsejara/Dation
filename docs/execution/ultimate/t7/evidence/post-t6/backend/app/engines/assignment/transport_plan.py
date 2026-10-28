"""Inactive transport_plan/2.0.0 core producer, callable on pinned DTOs in tests.

No CSV, DB, artifacts, worker admission, economic policy or D2 recommendation.
"""
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
import hashlib

from app.domain.logistics.base import Dimension, Priority
from app.domain.logistics.units import QuantityVector, QUANTITY_SCALES
from app.results import contracts as c
from app.results.canonical import canonical_bytes, input_context_hash, core_result_fingerprint
from app.results.reason_codes import ReasonEmission, reason_definition
from app.engines.common.day_resource_feasibility import (
    FixedTrip, FeasibilityCertificate, day_resource_feasibility, dispatch_window)
from .transport_contracts import TransportPlanInput, TransportPlanComputation, EngineCertificationError
from .transport_model import solve_structural, compatible

IDENTITY = c.RuntimeIdentity(engine_name='transport_plan',engine_version='2.0.0',
    runtime_profile='transport_plan_v1',result_schema='transport_plan_v1',result_schema_version=1)


def ratio(numerator, denominator, scale=4):
    if not denominator:
        return None
    with localcontext() as ctx:
        ctx.prec = 60
        return (Decimal(numerator)/Decimal(denominator)).quantize(Decimal(1).scaleb(-scale), rounding=ROUND_HALF_UP)


def vector(values):
    return QuantityVector(**values)


def run_transport_plan(request):
    request = TransportPlanInput.model_validate(request)
    with localcontext() as ctx:
        ctx.prec = 60
        return _run(request)


def _run(request):
    orders, denominators, slots, selected, trace = solve_structural(request)
    dims, context = request.model.active_dimensions, request.context
    staged = []
    if selected is not None:
        for slot, values in zip(slots,selected):
            allocations = []
            for i,numerator in sorted(values.items()):
                if not numerator:
                    continue
                denominator, units = denominators[i]
                load = vector({d:Decimal(units[d]*numerator).scaleb(-QUANTITY_SCALES[d]) for d in dims})
                allocations.append(c.Allocation(order_id=orders[i].order_id,
                    allocation_fraction=ratio(numerator,denominator,6),load=load))
            if not allocations:
                continue
            rows = [o for o in orders if o.order_id in {a.order_id for a in allocations}]
            load = vector({d:sum(getattr(a.load,d) for a in allocations) for d in dims})
            cap = vector({d:getattr(slot.resource.guaranteed_capacity,d) for d in dims})
            data = dict(origin_id=rows[0].origin_id,destination_id=rows[0].destination_id,
                distance_km=slot.distance,resource_id=slot.resource.resource_id,resource_source=slot.resource.source,
                orders=tuple(allocations),total_load=load,guaranteed_capacity=cap,
                utilization=c.UtilizationVector(**{d:ratio(getattr(load,d),getattr(cap,d)) for d in dims}),
                estimated_cost=None,ready_date=max(o.ready_date for o in rows),
                delivery_due_date=min(o.delivery_due_date for o in rows))
            staged.append((canonical_bytes(data),data))
    trips, repeated = [], Counter()
    for key,data in sorted(staged,key=lambda pair:pair[0]):
        digest = hashlib.sha256(key).hexdigest()[:24]
        repeated[digest] += 1
        trips.append(c.Trip(trip_id=f'TP-{digest}-{repeated[digest]}',**data))
    temporal = day_resource_feasibility([
        FixedTrip(trip_id=t.trip_id,resource_id=t.resource_id,distance_km=t.distance_km,
            ready_date=t.ready_date,delivery_due_date=t.delivery_due_date) for t in trips
    ],request.resources,{'planning_start':context.planning_start,'planning_end':context.planning_end},
        deterministic_budget=request.options.kernel_budget)
    if trips and temporal.status == 'INFEASIBLE':
        raise EngineCertificationError('D1 candidate and independent fixed-trip kernel disagree')
    usable = selected is not None and temporal.status == 'FEASIBLE'
    if not usable:
        trips = []
        if temporal.status == 'FEASIBLE':
            temporal = FeasibilityCertificate(status='UNKNOWN',native_status='NOT_RUN',cause='NO_STRUCTURAL_INCUMBENT')
    # A CP optimum for the restricted structural model is not a certificate of
    # T7's complete goal/policy. Preserve its native status in the search trace.
    status = 'FEASIBLE' if usable else ('INFEASIBLE' if trace['native_statuses'][-1:] == ('INFEASIBLE',) else 'UNKNOWN')
    assigned = {o.order_id:{d:Decimal(0) for d in dims} for o in orders}
    trip_refs = {o.order_id:[] for o in orders}
    for trip in trips:
        for allocation in trip.orders:
            trip_refs[allocation.order_id].append(trip.trip_id)
            for d in dims:
                assigned[allocation.order_id][d] += getattr(allocation.load,d)
    residuals = {o.order_id:vector({d:getattr(o.requested,d)-assigned[o.order_id][d] for d in dims}) for o in orders}
    resolutions, usages = [], []
    for order in orders:
        residual = residuals[order.order_id]
        has_gap = any(getattr(residual,d)>0 for d in dims)
        has_assigned = any(assigned[order.order_id][d]>0 for d in dims)
        resolutions.append(c.DemandResolution(order_id=order.order_id,priority=order.priority,
            requested=vector({d:getattr(order.requested,d) for d in dims}),assigned=vector(assigned[order.order_id]),
            coverage_ratio=ratio(assigned[order.order_id][request.model.primary_dimension],getattr(order.requested,request.model.primary_dimension)),
            trip_ids=tuple(sorted(trip_refs[order.order_id])),status='COVERED' if not has_gap else 'PARTIALLY_COVERED' if has_assigned else 'UNASSIGNED'))
    for resource in sorted(request.resources,key=lambda r:r.resource_id):
        used = [t for t in trips if t.resource_id == resource.resource_id]
        totals = {d:sum((getattr(t.total_load,d) for t in used),Decimal(0)) for d in dims}
        usages.append(c.ResourceUsage(resource_id=resource.resource_id,resource_source=resource.source,
            trip_ids=tuple(t.trip_id for t in used),total_load=vector(totals),total_cost=None,
            weighted_utilization=c.UtilizationVector(**{d:ratio(totals[d],len(used)*getattr(resource.guaranteed_capacity,d)) for d in dims}),
            services_available=resource.services_available,services_used=len(used) if resource.source=='EXTERNAL' else None,
            services_remaining=resource.services_available-len(used) if resource.services_available is not None else None,
            availability_source=resource.availability_source,units_available=resource.units_available,
            trip_count=len(used),total_distance_km=sum((t.distance_km for t in used),Decimal(0))))
    reasons, constraints = [], []
    def constraint(code, facts, *, entity='global', satisfied=True, hard=True):
        eid = 'E-'+hashlib.sha256(canonical_bytes([code,entity,facts])).hexdigest()[:24]
        constraints.append(c.ConstraintEvidence(evidence_id=eid,code=code,
            status='SATISFIED' if satisfied else 'VIOLATED',hard=hard,facts=facts))
        return eid
    def reason(code,kind,entity,facts,reference):
        definition=reason_definition(code)
        rid='R-'+hashlib.sha256(canonical_bytes([code,kind,entity,facts])).hexdigest()[:24]
        emission=ReasonEmission(emission_id=rid,code=code,entity_type=kind,entity_id=entity,
            producer='transport_plan',claim_strength=definition.claim_strength,facts=facts,evidence_refs=(reference,))
        reasons.append(emission)
    cert_ref=constraint('STRUCTURAL_CERTIFICATE',{'solution_found':usable,'temporal_status':temporal.status},hard=False)
    constraint('SEARCH_SCOPE',{'objective_scope':trace.get('version','D1_STRUCTURAL_FRACTION_COVERAGE_V1'),
        'native_statuses':trace['native_statuses'],'candidate_set_complete':False,
        'candidate_slots':trace['candidate_slots'],'variable_count':trace['variable_count'],
        'limits':trace['limits'],'seed':request.options.seed,'model_sha256':trace['model_sha256'],
        'solver_version':trace['solver_version']},hard=False)
    for witness in temporal.witness:
        constraint('TEMPORAL_WITNESS',witness.model_dump(mode='python'),entity=witness.trip_id)
    for trip in trips:
        for d in dims:
            facts=dict(dimension=d,guaranteed_capacity=getattr(trip.guaranteed_capacity,d),load=getattr(trip.total_load,d),capacity_basis='GUARANTEED')
            ref=constraint('VECTOR_CAPACITY',facts,entity=trip.trip_id)
            reason('GUARANTEED_CAPACITY_USED_FOR_FEASIBILITY','TRIP',trip.trip_id,facts,ref)
        if len(trip.orders)>1:
            first,last,_=dispatch_window(trip,next(r for r in request.resources if r.resource_id==trip.resource_id),context)
            ref=constraint('CONSOLIDATION',{'trip_id':trip.trip_id,'order_ids':tuple(a.order_id for a in trip.orders)},entity=trip.trip_id)
            reason('CONSOLIDATED_COMPATIBLE_DEMAND','TRIP',trip.trip_id,dict(order_ids=tuple(a.order_id for a in trip.orders),
                compatibility_certificate_ref=ref,window_start=date.fromordinal(first),window_end=date.fromordinal(last)),ref)
    for resource, usage in zip(sorted(request.resources,key=lambda r:r.resource_id),usages):
        if resource.source=='EXTERNAL':
            ref=constraint('FINITE_SERVICES',dict(resource_id=resource.resource_id,services_available=resource.services_available,services_used=usage.services_used),entity=resource.resource_id)
            if resource.availability_source=='ASSUMED':
                reason('ASSUMED_EXTERNAL_AVAILABILITY','RESOURCE',resource.resource_id,dict(services_available=resource.services_available,availability_source='ASSUMED'),ref)
            if resource.services_available==usage.services_used:
                reason('RESOURCE_SERVICE_LIMIT_REACHED','RESOURCE',resource.resource_id,dict(services_available=resource.services_available,services_used=usage.services_used),ref)
    for order in orders:
        eligible=[r for r in request.resources if compatible(order,r,request.model)]
        if not eligible:
            ref=constraint('COMPATIBILITY_EXHAUSTION',{'order_id':order.order_id,'resource_ids':tuple(r.resource_id for r in request.resources)},entity=order.order_id,hard=False)
            reason('NO_COMPATIBLE_RESOURCE','ORDER',order.order_id,dict(compatible_resource_count=0,candidate_set_complete=True,certificate_ref=ref),ref)
        if not(order.split_allowed and request.model.split_permitted) and eligible:
            for d in dims:
                maximum=max(getattr(r.guaranteed_capacity,d) for r in eligible)
                if getattr(order.requested,d)>maximum:
                    reason('NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY','ORDER',order.order_id,
                        dict(split_allowed=False,dimension=d,requested=getattr(order.requested,d),maximum_guaranteed_capacity=maximum),cert_ref)
        if eligible:
            windows=[dispatch_window(order,r,context)[:2] for r in eligible]
            if all(a>b for a,b in windows) and max(b for a,b in windows)>=1:
                reason('DATE_WINDOW_INCOMPATIBLE','ORDER',order.order_id,dict(earliest_dispatch=date.fromordinal(windows[0][0]),latest_dispatch=date.fromordinal(max(b for a,b in windows))),cert_ref)
        if usable:
            for d in dims:
                if getattr(residuals[order.order_id],d)>0:
                    reason('CAPACITY_GAP','ORDER',order.order_id,dict(dimension=d,unassigned_quantity=getattr(residuals[order.order_id],d)),cert_ref)
    def refs(kind,entity):
        return tuple(r.emission_id for r in reasons if r.entity_type==kind and r.entity_id==entity)
    trips=[c.Trip.model_validate({**t.model_dump(), 'reason_codes':tuple(sorted({r.code for r in reasons if r.entity_type=='TRIP' and r.entity_id==t.trip_id}))}) for t in trips]
    resolutions=[c.DemandResolution.model_validate({**o.model_dump(),'reason_codes':tuple(sorted({r.code for r in reasons if r.entity_type=='ORDER' and r.entity_id==o.order_id}))}) for o in resolutions]
    entities=[]
    for order,resolution in zip(orders,resolutions):
        facts={'priority':order.priority,'trip_ids':resolution.trip_ids,'split_allowed':order.split_allowed and request.model.split_permitted}
        for d in dims:
            facts.update({f'requested_{d}':getattr(order.requested,d),f'assigned_{d}':getattr(resolution.assigned,d),f'residual_{d}':getattr(residuals[order.order_id],d)})
        candidates=[]
        for resource in sorted(request.resources,key=lambda r:r.resource_id):
            rejected=[]
            if not compatible(order,resource,request.model):rejected.append('RESOURCE_INCOMPATIBLE')
            first,last,_=dispatch_window(order,resource,context)
            if first>last:rejected.append('DATE_WINDOW_INCOMPATIBLE')
            if not(order.split_allowed and request.model.split_permitted) and any(getattr(order.requested,d)>getattr(resource.guaranteed_capacity,d) for d in dims):rejected.append('NON_SPLIT_CAPACITY')
            available=resource.units_available if resource.source=='OWN' else resource.services_available
            if available==0:rejected.append('ZERO_AVAILABILITY')
            candidate_facts={'order_id':order.order_id,'resource_id':resource.resource_id,
                'rejected_by':tuple(rejected),'scope':'STATIC_PAIR_ONLY',
                'origin_id':order.origin_id,'destination_id':order.destination_id,
                'source':resource.source,'source_allowed':resource.source in request.model.allowed_sources,
                'lane_allowed':(order.origin_id,order.destination_id) in resource.lanes,
                'order_compatibility':tuple(sorted(order.compatibility_groups)),
                'resource_compatibility':tuple(sorted(resource.compatibility_groups)),
                'earliest_dispatch_ordinal':first,'latest_dispatch_ordinal':last,
                'availability':available,'split_permitted':order.split_allowed and request.model.split_permitted}
            for d in dims:
                candidate_facts.update({f'requested_{d}':getattr(order.requested,d),f'guaranteed_{d}':getattr(resource.guaranteed_capacity,d)})
            constraint('CANDIDATE_ELIGIBILITY',candidate_facts,entity=order.order_id+':'+resource.resource_id,satisfied=not rejected,hard=False)
            chosen=any(t.resource_id==resource.resource_id and any(a.order_id==order.order_id for a in t.orders) for t in trips)
            candidates.append(c.CandidateSummary(resource_id=resource.resource_id,status='SELECTED' if chosen else 'INFEASIBLE' if rejected else 'UNKNOWN',estimated_cost=None,reason_refs=()))
        entities.append(c.EntityEvidence(entity_type='ORDER',entity_id=order.order_id,facts=facts,reason_refs=refs('ORDER',order.order_id),candidate_summary=tuple(candidates)))
    for resource,usage in zip(sorted(request.resources,key=lambda r:r.resource_id),usages):
        facts={'source':resource.source,'trip_ids':usage.trip_ids,'services_available':resource.services_available,
            'services_used':usage.services_used,'units_available':resource.units_available,'availability_source':resource.availability_source,
            'operating_cost_per_km':resource.operating_cost_per_km,'external_cost_model':resource.external_cost.cost_model if resource.external_cost else None,
            'external_rate':resource.external_cost.rate if resource.external_cost else None,
            'billing_basis':resource.external_cost.billing_basis if resource.external_cost else None}
        entities.append(c.EntityEvidence(entity_type='RESOURCE',entity_id=resource.resource_id,facts=facts,reason_refs=refs('RESOURCE',resource.resource_id)))
    entities.extend(c.EntityEvidence(entity_type='TRIP',entity_id=t.trip_id,facts={'resource_id':t.resource_id,'order_ids':tuple(a.order_id for a in t.orders)},reason_refs=refs('TRIP',t.trip_id)) for t in trips)
    primary=request.model.primary_dimension
    requested=sum((getattr(o.requested,primary) for o in orders),Decimal(0))
    total_assigned=sum((getattr(o.assigned,primary) for o in resolutions),Decimal(0))
    own=sum(t.resource_source=='OWN' for t in trips)
    gap=vector({d:sum((getattr(v,d) for v in residuals.values()),Decimal(0)) for d in dims})
    coverage={p:(sum((getattr(o.assigned,primary) for o in resolutions if o.priority==p),Decimal(0)),sum((getattr(o.requested,primary) for o in orders if o.priority==p),Decimal(0))) for p in Priority}
    metrics=dict(total_cost=None,cost_completeness='UNKNOWN',trip_count=len(trips),
        demand_coverage=dict(primary_dimension=primary,requested=requested,assigned=total_assigned,unassigned=requested-total_assigned,ratio=ratio(total_assigned,requested)),
        capacity_utilization=dict(primary_dimension=primary,weighted_ratio=ratio(sum((getattr(t.total_load,primary) for t in trips),Decimal(0)),sum((getattr(t.guaranteed_capacity,primary) for t in trips),Decimal(0)))),
        resource_mix=dict(own_trip_ratio=ratio(own,len(trips)),external_trip_ratio=ratio(len(trips)-own,len(trips))),resources_used=len({t.resource_id for t in trips}),
        coverage_by_priority=[dict(priority=p,coverage_ratio=ratio(*coverage[p])) for p in Priority])
    core=c.EngineCoreResult(result_schema='transport_plan_v1',decision=c.Decision(node_id='logistics_assignment',decision_type='TRANSPORT_PLAN',decision_label='Transport Plan',run_id=request.run_id),
        context=context,engine=c.EngineHeader(engine_name=IDENTITY.engine_name,engine_version=IDENTITY.engine_version,runtime_profile=IDENTITY.runtime_profile,
            solver='OR_TOOLS_CP_SAT',solver_status=status,result_generated_at=request.result_generated_at),input_context_hash=input_context_hash(context,IDENTITY),
        feasibility=c.Feasibility(solution_found=usable,policy_feasible=None,hard_constraints_satisfied=True if usable else None,
            full_demand_coverage=not any(getattr(gap,d)>0 for d in dims) if usable else None),metrics=metrics,
        transport_plan=c.TransportPlan(trips=tuple(trips),unassigned_demand=tuple(o for o in resolutions if o.status!='COVERED'),capacity_gap=gap if any(getattr(gap,d)>0 for d in dims) else None))
    solver=dict(status=status,objective_value=None,best_bound=None,certificate=c.SolverCertificate(kind='FEASIBILITY' if usable else 'INFEASIBILITY',evidence_ref=cert_ref) if usable or status=='INFEASIBLE' else None)
    evidence=c.EngineEvidence(result_schema='transport_plan_v1',workspace_id=context.workspace_id,run_id=request.run_id,input_context_hash=core.input_context_hash,
        core_result_fingerprint=core_result_fingerprint(core),policy=c.PolicyEvidence(case_goal=context.case_policy.primary_goal,effective_node_policy=context.node_policy.primary_goal,
            override=context.node_policy.override,override_reason=context.node_policy.override_reason,evidence_id=cert_ref),constraints=tuple(constraints),solver=c.SolverEvidence(**solver),
        reasons=tuple(reasons),entities=tuple(entities))
    computation=TransportPlanComputation(output=c.EngineOutput(core=core,evidence=evidence),demand_resolution=tuple(resolutions),residuals=residuals,resource_usage=tuple(usages),temporal_certificate=temporal,search=trace)
    from .transport_validator import certify_transport_plan
    certify_transport_plan(request,computation)
    return computation
