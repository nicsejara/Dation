"""Versioned reason requirements. A code reference is not an emitted claim."""
from datetime import date
from decimal import Decimal
from types import MappingProxyType
import re
from typing import Literal, Annotated

from pydantic import Field, model_validator, BeforeValidator, StrictInt, StrictBool

from app.domain.logistics.base import (ContractModel, EntityType, Identifier, decimal_value, DecimalValue)

REASON_CATALOG_VERSION = "DATION_REASONS_V1"
CertifiedFactValue = str | StrictInt | StrictBool | DecimalValue | date | tuple[str, ...] | None


def _wire_fact(value):
    from .canonical import canonical_tree
    return canonical_tree(value)


# Generic projections preserve the exact scalar wire value. Certified reason
# facts use their catalog's typed requirements and restore Decimal/DATE types.
FactValue = Annotated[str | StrictInt | StrictBool | tuple[str, ...] | None, BeforeValidator(_wire_fact)]


class FactRequirement(ContractModel):
    name: Identifier
    kind: Literal["id", "text", "decimal", "positive", "count", "date", "true", "false", "ids",
                  "dimension", "currency", "priority", "availability", "capacity_basis", "reason_code"]


class ReasonCodeDefinition(ContractModel):
    stable_id: Identifier
    version: Literal[1] = 1
    entity_scope: tuple[EntityType, ...]
    producer: Literal["transport_plan", "day_scheduling"]
    required_facts: tuple[FactRequirement, ...]
    claim_strength: Literal["OBSERVED", "CERTIFIED_FEASIBILITY", "CERTIFIED_COMPARISON", "CERTIFIED_INFEASIBILITY"]
    message_key: str


def _definition(code, producer, scopes, facts, claim="OBSERVED"):
    return ReasonCodeDefinition(stable_id=code, producer=producer, entity_scope=scopes,
        required_facts=tuple(FactRequirement(name=name, kind=kind) for name, kind in facts.items()),
        claim_strength=claim, message_key="ultimate.reason." + code.lower())


