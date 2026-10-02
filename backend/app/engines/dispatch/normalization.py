"""Pure preparation and cross-file validation; no persistence."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import math
import unicodedata

D = lambda value: Decimal(str(value))


FINDING_COPY = {
    "origin_without_fleet": {
        "severity": "error",
        "consequence": (
            "Agregá capacidad propia o tercerizada disponible desde ese origen."
        ),
    },
    "unit_without_capacity": {
        "severity": "error",
        "consequence": (
            "No existe un vehículo habilitado en ese origen que pueda transportar una unidad entera."
        ),
    },
    "late_orders": {
        "severity": "warning",
        "consequence": (
            "La decisión las entrega igual y las marca como tardías."
        ),
    },
    "capacity_vs_demand": {
        "severity": "warning",
        "consequence": (
            "Es una comparación nominal del día; la optimización además descuenta "
            "unidades que sigan ocupadas por viajes anteriores."
        ),
    },
    "zero_slack": {
        "severity": "info",
        "consequence": "Su salida es el primer día posible.",
    },
    "no_third_party": {
        "severity": "warning",
        "consequence": (
            "Las órdenes que excedan la flota propia pueden quedar sin cobertura."
        ),
    },
    "weight_anomalies": {
        "severity": "warning",
        "consequence": (
            "Vas a decidir qué hacer con estas órdenes en el próximo paso."
        ),
    },
}


def _location_key(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    return "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    ).casefold()


def vehicle_can_serve_origin(order, vehicle):
    base = str(vehicle.get("base_location") or "").strip()
    return (
        base == "*"
        or _location_key(base) == _location_key(order.get("origin"))
    )


def fleet_for_origin(order, fleet):
    return [
        vehicle
        for vehicle in fleet
        if vehicle["units_available"] != 0
        and vehicle_can_serve_origin(order, vehicle)
    ]


def transit(order, vehicle):
    return math.ceil(
        D(order["distance_km"])
        / (
            D(vehicle["avg_speed_kmh"])
            * D(vehicle["driving_hours_per_day"])
        )
    )


def cycle_days(order, vehicle):
    """Calendar days that one finite resource remains occupied, including return."""
    daily_distance = (
        D(vehicle["avg_speed_kmh"])
        * D(vehicle["driving_hours_per_day"])
    )
    return max(
        1,
        math.ceil(
            (D(order["distance_km"]) * D(2))
            / daily_distance
        ),
    )


def resource_available_again(order, vehicle, dispatch_day):
    return (
        date.fromisoformat(dispatch_day)
        + timedelta(days=cycle_days(order, vehicle))
    ).isoformat()


def occupied_dates(order, vehicle, dispatch_day):
    start = date.fromisoformat(dispatch_day)
    return [
        (start + timedelta(days=offset)).isoformat()
        for offset in range(cycle_days(order, vehicle))
    ]


def capacity_units(order, vehicle):
    return int(
        D(vehicle["capacity_kg"])
        // D(order["unit_weight_kg"])
    )


def raw_cost(order, vehicle):
    return (
        2
        * D(order["distance_km"])
        * D(vehicle["cost_per_km"])
        + D(vehicle["fixed_trip_cost"])
    )


def eligible_fleet(order, fleet):
    return [
        vehicle
        for vehicle in fleet_for_origin(order, fleet)
        if capacity_units(order, vehicle)
    ]


def departure_days(order, vehicle, fleet):
    if not vehicle_can_serve_origin(order, vehicle):
        return []
    start = date.fromisoformat(order["dispatch_date"])
    deadline = date.fromisoformat(order["deadline"])
    eligible = eligible_fleet(order, fleet)
    if not eligible:
        return []
    inevitable = all(
        transit(order, candidate) > order["max_delivery_days"]
        for candidate in eligible
    )
    end = (
        start
        if inevitable
        else deadline - timedelta(days=transit(order, vehicle))
    )
    return [
        (start + timedelta(days=index)).isoformat()
        for index in range(max(0, (end - start).days + 1))
    ]


def _finding(identifier, title, items=None):
    copy = FINDING_COPY[identifier]
    return {
        "id": identifier,
        "severity": copy["severity"],
        "title": title,
        "consequence": copy["consequence"],
        "count": len(items or []),
        "items": items or [],
    }


def _capacity_check(orders, fleet):
    own = [
        vehicle
        for vehicle in fleet
        if vehicle["ownership"] == "own"
    ]
    global_legacy = any(
        vehicle.get("base_location") == "*"
        for vehicle in own
    )

    if global_legacy:
        own_capacity = sum(
            D(vehicle["capacity_kg"])
            * D(vehicle["units_available"] or 0)
            for vehicle in own
        )
        by_day = defaultdict(lambda: {"orders": 0, "kg": D(0)})
        for order in orders:
            item = by_day[order["dispatch_date"]]
            item["orders"] += 1
            item["kg"] += (
                D(order["quantity_units"])
                * D(order["unit_weight_kg"])
            )
        days = []
        for current_date, value in sorted(by_day.items()):
            ratio = (
                float(value["kg"] / own_capacity)
                if own_capacity > 0
                else None
            )
            days.append(
                {
                    "date": current_date,
                    "origin": "*",
                    "orders": value["orders"],
                    "kg": float(value["kg"]),
                    "own_capacity_kg": float(own_capacity),
                    "ratio": ratio,
                    "over": own_capacity > 0 and value["kg"] > own_capacity,
                }
            )
        return {
            "basis": "nominal_same_day",
            "scope": "global_legacy",
            "own_capacity_kg_per_day": float(own_capacity),
            "capacity_by_origin": {},
            "days_over": sum(item["over"] for item in days),
            "total_days": len(days),
            "days": days,
        }

    capacity_by_key = defaultdict(Decimal)
    display_by_key = {}
    for vehicle in own:
        key = _location_key(vehicle.get("base_location"))
        display_by_key.setdefault(key, vehicle.get("base_location"))
        capacity_by_key[key] += (
            D(vehicle["capacity_kg"])
            * D(vehicle["units_available"] or 0)
        )

    demand = defaultdict(lambda: {"orders": 0, "kg": D(0), "origin": ""})
    for order in orders:
        key = _location_key(order["origin"])
        item = demand[(order["dispatch_date"], key)]
        item["origin"] = order["origin"]
        item["orders"] += 1
        item["kg"] += (
            D(order["quantity_units"])
            * D(order["unit_weight_kg"])
        )

    days = []
    for (current_date, key), value in sorted(demand.items()):
        own_capacity = capacity_by_key.get(key, D(0))
        ratio = (
            float(value["kg"] / own_capacity)
            if own_capacity > 0
            else None
        )
        days.append(
            {
                "date": current_date,
                "origin": value["origin"],
                "orders": value["orders"],
                "kg": float(value["kg"]),
                "own_capacity_kg": float(own_capacity),
                "ratio": ratio,
                "over": own_capacity > 0 and value["kg"] > own_capacity,
            }
        )

    return {
        "basis": "nominal_same_day",
        "scope": "by_origin",
        "own_capacity_kg_per_day": float(sum(capacity_by_key.values(), D(0))),
        "capacity_by_origin": {
            display_by_key[key]: float(value)
            for key, value in sorted(capacity_by_key.items())
        },
        "days_over": sum(item["over"] for item in days),
        "total_days": len(days),
        "days": days,
    }


def preflight(orders, fleet, reference_fleet=None):
    warnings = []
    errors = []
    anomalies = []
    findings = []

    reference = reference_fleet or fleet
    own_capacities = [
        vehicle["capacity_kg"]
        for vehicle in fleet
        if vehicle["ownership"] == "own"
    ]
    cap = max(
        own_capacities
        or [vehicle["capacity_kg"] for vehicle in fleet]
    )

    if not any(
        vehicle["units_available"] is None
        for vehicle in fleet
    ):
        warnings.append(
            {
                "code": "FINITE_FLEET",
                "detail": (
                    "No hay flota ilimitada; la cobertura depende "
                    "del origen, las fechas y la disponibilidad."
                ),
            }
        )

    late_items = []
    origin_items = []
    capacity_items = []
    zero_slack_items = []

    for order in orders:
        base = {
            "order_id": order["order_id"],
            "row": order.get("_row"),
            "origin": order["origin"],
        }

        available_at_origin = fleet_for_origin(order, fleet)
        if not available_at_origin:
            error = {
                **base,
                "code": "NO_FLEET_AT_ORIGIN",
                "detail": (
                    f"No hay flota habilitada para despachar desde {order['origin']}."
                ),
            }
            errors.append(error)
            origin_items.append(
                {
                    **base,
                    "detail": order["origin"],
                }
            )
            continue

        eligible = [
            vehicle
            for vehicle in available_at_origin
            if capacity_units(order, vehicle)
        ]
        if not eligible:
            error = {
                **base,
                "code": "UNIT_EXCEEDS_CAPACITY",
                "detail": (
                    "No hay un vehículo disponible en este origen que pueda "
                    "transportar una unidad entera."
                ),
            }
            errors.append(error)
            capacity_items.append(base)
            continue

        fastest = min(transit(order, vehicle) for vehicle in eligible)
        if fastest > order["max_delivery_days"]:
            warning = {
                **base,
                "code": "UNAVOIDABLE_LATE",
                "detail": (
                    "La entrega resulta tardía aun con la salida más "
                    "temprana y el vehículo más rápido disponible en el origen."
                ),
            }
            warnings.append(warning)
            late_items.append(
                {
                    **base,
                    "route": (
                        f"{order['origin']} → {order['destination']}"
                    ),
                    "delivery_days": order["max_delivery_days"],
                    "transit_days": fastest,
                    "detail": (
                        f"Tránsito {fastest} días; "
                        f"plazo {order['max_delivery_days']} días."
                    ),
                }
            )
        elif fastest == order["max_delivery_days"]:
            zero_slack_items.append(
                {
                    **base,
                    "route": (
                        f"{order['origin']} → {order['destination']}"
                    ),
                    "detail": "Sin margen para reprogramar la salida.",
                }
            )

        trips = min(
            (
                math.ceil(
                    order["quantity_units"]
                    / capacity_units(order, vehicle)
                )
                for vehicle in eligible
            ),
            default=0,
        )
        if trips > 20:
            warnings.append(
                {
                    **base,
                    "code": "MANY_TRIPS",
                    "detail": (
                        f"La orden requiere al menos {trips} "
                        "viajes independientes."
                    ),
                }
            )

        if (
            D(order["quantity_units"])
            * D(order["unit_weight_kg"])
            > D(cap) * 20
        ):
            anomalies.append(
                {
                    **base,
                    "code": "ORDER_WEIGHT_OUTLIER",
                    "detail": (
                        "La orden supera 20 veces la mayor capacidad "
                        "propia; decidí incluirla o excluirla."
                    ),
                }
            )

    if origin_items:
        findings.append(
            _finding(
                "origin_without_fleet",
                (
                    f"{len(origin_items)} órdenes tienen un origen "
                    "sin flota habilitada"
                ),
                origin_items,
            )
        )

    if capacity_items:
        findings.append(
            _finding(
                "unit_without_capacity",
                (
                    f"{len(capacity_items)} órdenes no tienen "
                    "capacidad suficiente en su origen"
                ),
                capacity_items,
            )
        )

    if late_items:
        findings.append(
            _finding(
                "late_orders",
                (
                    f"{len(late_items)} órdenes llegarán tarde "
                    "aunque salgan el primer día"
                ),
                late_items,
            )
        )

    capacity_check = _capacity_check(orders, reference)
    if capacity_check["days_over"]:
        scope_label = (
            "combinaciones origen/fecha"
            if capacity_check["scope"] == "by_origin"
            else "días"
        )
        findings.append(
            _finding(
                "capacity_vs_demand",
                (
                    "La demanda del día supera la capacidad propia nominal en "
                    f"{capacity_check['days_over']} de "
                    f"{capacity_check['total_days']} {scope_label}"
                ),
                [
                    item
                    for item in capacity_check["days"]
                    if item["over"]
                ],
            )
        )

    if zero_slack_items:
        findings.append(
            _finding(
                "zero_slack",
                (
                    f"{len(zero_slack_items)} órdenes no tienen "
                    "margen para reprogramarse"
                ),
                zero_slack_items,
            )
        )

    has_third_party = any(
        vehicle["ownership"] == "third_party"
        for vehicle in reference
    )
    if not has_third_party:
        findings.append(
            _finding(
                "no_third_party",
                "La flota no incluye vehículos tercerizados",
            )
        )

    if anomalies:
        findings.append(
            _finding(
                "weight_anomalies",
                f"{len(anomalies)} órdenes requieren revisión de peso",
                anomalies,
            )
        )

    blockers = [
        finding["title"]
        for finding in findings
        if finding["severity"] == "error"
    ]
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "anomalies": anomalies,
        "findings": findings,
        "capacity_check": capacity_check,
        "readiness": {
            "can_continue": not blockers,
            "blockers": blockers,
            "reason": blockers[0] if blockers else None,
        },
    }
