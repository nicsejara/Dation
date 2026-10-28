"""Private test-profile D1 boundary; T1 DTOs remain the publication ABI."""
from math import gcd
from functools import reduce
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator
from app.domain.logistics.base import ContractModel
from app.domain.logistics.contracts import Demand, TransportResource, LogisticsModelVersion, FrozenCaseContext
from app.domain.logistics.units import QUANTITY_SCALES, scaled_integer
from app.domain.logistics.units import QuantityVector
from app.results.contracts import EngineOutput, DemandResolution, ResourceUsage
from app.engines.common.day_resource_feasibility import FeasibilityCertificate


class TransportPlanOptions(ContractModel):
    seed: int = Field(default=0, strict=True, ge=0, le=2**31-1)
    max_slots: int = Field(default=128, strict=True, ge=0, le=256)
    max_variables: int = Field(default=20000, strict=True, ge=0, le=30000)
    deterministic_budget: int = Field(default=5, strict=True, ge=0, le=30)
    kernel_budget: int = Field(default=2, strict=True, ge=0, le=30)


class TransportPlanInput(ContractModel):
    model: LogisticsModelVersion
    context: FrozenCaseContext
    demands: tuple[Demand, ...] = Field(max_length=100)
    resources: tuple[TransportResource, ...] = Field(max_length=40)
    run_id: UUID
    result_generated_at: AwareDatetime
    options: TransportPlanOptions = Field(default_factory=TransportPlanOptions)

    @model_validator(mode='after')
    def pinned_inputs(self):
        m, c = self.model, self.context
        if (m.workspace_id,m.model_id,m.version_id,m.version,m.configuration_hash,m.currency_policy,m.primary_dimension,set(m.active_dimensions)) != (c.workspace_id,c.logistics_model_id,c.logistics_model_version_id,c.logistics_model_version,c.model_hash,c.currency_policy,c.primary_dimension,set(c.active_dimensions)):
            raise ValueError('Model and Frozen Case context do not match')
        if {x.slot for x in c.read_set} != {'transport_demand','transport_resources'}:
            raise ValueError('D1 requires the two explicit T1 semantic inputs')
        for rows, key in [(self.demands,'order_id'),(self.resources,'resource_id')]:
            if len({getattr(row,key) for row in rows}) != len(rows):
                raise ValueError('Duplicate '+key)
        for order in self.demands:
            order.requested.require(m.active_dimensions)
            if not m.homogeneous_loads_declared and not order.compatibility_groups:
                raise ValueError('Compatibility must be explicit outside homogeneous Model')
            values = [scaled_integer(getattr(order.requested,d),QUANTITY_SCALES[d]) for d in m.active_dimensions]
            if not any(values):
                raise ValueError('Demand must be positive in an active dimension')
            # CP integer products and fraction display conversion stay bounded.
            if sum(values) > 2**50 or reduce(gcd, values)*1000000 > 2**60:
                raise ValueError('D1 numeric model budget exceeded')
        for resource in self.resources:
            resource.guaranteed_capacity.require(m.active_dimensions, positive=True)
            if not m.homogeneous_loads_declared and not resource.compatibility_groups:
                raise ValueError('Resource compatibility must be explicit')
            if any(scaled_integer(getattr(resource.guaranteed_capacity,d),QUANTITY_SCALES[d]) > 2**50 for d in m.active_dimensions):
                raise ValueError('D1 capacity numeric budget exceeded')
            if resource.source in m.allowed_sources and (resource.units_available is None if resource.source == 'OWN' else resource.services_available is None or resource.availability_source == 'UNKNOWN'):
                raise ValueError('Unknown availability cannot be invented by the solver')
        if (c.planning_end-c.planning_start).days > 365:
            raise ValueError('D1 supports at most 366 inclusive departure days')
        return self


class SearchTrace(ContractModel):
    version: Literal['D1_STRUCTURAL_FRACTION_COVERAGE_V1'] = 'D1_STRUCTURAL_FRACTION_COVERAGE_V1'
    native_statuses: tuple[str,...]
    solver_version: str
    seed: int
    candidate_slots: int
    variable_count: int
    candidate_set_complete: bool
    limits: tuple[str,...]
    model_sha256: str
    structural_input_sha256: str
    options: TransportPlanOptions


class TransportPlanComputation(ContractModel):
    output: EngineOutput
    demand_resolution: tuple[DemandResolution,...]
    residuals: dict[str,QuantityVector]
    resource_usage: tuple[ResourceUsage,...]
    temporal_certificate: FeasibilityCertificate
    search: SearchTrace


class EngineCertificationError(RuntimeError):
    """Technical failure. Never patch or publish an inconsistent candidate."""
