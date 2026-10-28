"""T7 certified policy producer. Assembly never calls optimization."""
from dataclasses import dataclass
from decimal import Decimal,localcontext
from collections import Counter
import hashlib

from app.domain.logistics.base import Priority
from app.domain.logistics.costs import trip_cost
from app.results import contracts as c
from app.results.canonical import canonical_bytes,core_result_fingerprint
from app.results.reason_codes import ReasonEmission,reason_definition
from app.engines.common.day_resource_feasibility import FixedTrip,day_resource_feasibility
from .transport_contracts import TransportPlanInput,TransportPlanComputation,EngineCertificationError
from .transport_plan import _run,ratio
from .transport_policies import PolicySearch,PolicyRequirementsError


@dataclass(frozen=True)
class CertifiedPlan:
    structural: TransportPlanComputation
    output: c.EngineOutput
    demand_resolution: tuple
    residuals: object
    resource_usage: tuple
    input_summary: c.InputSummary
    exploration_goal: str
    comparison_budget: Decimal


@dataclass(frozen=True)
class PolicyResult:
    recommended: CertifiedPlan
    alternatives: tuple[CertifiedPlan,...]
    alternatives_status: str
    explored_goals: tuple[str,...] = ()


def plan_signature(plan):
    trips=plan.output.core.transport_plan.trips
    return hashlib.sha256(canonical_bytes(sorted([
        {'resource_id':t.resource_id,'source':t.resource_source,'origin':t.origin_id,'destination':t.destination_id,
         'distance':t.distance_km,'orders':t.orders} for t in trips],key=canonical_bytes))).hexdigest()


def run_transport_policy(request, *, alternative_budget=3):
    request=TransportPlanInput.model_validate(request)
    if type(alternative_budget) is not int or not 0<=alternative_budget<=3:raise ValueError('Alternative budget 0..3 required')
    with localcontext() as ctx:
        ctx.prec=60
        kernel=Decimal(request.options.kernel_budget)/(2*(1+alternative_budget))
        comparison=kernel/64
        recommended=_produce(request,None,Decimal(request.options.deterministic_budget)*Decimal('.7') if alternative_budget else Decimal(request.options.deterministic_budget),kernel,comparison)
        if not alternative_budget:return PolicyResult(recommended,(),'BUDGET_LIMIT')
        if not recommended.output.core.feasibility.solution_found:return PolicyResult(recommended,(),'NOT_COMPUTED')
        choices=[g for g in ['MINIMIZE_COST','MAXIMIZE_OWN_CAPACITY','MINIMIZE_TRIPS','MAXIMIZE_SERVICE'] if g!=request.context.node_policy.primary_goal][:alternative_budget]
        alternatives=[];seen={plan_signature(recommended)};limited=False
        for other in choices:
            try:candidate=_produce(request,other,Decimal(request.options.deterministic_budget)*Decimal('.3')/alternative_budget,kernel,comparison)
            except PolicyRequirementsError:
                limited=True;continue
            if not candidate.output.core.feasibility.solution_found:
                limited=True;continue
            signature=plan_signature(candidate)
            if signature not in seen:
                alternatives.append(candidate);seen.add(signature)
        return PolicyResult(recommended,tuple(alternatives),'COMPUTED' if alternatives else 'BUDGET_LIMIT' if limited else 'NO_MATERIAL_ALTERNATIVE',tuple(choices))


