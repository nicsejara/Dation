"""T4 client intents contain IDs and CAS only, never paths or schemas."""
from typing import Literal
from uuid import UUID
from pydantic import Field,model_validator
from app.domain.logistics.base import ContractModel

Entity=Literal['transport_demand','transport_resources']

class SlotSelection(ContractModel):
    slot_key: Entity
    upload_id: UUID | None = None
    dataset_id: UUID | None = None
    @model_validator(mode='after')
    def one_reference(self):
        if (self.upload_id is None)==(self.dataset_id is None):raise ValueError('Elegí un candidato o dataset compatible.')
        return self

class PackPublication(ContractModel):
    publication_id: UUID
    expected_revision: int=Field(strict=True,ge=1)
    selection: tuple[SlotSelection,...]=Field(min_length=1,max_length=2)
    @model_validator(mode='after')
    def unique_slots(self):
        if len({s.slot_key for s in self.selection})!=len(self.selection):raise ValueError('Una selección por slot.')
        return self
