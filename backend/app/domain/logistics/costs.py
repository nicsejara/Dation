"""T1 pure price rules, not an optimizer or a result metric producer."""
from decimal import localcontext

from .base import ResourceSource, decimal_value
from .contracts import TransportResource
from .units import CurrencyPolicy, Money


def trip_cost(resource: TransportResource, distance_km, currency: CurrencyPolicy) -> Money | None:
    distance = decimal_value(distance_km)
    if distance <= 0:
        raise ValueError("Distance must be positive")
    with localcontext() as ctx:
        ctx.prec = 60
        if resource.source == ResourceSource.OWN:
            rate = resource.operating_cost_per_km
            amount = None if rate is None else rate * distance * 2
        else:
            cost = resource.external_cost
            amount = cost.rate
            if amount is not None and cost.cost_model == "PER_KM":
                amount *= distance * (2 if cost.billing_basis == "ROUND_TRIP" else 1)
    return None if amount is None else Money(amount=currency.rounded(amount), currency=currency.currency)
