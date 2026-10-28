"""Immutable, bounded primitives for the Ultimate v1 ABI only."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import re
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, WithJsonSchema, PlainSerializer, model_validator

MAX_SCALED_INTEGER = 2**63 - 1
MAX_WIRE_INTEGER = 2**53 - 1
CANONICAL_VERSION = "DATION_CANONICAL_V1"


class FrozenDict(dict):
    def _immutable(self, *args, **kwargs):
        raise TypeError("Ultimate contract maps are immutable")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable
    def __deepcopy__(self, memo):
        return self


def freeze(value):
    if isinstance(value, dict):
        return FrozenDict({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze(item) for item in value)
    return value


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True,
                              revalidate_instances="always", allow_inf_nan=False,
                              serialize_by_alias=True, validate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def exact_numeric_input(cls, value):
        def check(item):
            if isinstance(item, float):
                raise ValueError("Ultimate decimals use exact decimal strings, not binary floats")
            if isinstance(item, dict):
                for key, child in item.items():
                    if isinstance(child, bool) and isinstance(key, str) and (key == 'version' or key.endswith('_version')):
                        raise ValueError("Versions are not booleans")
                    check(child)
            elif isinstance(item, (list, tuple)):
                for child in item:
                    check(child)
        check(value)
        return value

    @model_validator(mode="after")
    def immutable_maps(self):
        for key in type(self).model_fields:
            object.__setattr__(self, key, freeze(getattr(self, key)))
        return self


def decimal_value(value):
    # Decimal strings are the wire ABI; integral JSON input is lossless too.
    # Reject binary floats before they can hide precision loss or non-finites.
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int)):
        raise ValueError("Use a finite decimal string, Decimal or integer")
    if isinstance(value, str) and not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value):
        raise ValueError("Invalid exact decimal grammar")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal") from exc
    if not result.is_finite() or result.copy_abs() > Decimal("1e18"):
        raise ValueError("Decimal must be finite and bounded")
    return result


def decimal_text(value: Decimal) -> str:
    if not value.is_finite() or value.copy_abs() > Decimal('1e18'):
        raise ValueError("Non-finite/out-of-bound canonical decimal")
    if value == 0:
        return '0'
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


DecimalValue = Annotated[Decimal, BeforeValidator(decimal_value),
    PlainSerializer(decimal_text, return_type=str, when_used='json'), WithJsonSchema(
    {"anyOf":[{"type":"string","pattern":r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"},
              {"type":"integer"}], "format":"exact-decimal"}, mode='validation')]
NonNegative = Annotated[DecimalValue, Field(ge=0, decimal_places=6)]
Positive = Annotated[DecimalValue, Field(gt=0, decimal_places=6)]
Ratio = Annotated[DecimalValue, Field(ge=0, le=1, decimal_places=4)]
Count = Annotated[int, Field(strict=True, ge=0, le=MAX_WIRE_INTEGER)]
Identifier = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
SHA256 = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
Currency = Annotated[str, Field(strict=True, pattern=r"^[A-Z]{3}$")]


class ResourceSource(StrEnum):
    OWN = "OWN"
    EXTERNAL = "EXTERNAL"


class Dimension(StrEnum):
    PALLETS = "pallets"
    WEIGHT_KG = "weight_kg"
    VOLUME_M3 = "volume_m3"
    UNITS = "units"


class Priority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EntityType(StrEnum):
    CASE = "CASE"
    ORDER = "ORDER"
    TRIP = "TRIP"
    RESOURCE = "RESOURCE"
    ALTERNATIVE = "ALTERNATIVE"


def date_only(value):
    if isinstance(value, datetime) or not (type(value) is date or isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)):
        raise ValueError("Decision calendar fields require an ISO DATE, not timestamps")
    return value


DecisionDate = Annotated[date, BeforeValidator(date_only)]
