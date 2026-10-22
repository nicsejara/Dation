from typing import Literal
from pydantic import BaseModel, Field, field_validator

CaseCategory = Literal['weekly', 'monthly', 'extraordinary', 'simulation', 'live_operation']

class CaseIdentity(BaseModel):
    label: str | None = Field(None, max_length=120)
    category: CaseCategory | None = None
    description: str | None = Field(None, max_length=1000)

    @field_validator('label', 'description')
    @classmethod
    def normalize(cls, value):
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError('Ingresá un texto o quitá el valor.')
        return value
