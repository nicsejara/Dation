"""Immutable deterministic review, separate from current approval authority."""
from .contracts import ApprovalReview,ReviewItem,EntityRef


def build_review(core,evidence,exceptions,assumptions):
    coverage='UNKNOWN' if core.feasibility.full_demand_coverage is None else 'FULL' if core.feasibility.full_demand_coverage else 'PARTIAL' if core.metrics.demand_coverage.assigned>0 else 'NONE'
    ready=core.feasibility.solution_found and core.feasibility.policy_feasible is True and core.feasibility.hard_constraints_satisfied is True
    items=[]
    if not ready:
        proof=next(c for c in evidence.constraints if c.code=='POLICY_CERTIFICATE')
        items.append(ReviewItem(priority=1,type='POLICY' if core.feasibility.policy_feasible is False else 'DATA',code='POLICY_INFEASIBLE' if core.feasibility.policy_feasible is False else 'SOLVER_UNCERTIFIED',entity=None,evidence_refs=(proof.evidence_id,)))
    for exception in exceptions:
        items.append(ReviewItem(priority=2,type='BUSINESS_GAP' if exception.category=='BUSINESS' else 'DATA',code=exception.code,
            entity=EntityRef(type=exception.entity_type,id=exception.entity_ids[0]),evidence_refs=(exception.reason_ref,)))
    for assumption in assumptions:
        items.append(ReviewItem(priority=3,type='ASSUMPTION',code=assumption.code,entity=EntityRef(type=assumption.entity_type,id=assumption.entity_id),evidence_refs=(assumption.reason_ref,)))
    return ApprovalReview(decision_ready_for_review=ready,hard_constraints_satisfied=core.feasibility.hard_constraints_satisfied,
        coverage_status=coverage,exception_count=len(exceptions),assumption_count=len(assumptions),
        review_items=tuple(sorted(items,key=lambda i:(i.priority,i.type,i.code,i.entity.id if i.entity else ''))))
