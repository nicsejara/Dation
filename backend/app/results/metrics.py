"""Single-producer metric catalog and typed values, with no KPI producers."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from types import MappingProxyType
from typing import Literal, Annotated

from pydantic import Field, model_validator

from app.domain.logistics.base import (ContractModel, Count, DecimalValue, Dimension,
                                      DecisionDate, Identifier, NonNegative, Priority, Ratio)
from app.domain.logistics.units import Money
from app.domain.logistics.units import scaled_integer

METRIC_CATALOG_VERSION = "DATION_METRICS_V1"


class MetricDescriptor(ContractModel):
    metric_id: Identifier
    version: Literal[1] = 1
    result_schema: Literal["transport_plan_v1", "day_scheduling_v1"]
    path: str
    producer: Literal["transport_plan", "day_scheduling"]
    unit: Literal["MONEY", "TRIP", "RESOURCE", "RATIO", "DAY", "QUANTITY", "COUNT"]
    precision: int = Field(strict=True, ge=0, le=6)
    null_semantics: str
    numerator: str | None = None
    denominator: str | None = None
    precision_source: Literal["FIXED", "CURRENCY_POLICY", "DIMENSION_POLICY"] = "FIXED"
    currency_path: str | None = None
    dimension_path: str | None = None


_METRICS = (
    ("transport_plan_v1", "total_cost", "MONEY", 6, None, None),
    ("transport_plan_v1", "trip_count", "TRIP", 0, None, None),
    ("transport_plan_v1", "demand_coverage.ratio", "RATIO", 4, "assigned", "requested"),
    ("transport_plan_v1", "demand_coverage.requested", "QUANTITY", 6, None, None),
    ("transport_plan_v1", "demand_coverage.assigned", "QUANTITY", 6, None, None),
    ("transport_plan_v1", "demand_coverage.unassigned", "QUANTITY", 6, None, None),
    ("transport_plan_v1", "capacity_utilization.weighted_ratio", "RATIO", 4, "sum_trip_load", "sum_trip_guaranteed_capacity"),
    ("transport_plan_v1", "resource_mix.own_trip_ratio", "RATIO", 4, "own_trips", "trip_count"),
    ("transport_plan_v1", "resource_mix.external_trip_ratio", "RATIO", 4, "external_trips", "trip_count"),
    ("transport_plan_v1", "resources_used", "RESOURCE", 0, None, None),
    ("transport_plan_v1", "coverage_by_priority.coverage_ratio", "RATIO", 4, "assigned_by_priority", "requested_by_priority"),
    ("day_scheduling_v1", "scheduled_trips.scheduled", "TRIP", 0, None, None),
    ("day_scheduling_v1", "scheduled_trips.total", "TRIP", 0, None, None),
    ("day_scheduling_v1", "scheduled_trips.ratio", "RATIO", 4, "scheduled", "total"),
    ("day_scheduling_v1", "service_level.on_time", "TRIP", 0, None, None),
    ("day_scheduling_v1", "service_level.at_risk", "TRIP", 0, None, None),
    ("day_scheduling_v1", "service_level.late", "TRIP", 0, None, None),
    ("day_scheduling_v1", "service_level.pre_horizon", "TRIP", 0, None, None),
    ("day_scheduling_v1", "service_level.unscheduled", "TRIP", 0, None, None),
    ("day_scheduling_v1", "on_time_ratio", "RATIO", 4, "on_time+at_risk", "total_trips"),
    ("day_scheduling_v1", "average_schedule_margin_days", "DAY", 4, "known_margins", "trips_with_known_margin"),
    ("day_scheduling_v1", "peak_dispatch_day.trip_count", "TRIP", 0, None, None),
    ("day_scheduling_v1", "exception_count", "COUNT", 0, None, None),
)


def make_catalog(descriptors):
    result = {}
    for item in descriptors:
        if item.producer != ("transport_plan" if item.result_schema == "transport_plan_v1" else "day_scheduling"):
            raise ValueError("A metric producer must own its registered result schema")
        key = (item.result_schema, item.metric_id)
        if key in result or (item.result_schema, item.path) in {(v.result_schema, v.path) for v in result.values()}:
            raise ValueError("A metric has exactly one certified producer")
        result[key] = item
    return MappingProxyType(result)


METRICS = make_catalog(MetricDescriptor(metric_id=path, result_schema=schema, path="metrics."+path,
    producer="transport_plan" if schema == "transport_plan_v1" else "day_scheduling", unit=unit,
    precision=precision, null_semantics="UNKNOWN_OR_UNDEFINED_IS_NULL_NEVER_ZERO", numerator=num,
    denominator=den, precision_source="CURRENCY_POLICY" if unit == "MONEY" else "DIMENSION_POLICY" if unit == "QUANTITY" else "FIXED",
    currency_path="context.currency_policy.currency" if unit == "MONEY" else None,
    dimension_path="context.primary_dimension" if unit == "QUANTITY" else None) for schema, path, unit, precision, num, den in _METRICS)


def validate_ratio(value, numerator, denominator):
    # Independent contract check only. Engines will own production certification.
    with localcontext() as ctx:
        ctx.prec = 60
        expected = None if denominator == 0 else (Decimal(numerator) / Decimal(denominator)).quantize(Decimal('.0001'), rounding=ROUND_HALF_UP)
    if value != expected:
        raise ValueError("Ratio must match its certified numerator/denominator; zero denominator is NULL")


class Coverage(ContractModel):
    primary_dimension: Dimension
    requested: NonNegative
    assigned: NonNegative
    unassigned: NonNegative
    ratio: Ratio | None

    @model_validator(mode="after")
    def consistent(self):
        with localcontext() as ctx:
            ctx.prec = 60
            if self.assigned + self.unassigned != self.requested:
                raise ValueError("Assigned plus residual must equal requested")
        validate_ratio(self.ratio, self.assigned, self.requested)
        return self


class PriorityCoverage(ContractModel):
    priority: Priority
    coverage_ratio: Ratio | None


class Utilization(ContractModel):
    primary_dimension: Dimension
    weighted_ratio: Ratio | None


class ResourceMix(ContractModel):
    own_trip_ratio: Ratio | None
    external_trip_ratio: Ratio | None

    @model_validator(mode="after")
    def complete(self):
        if (self.own_trip_ratio is None) != (self.external_trip_ratio is None):
            raise ValueError("Mix ratios share the same denominator")
        if self.own_trip_ratio is not None and scaled_integer(self.own_trip_ratio, 4) + scaled_integer(self.external_trip_ratio, 4) != 10000:
            raise ValueError("Trip source ratios must sum to one")
        return self


class TransportPlanMetrics(ContractModel):
    total_cost: Money | None
    cost_completeness: Literal["COMPLETE", "PARTIAL", "UNKNOWN"]
    trip_count: Count
    demand_coverage: Coverage
    capacity_utilization: Utilization
    resource_mix: ResourceMix
    resources_used: Count
    coverage_by_priority: tuple[PriorityCoverage, ...]

    @model_validator(mode="after")
    def known_cost(self):
        if (self.total_cost is not None) != (self.cost_completeness == "COMPLETE"):
            raise ValueError("An incomplete known subtotal is not total_cost")
        if self.trip_count == 0 and (self.resource_mix.own_trip_ratio is not None or self.capacity_utilization.weighted_ratio is not None):
            raise ValueError("Undefined mix/utilization is NULL, not zero/full")
        if self.trip_count > 0 and self.resource_mix.own_trip_ratio is None:
            raise ValueError("Used trips have a known source denominator")
        if len({v.priority for v in self.coverage_by_priority}) != len(self.coverage_by_priority):
            raise ValueError("Duplicate priority metric")
        return self


class ScheduledTrips(ContractModel):
    scheduled: Count
    total: Count
    ratio: Ratio | None

    @model_validator(mode="after")
    def consistent(self):
        if self.scheduled > self.total:
            raise ValueError("Scheduled exceeds approved D1 trips")
        validate_ratio(self.ratio, self.scheduled, self.total)
        return self


class ServiceLevel(ContractModel):
    on_time: Count
    at_risk: Count
    late: Count
    pre_horizon: Count
    unscheduled: Count


class PeakDispatchDay(ContractModel):
    date: DecisionDate
    trip_count: int = Field(strict=True, ge=1)


class DaySchedulingMetrics(ContractModel):
    scheduled_trips: ScheduledTrips
    service_level: ServiceLevel
    on_time_ratio: Ratio | None
    average_schedule_margin_days: Annotated[DecimalValue, Field(decimal_places=4)] | None
    peak_dispatch_day: PeakDispatchDay | None
    exception_count: Count

    @model_validator(mode="after")
    def disjoint_counts(self):
        s = self.service_level
        if s.on_time + s.at_risk + s.late + s.pre_horizon + s.unscheduled != self.scheduled_trips.total:
            raise ValueError("Service categories must be disjoint and cover all approved trips")
        if s.on_time + s.at_risk + s.late != self.scheduled_trips.scheduled:
            raise ValueError("Pre-horizon and unscheduled are not scheduled late trips")
        validate_ratio(self.on_time_ratio, s.on_time + s.at_risk, self.scheduled_trips.total)
        if self.scheduled_trips.scheduled == 0 and (self.peak_dispatch_day is not None or self.average_schedule_margin_days is not None):
            raise ValueError("Unknown/undefined timing is NULL")
        return self
