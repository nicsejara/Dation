"""Snapshots and policies, not Case persistence, readiness or optimizers."""
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictBool, model_validator

from .base import (ContractModel, Count, DecisionDate, Dimension, Identifier, NonNegative,
                   Positive, Priority, Ratio, ResourceSource, SHA256)
from .units import CurrencyPolicy, QuantityVector, scaled_integer, DISTANCE_SCALE

Goal = Literal["MINIMIZE_COST", "MAXIMIZE_SERVICE", "MAXIMIZE_OWN_CAPACITY",
               "MINIMIZE_TRIPS", "BALANCED", "CUSTOM"]


class Horizon(ContractModel):
    planning_start: DecisionDate
    planning_end: DecisionDate

    @model_validator(mode="after")
    def ordered(self):
        if self.planning_end < self.planning_start:
            raise ValueError("Horizon departure bounds are inclusive and ordered")
        return self


class Guardrail(ContractModel):
    kind: Literal["MINIMUM_DEMAND_COVERAGE", "CRITICAL_DEMAND_COVERAGE",
                  "MAXIMUM_EXTERNAL_SHARE", "MINIMUM_OWN_SHARE"]
    limit: Ratio
    hard: Literal[True] = True


class Preference(ContractModel):
    kind: Literal["COST", "TRIPS", "SERVICE", "OWN_CAPACITY"]
    weight: Ratio


class CasePolicy(ContractModel):
    version: Literal[1] = 1
    primary_goal: Goal
    guardrails: tuple[Guardrail, ...] = ()
    preferences: tuple[Preference, ...] = ()

    @model_validator(mode="after")
    def distinct_rules(self):
        for rules in (self.guardrails, self.preferences):
            if len({rule.kind for rule in rules}) != len(rules):
                raise ValueError("Duplicate policy rule")
        if self.primary_goal == "CUSTOM" and not self.preferences:
            raise ValueError("CUSTOM requires explicit preference weights")
        if self.preferences and sum(scaled_integer(p.weight, 4) for p in self.preferences) != 10000:
            raise ValueError("Preference weights must sum to one")
        return self


class NodePolicy(CasePolicy):
    override: StrictBool = False
    override_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def override_is_explicit(self):
        if self.override != bool(self.override_reason and self.override_reason.strip()):
            raise ValueError("An override requires a nonempty reason, and vice versa")
        return self

    def validate_case_policy(self, policy: CasePolicy):
        local = {rule.kind: rule.limit for rule in self.guardrails}
        for rule in policy.guardrails:
            limit = local.get(rule.kind)
            if limit is None or (limit > rule.limit if rule.kind == "MAXIMUM_EXTERNAL_SHARE" else limit < rule.limit):
                raise ValueError("A node override cannot relax hard Case guardrails")
        if not self.override and (self.primary_goal, self.preferences, self.guardrails) != (policy.primary_goal, policy.preferences, policy.guardrails):
            raise ValueError("Policy divergence must be an explicit override")
        return self


class Demand(ContractModel):
    order_id: Identifier
    origin_id: Identifier
    destination_id: Identifier
    distance_km: Positive
    ready_date: DecisionDate
    delivery_due_date: DecisionDate
    priority: Priority
    split_allowed: StrictBool
    requested: QuantityVector
    compatibility_groups: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def meaningful_demand(self):
        scaled_integer(self.distance_km, DISTANCE_SCALE)
        if self.delivery_due_date < self.ready_date:
            raise ValueError("Due date precedes ready date")
        if not any(value is not None and value > 0 for value in self.requested.model_dump().values()):
            raise ValueError("Demand must contain a positive explicit quantity")
        return self


class ExternalCost(ContractModel):
    cost_model: Literal["PER_TRIP", "PER_KM"]
    rate: NonNegative | None
    billing_basis: Literal["ONE_WAY", "ROUND_TRIP"] | None

    @model_validator(mode="after")
    def unambiguous_basis(self):
        if (self.cost_model == "PER_KM") != (self.billing_basis is not None):
            raise ValueError("PER_KM requires a mileage basis; PER_TRIP has none")
        return self


