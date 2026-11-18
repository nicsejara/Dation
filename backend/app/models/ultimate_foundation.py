"""T3 setup DTOs. No datasets, admission requests, engines or result producers."""
from datetime import datetime
from typing import Literal
from uuid import UUID
import unicodedata

from pydantic import AwareDatetime, Field, StrictBool, TypeAdapter, field_validator, model_validator
from app.domain.logistics.base import ContractModel, DecisionDate, Dimension, ResourceSource
from app.domain.logistics.contracts import CasePolicy, Horizon, LogisticsModelVersion
from app.domain.logistics.units import CurrencyPolicy
from app.domain.logistics.cargo import CargoConfiguration

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


class LogisticsModelConfigurationV2(LogisticsModelConfigurationV1):
    """Explicit opt-in; v1 storage and mathematical semantics are unchanged."""
    version: Literal[2] = 2
    consolidation_permitted: StrictBool = True
    resource_categories: tuple[str, ...] = Field(default=(), max_length=20)
    cargo: CargoConfiguration

    @model_validator(mode='after')
    def cargo_contract(self):
        from app.domain.logistics.physical import normalize_catalog
        if self.split_permitted != (self.cargo.split_policy != 'INDIVISIBLE'):
            raise ValueError('Fraccionamiento de modelo y política de carga contradictorios.')
        if self.homogeneous_loads_declared != (self.cargo.compatibility_policy == 'UNIFORM_DECLARED'):
            raise ValueError('La declaración de compatibilidad debe ser explícita y coherente.')
        if len(self.resource_categories) != len(set(self.resource_categories)):
            raise ValueError('No repitas categorías de recursos.')
        from app.domain.logistics.base import Identifier
        for category in self.resource_categories:TypeAdapter(Identifier).validate_python(category)
        catalog=normalize_catalog(self.cargo,self.active_dimensions)
        if any(getattr(p.coefficients,self.primary_dimension) <= 0 for p in catalog.values()):
            raise ValueError('Cada presentación necesita una cantidad positiva en la dimensión principal.')
        return self


LogisticsModelConfiguration = LogisticsModelConfigurationV1 | LogisticsModelConfigurationV2


def parse_configuration(value):
    return TypeAdapter(LogisticsModelConfiguration).validate_python(value)


class LogisticsModelSnapshotV2(LogisticsModelVersion):
    configuration: LogisticsModelConfigurationV2

    @model_validator(mode='after')
    def exact_published_configuration(self):
        from app.results.canonical import canonical_bytes,content_sha256
        c=self.configuration
        expected=content_sha256(canonical_bytes({'canonical_version':'DATION_CANONICAL_V1','kind':'logistics_model_configuration_v2','value':c}))
        if self.configuration_hash!=expected or self.contract_registry_version!='SAGA10_DOMAIN_V2':
            raise ValueError('El catálogo no coincide con el hash/versionado publicado.')
        for key in ['operating_role','transport_pattern','primary_dimension','active_dimensions','allowed_sources','homogeneous_loads_declared','split_permitted','currency_policy']:
            if getattr(self,key)!=getattr(c,key):raise ValueError('La proyección del modelo no coincide con su configuración: '+key)
        return self


class ModelCreate(ContractModel):
    id: UUID
    name: str = Field(min_length=1,max_length=120)
    description: str | None = Field(default=None,max_length=1000)
    configuration: LogisticsModelConfiguration
    _text=field_validator('name','description')(clean_text)


class ModelUpdate(ContractModel):
    expected_revision: int = Field(strict=True,ge=1)
    name: str = Field(min_length=1,max_length=120)
    description: str | None = Field(default=None,max_length=1000)
    status: Literal['active','archived'] = 'active'
    configuration: LogisticsModelConfiguration
    _text=field_validator('name','description')(clean_text)


class ModelPublish(ContractModel):
    version_id: UUID
    expected_revision: int = Field(strict=True,ge=1)


class ModelContractPreview(ContractModel):
    configuration: LogisticsModelConfiguration | None = None
    model_id: UUID | None = None
    version_id: UUID | None = None

    @model_validator(mode='after')
    def one_source(self):
        if self.configuration is not None:
            if self.model_id is not None or self.version_id is not None:
                raise ValueError('Elegí una configuración o una versión publicada.')
        elif self.model_id is None or self.version_id is None:
            raise ValueError('Seleccioná el Model y su versión publicada.')
        return self


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
    model: LogisticsModelSnapshotV2 | LogisticsModelVersion
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
