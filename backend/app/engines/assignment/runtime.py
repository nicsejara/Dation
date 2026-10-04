import csv
import io

from app.models.assignment_config import AssignmentConfig, AssignmentOptions
from app.validators.contracts import CONTRACTS
from app.validators.fleet_schema import validate_fleet_csv
from app.validators.orders_schema import validate_orders_csv

from .engine import run_assignment_engine as _run_assignment_engine
from .scope import apply_order_scope


def _csv_bytes(kind, records):
    columns = [column["name"] for column in CONTRACTS[kind]["columns"]]
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=columns,
        extrasaction="ignore",
        lineterminator="\r\n",
    )
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                column: (
                    ""
                    if record.get(column) is None
                    else record.get(column)
                )
                for column in columns
            }
        )
    return buffer.getvalue().encode("utf-8")


def _resource_records(records, mode):
    if mode == "own":
        return [row for row in records if row.get("ownership") == "own"]
    if mode == "outsourced":
        return [row for row in records if row.get("ownership") == "third_party"]
    return list(records)


def run_assignment_engine(
    orders_bytes,
    fleet_bytes,
    configuration=None,
    options=None,
    inputs=None,
    progress=None,
):
    config = AssignmentConfig.model_validate(configuration or {})
    opts = AssignmentOptions.model_validate(options or {})

    orders_report = validate_orders_csv(orders_bytes)
    fleet_report = validate_fleet_csv(fleet_bytes)
    source_orders = orders_report["records"]
    source_fleet = fleet_report["records"]

    filters = [item.model_dump() for item in config.scope.filters]
    scoped_orders = apply_order_scope(source_orders, filters)
    if not scoped_orders:
        raise ValueError(
            "Los filtros no dejan ninguna orden. Ampliá el alcance antes de ejecutar."
        )

    scoped_fleet = _resource_records(source_fleet, opts.resource_mode)
    if not scoped_fleet:
        if opts.resource_mode == "own":
            detail = "Tu flota no incluye vehículos propios."
        elif opts.resource_mode == "outsourced":
            detail = "Tu flota no incluye vehículos tercerizados."
        else:
            detail = "No hay vehículos disponibles para la política seleccionada."
        raise ValueError(detail)

    canonical_options = opts.model_dump()
    canonical_options["allow_third_party"] = opts.resource_mode != "own"

    result = _run_assignment_engine(
        _csv_bytes("orders", scoped_orders),
        _csv_bytes("fleet", scoped_fleet),
        config.model_dump(),
        canonical_options,
        inputs,
        progress,
    )
    result["scope"] = {
        "filters": filters,
        "counts": {
            "orders_included": len(scoped_orders),
            "orders_total": len(source_orders),
            "vehicles_included": len(scoped_fleet),
            "vehicles_total": len(source_fleet),
        },
    }
    result["resource_policy"] = {
        "mode": opts.resource_mode,
    }
    result.setdefault("inputs", {}).setdefault("orders", {})[
        "source_rows"
    ] = len(source_orders)
    result.setdefault("inputs", {}).setdefault("fleet", {})[
        "source_rows"
    ] = len(source_fleet)
    return result
