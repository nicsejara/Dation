"""Cross-file checks specific to the non-temporal Assignment decision."""

from decimal import Decimal
import math

from app.engines.dispatch.normalization import (
    D,
    capacity_units,
    vehicle_can_serve_origin,
)


def _active(vehicle):
    status = str(
        vehicle.get("status") or "available"
    ).strip()
    return status not in (
        "maintenance",
        "unavailable",
    )


def _eligible(order, fleet):
    return [
        vehicle
        for vehicle in fleet
        if (
            _active(vehicle)
            and vehicle_can_serve_origin(
                order,
                vehicle,
            )
            and capacity_units(
                order,
                vehicle,
            )
            > 0
        )
    ]


def assignment_preflight(
    orders,
    fleet,
    reference_fleet=None,
):
    """Validate only facts required by Assignment.

    Dates, transit time, SLA and temporal occupancy intentionally do not
    participate in this decision.
    """
    errors = []
    warnings = []
    anomalies = []
    findings = []
    reference = reference_fleet or fleet

    origin_items = []
    capacity_items = []
    anomaly_items = []

    for order in orders:
        base = {
            "order_id": order["order_id"],
            "row": order.get("_row"),
            "origin": order["origin"],
        }

        active_at_origin = [
            vehicle
            for vehicle in fleet
            if (
                _active(vehicle)
                and vehicle_can_serve_origin(
                    order,
                    vehicle,
                )
            )
        ]
        if not active_at_origin:
            error = {
                **base,
                "code": "NO_FLEET_AT_ORIGIN",
                "detail": (
                    "No hay flota habilitada para "
                    f"atender el origen {order['origin']}."
                ),
            }
            errors.append(error)
            origin_items.append(error)
            continue

        eligible = _eligible(order, fleet)
        if not eligible:
            error = {
                **base,
                "code": "UNIT_EXCEEDS_CAPACITY",
                "detail": (
                    "Ningún vehículo habilitado en este origen "
                    "puede transportar una unidad completa."
                ),
            }
            errors.append(error)
            capacity_items.append(error)
            continue

        minimum_trips = min(
            math.ceil(
                order["quantity_units"]
                / capacity_units(
                    order,
                    vehicle,
                )
            )
            for vehicle in eligible
        )
        if minimum_trips > 20:
            warning = {
                **base,
                "code": "MANY_TRIPS",
                "detail": (
                    f"La orden requiere al menos "
                    f"{minimum_trips} viajes."
                ),
            }
            warnings.append(warning)

        max_capacity = max(
            D(vehicle["capacity_kg"])
            for vehicle in eligible
        )
        order_kg = (
            D(order["quantity_units"])
            * D(order["unit_weight_kg"])
        )
        if order_kg > max_capacity * Decimal("20"):
            anomaly = {
                **base,
                "code": "ORDER_WEIGHT_OUTLIER",
                "detail": (
                    "La orden supera 20 veces la mayor "
                    "capacidad compatible; decidí incluirla "
                    "o excluirla."
                ),
            }
            anomalies.append(anomaly)
            anomaly_items.append(anomaly)

    if origin_items:
        findings.append(
            {
                "id": "origin_without_fleet",
                "severity": "error",
                "title": (
                    f"{len(origin_items)} órdenes tienen "
                    "un origen sin flota habilitada"
                ),
                "consequence": (
                    "Agregá capacidad propia o tercerizada "
                    "para ese site."
                ),
                "count": len(origin_items),
                "items": origin_items,
            }
        )

    if capacity_items:
        findings.append(
            {
                "id": "unit_without_capacity",
                "severity": "error",
                "title": (
                    f"{len(capacity_items)} órdenes no entran "
                    "en ningún vehículo compatible"
                ),
                "consequence": (
                    "Revisá el peso unitario o incorporá un "
                    "vehículo con mayor capacidad."
                ),
                "count": len(capacity_items),
                "items": capacity_items,
            }
        )

    if anomaly_items:
        findings.append(
            {
                "id": "weight_anomalies",
                "severity": "warning",
                "title": (
                    f"{len(anomaly_items)} órdenes requieren "
                    "una decisión explícita"
                ),
                "consequence": (
                    "Podés incluirlas o excluirlas antes "
                    "de ejecutar Assignment."
                ),
                "count": len(anomaly_items),
                "items": anomaly_items,
            }
        )

    active_reference = [
        vehicle
        for vehicle in reference
        if _active(vehicle)
    ]
    return {
        "valid": not errors,
        "decision": "logistics_assignment",
        "scope": "non_temporal",
        "errors": errors,
        "warnings": warnings,
        "anomalies": anomalies,
        "findings": findings,
        "summary": {
            "orders": len(orders),
            "fleet_rows": len(reference),
            "active_vehicles": len(
                active_reference
            ),
            "origins": len(
                {
                    order["origin"]
                    for order in orders
                }
            ),
        },
    }
