from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
