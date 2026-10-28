"""T3 setup DTOs. No datasets, admission requests, engines or result producers."""
from datetime import datetime
from typing import Literal
from uuid import UUID
import unicodedata

from pydantic import AwareDatetime, Field, StrictBool, field_validator, model_validator
from app.domain.logistics.base import ContractModel, DecisionDate, Dimension, ResourceSource
from app.domain.logistics.contracts import CasePolicy, Horizon, LogisticsModelVersion
from app.domain.logistics.units import CurrencyPolicy

HorizonType = Literal['DAILY','WEEKLY','MONTHLY','CUSTOM']
OperatingMode = Literal['OPERATIONAL','SIMULATION']


def clean_text(value):
    if value is None:return None
    value=unicodedata.normalize('NFC',value.strip())
    if not value:raise ValueError('Ingresá un texto o quitá el valor opcional.')
    return value


class LogisticsModelConfigurationV1(ContractModel):
    version: Literal[1] = 1
    operating_role: Literal['SHIPPER','LOGISTICS_PROVIDER','HYBRID']
    transport_pattern: Literal['DIRECT'] = 'DIRECT'
    allowed_sources: tuple[ResourceSource,...] = Field(min_length=1,max_length=2)
    active_dimensions: tuple[Dimension,...] = Field(min_length=1,max_length=4)
    primary_dimension: Dimension
    split_permitted: StrictBool = False
    homogeneous_loads_declared: StrictBool = False
    currency_policy: CurrencyPolicy
    own_cost_model: Literal['OWN_OPERATING_CYCLE'] = 'OWN_OPERATING_CYCLE'
    external_cost_models: tuple[Literal['PER_TRIP','PER_KM'],...] = ('PER_TRIP','PER_KM')
    per_km_billing_bases: tuple[Literal['ONE_WAY','ROUND_TRIP'],...] = ('ONE_WAY','ROUND_TRIP')

    @model_validator(mode='after')
    def explicit_configuration(self):
        for values in [self.active_dimensions,self.allowed_sources,self.external_cost_models,self.per_km_billing_bases]:
            if len(values)!=len(set(values)):raise ValueError('Las opciones no pueden repetirse.')
        if self.primary_dimension not in self.active_dimensions:
            raise ValueError('La dimensión principal debe estar activa.')
        if ResourceSource.EXTERNAL in self.allowed_sources and not self.external_cost_models:
            raise ValueError('Definí al menos una tarifa externa permitida.')
        if 'PER_KM' in self.external_cost_models and not self.per_km_billing_bases:
            raise ValueError('Definí la base de facturación por kilómetro.')
        return self


class ModelCreate(ContractModel):
    id: UUID
    name: str = Field(min_length=1,max_length=120)
    description: str | None = Field(default=None,max_length=1000)
    configuration: LogisticsModelConfigurationV1
    _text=field_validator('name','description')(clean_text)


class ModelUpdate(ContractModel):
    expected_revision: int = Field(strict=True,ge=1)
    name: str = Field(min_length=1,max_length=120)
    description: str | None = Field(default=None,max_length=1000)
    status: Literal['active','archived'] = 'active'
    configuration: LogisticsModelConfigurationV1
    _text=field_validator('name','description')(clean_text)


class ModelPublish(ContractModel):
    version_id: UUID
    expected_revision: int = Field(strict=True,ge=1)


class UltimateCaseCreate(Horizon):
    id: UUID
    name: str = Field(min_length=1,max_length=120)
    description: str | None = Field(default=None,max_length=1000)
    logistics_model_version_id: UUID
    horizon_type: HorizonType
    operating_mode: OperatingMode = 'OPERATIONAL'
    case_policy: CasePolicy
    decision_owner_user_id: UUID | None = None
    _text=field_validator('name','description')(clean_text)


class OwnerUpdate(ContractModel):
    node_id: Literal['logistics_assignment','logistics_scheduling']
    owner_user_id: UUID | None
    expected_updated_at: AwareDatetime | None


class UltimateCaseUpdate(ContractModel):
    expected_updated_at: AwareDatetime
    name: str | None = Field(default=None,min_length=1,max_length=120)
    description: str | None = Field(default=None,max_length=1000)
    planning_start: DecisionDate | None = None
    planning_end: DecisionDate | None = None
    horizon_type: HorizonType | None = None
    operating_mode: OperatingMode | None = None
    case_policy: CasePolicy | None = None
    owner_updates: tuple[OwnerUpdate,...] = Field(default=(),max_length=2)
    _text=field_validator('name','description')(clean_text)

    @model_validator(mode='after')
    def actual_change(self):
        if not self.model_fields_set-{'expected_updated_at','owner_updates'} and not self.owner_updates:
            raise ValueError('Elegí un cambio para guardar.')
        if len({x.node_id for x in self.owner_updates})!=len(self.owner_updates):
            raise ValueError('Una asignación por decisión.')
        for key in self.model_fields_set-{'description','owner_updates'}:
            if getattr(self,key) is None:raise ValueError('El campo requerido no puede quitarse: '+key)
        return self


class PlanningContextV1(Horizon):
    """Durable pre-admission context; an empty Pack is NOT a FrozenCaseContext."""
    schema_version: Literal['planning_context_v1'] = 'planning_context_v1'
    workspace_id: UUID
    case_id: UUID
    operating_mode: OperatingMode
    horizon_type: HorizonType | None
    model: LogisticsModelVersion
    case_policy: CasePolicy
    case_policy_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    graph_definition_version: str
    data_pack_id: UUID
    data_pack_version_id: UUID
    data_pack_version: int = Field(strict=True,ge=1)
    pack_manifest_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    contract_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    context_frozen_at: AwareDatetime | None
    # No raw IDs/read sets invented; assembly/admission remains T4/T8.
    admission_available: Literal[False] = False
