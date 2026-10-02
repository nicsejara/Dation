from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


OBJECTIVE_KEYS = ("cost", "time", "utilization", "co2")

PRESETS = {
    "min_cost": (1, 0, 0, 0),
    "min_time": (0, 1, 0, 0),
    "max_utilization": (0, 0, 1, 0),
    "min_co2": (0, 0, 0, 1),
    "balanced": (.25, .25, .25, .25),
}


class DispatchWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost: float = Field(ge=0, le=1)
    time: float = Field(ge=0, le=1)
    utilization: float = Field(ge=0, le=1)
    co2: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def total(self):
        if abs(sum(getattr(self, key) for key in OBJECTIVE_KEYS) - 1) > 1e-6:
            raise ValueError("Los pesos deben sumar 100 %.")
        return self


class DispatchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["preset", "custom"] = "preset"
    objective: Literal[
        "min_cost",
        "min_time",
        "max_utilization",
        "min_co2",
        "balanced",
        "custom",
    ] = "balanced"
    weights: DispatchWeights | None = None

    @model_validator(mode="after")
    def canonical(self):
        if self.mode == "preset":
            if self.objective == "custom":
                raise ValueError("Seleccioná un objetivo predefinido.")
            canonical = dict(zip(OBJECTIVE_KEYS, PRESETS[self.objective]))
            if self.weights and any(
                abs(getattr(self.weights, key) - value) > 1e-6
                for key, value in canonical.items()
            ):
                raise ValueError(
                    "Los pesos no coinciden con el objetivo predefinido."
                )
            self.weights = DispatchWeights(**canonical)
        elif self.objective != "custom" or self.weights is None:
            raise ValueError(
                "La configuración personalizada requiere los cuatro pesos."
            )
        return self


class DispatchOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_third_party: bool = True
    anomaly_decisions: dict[
        str,
        Literal["include", "exclude"],
    ] = Field(default_factory=dict)
    # A late recovery horizon is needed so an otherwise infeasible finite-fleet
    # case can still return the minimum-SLA-violation distribution. It is a
    # policy guardrail, not a business objective.
    max_late_days: int = Field(default=30, ge=0, le=90)
    solve_time_limit_s: float = Field(default=12, ge=.1, le=30)
    deterministic_limit: float = Field(default=.15, ge=.001, le=2)
    total_time_limit_s: float = Field(default=120, ge=5, le=240)
    sensitivity: bool = True
