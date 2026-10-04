from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AssignmentObjectiveKey = Literal["trips", "cost", "own_fleet", "co2"]
ASSIGNMENT_OBJECTIVE_KEYS = ("trips", "cost", "own_fleet", "co2")

AssignmentFilterColumn = Literal[
    "estimated_dispatch_date",
    "delivery_due_date",
    "destination",
    "origin",
    "product",
    "priority",
    "quantity_units",
    "unit_weight_kg",
    "distance_km",
]
AssignmentFilterType = Literal["date", "category", "number"]
AssignmentResourceMode = Literal["own", "mixed", "outsourced"]

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


class AssignmentScopeFilter(BaseModel):
    """A resolved, reproducible filter applied to Orders before Assignment."""

    model_config = ConfigDict(extra="forbid")

    column: AssignmentFilterColumn
    type: AssignmentFilterType
    operator: Literal["between", "in"]
    value: list[str | float] = Field(default_factory=list, max_length=100)
    resolved: list[str | float] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def canonical(self):
        expected = {
            "estimated_dispatch_date": "date",
            "delivery_due_date": "date",
            "destination": "category",
            "origin": "category",
            "product": "category",
            "priority": "category",
            "quantity_units": "number",
            "unit_weight_kg": "number",
            "distance_km": "number",
        }[self.column]
        if self.type != expected:
            raise ValueError(
                f"El filtro {self.column} debe ser de tipo {expected}."
            )
        if self.type == "category" and self.operator != "in":
            raise ValueError("Los filtros categóricos usan el operador in.")
        if self.type in ("date", "number") and self.operator != "between":
            raise ValueError("Los filtros de rango usan el operador between.")
        values = self.resolved if self.resolved is not None else self.value
        if self.type in ("date", "number") and len(values) != 2:
            raise ValueError("El filtro de rango requiere dos valores.")
        return self


class AssignmentScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filters: list[AssignmentScopeFilter] = Field(default_factory=list, max_length=12)


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
    scope: AssignmentScope = Field(default_factory=AssignmentScope)

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
    resource_mode: AssignmentResourceMode = "mixed"
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

    @model_validator(mode="before")
    @classmethod
    def resource_compatibility(cls, values):
        data = dict(values or {})
        if "resource_mode" not in data:
            data["resource_mode"] = (
                "mixed"
                if data.get("allow_third_party", True)
                else "own"
            )
        data["allow_third_party"] = data["resource_mode"] != "own"
        return data
