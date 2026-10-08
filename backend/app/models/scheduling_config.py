from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SchedulingTemporalRule(BaseModel):
    """Temporal policy applied to a filtered subset of approved Assignment trips."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    field: Literal[
        "destination",
        "origin",
        "vehicle_id",
        "ownership",
        "product",
    ]
    values: list[str] = Field(min_length=1, max_length=100)
    action: Literal[
        "prioritize",
        "window",
    ]
    planning_window_start: date | None = None
    planning_window_end: date | None = None

    @model_validator(mode="after")
    def validate_rule(self):
        normalized = []
        seen = set()
        for value in self.values:
            clean = str(value).strip()
            if not clean:
                continue
            key = clean.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(clean)
        if not normalized:
            raise ValueError(
                "La regla temporal debe seleccionar al menos un valor."
            )
        self.values = normalized

        if self.action == "window":
            if not self.planning_window_start or not self.planning_window_end:
                raise ValueError(
                    "Una regla con ventana requiere fecha desde y fecha hasta."
                )
            if self.planning_window_end < self.planning_window_start:
                raise ValueError(
                    "La fecha hasta de la regla no puede ser anterior a la fecha desde."
                )
        else:
            self.planning_window_start = None
            self.planning_window_end = None
        return self


class SchedulingConfig(BaseModel):
    """Policy for the temporal decision. Assignment is immutable upstream."""

    model_config = ConfigDict(extra="forbid")

    strategy: Literal[
        "service_first",
        "earliest_dispatch",
    ] = "service_first"
    use_delivery_due_dates: bool = True
    planning_window_start: date | None = None
    planning_window_end: date | None = None
    temporal_rules: list[SchedulingTemporalRule] = Field(
        default_factory=list,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_window(self):
        if (
            self.planning_window_start
            and self.planning_window_end
            and self.planning_window_end < self.planning_window_start
        ):
            raise ValueError(
                "La fecha hasta de la ventana de planificación no puede ser anterior a la fecha desde."
            )
        if self.strategy == "earliest_dispatch":
            self.use_delivery_due_dates = False

        ids = set()
        for rule in self.temporal_rules:
            if rule.id in ids:
                raise ValueError(
                    "Cada regla temporal debe tener un identificador único."
                )
            ids.add(rule.id)
            if rule.action != "window":
                continue
            if (
                self.planning_window_start
                and rule.planning_window_start
                and rule.planning_window_start < self.planning_window_start
            ):
                raise ValueError(
                    "La ventana específica de una regla no puede comenzar antes de la ventana global."
                )
            if (
                self.planning_window_end
                and rule.planning_window_end
                and rule.planning_window_end > self.planning_window_end
            ):
                raise ValueError(
                    "La ventana específica de una regla no puede terminar después de la ventana global."
                )
        return self


class SchedulingOptions(BaseModel):
    """Execution budgets for Scheduling."""

    model_config = ConfigDict(extra="forbid")

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
    max_horizon_days: int = Field(
        default=180,
        ge=1,
        le=365,
    )
