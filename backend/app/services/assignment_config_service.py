from app.engines.assignment.preflight import assignment_preflight
from app.engines.assignment.scope import apply_order_scope, scope_preview
from app.services.dispatch_service import load_inputs
from app.validators.fleet_schema import validate_fleet_csv
from app.validators.orders_schema import validate_orders_csv


def _resource_records(records, mode):
    if mode == "own":
        return [row for row in records if row.get("ownership") == "own"]
    if mode == "outsourced":
        return [row for row in records if row.get("ownership") == "third_party"]
    return list(records)


async def preview_assignment_configuration(
    orders_id,
    fleet_id,
    *,
    filters=None,
    resource_mode="mixed",
):
    (
        orders_dataset,
        fleet_dataset,
        orders_bytes,
        fleet_bytes,
    ) = await load_inputs(orders_id, fleet_id)
    orders = validate_orders_csv(orders_bytes)
    fleet = validate_fleet_csv(fleet_bytes)

    filter_payload = filters or []
    scoped_orders = apply_order_scope(orders["records"], filter_payload)
    scoped_fleet = _resource_records(fleet["records"], resource_mode)

    preview = scope_preview(orders, fleet, filter_payload)
    preview["resource_mode"] = resource_mode
    preview["resources"] = {
        "included": len(scoped_fleet),
        "total": len(fleet["records"]),
        "own": sum(row.get("ownership") == "own" for row in fleet["records"]),
        "third_party": sum(
            row.get("ownership") == "third_party" for row in fleet["records"]
        ),
    }
    preview["datasets"] = {
        "orders": {
            "id": orders_dataset["id"],
            "row_count": orders_dataset.get("row_count"),
        },
        "fleet": {
            "id": fleet_dataset["id"],
            "row_count": fleet_dataset.get("row_count"),
        },
    }

    if not scoped_orders:
        preview["valid"] = False
        preview["errors"] = [
            {
                "code": "EMPTY_SCOPE",
                "detail": "Los filtros no dejan ninguna orden. Ampliá el alcance.",
            }
        ]
        preview["anomalies"] = []
        return preview

    if not scoped_fleet:
        preview["valid"] = False
        preview["errors"] = [
            {
                "code": "EMPTY_RESOURCE_POLICY",
                "detail": (
                    "La política de recursos seleccionada no habilita ningún vehículo."
                ),
            }
        ]
        preview["anomalies"] = []
        return preview

    check = assignment_preflight(
        scoped_orders,
        scoped_fleet,
        fleet["records"],
    )
    preview["valid"] = not check["errors"]
    preview["errors"] = check["errors"]
    preview["anomalies"] = check["anomalies"]
    return preview
