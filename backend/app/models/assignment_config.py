from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AssignmentObjectiveKey = Literal["trips", "cost", "own_fleet", "co2"]
ASSIGNMENT_OBJECTIVE_KEYS = ("trips", "cost", "own_fleet", "co2")

ASSIGNMENT_PRESETS = {
    "min_trips": (1, 0, 0, 0),
    "min_cost": (0, 1, 0, 0),
    "max_own_fleet": (0, 0, 1, 0),
    "min_co2": (0, 0, 0, 1),
}

ASSIGNMENT_OBJECTIVE_DIMENSION = {
    "min_trips": "trips",
    "min_cost": "cost",
    "max_own_fleet": "own_fleet",
    "min_co2": "co2",
}


class AssignmentWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trips: float = Field(ge=0, le=1)
    cost: float = Field(ge=0, le=1)
    own_fleet: float = Field(ge=0, le=1)
    co2: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def total(self):
        if (
            abs(
                sum(
                    getattr(self, key)
                    for key in ASSIGNMENT_OBJECTIVE_KEYS
                )
                - 1
            )
            > 1e-6
        ):
            raise ValueError("Los pesos deben sumar 100 %.")
        return self


class AssignmentConfig(BaseModel):
    """Business priorities for the non-temporal load-assignment decision."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["preset", "custom"] = "preset"
    objective: Literal[
        "min_trips",
        "min_cost",
        "max_own_fleet",
        "min_co2",
        "balanced",
        "custom",
    ] = "balanced"
    dimensions: list[AssignmentObjectiveKey] = Field(
        default_factory=lambda: ["trips", "own_fleet"],
        min_length=1,
    )
    weights: AssignmentWeights | None = None

    @model_validator(mode="after")
    def canonical(self):
        dimensions = [
            key
            for key in ASSIGNMENT_OBJECTIVE_KEYS
            if key in self.dimensions
        ]
        if len(dimensions) != len(self.dimensions):
            raise ValueError(
                "Las dimensiones activas no pueden repetirse."
            )
        self.dimensions = dimensions

        if self.mode == "preset":
            if self.objective == "custom":
                raise ValueError(
                    "Seleccioná un objetivo predefinido."
                )

            required = ASSIGNMENT_OBJECTIVE_DIMENSION.get(
                self.objective
            )
            if required and required not in self.dimensions:
                raise ValueError(
                    "El objetivo seleccionado requiere activar "
                    f"la dimensión {required}."
                )

            if self.objective == "balanced":
                share = 1 / len(self.dimensions)
                canonical = {
                    key: (
                        share
                        if key in self.dimensions
                        else 0
                    )
                    for key in ASSIGNMENT_OBJECTIVE_KEYS
                }
            else:
                canonical = dict(
                    zip(
                        ASSIGNMENT_OBJECTIVE_KEYS,
                        ASSIGNMENT_PRESETS[
                            self.objective
                        ],
                    )
                )

            if self.weights and any(
                abs(
                    getattr(self.weights, key)
                    - value
                )
                > 1e-6
                for key, value in canonical.items()
            ):
                raise ValueError(
                    "Los pesos no coinciden con el objetivo "
                    "y las dimensiones activas."
                )
            self.weights = AssignmentWeights(
                **canonical
            )

        elif (
            self.objective != "custom"
            or self.weights is None
        ):
            raise ValueError(
                "La configuración personalizada requiere "
                "los cuatro pesos."
            )
        else:
            for key in ASSIGNMENT_OBJECTIVE_KEYS:
                value = getattr(self.weights, key)
                if (
                    key not in self.dimensions
                    and value > 1e-9
                ):
                    raise ValueError(
                        "Una dimensión inactiva debe "
                        "tener peso 0."
                    )

        return self


class AssignmentOptions(BaseModel):
    """Execution options for Assignment. No temporal policy belongs here."""

    model_config = ConfigDict(extra="forbid")

    allow_third_party: bool = True
    anomaly_decisions: dict[
        str,
        Literal["include", "exclude"],
    ] = Field(default_factory=dict)
    analysis_depth: Literal[
        "essential",
        "comparative",
        "deep",
    ] = "comparative"
    solve_time_limit_s: float = Field(
        default=10,
        ge=.1,
        le=30,
    )
    deterministic_limit: float = Field(
        default=.12,
        ge=.001,
        le=2,
    )
    total_time_limit_s: float = Field(
        default=90,
        ge=5,
        le=180,
    )
