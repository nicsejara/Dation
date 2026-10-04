import csv
import io

from app.models.assignment_config import AssignmentConfig, AssignmentOptions
from app.validators.contracts import CONTRACTS
from app.validators.fleet_schema import validate_fleet_csv
from app.validators.orders_schema import validate_orders_csv

from .engine import run_assignment_engine as _run_assignment_engine
from .scope import apply_order_scope


def _csv_bytes(kind, records, completeness):
    """Serialize only columns that actually existed in the source CSV.

    Validators expose canonical records with compatibility defaults. Keeping only
    source columns avoids manufacturing optional fields that were never supplied.
    Capability completeness is checked separately before the scoped run because
    canonical records intentionally replace some blank optional values with zero.
    """

    columns = [
        column["name"]
        for column in CONTRACTS[kind]["columns"]
        if (completeness or {}).get(column["name"], {}).get("present")
    ]
    if not columns:
        raise ValueError(f"No se pudieron conservar las columnas del archivo {kind}.")

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


def _validate_source_capabilities(config, fleet_report):
    """Keep the original engine's capability semantics before canonical defaults.

    Fleet validation normalizes missing optional numeric values to zero for legacy
    compatibility. That default is useful for non-cost/non-CO₂ runs, but it must not
    make an incomplete source suddenly eligible for a cost or emissions objective.
    """

    completeness = fleet_report.get("completeness", {})

    def complete(column):
        return bool(completeness.get(column, {}).get("complete"))

    unavailable = []
    if "cost" in config.dimensions and not (
        complete("cost_per_km") and complete("fixed_trip_cost")
    ):
        unavailable.append("costo por km y costo fijo")
    if "co2" in config.dimensions and not complete("co2_kg_per_km"):
        unavailable.append("factor de CO₂")
    if unavailable:
        raise ValueError(
            "La configuración usa dimensiones sin datos completos: "
            + ", ".join(unavailable)
            + "."
        )


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
    _validate_source_capabilities(config, fleet_report)

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
        _csv_bytes(
            "orders",
            scoped_orders,
            orders_report.get("completeness"),
        ),
        _csv_bytes(
            "fleet",
            scoped_fleet,
            fleet_report.get("completeness"),
        ),
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