_D1 = [
 ("SELECTED_LOWEST_COST_FEASIBLE", ("TRIP",), dict(selected_resource_id="id", selected_cost="decimal", currency="currency", minimum_feasible_cost="decimal", candidate_set_complete="true", certificate_ref="id"), "CERTIFIED_COMPARISON"),
 ("SELECTED_ONLY_FEASIBLE_RESOURCE", ("TRIP",), dict(selected_resource_id="id", feasible_candidate_count="count", candidate_set_complete="true", certificate_ref="id"), "CERTIFIED_FEASIBILITY"),
 ("SELECTED_PRIORITY_PROTECTION", ("ORDER", "TRIP"), dict(protected_priority="priority", assigned_quantity="positive", policy_evidence_ref="id"), "OBSERVED"),
 ("SELECTED_OWN_COST_ADVANTAGE", ("TRIP",), dict(own_cost="decimal", external_cost="decimal", currency="currency", candidate_set_complete="true", certificate_ref="id"), "CERTIFIED_COMPARISON"),
 ("CONSOLIDATED_COMPATIBLE_DEMAND", ("TRIP",), dict(order_ids="ids", compatibility_certificate_ref="id", window_start="date", window_end="date"), "CERTIFIED_FEASIBILITY"),
 ("NO_COMPATIBLE_RESOURCE", ("ORDER",), dict(compatible_resource_count="count", candidate_set_complete="true", certificate_ref="id"), "CERTIFIED_INFEASIBILITY"),
 ("NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY", ("ORDER",), dict(split_allowed="false", dimension="dimension", requested="positive", maximum_guaranteed_capacity="decimal"), "CERTIFIED_INFEASIBILITY"),
 ("EXTERNAL_SERVICE_LIMIT", ("ORDER", "RESOURCE"), dict(resource_id="id", services_available="count", services_used="count"), "OBSERVED"),
 ("HORIZON_CAPACITY_LIMIT", ("ORDER", "CASE"), dict(planning_start="date", planning_end="date", feasibility_certificate_ref="id"), "CERTIFIED_INFEASIBILITY"),
 ("DATE_WINDOW_INCOMPATIBLE", ("ORDER", "TRIP"), dict(earliest_dispatch="date", latest_dispatch="date"), "CERTIFIED_INFEASIBILITY"),
 ("CAPACITY_GAP", ("ORDER", "CASE"), dict(dimension="dimension", unassigned_quantity="positive"), "OBSERVED"),
 ("RESOURCE_SERVICE_LIMIT_REACHED", ("RESOURCE",), dict(services_available="count", services_used="count"), "OBSERVED"),
 ("ASSUMED_EXTERNAL_AVAILABILITY", ("RESOURCE",), dict(services_available="count", availability_source="availability"), "OBSERVED"),
 ("GUARANTEED_CAPACITY_USED_FOR_FEASIBILITY", ("TRIP", "RESOURCE"), dict(dimension="dimension", guaranteed_capacity="positive", load="decimal", capacity_basis="capacity_basis"), "CERTIFIED_FEASIBILITY"),
]
_D2 = [
 ("SCHEDULED_WITHIN_FEASIBLE_WINDOW", dict(earliest_dispatch="date", latest_dispatch="date", selected_dispatch="date"), "CERTIFIED_FEASIBILITY"),
 ("SCHEDULED_EARLIEST_FEASIBLE", dict(earliest_dispatch="date", selected_dispatch="date"), "CERTIFIED_FEASIBILITY"),
 ("SCHEDULED_TO_PROTECT_DUE_DATE", dict(arrival_date="date", delivery_due_date="date", schedule_evidence_ref="id"), "OBSERVED"),
 ("DELAYED_BY_READY_DATE", dict(unconstrained_dispatch="date", ready_date="date", selected_dispatch="date"), "OBSERVED"),
 ("DELAYED_BY_RESOURCE_OCCUPANCY", dict(resource_id="id", desired_dispatch="date", resource_busy_until="date", selected_dispatch="date"), "OBSERVED"),
 ("ZERO_MARGIN", dict(margin_days="count", arrival_date="date", delivery_due_date="date"), "OBSERVED"),
 ("PRE_HORIZON_DISPATCH_REQUIRED", dict(latest_dispatch="date", planning_start="date"), "CERTIFIED_INFEASIBILITY"),
 ("NO_FEASIBLE_DISPATCH_DAY", dict(feasible_day_count="count", feasibility_certificate_ref="id"), "CERTIFIED_INFEASIBILITY"),
 ("RESOURCE_CAPACITY_CONFLICT", dict(resource_id="id", concurrent_trips="count", units_available="count", conflict_date="date"), "OBSERVED"),
 ("UNSCHEDULED", dict(cause_code="reason_code", cause_evidence_ref="id"), "OBSERVED"),
]
REASON_CODES = MappingProxyType({definition.stable_id: definition for definition in (
    *(_definition(code, "transport_plan", scopes, facts, claim) for code, scopes, facts, claim in _D1),
    *(_definition(code, "day_scheduling", ("TRIP",), facts, claim) for code, facts, claim in _D2),
)})


def reason_definition(code: str) -> ReasonCodeDefinition:
    try:
        return REASON_CODES[code]
    except KeyError as exc:
        raise ValueError("Unsupported reason code: " + str(code)) from exc


def _fact(value, kind):
    enums={'dimension':('pallets','weight_kg','volume_m3','units'), 'priority':('HIGH','MEDIUM','LOW'),
           'availability':('CONFIRMED','ASSUMED','UNKNOWN'), 'capacity_basis':('GUARANTEED',),
           'reason_code':tuple(REASON_CODES)}
    if kind in enums:
        if not isinstance(value,str) or value not in enums[kind]:
            raise ValueError("Unsupported typed fact: " + kind)
        return value
    if kind == 'currency':
        if not isinstance(value,str) or not re.fullmatch(r'[A-Z]{3}',value):
            raise ValueError("Explicit currency code required")
        return value
    if kind in ("decimal", "positive"):
        value = decimal_value(value)
        if value < 0 or kind == "positive" and value <= 0:
            raise ValueError("Reason quantity must be nonnegative/positive")
    elif kind == "count":
        if type(value) is not int or value < 0:
            raise ValueError("Reason count must be a nonnegative integer")
    elif kind == "date":
        if type(value) is not date:
            if not isinstance(value, str):
                raise ValueError("Reason DATE required")
            value = date.fromisoformat(value)
    elif kind in ("true", "false"):
        if value is not (kind == "true"):
            raise ValueError("Reason boolean witness contradicts claim")
    elif kind == "ids":
        if not isinstance(value, (list, tuple)) or not value or any(not isinstance(v, str) or not v.strip() for v in value):
            raise ValueError("Nonempty entity IDs required")
        value = tuple(value)
    elif not isinstance(value, str) or not value.strip():
        raise ValueError("Nonempty reason fact required")
    if kind == 'id' and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',value):
        raise ValueError("Invalid evidence/entity identifier")
    return value


