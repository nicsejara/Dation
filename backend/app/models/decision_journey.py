"""UX04 intents carry identities/CAS, never storage paths or client schemas."""
from uuid import UUID
from pydantic import Field
from app.domain.logistics.base import ContractModel
from app.models.ultimate_foundation import UltimateCaseCreate

class PreparationCreate(ContractModel):
    id: UUID
    model_version_id: UUID
    parent_case_id: UUID | None = None

class PreparationRevision(ContractModel):
    expected_revision: int = Field(strict=True,ge=1)

class PreparationOwner(PreparationRevision):
    data_owner_user_id: UUID | None

class PreparationFinalize(PreparationRevision):
    case: UltimateCaseCreate

class CaseClose(ContractModel):
    token: str = Field(pattern=r'^[0-9a-f]{32}$')

class PreparationReuse(PreparationRevision):
    dataset_id: UUID
