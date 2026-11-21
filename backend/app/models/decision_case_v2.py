"""Six-block definition, separately versioned from the existing CasePolicy V1."""
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, field_validator, model_validator
from app.domain.logistics.base import ContractModel, SHA256
from app.domain.logistics.contracts import CasePolicy, Horizon
from app.domain.logistics.case_policy_v2 import CaseBusinessRulesV2, CaseAcceptancePolicyV2
from app.models.ultimate_foundation import UltimateCaseCreate, clean_text, OwnerUpdate


class CaseIdentityV2(ContractModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    _text = field_validator('name', 'description')(clean_text)


class CaseModelBindingV2(ContractModel):
    model_id: UUID
    model_version_id: UUID
    configuration_hash: SHA256
    contract_hash: SHA256


class CaseDecisionContextV2(Horizon):
    horizon_type: Literal['DAILY', 'WEEKLY', 'MONTHLY', 'CUSTOM']
    operating_mode: Literal['OPERATIONAL', 'SIMULATION']


class CaseApprovalV2(ContractModel):
    kind: Literal['MANUAL_DECISION_OWNER'] = 'MANUAL_DECISION_OWNER'


class CaseProvenanceV2(ContractModel):
    parent_case_id: UUID
    parent_definition_revision_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=1000)
    _text = field_validator('reason')(clean_text)


class DecisionCaseDefinitionV2(ContractModel):
    schema_version: Literal['decision_case_definition_v2']
    case_work_id: UUID
    identity: CaseIdentityV2
    model_binding: CaseModelBindingV2
    decision_context: CaseDecisionContextV2
    case_policy: CasePolicy
    business_rules: CaseBusinessRulesV2
    acceptance_policy: CaseAcceptancePolicyV2
    approval_policy: CaseApprovalV2
    provenance: CaseProvenanceV2 | None = None

    @model_validator(mode='after')
    def executable_scope(self):
        if len(self.case_policy.guardrails) != 1 or self.case_policy.guardrails[0].kind != 'CRITICAL_DEMAND_COVERAGE':
            raise ValueError('Definí únicamente la restricción obligatoria de demanda crítica.')
        if self.business_rules.prefer_own_fleet_on_cost_tie and (self.case_policy.primary_goal != 'MINIMIZE_COST' or self.case_policy.preferences):
            raise ValueError('El desempate requiere minimizar costo, sin preferencias adicionales que cambien su orden.')
        return self


class UltimateCaseCreateV2(UltimateCaseCreate):
    definition_v2: DecisionCaseDefinitionV2

    @model_validator(mode='after')
    def exact_definition(self):
        d = self.definition_v2
        if (self.name, self.description, self.logistics_model_version_id, self.case_policy) != (
                d.identity.name, d.identity.description, d.model_binding.model_version_id, d.case_policy):
            raise ValueError('La intención no coincide con la definición confirmada.')
        if any(getattr(self, key) != value for key, value in d.decision_context.model_dump().items()):
            raise ValueError('El horizonte/modalidad no coincide con la definición confirmada.')
        if d.provenance and d.provenance.parent_case_id == self.id:
            raise ValueError('La derivación requiere otra identidad de Case.')
        return self


class CaseDefinitionUpdateV2(ContractModel):
    mutation_id: UUID
    expected_revision: int = Field(strict=True, ge=1)
    expected_updated_at: AwareDatetime
    definition_v2: DecisionCaseDefinitionV2
    owner_updates: tuple[OwnerUpdate, ...] = Field(default=(), max_length=2)