def validate_facts(definition, facts):
    expected = {item.name: item.kind for item in definition.required_facts}
    if set(facts) != set(expected):
        raise ValueError("Reason requires exactly its catalog facts: " + ",".join(expected))
    f = {name: _fact(facts[name], kind) for name, kind in expected.items()}
    code = definition.stable_id
    checks = {
        "SELECTED_LOWEST_COST_FEASIBLE": lambda: f['selected_cost'] == f['minimum_feasible_cost'],
        "SELECTED_ONLY_FEASIBLE_RESOURCE": lambda: f['feasible_candidate_count'] == 1,
        "SELECTED_OWN_COST_ADVANTAGE": lambda: f['own_cost'] < f['external_cost'],
        "CONSOLIDATED_COMPATIBLE_DEMAND": lambda: len(set(f['order_ids'])) >= 2 and f['window_start'] <= f['window_end'],
        "NO_COMPATIBLE_RESOURCE": lambda: f['compatible_resource_count'] == 0,
        "NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY": lambda: f['requested'] > f['maximum_guaranteed_capacity'],
        "EXTERNAL_SERVICE_LIMIT": lambda: f['services_used'] == f['services_available'],
        "RESOURCE_SERVICE_LIMIT_REACHED": lambda: f['services_used'] == f['services_available'],
        "ASSUMED_EXTERNAL_AVAILABILITY": lambda: f['availability_source'] == 'ASSUMED',
        "GUARANTEED_CAPACITY_USED_FOR_FEASIBILITY": lambda: f['load'] <= f['guaranteed_capacity'] and f['capacity_basis'] == 'GUARANTEED',
        "HORIZON_CAPACITY_LIMIT": lambda: f['planning_start'] <= f['planning_end'],
        "DATE_WINDOW_INCOMPATIBLE": lambda: f['earliest_dispatch'] > f['latest_dispatch'],
        "SCHEDULED_WITHIN_FEASIBLE_WINDOW": lambda: f['earliest_dispatch'] <= f['selected_dispatch'] <= f['latest_dispatch'],
        "SCHEDULED_EARLIEST_FEASIBLE": lambda: f['selected_dispatch'] == f['earliest_dispatch'],
        "SCHEDULED_TO_PROTECT_DUE_DATE": lambda: f['arrival_date'] <= f['delivery_due_date'],
        "DELAYED_BY_READY_DATE": lambda: f['unconstrained_dispatch'] < f['ready_date'] <= f['selected_dispatch'],
        "DELAYED_BY_RESOURCE_OCCUPANCY": lambda: f['desired_dispatch'] < f['resource_busy_until'] <= f['selected_dispatch'],
        "ZERO_MARGIN": lambda: f['margin_days'] == 0 and f['arrival_date'] == f['delivery_due_date'],
        "PRE_HORIZON_DISPATCH_REQUIRED": lambda: f['latest_dispatch'] < f['planning_start'],
        "NO_FEASIBLE_DISPATCH_DAY": lambda: f['feasible_day_count'] == 0,
        "RESOURCE_CAPACITY_CONFLICT": lambda: f['concurrent_trips'] > f['units_available'],
        "SELECTED_PRIORITY_PROTECTION": lambda: f['protected_priority'] in ('HIGH', 'MEDIUM', 'LOW'),
        "CAPACITY_GAP": lambda: f['dimension'] in ('pallets', 'weight_kg', 'volume_m3', 'units'),
        "UNSCHEDULED": lambda: f['cause_code'] in REASON_CODES and f['cause_code'] != 'UNSCHEDULED',
    }
    if code in checks and not checks[code]():
        raise ValueError("Reason facts contradict " + code)
    return f


class ReasonEmission(ContractModel):
    emission_id: Identifier
    code: Identifier
    version: Literal[1] = 1
    entity_type: EntityType
    entity_id: Identifier
    producer: Literal["transport_plan", "day_scheduling"]
    claim_strength: Literal["OBSERVED", "CERTIFIED_FEASIBILITY", "CERTIFIED_COMPARISON", "CERTIFIED_INFEASIBILITY"]
    facts: dict[str, CertifiedFactValue]
    evidence_refs: tuple[Identifier, ...] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def typed_facts(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            value['facts'] = validate_facts(reason_definition(value.get('code')), value.get('facts') or {})
        return value

    @model_validator(mode="after")
    def claim(self):
        definition = reason_definition(self.code)
        if self.entity_type not in definition.entity_scope or self.producer != definition.producer or self.claim_strength != definition.claim_strength:
            raise ValueError("Reason scope/producer/claim must match its catalog")
        validate_facts(definition, self.facts)
        return self