class TransportResource(ContractModel):
    resource_id: Identifier
    source: ResourceSource
    guaranteed_capacity: QuantityVector
    maximum_capacity: QuantityVector | None = None
    lanes: tuple[tuple[Identifier, Identifier], ...]
    compatibility_groups: tuple[Identifier, ...] = ()
    units_available: Count | None = None
    base_origin_id: Identifier | None = None
    operating_cost_per_km: NonNegative | None = None
    services_available: Count | None = None
    availability_source: Literal["CONFIRMED", "ASSUMED", "UNKNOWN"] | None = None
    external_cost: ExternalCost | None = None

    @model_validator(mode="after")
    def source_contract(self):
        if not self.lanes:
            raise ValueError("Explicit eligible lanes required; no arbitrary consolidation")
        for dim in Dimension:
            cap = getattr(self.guaranteed_capacity, dim)
            maximum = getattr(self.maximum_capacity, dim) if self.maximum_capacity else None
            if cap is not None and cap <= 0:
                raise ValueError("Guaranteed capacity is positive, never unknown-as-unlimited")
            if maximum is not None and (cap is None or maximum < cap):
                raise ValueError("Maximum cannot replace or be below guaranteed capacity")
        if self.source == ResourceSource.OWN:
            if not self.base_origin_id or self.services_available is not None or self.external_cost is not None or self.availability_source is not None:
                raise ValueError("OWN uses a base, units and operating cycle cost only")
        else:
            if self.units_available is not None or self.base_origin_id is not None or self.operating_cost_per_km is not None or self.external_cost is None:
                raise ValueError("EXTERNAL uses finite horizon services and its explicit cost model")
            if (self.services_available is None) != (self.availability_source == "UNKNOWN") or self.availability_source is None:
                raise ValueError("Unknown services cannot be confirmed or assumed available")
        return self


class SemanticInput(ContractModel):
    slot: Literal["transport_demand", "transport_resources", "scheduling_enrichment"]
    canonical_sha256: SHA256
    contract_hash: SHA256
    normalizer_version: Identifier


class LogisticsModelVersion(ContractModel):
    workspace_id: UUID
    model_id: UUID
    version_id: UUID
    version: int = Field(strict=True, ge=1)
    operating_role: Literal["SHIPPER", "LOGISTICS_PROVIDER", "HYBRID"]
    transport_pattern: Literal["DIRECT"] = "DIRECT"
    primary_dimension: Dimension
    active_dimensions: tuple[Dimension, ...]
    allowed_sources: tuple[ResourceSource, ...]
    homogeneous_loads_declared: StrictBool
    split_permitted: StrictBool
    currency_policy: CurrencyPolicy
    contract_registry_version: Identifier
    configuration_hash: SHA256

    @model_validator(mode="after")
    def explicit_model(self):
        if not self.active_dimensions or self.primary_dimension not in self.active_dimensions or len(set(self.active_dimensions)) != len(self.active_dimensions):
            raise ValueError("Model requires explicit unique active dimensions")
        if not self.allowed_sources or len(set(self.allowed_sources)) != len(self.allowed_sources):
            raise ValueError("Model requires explicit unique resource sources")
        return self


class FrozenCaseContext(Horizon):
    workspace_id: UUID
    case_id: UUID
    case_name: str = Field(max_length=200)
    operating_role: Literal["SHIPPER", "LOGISTICS_PROVIDER", "HYBRID"]
    logistics_model_id: UUID
    logistics_model_version_id: UUID
    logistics_model_version: int = Field(strict=True, ge=1)
    data_pack_version_id: UUID
    data_pack_version: int = Field(strict=True, ge=1)
    model_hash: SHA256
    pack_manifest_hash: SHA256
    graph_version: Identifier
    contract_hash: SHA256
    case_policy: CasePolicy
    node_policy: NodePolicy
    currency_policy: CurrencyPolicy
    primary_dimension: Dimension
    active_dimensions: tuple[Dimension, ...]
    read_set: tuple[SemanticInput, ...]
    display_metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def snapshot(self):
        self.node_policy.validate_case_policy(self.case_policy)
        if not self.active_dimensions or self.primary_dimension not in self.active_dimensions or len(set(self.active_dimensions)) != len(self.active_dimensions):
            raise ValueError("Explicit unique active dimensions including primary dimension required")
        if not self.read_set or len({item.slot for item in self.read_set}) != len(self.read_set):
            raise ValueError("Explicit unique semantic read set required")
        return self
