"""Additive J1.02 policy binding. CasePolicy V1 and old fingerprints stay intact."""
from typing import Literal
from uuid import UUID
from pydantic import StrictBool
from .base import ContractModel, Ratio, SHA256


class CaseBusinessRulesV2(ContractModel):
    version: Literal[1] = 1
    prefer_own_fleet_on_cost_tie: StrictBool = False


class CaseAcceptancePolicyV2(ContractModel):
    version: Literal[1] = 1
    metric: Literal['TOTAL_DEMAND_COVERAGE'] = 'TOTAL_DEMAND_COVERAGE'
    comparator: Literal['GTE'] = 'GTE'
    threshold: Ratio
    basis: Literal['CANONICAL_MODEL_PRIMARY_DIMENSION'] = 'CANONICAL_MODEL_PRIMARY_DIMENSION'


class CaseExecutionBindingV2(ContractModel):
    definition_revision_id: UUID
    definition_hash: SHA256
    business_rules: CaseBusinessRulesV2
    acceptance_policy: CaseAcceptancePolicyV2
