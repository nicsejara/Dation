"""Sole authority for Ultimate transit; deliberately independent of v1 helpers."""
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from pydantic import Field

from .base import ContractModel, DecisionDate, ResourceSource, decimal_value

TRANSIT_MODEL_VERSION = "DATION_TRANSIT_V1"
EFFECTIVE_DISTANCE_PER_DAY_KM = 500


class TransitEstimate(ContractModel):
    transit_model_version: Literal["DATION_TRANSIT_V1"] = TRANSIT_MODEL_VERSION
    outbound_days: int = Field(strict=True, ge=1)
    cycle_days: int | None = Field(ge=1)


class TransitDates(ContractModel):
    dispatch: DecisionDate
    arrival: DecisionDate
    available_again: DecisionDate | None


class TransitEstimator:
    version = TRANSIT_MODEL_VERSION

    @staticmethod
    def estimate(distance_km: Decimal | str | int, source: ResourceSource) -> TransitEstimate:
        distance = decimal_value(distance_km)
        if distance <= 0:
            raise ValueError("Transit distance must be positive")
        source = ResourceSource(source)
        numerator, denominator = distance.as_integer_ratio()
        def days(multiplier):
            divisor = denominator * EFFECTIVE_DISTANCE_PER_DAY_KM
            return (numerator * multiplier + divisor - 1) // divisor
        return TransitEstimate(outbound_days=days(1),
                               cycle_days=days(2) if source == ResourceSource.OWN else None)

    @classmethod
    def dates(cls, dispatch: DecisionDate, distance_km, source: ResourceSource) -> TransitDates:
        if type(dispatch) is not date:
            raise ValueError("dispatch must be a DATE")
        estimate = cls.estimate(distance_km, source)
        return TransitDates(dispatch=dispatch, arrival=dispatch + timedelta(days=estimate.outbound_days - 1),
                            available_again=dispatch + timedelta(days=estimate.cycle_days) if estimate.cycle_days is not None else None)
