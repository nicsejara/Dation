from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ObjectiveKey = Literal["cost", "time", "utilization", "co2"]
OBJECTIVE_KEYS = ("cost", "time", "utilization", "co2")

PRESETS = {
    "min_cost": (1, 0, 0, 0),
    "min_time": (0, 1, 0, 0),
    "max_utilization": (0, 0, 1, 0),
    "min_co2": (0, 0, 0, 1),
}

OBJECTIVE_DIMENSION = {
    "min_cost": "cost",
    "min_time": "time",
    "max_utilization": "utilization",
    "min_co2": "co2",
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
    dimensions: list[ObjectiveKey] = Field(
        default_factory=lambda: list(OBJECTIVE_KEYS),
        min_length=1,
    )
    weights: DispatchWeights | None = None

    @model_validator(mode="after")
    def canonical(self):
        # Keep a deterministic canonical order and reject duplicates.
        dimensions = [
            key
            for key in OBJECTIVE_KEYS
            if key in self.dimensions
        ]
        if len(dimensions) != len(self.dimensions):
            raise ValueError(
                "Las dimensiones activas no pueden repetirse."
            )
        self.dimensions = dimensions

        if self.mode == "preset":
            if self.objective == "custom":
                raise ValueError("Seleccioná un objetivo predefinido.")

            required = OBJECTIVE_DIMENSION.get(self.objective)
            if required and required not in self.dimensions:
                raise ValueError(
                    "El objetivo seleccionado requiere activar "
                    f"la dimensión {required}."
                )

            if self.objective == "balanced":
                share = 1 / len(self.dimensions)
                canonical = {
                    key: share if key in self.dimensions else 0
                    for key in OBJECTIVE_KEYS
                }
            else:
                canonical = dict(
                    zip(OBJECTIVE_KEYS, PRESETS[self.objective])
                )

            if self.weights and any(
                abs(getattr(self.weights, key) - value) > 1e-6
                for key, value in canonical.items()
            ):
                raise ValueError(
                    "Los pesos no coinciden con el objetivo y "
                    "las dimensiones activas."
                )
            self.weights = DispatchWeights(**canonical)

        elif self.objective != "custom" or self.weights is None:
            raise ValueError(
                "La configuración personalizada requiere los cuatro pesos."
            )
        else:
            for key in OBJECTIVE_KEYS:
                value = getattr(self.weights, key)
                if key not in self.dimensions and value > 1e-9:
                    raise ValueError(
                        "Una dimensión inactiva debe tener peso 0."
                    )
            if not any(
                getattr(self.weights, key) > 0
                for key in self.dimensions
            ):
                raise ValueError(
                    "Al menos una dimensión activa debe tener peso."
                )

        return self


class DispatchOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_third_party: bool = True
    anomaly_decisions: dict[
        str,
        Literal["include", "exclude"],
    ] = Field(default_factory=dict)
    max_late_days: int = Field(default=30, ge=0, le=90)
    analysis_depth: Literal[
        "essential",
        "comparative",
        "deep",
    ] = "comparative"
    # Backward-compatible override for historical API clients. New UI uses
    # analysis_depth instead of exposing sensitivity as a technical switch.
    sensitivity: bool | None = None
    solve_time_limit_s: float = Field(default=12, ge=.1, le=30)
    deterministic_limit: float = Field(default=.15, ge=.001, le=2)
    total_time_limit_s: float = Field(default=120, ge=5, le=240)
