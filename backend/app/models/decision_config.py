from typing import Literal

from pydantic import BaseModel, Field, model_validator


DecisionMode = Literal["preset", "custom"]
DecisionObjective = Literal["min_cost", "min_trips", "custom"]


class DecisionWeights(BaseModel):
    cost: float = Field(ge=0.0, le=1.0)
    trips: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_sum(self):
        if abs((self.cost + self.trips) - 1.0) > 1e-6:
            raise ValueError(
                "Los pesos de costo y viajes deben sumar exactamente 1."
            )
        return self


class DecisionRunConfig(BaseModel):
    mode: DecisionMode = "preset"
    objective: DecisionObjective = "min_cost"
    weights: DecisionWeights | None = None

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.mode == "preset":
            if self.objective == "custom":
                raise ValueError(
                    "Un modo predefinido no puede utilizar el objetivo custom."
                )

            canonical = {
                "min_cost": DecisionWeights(cost=1.0, trips=0.0),
                "min_trips": DecisionWeights(cost=0.0, trips=1.0),
            }[self.objective]

            if self.weights is None:
                self.weights = canonical
            elif (
                abs(self.weights.cost - canonical.cost) > 1e-6
                or abs(self.weights.trips - canonical.trips) > 1e-6
            ):
                raise ValueError(
                    "Los modos predefinidos deben utilizar sus ponderaciones "
                    "canónicas: costo 100/0 o viajes 0/100."
                )

        if self.mode == "custom":
            if self.objective != "custom":
                raise ValueError(
                    "El modo personalizado debe utilizar objective='custom'."
                )
            if self.weights is None:
                raise ValueError(
                    "El modo personalizado requiere ponderaciones de costo y viajes."
                )

        return self

    @classmethod
    def from_legacy_objective(cls, objective: str | None):
        normalized = objective or "min_cost"

        if normalized == "min_trips":
            return cls(
                mode="preset",
                objective="min_trips",
                weights={"cost": 0.0, "trips": 1.0},
            )

        return cls(
            mode="preset",
            objective="min_cost",
            weights={"cost": 1.0, "trips": 0.0},
        )


def normalize_stored_configuration(
    configuration: dict | None,
    result_json: dict | None = None,
) -> dict:
    configuration = configuration or {}
    objective = configuration.get("objective")

    if not objective and result_json:
        objective = result_json.get("objective")

    mode = configuration.get("mode")

    if mode == "custom" or objective == "custom":
        weights = configuration.get("weights") or (
            (result_json or {}).get("configuration", {}).get("weights")
        )

        if isinstance(weights, dict):
            try:
                return DecisionRunConfig(
                    mode="custom",
                    objective="custom",
                    weights=weights,
                ).model_dump()
            except ValueError:
                pass

    legacy = DecisionRunConfig.from_legacy_objective(
        objective if objective in {"min_cost", "min_trips"} else "min_cost"
    )
    return legacy.model_dump()
