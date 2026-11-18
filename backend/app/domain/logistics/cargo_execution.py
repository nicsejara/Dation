"""Explicit v2 execution lines; base Demand and Resource ABI stay unchanged."""
from pydantic import Field,model_validator
from .base import ContractModel,Identifier,Positive
from .contracts import Demand,TransportResource

class CargoOrderLine(ContractModel):
    line_id: Identifier
    presentation_id: Identifier
    quantity: Positive
    compatibility_groups: tuple[Identifier,...] = ()

class CatalogDemand(Demand):
    lines: tuple[CargoOrderLine,...] = Field(min_length=1,max_length=500)
    @model_validator(mode='after')
    def unique_lines(self):
        if len({l.line_id for l in self.lines})!=len(self.lines) or len({l.presentation_id for l in self.lines})!=len(self.lines):raise ValueError('Líneas duplicadas dentro de una orden.')
        return self

class CategorizedTransportResource(TransportResource):
    resource_category: Identifier
