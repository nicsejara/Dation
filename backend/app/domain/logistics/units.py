"""Explicit precision; no FX and no inference from a live workspace."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Literal
from types import MappingProxyType

from pydantic import Field, model_validator

from .base import (ContractModel, Currency, DecimalValue, Dimension, MAX_SCALED_INTEGER,
                   NonNegative, Ratio)

QUANTITY_SCALES = MappingProxyType({Dimension.PALLETS: 3, Dimension.WEIGHT_KG: 3,
                   Dimension.VOLUME_M3: 6, Dimension.UNITS: 3})
RATIO_SCALE = 4
DISTANCE_SCALE = 3
RATE_SCALE = 6


def scaled_integer(value: Decimal, scale: int) -> int:
    if not isinstance(value, Decimal) or not value.is_finite() or not 0 <= scale <= 6:
        raise ValueError("Finite Decimal and scale 0..6 required")
    with localcontext() as ctx:
        ctx.prec = 60
        scaled = value * (10**scale)
    if scaled != scaled.to_integral_value() or scaled.copy_abs() > MAX_SCALED_INTEGER:
        raise ValueError("Precision or signed 64-bit scaled-integer bound exceeded")
    return int(scaled)


class CurrencyPolicy(ContractModel):
    currency: Currency
    minor_units: int = Field(strict=True, ge=0, le=6)
    rounding: Literal["ROUND_HALF_UP"] = "ROUND_HALF_UP"

    def rounded(self, value: Decimal) -> Decimal:
        with localcontext() as ctx:
            ctx.prec = 60
            result = value.quantize(Decimal(1).scaleb(-self.minor_units), rounding=ROUND_HALF_UP)
        scaled_integer(result, self.minor_units)
        return result


class Money(ContractModel):
    amount: NonNegative
    currency: Currency

    def validate_policy(self, policy: CurrencyPolicy):
        if self.currency != policy.currency:
            raise ValueError("A Case has one pinned currency; FX is not supported")
        scaled_integer(self.amount, policy.minor_units)
        return self


class QuantityVector(ContractModel):
    pallets: NonNegative | None = None
    weight_kg: NonNegative | None = None
    volume_m3: NonNegative | None = None
    units: NonNegative | None = None

    @model_validator(mode="after")
    def precision(self):
        if not any(getattr(self, dim) is not None for dim in Dimension):
            raise ValueError("At least one explicit capacity dimension is required")
        for dim, scale in QUANTITY_SCALES.items():
            value = getattr(self, dim)
            if value is not None:
                scaled_integer(value, scale)
        return self

    def require(self, dimensions: tuple[Dimension, ...], *, positive=False):
        for dim in dimensions:
            value = getattr(self, dim)
            if value is None or (positive and value <= 0):
                raise ValueError("Missing/invalid guaranteed quantity for active dimension " + dim)
        return self
