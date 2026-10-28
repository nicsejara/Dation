"""Hash-DAG base, then binding to the completed package. No LLM calls."""
from typing import Literal
from uuid import UUID
from app.domain.logistics.base import ContractModel,SHA256
from app.domain.logistics.contracts import FrozenCaseContext,CasePolicy,NodePolicy
from . import contracts as c
from .canonical import decision_context_hash


class DecisionContextBase(ContractModel):
    schema_version: Literal['decision_context_v1']='decision_context_v1'
    base_version: Literal[1]=1
    run_id: UUID
    core_result_fingerprint: SHA256
    case: FrozenCaseContext
    logistics_model: c.ModelContext
    case_policy: CasePolicy
    decision_definition: c.DecisionDefinitionContext
    node_policy: NodePolicy
    input_summary: c.InputSummary
    result_summary: c.ExecutiveSummary
    metrics: c.Metrics
    exceptions: tuple[c.ExceptionDescriptor,...]
    assumptions: tuple[c.AssumptionDescriptor,...]
    evidence_summary: c.EvidenceSummary
    alternatives_summary: tuple[c.AlternativeSummary,...]
    approval_review: c.ApprovalReview
    entity_refs: tuple[c.EntityRef,...]


def build_base(plan,summary,evidence_summary,exceptions,assumptions,review,alternatives):
    core=plan.output.core;context=core.context
    from .canonical import core_result_fingerprint
    return DecisionContextBase(run_id=core.decision.run_id,core_result_fingerprint=core_result_fingerprint(core),case=context,
        logistics_model=c.ModelContext(id=context.logistics_model_id,version_id=context.logistics_model_version_id,
            version=context.logistics_model_version,model_hash=context.model_hash),case_policy=context.case_policy,node_policy=context.node_policy,
        decision_definition=c.DecisionDefinitionContext(node_id=core.decision.node_id,version=context.graph_version,decision_type=core.decision.decision_type),
        input_summary=plan.input_summary,result_summary=summary,metrics=core.metrics,exceptions=exceptions,assumptions=assumptions,
        evidence_summary=evidence_summary,alternatives_summary=tuple(c.AlternativeSummary(alternative_id=a.alternative_id,metrics=a.metrics,
            evidence_refs=tuple((*a.plan.artifacts,*a.evidence.artifacts))) for a in alternatives),approval_review=review,
        entity_refs=tuple(c.EntityRef(type=e.entity_type,id=e.entity_id) for e in plan.output.evidence.entities))


def bind_context(base,package):
    base=DecisionContextBase.model_validate(base)
    if (base.run_id,base.core_result_fingerprint)!=(package.decision.run_id,package.fingerprints.core_result_fingerprint):raise ValueError('AI base belongs to another Core')
    data=base.model_dump()
    for key in ['base_version','run_id','core_result_fingerprint','entity_refs']:data.pop(key)
    data.update(context_version=1,provenance=c.ResultBinding(run_id=package.decision.run_id,result_fingerprint=package.fingerprints.result_fingerprint),
        mode='EXPLAIN',selected_entity=None,selected_alternative_ids=(),selected_evidence_refs=())
    data['context_hash']=decision_context_hash(data)
    return c.DecisionContextV1.model_validate(data)