def _produce(request,goal=None,model_budget=None,kernel_budget=Decimal(1),comparison_budget=Decimal('.01')):
    search=PolicySearch(request,goal,model_budget=float(model_budget) if model_budget is not None else None,kernel_budget=float(kernel_budget))
    structural=_run(request,search)
    old=structural.output
    usable=old.core.feasibility.solution_found
    complete=structural.search.candidate_set_complete
    optimal=usable and complete and search.all_optimal
    infeasible=not usable and complete and search.native_statuses[-1:]==['INFEASIBLE']
    status='OPTIMAL' if optimal else 'FEASIBLE' if usable else 'INFEASIBLE' if infeasible else 'UNKNOWN'
    resources={r.resource_id:r for r in request.resources}
    trips=[]
    for trip in old.core.transport_plan.trips:
        resource=resources[trip.resource_id]
        price=trip_cost(resource,trip.distance_km,request.context.currency_policy)
        cost=c.EstimatedCost(**price.model_dump(),cost_model='OWN_OPERATING_CYCLE' if resource.source=='OWN' else resource.external_cost.cost_model) if price else None
        trips.append(c.Trip.model_validate({**trip.model_dump(),'estimated_cost':cost}))
    all_known=usable and all(t.estimated_cost is not None for t in trips)
    known=[t.estimated_cost.amount for t in trips if t.estimated_cost]
    currency=request.context.currency_policy.currency
    metrics=c.TransportPlanMetrics.model_validate({**old.core.metrics.model_dump(),
        'total_cost':{'amount':sum(known,Decimal(0)),'currency':currency} if all_known else None,
        'cost_completeness':'COMPLETE' if all_known else 'PARTIAL' if known else 'UNKNOWN'})
    usages=[]
    for u in structural.resource_usage:
        used=[t for t in trips if t.resource_id==u.resource_id]
        cost={'amount':sum((t.estimated_cost.amount for t in used),Decimal(0)),'currency':currency} if usable and all(t.estimated_cost is not None for t in used) else None
        usages.append(c.ResourceUsage.model_validate({**u.model_dump(),'total_cost':cost}))
    constraints=[v for v in old.evidence.constraints if v.code!='SEARCH_SCOPE'];reasons=list(old.evidence.reasons)
    proof_id='POL-'+hashlib.sha256(canonical_bytes([search.model_sha256,search.stages,complete])).hexdigest()[:24]
    facts={'definition':'D1_POLICY_V1','goal':goal or request.context.node_policy.primary_goal,
        'coverage_basis':'PRIMARY_DIMENSION','source_share_basis':'TRIPS','critical_priority':'HIGH',
        'candidate_set_complete':complete,'model_sha256':search.model_sha256,
        'model_deterministic_budget':model_budget,'kernel_deterministic_budget':kernel_budget,'local_comparison_budget':comparison_budget,**search.normalization}
    for i,(label,native,value,bound) in enumerate(search.stages):
        facts.update({f'stage_{i}_name':label,f'stage_{i}_status':native,f'stage_{i}_value':value,f'stage_{i}_bound':bound})
    constraints.append(c.ConstraintEvidence(evidence_id=proof_id,code='POLICY_CERTIFICATE',status='SATISFIED' if usable else 'VIOLATED' if infeasible else 'UNKNOWN',hard=True,facts=facts))
    high_requested=sum((getattr(o.requested,request.model.primary_dimension) for o in request.demands if o.priority=='HIGH'),Decimal(0))
    high_assigned=sum((getattr(o.assigned,request.model.primary_dimension) for o in structural.demand_resolution if o.priority=='HIGH'),Decimal(0))
    assigned=metrics.demand_coverage.assigned;requested=metrics.demand_coverage.requested
    own=sum(t.resource_source=='OWN' for t in trips);external=len(trips)-own
    for i,guard in enumerate(request.context.node_policy.guardrails):
        n,d=(assigned,requested) if guard.kind=='MINIMUM_DEMAND_COVERAGE' else (high_assigned,high_requested) if guard.kind=='CRITICAL_DEMAND_COVERAGE' else (Decimal(external),Decimal(len(trips))) if guard.kind=='MAXIMUM_EXTERNAL_SHARE' else (Decimal(own),Decimal(len(trips)))
        satisfied=d==0 or (n<=guard.limit*d if guard.kind=='MAXIMUM_EXTERNAL_SHARE' else n>=guard.limit*d)
        if usable and not satisfied:raise EngineCertificationError('CP policy and guardrail facts disagree')
        constraints.append(c.ConstraintEvidence(evidence_id=f'GUARD-{i}',code=guard.kind,
            status='SATISFIED' if usable and satisfied else 'VIOLATED' if infeasible else 'UNKNOWN',hard=True,
            facts={'numerator':n,'denominator':d,'limit':guard.limit,'zero_denominator':'VACUOUS','proof_ref':proof_id}))
    def emit(code,kind,entity,facts,ref):
        spec=reason_definition(code)
        reasons.append(ReasonEmission(emission_id='R-'+hashlib.sha256(canonical_bytes([code,kind,entity,facts])).hexdigest()[:24],code=code,
            entity_type=kind,entity_id=entity,producer='transport_plan',claim_strength=spec.claim_strength,facts=facts,evidence_refs=(ref,)))
    if usable and complete and any(label=='COVERAGE_HIGH' and native=='OPTIMAL' for label,native,_,_ in search.stages):
        for order in structural.demand_resolution:
            quantity=getattr(order.assigned,request.model.primary_dimension)
            if order.priority=='HIGH' and quantity>0:
                emit('SELECTED_PRIORITY_PROTECTION','ORDER',order.order_id,dict(protected_priority='HIGH',assigned_quantity=quantity,policy_evidence_ref=proof_id),proof_id)
    # Explicit local counterfactual scope: hold every other Trip fixed. Only
    # complete feasible-resource comparisons can emit a positive selection claim.
    if usable and len(trips)<=8 and len(resources)<=4:
        for trip in trips:
            candidates=[];comparison_complete=True
            for resource in sorted(resources.values(),key=lambda r:r.resource_id):
                rows=[o for o in request.demands if o.order_id in {a.order_id for a in trip.orders}]
                if resource.source not in request.model.allowed_sources or (trip.origin_id,trip.destination_id) not in resource.lanes:continue
                if resource.source=='OWN' and resource.base_origin_id!=trip.origin_id:continue
                if any(not set(o.compatibility_groups).issubset(resource.compatibility_groups) for o in rows):continue
                if any(getattr(trip.total_load,d)>getattr(resource.guaranteed_capacity,d) for d in request.model.active_dimensions):continue
                if (resource.units_available if resource.source=='OWN' else resource.services_available) is None:
                    comparison_complete=False;continue
                fixed=[FixedTrip(trip_id=t.trip_id,resource_id=resource.resource_id if t.trip_id==trip.trip_id else t.resource_id,
                    distance_km=t.distance_km,ready_date=t.ready_date,delivery_due_date=t.delivery_due_date) for t in trips]
                certificate=day_resource_feasibility(fixed,request.resources,{'planning_start':request.context.planning_start,'planning_end':request.context.planning_end},deterministic_budget=float(comparison_budget))
                if certificate.status=='UNKNOWN':comparison_complete=False
                if certificate.status=='FEASIBLE':candidates.append((resource,trip_cost(resource,trip.distance_km,request.context.currency_policy)))
            if not comparison_complete or not candidates:continue
            ref='CMP-'+trip.trip_id
            constraints.append(c.ConstraintEvidence(evidence_id=ref,code='LOCAL_RESOURCE_COMPARISON',status='SATISFIED',hard=False,
                facts={'trip_id':trip.trip_id,'scope':'FIXED_OTHER_TRIPS','candidate_set_complete':True,'feasible_resource_ids':tuple(r.resource_id for r,_ in candidates),
                    **{'cost_'+str(i):p.amount if p else None for i,(_,p) in enumerate(candidates)}}))
            if len(candidates)==1:emit('SELECTED_ONLY_FEASIBLE_RESOURCE','TRIP',trip.trip_id,dict(selected_resource_id=trip.resource_id,feasible_candidate_count=1,candidate_set_complete=True,certificate_ref=ref),ref)
            if trip.estimated_cost is not None and all(p is not None for _,p in candidates):
                minimum=min(p.amount for _,p in candidates)
                if trip.estimated_cost.amount==minimum:emit('SELECTED_LOWEST_COST_FEASIBLE','TRIP',trip.trip_id,dict(selected_resource_id=trip.resource_id,selected_cost=minimum,currency=currency,minimum_feasible_cost=minimum,candidate_set_complete=True,certificate_ref=ref),ref)
                external_cost=[p.amount for r,p in candidates if r.source=='EXTERNAL']
                if trip.resource_source=='OWN' and external_cost and trip.estimated_cost.amount<min(external_cost):
                    emit('SELECTED_OWN_COST_ADVANTAGE','TRIP',trip.trip_id,dict(own_cost=trip.estimated_cost.amount,external_cost=min(external_cost),currency=currency,candidate_set_complete=True,certificate_ref=ref),ref)
    def codes(kind,eid):return tuple(sorted({r.code for r in reasons if r.entity_type==kind and r.entity_id==eid}))
    trips=[c.Trip.model_validate({**t.model_dump(),'reason_codes':codes('TRIP',t.trip_id)}) for t in trips]
    resolutions=tuple(c.DemandResolution.model_validate({**o.model_dump(),'reason_codes':codes('ORDER',o.order_id)}) for o in structural.demand_resolution)
    entities=[]
    for e in old.evidence.entities:
        facts=dict(e.facts)
        if e.entity_type=='ORDER':
            resolution=next(o for o in resolutions if o.order_id==e.entity_id)
            facts.update(resource_ids=tuple(sorted({t.resource_id for t in trips if any(a.order_id==e.entity_id for a in t.orders)})),
                status=resolution.status,coverage_ratio=resolution.coverage_ratio)
        if e.entity_type=='RESOURCE':
            u=next(u for u in usages if u.resource_id==e.entity_id)
            facts.update(total_cost=u.total_cost.amount if u.total_cost else None)
        entities.append(c.EntityEvidence.model_validate({**e.model_dump(),'facts':facts,'reason_refs':tuple(r.emission_id for r in reasons if (r.entity_type,r.entity_id)==(e.entity_type,e.entity_id))}))
    core=c.EngineCoreResult.model_validate({**old.core.model_dump(),'engine':{**old.core.engine.model_dump(),'solver_status':status},
        'feasibility':dict(solution_found=usable,policy_feasible=True if usable else False if infeasible else None,
            hard_constraints_satisfied=True if usable else False if infeasible else None,full_demand_coverage=old.core.feasibility.full_demand_coverage),
        'metrics':metrics,'transport_plan':dict(trips=trips,unassigned_demand=tuple(o for o in resolutions if o.status!='COVERED'),capacity_gap=old.core.transport_plan.capacity_gap)})
    goal_stage=next(((value,bound) for label,_,value,bound in search.stages if label==(goal or request.context.node_policy.primary_goal)),(None,None))
    solver=c.SolverEvidence(status=status,objective_value=Decimal(goal_stage[0]) if goal_stage[0] is not None else None,best_bound=Decimal(goal_stage[1]) if optimal and goal_stage[1] is not None else None,
        certificate=c.SolverCertificate(kind='GLOBAL_OPTIMUM' if optimal else 'FEASIBILITY' if usable else 'INFEASIBILITY',evidence_ref=proof_id) if optimal or usable or infeasible else None)
    evidence=c.EngineEvidence.model_validate({**old.evidence.model_dump(),'core_result_fingerprint':core_result_fingerprint(core),
        'policy':c.PolicyEvidence.model_validate({**old.evidence.policy.model_dump(),'evidence_id':proof_id}),
        'constraints':constraints,'solver':solver,'reasons':reasons,'entities':entities})
    summary=c.InputSummary(orders=len(request.demands),demand={d:sum((getattr(o.requested,d) for o in request.demands),Decimal(0)) for d in request.model.active_dimensions},
        priority_distribution={p:sum(o.priority==p for o in request.demands) for p in Priority},own_resources=sum(r.source=='OWN' for r in request.resources),external_resources=sum(r.source=='EXTERNAL' for r in request.resources))
    result=CertifiedPlan(structural,c.EngineOutput(core=core,evidence=evidence),resolutions,structural.residuals,tuple(usages),summary,goal or request.context.node_policy.primary_goal,comparison_budget)
    from .transport_policy_validator import certify_policy_result
    certify_policy_result(request,result)
    return result
