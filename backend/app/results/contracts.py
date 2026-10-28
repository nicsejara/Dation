"""Ultimate v1 Core/Evidence/Package and consumption ABI; no result producers."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from app.domain.logistics.base import (ContractModel, Count, DecisionDate, DecimalValue,
    Dimension, EntityType, Identifier, NonNegative, Positive, Priority, Ratio, ResourceSource, SHA256)
from app.domain.logistics.contracts import CasePolicy, FrozenCaseContext, NodePolicy
from app.domain.logistics.transit import TRANSIT_MODEL_VERSION
from app.domain.logistics.units import Money, QuantityVector, scaled_integer, DISTANCE_SCALE
from .metrics import DaySchedulingMetrics, TransportPlanMetrics, validate_ratio
from .reason_codes import FactValue, ReasonEmission, reason_definition

ResultSchema = Literal["transport_plan_v1", "day_scheduling_v1"]
NodeID = Literal["logistics_assignment", "logistics_scheduling"]
SolverStatus = Literal["OPTIMAL", "FEASIBLE", "UNKNOWN", "INFEASIBLE"]
ScheduleStatus = Literal["ON_TIME", "AT_RISK", "LATE", "PRE_HORIZON_DISPATCH_REQUIRED", "UNSCHEDULED"]
ArtifactKind = Literal["CORE", "EVIDENCE", "ENTITY_EVIDENCE", "DETAIL_DATASET", "VISUAL", "EXPORT_ROWS", "AI_BASE", "ALTERNATIVE_PLAN"]
ContextMode = Literal["EXPLAIN", "EXPLORE", "COMPARE", "REVIEW"]
DatasetSchema = Literal["transport_trip_v1", "demand_resolution_v1", "resource_usage_v1",
    "day_schedule_trip_v1", "resource_timeline_v1", "service_analysis_v1", "entity_evidence_v1",
    "reason_emission_v1", "export_rows_v1", "decision_context_v1", "engine_core_v1",
    "engine_evidence_v1", "sankey_projection_v1", "day_gantt_projection_v1"]
Metrics = TransportPlanMetrics | DaySchedulingMetrics
T = TypeVar("T")
PACKAGE_MAX_BYTES = 512 * 1024
VISUAL_INLINE_MAX_BYTES = 256 * 1024
EVIDENCE_CHUNK_MAX_BYTES = 1024 * 1024
EVIDENCE_CHUNK_MAX_ENTITIES = 100
PAGE_MAX_ROWS = 100
SELECTED_ENTITY_MAX_BYTES = 50 * 1024


class RuntimeIdentity(ContractModel):
    engine_name: Identifier
    engine_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    runtime_profile: Identifier | None
    result_schema: Identifier
    result_schema_version: int = Field(strict=True, ge=1)


class EngineHeader(ContractModel):
    engine_name: Identifier
    engine_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    runtime_profile: Identifier
    solver: Literal["OR_TOOLS_CP_SAT"]
    solver_status: SolverStatus
    result_generated_at: AwareDatetime
    transit_model_version: Literal["DATION_TRANSIT_V1"] = TRANSIT_MODEL_VERSION


class Decision(ContractModel):
    node_id: NodeID
    decision_type: Literal["TRANSPORT_PLAN", "DAY_SCHEDULING"]
    decision_label: str = Field(min_length=1, max_length=200)
    run_id: UUID
    status: Literal["COMPLETED"] = "COMPLETED"


class ResultBinding(ContractModel):
    run_id: UUID
    result_fingerprint: SHA256


class EntityRef(ContractModel):
    type: EntityType
    id: Identifier


class Feasibility(ContractModel):
    solution_found: StrictBool
    policy_feasible: StrictBool | None
    hard_constraints_satisfied: StrictBool | None
    full_demand_coverage: StrictBool | None

    @model_validator(mode="after")
    def no_false_solution(self):
        if not self.solution_found and (self.policy_feasible is True or self.full_demand_coverage is True):
            raise ValueError("No usable solution cannot claim policy feasibility/full coverage")
        return self

    def validate_solver_status(self, status):
        if (status in ('FEASIBLE','OPTIMAL') and not self.solution_found) or (status == 'INFEASIBLE' and self.solution_found):
            raise ValueError("Solver status contradicts usable-solution evidence")


class Allocation(ContractModel):
    order_id: Identifier
    allocation_fraction: Annotated[Positive, Field(le=1)]
    load: QuantityVector


class UtilizationVector(ContractModel):
    pallets: Ratio | None = None
    weight_kg: Ratio | None = None
    volume_m3: Ratio | None = None
    units: Ratio | None = None


class EstimatedCost(Money):
    cost_model: Literal["PER_TRIP", "PER_KM", "OWN_OPERATING_CYCLE"]


class Trip(ContractModel):
    trip_id: Identifier
    origin_id: Identifier
    destination_id: Identifier
    distance_km: Positive
    resource_id: Identifier
    resource_source: ResourceSource
    orders: tuple[Allocation, ...] = Field(min_length=1)
    total_load: QuantityVector
    guaranteed_capacity: QuantityVector
    utilization: UtilizationVector
    estimated_cost: EstimatedCost | None
    ready_date: DecisionDate
    delivery_due_date: DecisionDate
    reason_codes: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def references(self):
        scaled_integer(self.distance_km,DISTANCE_SCALE)
        if len({item.order_id for item in self.orders}) != len(self.orders):
            raise ValueError("Duplicate allocation in a Trip")
        if self.delivery_due_date < self.ready_date:
            raise ValueError("Trip dates must be ordered")
        for code in self.reason_codes:
            reason_definition(code)
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("Duplicate Trip reason reference")
        for dim in Dimension:
            load, cap = getattr(self.total_load, dim), getattr(self.guaranteed_capacity, dim)
            ratio = getattr(self.utilization, dim)
            if load is not None:
                if cap is None or cap <= 0 or load > cap:
                    raise ValueError("Feasibility uses guaranteed per-trip capacity only")
                validate_ratio(ratio, load, cap)
            elif ratio is not None:
                raise ValueError("Missing load cannot have a utilization value")
        return self


class DemandResolution(ContractModel):
    order_id: Identifier
    priority: Priority
    requested: QuantityVector
    assigned: QuantityVector
    coverage_ratio: Ratio | None
    trip_ids: tuple[Identifier, ...]
    status: Literal["COVERED", "PARTIALLY_COVERED", "UNASSIGNED"]
    reason_codes: tuple[Identifier, ...] = ()


class ResourceUsage(ContractModel):
    resource_id: Identifier
    resource_source: ResourceSource
    trip_ids: tuple[Identifier, ...]
    total_load: QuantityVector
    total_cost: Money | None
    weighted_utilization: UtilizationVector
    services_available: Count | None = None
    services_used: Count | None = None
    services_remaining: Count | None = None
    availability_source: Literal["CONFIRMED", "ASSUMED", "UNKNOWN"] | None = None
    units_available: Count | None = None
    trip_count: Count | None = None
    total_distance_km: NonNegative | None = None


class ScheduleTrip(ContractModel):
    trip_id: Identifier
    resource_id: Identifier
    resource_source: ResourceSource
    ready_date: DecisionDate
    delivery_due_date: DecisionDate
    dispatch_date: DecisionDate | None
    expected_arrival_date: DecisionDate | None
    outbound_days: int = Field(strict=True, ge=1)
    cycle_days: int | None = Field(default=None, strict=True, ge=1)
    resource_busy_until: DecisionDate | None = None
    available_again: DecisionDate | None = None
    schedule_margin_days: int | None = Field(default=None, strict=True)
    status: ScheduleStatus
    reason_codes: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def timing_shape(self):
        scheduled = self.status in ("ON_TIME", "AT_RISK", "LATE")
        if scheduled:
            if self.dispatch_date is None or self.expected_arrival_date is None or self.schedule_margin_days is None:
                raise ValueError("Scheduled trips require certified dates and margin")
            if self.dispatch_date < self.ready_date or self.expected_arrival_date < self.dispatch_date:
                raise ValueError("Invalid certified date order")
            margin = self.schedule_margin_days
            if not {"ON_TIME": margin > 0, "AT_RISK": margin == 0, "LATE": margin < 0}[self.status]:
                raise ValueError("Service category contradicts certified margin")
        elif any(v is not None for v in (self.dispatch_date, self.expected_arrival_date, self.schedule_margin_days, self.available_again, self.resource_busy_until)):
            raise ValueError("Pre-horizon/unscheduled cannot masquerade as a scheduled late trip")
        if self.resource_source == "EXTERNAL":
            if any(v is not None for v in (self.cycle_days, self.resource_busy_until, self.available_again)):
                raise ValueError("External trips have no own return occupancy")
        elif self.cycle_days is None or scheduled and (self.available_again is None or self.resource_busy_until != self.available_again):
            raise ValueError("OWN requires its certified cycle and exclusive availability end")
        for code in self.reason_codes:
            reason_definition(code)
        return self


class ServiceAnalysis(ContractModel):
    trip_id: Identifier
    dispatch_date: DecisionDate | None
    arrival_date: DecisionDate | None
    delivery_due_date: DecisionDate
    margin_days: int | None = Field(strict=True)
    status: ScheduleStatus


class Occupancy(ContractModel):
    trip_id: Identifier
    dispatch_date: DecisionDate
    busy_until: DecisionDate


class DispatchEvent(ContractModel):
    trip_id: Identifier
    dispatch_date: DecisionDate
    arrival_date: DecisionDate


class ResourceTimeline(ContractModel):
    resource_id: Identifier
    resource_source: ResourceSource
    units_available: Count | None
    occupancy: tuple[Occupancy, ...] = ()
    dispatch_events: tuple[DispatchEvent, ...] = ()

    @model_validator(mode="after")
    def no_external_occupancy(self):
        if self.resource_source == "EXTERNAL" and (self.occupancy or self.units_available is not None):
            raise ValueError("External resources are dispatch events, not return occupancy")
        return self


class TransportPlan(ContractModel):
    trips: tuple[Trip, ...]
    unassigned_demand: tuple[DemandResolution, ...]
    capacity_gap: QuantityVector | None


class DaySchedule(ContractModel):
    trips: tuple[ScheduleTrip, ...]


class EngineCoreResult(ContractModel):
    contract_version: Literal[1] = 1
    result_schema: ResultSchema
    result_schema_version: Literal[1] = 1
    decision: Decision
    context: FrozenCaseContext
    engine: EngineHeader
    input_context_hash: SHA256
    feasibility: Feasibility
    metrics: Metrics
    transport_plan: TransportPlan | None = None
    schedule: DaySchedule | None = None
    source_transport_plan: ResultBinding | None = None

    @property
    def runtime_identity(self):
        return RuntimeIdentity(engine_name=self.engine.engine_name, engine_version=self.engine.engine_version,
            runtime_profile=self.engine.runtime_profile, result_schema=self.result_schema,
            result_schema_version=self.result_schema_version)

    @model_validator(mode="after")
    def specialized_body(self):
        from .registry import resolve_runtime
        from .canonical import input_context_hash
        runtime = resolve_runtime(self.runtime_identity)
        if self.decision.node_id != runtime.node_id:
            raise ValueError("Decision node conflicts with persisted runtime identity")
        d1 = self.result_schema == "transport_plan_v1"
        if d1:
            valid = self.transport_plan is not None and self.schedule is None and self.source_transport_plan is None and isinstance(self.metrics, TransportPlanMetrics) and self.decision.decision_type == "TRANSPORT_PLAN"
        else:
            valid = self.schedule is not None and self.transport_plan is None and self.source_transport_plan is not None and isinstance(self.metrics, DaySchedulingMetrics) and self.decision.decision_type == "DAY_SCHEDULING"
        if not valid:
            raise ValueError("Wrong specialized result body/metrics/upstream")
        if self.source_transport_plan and self.source_transport_plan.run_id == self.decision.run_id:
            raise ValueError("A Run cannot be its own upstream")
        if self.input_context_hash != input_context_hash(self.context, self.runtime_identity, self.source_transport_plan):
            raise ValueError("Input context hash disagrees with the pinned snapshot")
        trips = self.transport_plan.trips if d1 else self.schedule.trips
        self.feasibility.validate_solver_status(self.engine.solver_status)
        if len({t.trip_id for t in trips}) != len(trips):
            raise ValueError("Duplicate Trip IDs")
        for money in _money_values(self.metrics) + _money_values(trips):
            money.validate_policy(self.context.currency_policy)
        return self


class ResultArtifactReference(ContractModel):
    artifact_id: UUID
    workspace_id: UUID
    run_id: UUID
    kind: ArtifactKind
    part_key: Identifier
    artifact_schema: DatasetSchema
    schema_version: Literal[1] = 1
    content_sha256: SHA256
    size_bytes: Count
    media_type: Literal["application/json", "application/x-ndjson"]
    core_fingerprint: SHA256
    assembler_version: Identifier


class ArtifactManifest(ContractModel):
    version: Literal[1] = 1
    artifacts: tuple[ResultArtifactReference, ...]

    @model_validator(mode="after")
    def distinct_parts(self):
        if len({a.artifact_id for a in self.artifacts}) != len(self.artifacts) or len({(a.kind, a.part_key) for a in self.artifacts}) != len(self.artifacts):
            raise ValueError("Duplicate artifact identity or role/part")
        return self


class InlineDataset(ContractModel, Generic[T]):
    mode: Literal["INLINE"] = "INLINE"
    delivery_version: Literal[1] = 1
    dataset_id: Identifier
    row_schema: DatasetSchema
    schema_version: Literal[1] = 1
    row_count: Count
    rows: tuple[T, ...]

    @model_validator(mode="after")
    def explicit_empty(self):
        if self.row_count != len(self.rows):
            raise ValueError("Inline row_count must equal the actual dataset")
        expected = _row_schema_type(self.row_schema)
        if any(not isinstance(row,expected) for row in self.rows):
            raise ValueError("Inline row schema conflicts with typed rows")
        return self


class ReferenceDataset(ContractModel):
    mode: Literal["REFERENCE"] = "REFERENCE"
    delivery_version: Literal[1] = 1
    dataset_id: Identifier
    row_schema: DatasetSchema
    schema_version: Literal[1] = 1
    row_count: Count
    artifacts: tuple[ResultArtifactReference, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def same_logical_schema(self):
        if any((ref.artifact_schema,ref.schema_version) != (self.row_schema,self.schema_version) for ref in self.artifacts):
            raise ValueError("Reference descriptor and artifact schemas disagree")
        return self


type Delivery[Row] = Annotated[InlineDataset[Row] | ReferenceDataset, Field(discriminator="mode")]


class ArtifactReadError(ContractModel):
    status: Literal["UNAVAILABLE", "CORRUPT"]
    artifact_id: UUID
    expected_sha256: SHA256
    code: Literal["ARTIFACT_MISSING", "ARTIFACT_INTEGRITY_ERROR"]

    @model_validator(mode="after")
    def explicit_error(self):
        if (self.status == "UNAVAILABLE") != (self.code == "ARTIFACT_MISSING"):
            raise ValueError("Missing and corrupt artifacts are distinct errors")
        return self


class SolverCertificate(ContractModel):
    kind: Literal["GLOBAL_OPTIMUM", "INFEASIBILITY", "FEASIBILITY"]
    evidence_ref: Identifier


class SolverEvidence(ContractModel):
    status: SolverStatus
    objective_value: DecimalValue | None
    best_bound: DecimalValue | None
    certificate: SolverCertificate | None

    @model_validator(mode="after")
    def honest_status(self):
        if self.status == "OPTIMAL" and (self.certificate is None or self.certificate.kind != "GLOBAL_OPTIMUM" or self.objective_value is None or self.best_bound != self.objective_value):
            raise ValueError("OPTIMAL requires an explicit matching optimum certificate/bound")
        if self.status == "INFEASIBLE" and (self.certificate is None or self.certificate.kind != "INFEASIBILITY"):
            raise ValueError("INFEASIBLE requires a certificate, not UNKNOWN without a solution")
        if self.status not in ("OPTIMAL", "INFEASIBLE") and self.certificate and self.certificate.kind != "FEASIBILITY":
            raise ValueError("FEASIBLE/UNKNOWN cannot claim a global proof")
        return self


class ConstraintEvidence(ContractModel):
    evidence_id: Identifier
    code: Identifier
    status: Literal["SATISFIED", "VIOLATED", "UNKNOWN"]
    hard: StrictBool
    facts: dict[str, FactValue]


class CandidateSummary(ContractModel):
    resource_id: Identifier
    status: Literal["SELECTED", "FEASIBLE", "INFEASIBLE", "UNKNOWN"]
    estimated_cost: NonNegative | None
    reason_refs: tuple[Identifier, ...]


class EntityEvidence(ContractModel):
    entity_type: EntityType
    entity_id: Identifier
    facts: dict[str, FactValue]
    reason_refs: tuple[Identifier, ...]
    candidate_summary: tuple[CandidateSummary, ...] = ()


class PolicyEvidence(ContractModel):
    case_goal: str
    effective_node_policy: str
    override: StrictBool
    override_reason: str | None
    evidence_id: Identifier


class EngineEvidence(ContractModel):
    contract_version: Literal[1] = 1
    result_schema: ResultSchema
    workspace_id: UUID
    run_id: UUID
    input_context_hash: SHA256
    core_result_fingerprint: SHA256
    policy: PolicyEvidence
    constraints: tuple[ConstraintEvidence, ...]
    solver: SolverEvidence
    reasons: tuple[ReasonEmission, ...]
    entities: tuple[EntityEvidence, ...]

    @model_validator(mode="after")
    def reason_links(self):
        reasons = {r.emission_id: r for r in self.reasons}
        if len(reasons) != len(self.reasons):
            raise ValueError("Duplicate emitted reason ID")
        producer = "transport_plan" if self.result_schema == "transport_plan_v1" else "day_scheduling"
        for reason in self.reasons:
            if reason.producer != producer:
                raise ValueError("Wrong reason producer for result schema")
            if self.solver.status == "UNKNOWN" and reason.entity_type == 'CASE' and reason.claim_strength == "CERTIFIED_INFEASIBILITY":
                raise ValueError("UNKNOWN is not evidence of inevitable infeasibility")
        for entity in self.entities:
            for ref in (*entity.reason_refs, *(ref for c in entity.candidate_summary for ref in c.reason_refs)):
                if ref not in reasons:
                    raise ValueError("Entity references a reason without facts")
        return self


class EngineOutput(ContractModel):
    core: EngineCoreResult
    evidence: EngineEvidence

    @model_validator(mode="after")
    def bound(self):
        from .canonical import core_result_fingerprint
        c, e = self.core, self.evidence
        if (e.result_schema, e.run_id, e.workspace_id, e.input_context_hash, e.core_result_fingerprint, e.solver.status) != (c.result_schema, c.decision.run_id, c.context.workspace_id, c.input_context_hash, core_result_fingerprint(c), c.engine.solver_status):
            raise ValueError("Evidence is not bound to this exact Core/Run")
        trips = c.transport_plan.trips if c.transport_plan else c.schedule.trips
        for trip in trips:
            for code in trip.reason_codes:
                if not any(r.code == code and r.entity_type == "TRIP" and r.entity_id == trip.trip_id for r in e.reasons):
                    raise ValueError("A Trip reason reference requires certified facts in EngineEvidence")
        if c.transport_plan:
            for order in c.transport_plan.unassigned_demand:
                for code in order.reason_codes:
                    if not any(r.code == code and r.entity_type == 'ORDER' and r.entity_id == order.order_id for r in e.reasons):
                        raise ValueError("A residual reason requires Order facts")
        if (e.policy.case_goal, e.policy.effective_node_policy, e.policy.override, e.policy.override_reason) != (c.context.case_policy.primary_goal,c.context.node_policy.primary_goal,c.context.node_policy.override,c.context.node_policy.override_reason):
            raise ValueError("Policy evidence contradicts the admitted snapshot")
        for reason in e.reasons:
            if 'currency' in reason.facts and reason.facts['currency'] != c.context.currency_policy.currency:
                raise ValueError("Reason costs cannot use another Case currency")
        for entity in e.entities:
            for candidate in entity.candidate_summary:
                if candidate.estimated_cost is not None:
                    scaled_integer(candidate.estimated_cost,c.context.currency_policy.minor_units)
        if c.feasibility.hard_constraints_satisfied is True and any(v.hard and v.status != "SATISFIED" for v in e.constraints):
            raise ValueError("Constraint evidence contradicts feasibility")
        return self


class ExceptionDescriptor(ContractModel):
    exception_id: Identifier
    category: Literal["BUSINESS", "FEASIBILITY", "POLICY", "DATA", "ASSUMPTION"]
    severity: Literal["INFO", "ATTENTION", "BLOCKING"]
    code: Identifier
    entity_type: EntityType
    entity_ids: tuple[Identifier, ...] = Field(min_length=1)
    message_key: Identifier
    facts: dict[str, FactValue]
    reason_ref: Identifier


class AssumptionDescriptor(ContractModel):
    assumption_id: Identifier
    code: Identifier
    entity_type: EntityType
    entity_id: Identifier
    value: FactValue
    unit: Identifier
    source: Literal["USER_CONFIRMED", "MODEL_DEFAULT", "DATION_DEFAULT", "DERIVED"]
    reason_ref: Identifier


class ReviewItem(ContractModel):
    priority: int = Field(strict=True, ge=1)
    type: Literal["ASSUMPTION", "BUSINESS_GAP", "SERVICE_RISK", "HARD_CONSTRAINT", "POLICY", "DATA"]
    code: Identifier
    entity: EntityRef | None
    evidence_refs: tuple[Identifier, ...] = Field(min_length=1)


class ApprovalReview(ContractModel):
    schema_version: Literal["approval_review_v1"] = "approval_review_v1"
    decision_ready_for_review: StrictBool
    hard_constraints_satisfied: StrictBool | None
    coverage_status: Literal["FULL", "PARTIAL", "NONE", "UNKNOWN"]
    exception_count: Count
    assumption_count: Count
    review_items: tuple[ReviewItem, ...]
    scheduled_ratio: Ratio | None = None
    expected_delivery_compliance: Ratio | None = None
    at_risk_count: Count | None = None
    late_count: Count | None = None
    pre_horizon_count: Count | None = None


class ApprovalOverlay(ContractModel):
    run_id: UUID
    result_fingerprint: SHA256
    approval_allowed: StrictBool
    freshness: Literal["CURRENT", "STALE", "SUPERSEDED", "UNKNOWN"]
    approval_blockers: tuple[Identifier, ...]

    @model_validator(mode="after")
    def current_authority(self):
        if self.approval_allowed and (self.freshness != "CURRENT" or self.approval_blockers):
            raise ValueError("Current backend authority cannot allow a blocked/stale approval")
        return self


class ExecutiveSummary(ContractModel):
    template_id: Identifier
    template_version: Literal[1] = 1
    facts: dict[str, FactValue]


class SankeyNode(ContractModel):
    id: Identifier
    type: Literal["DESTINATION", "TRIP", "RESOURCE"]
    label: str


class SankeyLink(ContractModel):
    source: Identifier
    target: Identifier
    value: NonNegative
    order_ids: tuple[Identifier, ...] = ()


class SankeyProjection(ContractModel):
    type: Literal["SANKEY"] = "SANKEY"
    value_dimension: Dimension
    nodes: tuple[SankeyNode, ...]
    links: tuple[SankeyLink, ...]


class GanttRow(ContractModel):
    resource_id: Identifier
    label: str
    source: ResourceSource


class GanttItem(ContractModel):
    trip_id: Identifier
    resource_id: Identifier
    dispatch_date: DecisionDate
    arrival_date: DecisionDate
    occupancy_start: DecisionDate | None
    occupancy_end: DecisionDate | None
    status: ScheduleStatus


class GanttProjection(ContractModel):
    type: Literal["DAY_GANTT"] = "DAY_GANTT"
    planning_start: DecisionDate
    planning_end: DecisionDate
    rows: tuple[GanttRow, ...]
    items: tuple[GanttItem, ...]


class PrimaryVisual(ContractModel):
    type: Literal["SANKEY", "DAY_GANTT"]
    projection: SankeyProjection | GanttProjection | ReferenceDataset

    @model_validator(mode="after")
    def correct_projection(self):
        if not isinstance(self.projection, ReferenceDataset) and self.type != self.projection.type:
            raise ValueError("Visual type conflicts with its certified projection")
        return self


DetailRow = DemandResolution | ResourceUsage | ResourceTimeline | ServiceAnalysis | EntityEvidence | Trip | ScheduleTrip


class DetailColumn(ContractModel):
    key: Identifier
    unit: str | None
    format: Literal["ID", "TEXT", "DATE", "DECIMAL", "MONEY", "RATIO", "COUNT", "STATUS"]


class DetailDatasetDescriptor(ContractModel):
    dataset_id: Identifier
    dataset_type: Literal["PLAN", "DEMAND", "RESOURCES", "SCHEDULE", "TRIPS", "SERVICE", "EVIDENCE"]
    columns: tuple[DetailColumn, ...]
    primary_key: tuple[Identifier, ...] = Field(min_length=1)
    stable_order: tuple[Identifier, ...] = Field(min_length=1)
    data: Delivery[DetailRow]

    @model_validator(mode="after")
    def dataset_identity(self):
        if self.dataset_id != self.data.dataset_id:
            raise ValueError("Detail descriptor/delivery dataset IDs disagree")
        if len({col.key for col in self.columns}) != len(self.columns):
            raise ValueError("Duplicate detail column")
        return self


class AlternativeMetrics(ContractModel):
    total_cost: NonNegative | None
    trip_count: Count
    coverage_ratio: Ratio | None
    own_trip_ratio: Ratio | None


class AlternativeDifference(ContractModel):
    cost_delta: DecimalValue | None
    trip_delta: int = Field(strict=True)
    own_share_delta: Annotated[DecimalValue, Field(ge=-1, le=1, decimal_places=4)] | None


class AlternativeDescriptor(ContractModel):
    alternative_id: Identifier
    policy: str
    metrics: AlternativeMetrics
    difference_vs_recommended: AlternativeDifference
    material_differences: tuple[Identifier, ...]
    plan: Delivery[Trip | ScheduleTrip]
    evidence: Delivery[EntityEvidence]


class ExportDescriptor(ContractModel):
    available: StrictBool
    type: Literal["TRANSPORT_PLAN", "DAY_SCHEDULE", "DECISION_RESULT_PACKAGE"]
    granularity: Literal["TRIP_ORDER", "TRIP", "PACKAGE"]
    cost_scope: Literal["TRIP_ONCE"] | None = None
    rows: Delivery[dict[str, FactValue]] | None = None

    @model_validator(mode="after")
    def recoverable(self):
        if self.available and self.granularity != "PACKAGE" and self.rows is None:
            raise ValueError("Available CSV must reference its complete certified rows")
        if self.granularity == "PACKAGE" and self.rows is not None:
            raise ValueError("JSON exports this package, not a self-referential future artifact")
        if self.available and self.type == "TRANSPORT_PLAN" and self.cost_scope != "TRIP_ONCE":
            raise ValueError("D1 cost is recognized once per Trip, never repeated per allocation")
        return self


class Exports(ContractModel):
    csv: ExportDescriptor
    json_export: ExportDescriptor = Field(alias="json")


class FingerprintSet(ContractModel):
    canonical_version: Literal["DATION_CANONICAL_V1"] = "DATION_CANONICAL_V1"
    input_context_hash: SHA256
    core_result_fingerprint: SHA256
    result_fingerprint: SHA256
    model_version: int = Field(strict=True, ge=1)
    data_pack_version: int = Field(strict=True, ge=1)
    case_policy_hash: SHA256
    node_policy_hash: SHA256
    contract_hash: SHA256
    engine_version: str
    transit_model_version: Literal["DATION_TRANSIT_V1"] = TRANSIT_MODEL_VERSION
    upstream_result_fingerprint: SHA256 | None


class PublishedTransportPlan(ContractModel):
    trips: Delivery[Trip]
    unassigned_demand: Delivery[DemandResolution]
    capacity_gap: QuantityVector | None


class PublishedSchedule(ContractModel):
    trips: Delivery[ScheduleTrip]


class EvidenceSummary(ContractModel):
    solver: SolverEvidence
    policy: PolicyEvidence
    constraints: tuple[ConstraintEvidence, ...]
    reason_emissions: Delivery[ReasonEmission]
    parts: tuple[ReferenceDataset, ...] = ()


class AIContextReference(ContractModel):
    schema_version: Literal["decision_context_v1"] = "decision_context_v1"
    base_context: ReferenceDataset | None


class DecisionResultPackageV1(ContractModel):
    result_schema: ResultSchema
    result_schema_version: Literal[1] = 1
    package_version: Literal[1] = 1
    assembler_version: Identifier
    decision: Decision
    context: FrozenCaseContext
    engine: EngineHeader
    feasibility: Feasibility
    transport_plan: PublishedTransportPlan | None = None
    schedule: PublishedSchedule | None = None
    source_transport_plan: ResultBinding | None = None
    summary: ExecutiveSummary
    metrics: Metrics
    primary_visual: PrimaryVisual
    details: tuple[DetailDatasetDescriptor, ...]
    alternatives: tuple[AlternativeDescriptor, ...] = Field(max_length=3)
    alternatives_state: Literal["NOT_COMPUTED", "COMPUTED_NONE", "COMPUTED"]
    exceptions: tuple[ExceptionDescriptor, ...]
    assumptions: tuple[AssumptionDescriptor, ...]
    evidence: EvidenceSummary
    approval_review: ApprovalReview
    exports: Exports
    ai_context: AIContextReference
    artifact_manifest: ArtifactManifest
    fingerprints: FingerprintSet

    @model_validator(mode="after")
    def published_contract(self):
        from .canonical import input_context_hash, policy_hash, result_fingerprint, canonical_bytes
        from .registry import resolve_runtime
        identity = RuntimeIdentity(engine_name=self.engine.engine_name, engine_version=self.engine.engine_version,
            runtime_profile=self.engine.runtime_profile, result_schema=self.result_schema, result_schema_version=1)
        spec = resolve_runtime(identity)
        d1 = self.result_schema == "transport_plan_v1"
        if self.decision.node_id != spec.node_id or self.decision.decision_type != ("TRANSPORT_PLAN" if d1 else "DAY_SCHEDULING"):
            raise ValueError("Package node/type conflicts with result identity")
        if (self.transport_plan is not None) != d1 or (self.schedule is not None) == d1 or (self.source_transport_plan is not None) == d1:
            raise ValueError("Missing/wrong specialized root/upstream")
        if not isinstance(self.metrics, TransportPlanMetrics if d1 else DaySchedulingMetrics) or self.primary_visual.type != ("SANKEY" if d1 else "DAY_GANTT"):
            raise ValueError("Wrong metrics/visual contract for schema")
        if self.source_transport_plan and self.source_transport_plan.run_id == self.decision.run_id:
            raise ValueError("Cyclic upstream")
        f = self.fingerprints
        if (f.input_context_hash, f.case_policy_hash, f.node_policy_hash, f.contract_hash, f.model_version, f.data_pack_version, f.engine_version, f.upstream_result_fingerprint) != (
            input_context_hash(self.context, identity, self.source_transport_plan), policy_hash(self.context.case_policy),
            policy_hash(self.context.node_policy), self.context.contract_hash, self.context.logistics_model_version,
            self.context.data_pack_version, self.engine.engine_version,
            self.source_transport_plan.result_fingerprint if self.source_transport_plan else None):
            raise ValueError("Fingerprint provenance conflicts with package snapshot")
        if self.evidence.solver.status != self.engine.solver_status:
            raise ValueError("Solver evidence conflicts with engine status")
        self.feasibility.validate_solver_status(self.engine.solver_status)
        if (self.evidence.policy.case_goal,self.evidence.policy.effective_node_policy,self.evidence.policy.override,self.evidence.policy.override_reason) != (self.context.case_policy.primary_goal,self.context.node_policy.primary_goal,self.context.node_policy.override,self.context.node_policy.override_reason):
            raise ValueError("Package policy evidence conflicts with the frozen Case")
        if self.approval_review.hard_constraints_satisfied != self.feasibility.hard_constraints_satisfied:
            raise ValueError("Review cannot describe different hard-constraint evidence")
        if self.feasibility.hard_constraints_satisfied is True and any(v.hard and v.status != 'SATISFIED' for v in self.evidence.constraints):
            raise ValueError("Hard-constraint evidence contradicts feasibility")
        if self.feasibility.full_demand_coverage is not None and (self.approval_review.coverage_status == 'FULL') != self.feasibility.full_demand_coverage:
            raise ValueError("Review coverage conflicts with certified coverage")
        if not d1 and (self.approval_review.scheduled_ratio,self.approval_review.expected_delivery_compliance,self.approval_review.at_risk_count,self.approval_review.late_count,self.approval_review.pre_horizon_count) != (
            self.metrics.scheduled_trips.ratio,self.metrics.on_time_ratio,self.metrics.service_level.at_risk,self.metrics.service_level.late,self.metrics.service_level.pre_horizon):
            raise ValueError("D2 review must copy the exact certified service metrics")
        if bool(self.alternatives) != (self.alternatives_state == "COMPUTED") or len({a.alternative_id for a in self.alternatives}) != len(self.alternatives):
            raise ValueError("No alternatives computed is not proof none exist; state required")
        if self.approval_review.exception_count != len(self.exceptions) or self.approval_review.assumption_count != len(self.assumptions):
            raise ValueError("Review counts must describe this exact package")
        if self.approval_review.decision_ready_for_review and (not self.feasibility.solution_found or self.feasibility.hard_constraints_satisfied is not True or self.feasibility.policy_feasible is not True):
            raise ValueError("Review-ready cannot fabricate a usable policy-feasible solution")
        for money in _money_values(self):
            money.validate_policy(self.context.currency_policy)
        for alternative in self.alternatives:
            for value in (alternative.metrics.total_cost, alternative.difference_vs_recommended.cost_delta):
                if value is not None:
                    scaled_integer(value, self.context.currency_policy.minor_units)
        manifest = {a.artifact_id: a for a in self.artifact_manifest.artifacts}
        for ref in _artifact_refs(self):
            if (ref.workspace_id, ref.run_id, ref.core_fingerprint) != (self.context.workspace_id, self.decision.run_id, f.core_result_fingerprint) or manifest.get(ref.artifact_id) != ref:
                raise ValueError("Artifact is missing or belongs to another Run/workspace/core")
        if isinstance(self.evidence.reason_emissions, InlineDataset):
            reasons = {r.emission_id: r for r in self.evidence.reason_emissions.rows}
            if len(reasons) != len(self.evidence.reason_emissions.rows):
                raise ValueError("Duplicate reason emission")
            if any(r.producer != self.engine.engine_name for r in reasons.values()):
                raise ValueError("Reason producer conflicts with this package")
            if any('currency' in r.facts and r.facts['currency'] != self.context.currency_policy.currency for r in reasons.values()):
                raise ValueError("Reason costs cannot use another Case currency")
            trip_data = self.transport_plan.trips if d1 else self.schedule.trips
            if isinstance(trip_data, InlineDataset):
                for trip in trip_data.rows:
                    for code in trip.reason_codes:
                        if not any(r.code == code and r.entity_type == 'TRIP' and r.entity_id == trip.trip_id for r in reasons.values()):
                            raise ValueError("Trip reason has no matching facts")
            for item in (*self.exceptions, *self.assumptions):
                if item.reason_ref not in reasons or reasons[item.reason_ref].code != item.code:
                    raise ValueError("Exception/assumption has no matching certified facts")
        if f.result_fingerprint != result_fingerprint(self):
            raise ValueError("Package/manifest content does not match result fingerprint")
        if len(canonical_bytes(self)) > PACKAGE_MAX_BYTES:
            raise ValueError("Package exceeds 512KiB; use typed references/chunks")
        if not isinstance(self.primary_visual.projection, ReferenceDataset) and len(canonical_bytes(self.primary_visual.projection)) > VISUAL_INLINE_MAX_BYTES:
            raise ValueError("Inline visual exceeds its budget; use a reference")
        return self


class InputSummary(ContractModel):
    orders: Count
    demand: QuantityVector
    priority_distribution: dict[Priority, Count]
    own_resources: Count
    external_resources: Count


class ModelContext(ContractModel):
    id: UUID
    version_id: UUID
    version: int = Field(strict=True, ge=1)
    model_hash: SHA256


class DecisionDefinitionContext(ContractModel):
    node_id: NodeID
    version: Identifier
    decision_type: Literal["TRANSPORT_PLAN", "DAY_SCHEDULING"]


class AlternativeSummary(ContractModel):
    alternative_id: Identifier
    metrics: AlternativeMetrics
    evidence_refs: tuple[ResultArtifactReference, ...]


class DecisionContextV1(ContractModel):
    schema_version: Literal["decision_context_v1"] = "decision_context_v1"
    context_version: Literal[1] = 1
    provenance: ResultBinding
    mode: ContextMode
    case: FrozenCaseContext
    logistics_model: ModelContext
    case_policy: CasePolicy
    decision_definition: DecisionDefinitionContext
    node_policy: NodePolicy
    input_summary: InputSummary
    result_summary: ExecutiveSummary
    metrics: Metrics
    exceptions: tuple[ExceptionDescriptor, ...]
    assumptions: tuple[AssumptionDescriptor, ...]
    evidence_summary: EvidenceSummary
    alternatives_summary: tuple[AlternativeSummary, ...]
    approval_review: ApprovalReview
    selected_entity: EntityRef | None
    selected_alternative_ids: tuple[Identifier, ...] = ()
    selected_evidence_refs: tuple[ResultArtifactReference, ...] = ()
    context_hash: SHA256

    @model_validator(mode="after")
    def exact_context(self):
        from .canonical import decision_context_hash, canonical_bytes
        if self.case_policy != self.case.case_policy or self.node_policy != self.case.node_policy:
            raise ValueError("IA policies must be the exact admitted policies")
        if (self.logistics_model.id, self.logistics_model.version_id, self.logistics_model.version, self.logistics_model.model_hash) != (self.case.logistics_model_id, self.case.logistics_model_version_id, self.case.logistics_model_version, self.case.model_hash):
            raise ValueError("IA model is not from this frozen Case")
        if self.mode == "COMPARE" and not self.selected_alternative_ids:
            raise ValueError("COMPARE requires certified alternative IDs")
        d1 = self.decision_definition.node_id == 'logistics_assignment'
        if self.decision_definition.decision_type != ('TRANSPORT_PLAN' if d1 else 'DAY_SCHEDULING') or not isinstance(self.metrics,TransportPlanMetrics if d1 else DaySchedulingMetrics):
            raise ValueError("IA decision/metric schema mismatch")
        if not set(self.selected_alternative_ids) <= {a.alternative_id for a in self.alternatives_summary}:
            raise ValueError("Cannot compare an invented alternative")
        for ref in _artifact_refs(self):
            if ref.workspace_id != self.case.workspace_id or ref.run_id != self.provenance.run_id:
                raise ValueError("IA evidence from another workspace/Run")
        if self.selected_entity and len(canonical_bytes(self.selected_evidence_refs)) > SELECTED_ENTITY_MAX_BYTES:
            raise ValueError("Selected evidence descriptors exceed context budget")
        if self.context_hash != decision_context_hash(self):
            raise ValueError("Context hash must include mode, selection and evidence hashes")
        return self


class DecisionIntentV2(ContractModel):
    schema_version: Literal["decision_intent_v2"] = "decision_intent_v2"
    provenance: ResultBinding
    context_version: Literal[1] = 1
    context_hash: SHA256
    mode: ContextMode
    question: str = Field(min_length=1, max_length=4000)
    selected_entity: EntityRef | None
    selected_alternative_ids: tuple[Identifier, ...] = ()
    evidence_hashes: tuple[SHA256, ...]

    @model_validator(mode="after")
    def meaningful_question(self):
        if not self.question.strip():
            raise ValueError("Question cannot be whitespace only")
        return self


class UltimateRunRequest(ContractModel):
    request_schema: Literal["ultimate_run_request_v1"] = "ultimate_run_request_v1"
    workflow_version: Literal[2] = 2
    case_id: UUID
    node_id: NodeID
    expected_context_hash: SHA256
    model_version_id: UUID
    data_pack_version_id: UUID
    node_policy: NodePolicy
    source_transport_plan: ResultBinding | None = None

    @model_validator(mode="after")
    def explicit_source(self):
        if (self.node_id == "logistics_scheduling") != (self.source_transport_plan is not None):
            raise ValueError("D2 requires its exact approved D1 binding; D1 has no upstream")
        return self


class ResultResponse(ContractModel):
    package: DecisionResultPackageV1
    provenance: ResultBinding
    approval_overlay: ApprovalOverlay

    @model_validator(mode="after")
    def same_publication(self):
        expected = (self.package.decision.run_id, self.package.fingerprints.result_fingerprint)
        if (self.provenance.run_id, self.provenance.result_fingerprint) != expected or (self.approval_overlay.run_id, self.approval_overlay.result_fingerprint) != expected:
            raise ValueError("Response provenance/overlay belongs to another publication")
        return self


class DecisionContextResponse(ContractModel):
    context: DecisionContextV1
    approval_overlay: ApprovalOverlay

    @model_validator(mode="after")
    def exact_run_overlay(self):
        if (self.approval_overlay.run_id, self.approval_overlay.result_fingerprint) != (self.context.provenance.run_id, self.context.provenance.result_fingerprint):
            raise ValueError("IA current approval state must describe this exact publication")
        return self


class ApprovalReviewResponse(ContractModel):
    provenance: ResultBinding
    approval_review: ApprovalReview
    approval_overlay: ApprovalOverlay

    @model_validator(mode="after")
    def separate_authority(self):
        if (self.provenance.run_id, self.provenance.result_fingerprint) != (self.approval_overlay.run_id, self.approval_overlay.result_fingerprint):
            raise ValueError("Review and current approval authority must have the same provenance")
        return self


class DetailPage(ContractModel, Generic[T]):
    provenance: ResultBinding
    dataset_id: Identifier
    offset: Count
    limit: int = Field(strict=True, ge=1, le=PAGE_MAX_ROWS)
    total: Count
    rows: tuple[T, ...]

    @model_validator(mode="after")
    def page_bounds(self):
        if len(self.rows) > self.limit or self.offset + len(self.rows) > self.total:
            raise ValueError("Invalid bounded detail page")
        return self


class ResultError(ContractModel):
    code: Literal["UNSUPPORTED_RESULT_SCHEMA", "UNSUPPORTED_RUNTIME_IDENTITY", "RUNTIME_UNAVAILABLE",
                  "RESULT_FINGERPRINT_MISMATCH", "ARTIFACT_MISSING", "ARTIFACT_INTEGRITY_ERROR", "CONTEXT_MISMATCH"]
    run_id: UUID
    expected_result_fingerprint: SHA256 | None
    retryable: StrictBool


def _money_values(value):
    if isinstance(value, Money):
        return [value]
    if isinstance(value, ContractModel):
        return [m for key in type(value).model_fields for m in _money_values(getattr(value, key))]
    if isinstance(value, (list, tuple)):
        return [m for item in value for m in _money_values(item)]
    if isinstance(value, dict):
        return [m for item in value.values() for m in _money_values(item)]
    return []


def _artifact_refs(value):
    if isinstance(value, ResultArtifactReference):
        yield value
    elif isinstance(value, ContractModel):
        for key in type(value).model_fields:
            yield from _artifact_refs(getattr(value, key))
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _artifact_refs(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _artifact_refs(item)


def validate_schedule_source(source: EngineCoreResult, child: EngineCoreResult, source_result_fingerprint: SHA256):
    """Pure contract comparison, not scheduling or approval/freshness authority."""
    if source.result_schema != "transport_plan_v1" or child.result_schema != "day_scheduling_v1":
        raise ValueError("D2 consumes a transport_plan_v1 source only")
    if source.context.workspace_id != child.context.workspace_id or source.context.case_id != child.context.case_id:
        raise ValueError("Cross-Case/tenant upstream")
    # The publication binding is checked by its caller; core identity verifies
    # allocations/routes/loads remain in the immutable source, never copied/edited.
    if source.decision.run_id != child.source_transport_plan.run_id or child.source_transport_plan.result_fingerprint != source_result_fingerprint:
        raise ValueError("Wrong upstream Run")
    previous = {t.trip_id: (t.resource_id, t.resource_source) for t in source.transport_plan.trips}
    current = {t.trip_id: (t.resource_id, t.resource_source) for t in child.schedule.trips}
    if previous != current:
        raise ValueError("D2 must preserve all Trip IDs and resource assignments")
    return True


class ResultContractBundle(EngineOutput):
    """Validates a supplied bundle; never assembles, publishes or reads artifacts."""
    package: DecisionResultPackageV1

    @model_validator(mode='after')
    def same_certified_result(self):
        validate_result_binding(self.core,self.evidence,self.package)
        return self


def validate_result_binding(core: EngineCoreResult, evidence: EngineEvidence, package: DecisionResultPackageV1):
    """Cross-bind already schema-validated Core/Evidence/Package snapshots.

    ResultContractBundle still validates all its fields and EngineOutput guards
    before calling this predicate. D1's independent bundle validator can reuse
    its checked EngineOutput and Package instead of reconstructing that graph.
    """
    from .canonical import core_result_fingerprint
    p,c,e=package,core,evidence
    if (p.result_schema,p.decision,p.context,p.engine,p.feasibility,p.metrics,p.source_transport_plan,p.fingerprints.core_result_fingerprint) != (
        c.result_schema,c.decision,c.context,c.engine,c.feasibility,c.metrics,c.source_transport_plan,core_result_fingerprint(c)):
        raise ValueError("Package diverges from its supplied certified Core")
    trip_data=p.transport_plan.trips if p.transport_plan else p.schedule.trips
    core_trips=c.transport_plan.trips if c.transport_plan else c.schedule.trips
    if isinstance(trip_data,InlineDataset) and trip_data.rows != core_trips:
        raise ValueError("Package changed canonical trips/timing")
    if isinstance(p.evidence.reason_emissions,InlineDataset) and p.evidence.reason_emissions.rows != e.reasons:
        raise ValueError("Package replaced certified reason facts")


def _row_schema_type(schema):
    return {'transport_trip_v1':Trip,'demand_resolution_v1':DemandResolution,'resource_usage_v1':ResourceUsage,
        'day_schedule_trip_v1':ScheduleTrip,'resource_timeline_v1':ResourceTimeline,'service_analysis_v1':ServiceAnalysis,
        'entity_evidence_v1':EntityEvidence,'reason_emission_v1':ReasonEmission,'export_rows_v1':dict,
        'decision_context_v1':DecisionContextV1,'engine_core_v1':EngineCoreResult,'engine_evidence_v1':EngineEvidence,
        'sankey_projection_v1':SankeyProjection,'day_gantt_projection_v1':GanttProjection}[schema]
