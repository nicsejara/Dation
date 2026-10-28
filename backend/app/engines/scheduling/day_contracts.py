"""Versioned D2 input: exact D1 Core/binding and its frozen resource snapshot."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from pydantic import AwareDatetime,StrictBool,model_validator
from app.domain.logistics.base import ContractModel
from app.domain.logistics.contracts import FrozenCaseContext,LogisticsModelVersion,TransportResource
from app.results import contracts as c
from app.results.canonical import core_result_fingerprint

class DaySchedulingInput(ContractModel):
    model: LogisticsModelVersion
    context: FrozenCaseContext
    source_core: c.EngineCoreResult
    source_evidence: c.EngineEvidence
    source_transport_plan: c.ResultBinding
    resources: tuple[TransportResource,...]
    input_summary: c.InputSummary
    run_id: UUID
    result_generated_at: AwareDatetime
    # False is for explicit defensive unit handoffs, never public admission.
    source_temporal_certified: StrictBool=True

    @model_validator(mode='after')
    def exact_upstream(self):
        s=self.source_core
        c.EngineOutput(core=s,evidence=self.source_evidence)
        if s.result_schema!='transport_plan_v1' or s.decision.run_id!=self.source_transport_plan.run_id or s.decision.run_id==self.run_id:
            raise ValueError('D2 requires a distinct exact D1 Core/Run')
        if (s.context.workspace_id,s.context.case_id,s.context.logistics_model_version_id,s.context.model_hash,s.context.planning_start,s.context.planning_end)!=(self.context.workspace_id,self.context.case_id,self.context.logistics_model_version_id,self.context.model_hash,self.context.planning_start,self.context.planning_end):
            raise ValueError('Cross-Case/model/horizon handoff')
        by_id={r.resource_id:r for r in self.resources}
        if len(by_id)!=len(self.resources):raise ValueError('Duplicate source resource')
        for t in s.transport_plan.trips:
            r=by_id.get(t.resource_id)
            if r is None or r.source!=t.resource_source or (t.origin_id,t.destination_id) not in r.lanes or r.guaranteed_capacity!=t.guaranteed_capacity:
                raise ValueError('D1 Trip/resource snapshot mismatch')
        return self

class UpstreamCertificationConflict(ValueError):pass
class SchedulingNotCertified(ValueError):pass

@dataclass(frozen=True)
class DaySchedulingResult:
    output: c.EngineOutput
    source: DaySchedulingInput
    resource_timeline: tuple[c.ResourceTimeline,...]
    service_analysis: tuple[c.ServiceAnalysis,...]
    windows: tuple[c.EntityEvidence,...]

    @property
    def input_summary(self):return self.source.input_summary
