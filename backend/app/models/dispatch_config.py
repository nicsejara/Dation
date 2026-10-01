from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict

PRESETS = {'min_cost': (1, 0, 0), 'min_trips': (0, 1, 0), 'min_time': (0, 0, 1), 'balanced': (1/3, 1/3, 1/3)}


class DispatchWeights(BaseModel):
    cost: float = Field(ge=0, le=1)
    trips: float = Field(ge=0, le=1)
    time: float = Field(default=0, ge=0, le=1)

    @model_validator(mode='after')
    def total(self):
        if abs(self.cost + self.trips + self.time - 1) > 1e-6:
            raise ValueError('Los pesos deben sumar 100 %.')
        return self


class DispatchConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['preset', 'custom'] = 'preset'
    objective: Literal['min_cost', 'min_trips', 'min_time', 'balanced', 'custom'] = 'balanced'
    weights: DispatchWeights | None = None

    @model_validator(mode='after')
    def canonical(self):
        if self.mode == 'preset':
            if self.objective == 'custom':
                raise ValueError('Seleccioná un objetivo predefinido.')
            canonical = dict(zip(('cost', 'trips', 'time'), PRESETS[self.objective]))
            if self.weights and any(abs(getattr(self.weights, k)-v) > 1e-6 for k,v in canonical.items()):
                raise ValueError('Los pesos no coinciden con el objetivo predefinido.')
            self.weights = DispatchWeights(**canonical)
        elif self.objective != 'custom' or self.weights is None:
            raise ValueError('La configuración personalizada requiere los tres pesos.')
        return self


class DispatchOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    allow_third_party: bool = True
    anomaly_decisions: dict[str, Literal['include', 'exclude']] = Field(default_factory=dict)
    solve_time_limit_s: float = Field(default=10, ge=.1, le=20)
    deterministic_limit: float = Field(default=.1, ge=.001, le=1)
    total_time_limit_s: float = Field(default=90, ge=5, le=180)
    sensitivity: bool = True
