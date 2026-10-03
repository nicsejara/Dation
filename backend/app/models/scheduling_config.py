from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SchedulingConfig(BaseModel):
    """Policy for the temporal decision. Assignment is immutable upstream."""

    model_config = ConfigDict(extra="forbid")

    strategy: Literal["service_first"] = "service_first"
    use_delivery_due_dates: bool = True


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
        ge=14,
        le=365,
    )
