import csv
import io
from collections import defaultdict

from app.validators.contracts import CONTRACTS
from app.validators.dispatch_common import (
    DispatchValidationError,
    ValidationProblems,
    duplicate_values,
    issue_text,
    parse_csv_report,
    parse_number,
)
from app.validators.profile_utils import (
    detected_metadata,
    format_fleet_label,
    preview_payload,
)

COLUMNS = [
    column["name"]
    for column in CONTRACTS["fleet"]["columns"]
]

LEGACY_FLEET_COLUMNS = [
    "vehicle_type",
    "ownership",
    "capacity_kg",
    "cost_per_km",
    "fixed_trip_cost",
    "units_available",
    "avg_speed_kmh",
    "driving_hours_per_day",
    "fuel_l_per_100km",
    "co2_kg_per_km",
]


def _upgrade_legacy_fleet(contents: bytes) -> tuple[bytes, bool, int]:
    """Adapt fleet_v1 only in memory so historical datasets remain executable."""
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contents, False, 0
    lines = text.splitlines()
    if not lines:
        return contents, False, 0
    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    raw_columns = [str(value).strip() for value in (reader.fieldnames or [])]
    if "fleet_pool_id" in raw_columns or "base_location" in raw_columns:
        return contents, False, len(raw_columns)
    if not set(LEGACY_FLEET_COLUMNS).issubset(raw_columns):
        return contents, False, len(raw_columns)

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=COLUMNS,
        delimiter=delimiter,
        lineterminator="\r\n",
    )
    writer.writeheader()
    for raw in reader:
        row = {
            str(key).strip(): ("" if value is None else str(value).strip())
            for key, value in raw.items()
            if key is not None
        }
        vehicle_type = row.get("vehicle_type", "")
        upgraded = {
            "fleet_pool_id": f"LEGACY-{vehicle_type}",
            "vehicle_type": vehicle_type,
            "ownership": row.get("ownership", ""),
            "base_location": "*",
            **{
                key: row.get(key, "")
                for key in LEGACY_FLEET_COLUMNS
                if key not in {"vehicle_type", "ownership"}
            },
        }
        writer.writerow(upgraded)
    return buffer.getvalue().encode("utf-8"), True, len(raw_columns)


def validate_fleet_report(contents: bytes, max_problems: int = 100) -> dict:
    normalized_contents, legacy_v1, raw_column_count = _upgrade_legacy_fleet(contents)
    problems = ValidationProblems(max_problems)
    rows, columns, delimiter, detected = parse_csv_report(
        normalized_contents,
        "fleet",
        problems,
    )

    if legacy_v1:
        detected = "fleet_v1"
        problems.warning(
            "LEGACY_FLEET_GLOBAL_SCOPE",
            (
                "Esta flota no informa base operativa. Por compatibilidad se "
                "considera disponible desde cualquier origen."
            ),
            row=1,
            hint=(
                "Cargá una versión fleet_v2 con fleet_pool_id y base_location "
                "para que la decisión respete la ubicación real de la flota."
            ),
        )

    duplicate_values(rows, "fleet_pool_id", problems)

    for row in rows:
        ownership = row.get("ownership")
        if ownership and ownership not in ("own", "third_party"):
            problems.error(
                "INVALID_OPTION",
                f"'{ownership}' no es un tipo de propiedad válido.",
                row=row["_row"],
                column="ownership",
                hint="Usá own para propio o third_party para tercerizado.",
                value=ownership,
            )

        base_location = row.get("base_location", "")
        if base_location == "*" and ownership == "own" and not legacy_v1:
            problems.error(
                "INVALID_BASE_LOCATION",
                "La flota propia debe indicar una base operativa concreta.",
                row=row["_row"],
                column="base_location",
                hint="Indicá el origen real del pool, por ejemplo Cordoba.",
                value=base_location,
            )

        capacity = parse_number(
            row,
            "capacity_kg",
            problems,
            positive=True,
            delimiter=delimiter,
        )
        cost = parse_number(
            row,
            "cost_per_km",
            problems,
            delimiter=delimiter,
        )
        fixed = parse_number(
            row,
            "fixed_trip_cost",
            problems,
            delimiter=delimiter,
        )
        speed = parse_number(
            row,
            "avg_speed_kmh",
            problems,
            positive=True,
            delimiter=delimiter,
        )
        driving = parse_number(
            row,
            "driving_hours_per_day",
            problems,
            minimum=1,
            delimiter=delimiter,
        )
        fuel = parse_number(
            row,
            "fuel_l_per_100km",
            problems,
            delimiter=delimiter,
        )
        co2 = parse_number(
            row,
            "co2_kg_per_km",
            problems,
            delimiter=delimiter,
        )

        if driving is not None and driving > 24:
            problems.error(
                "OUT_OF_RANGE",
                "Las horas de conducción no pueden superar 24.",
                row=row["_row"],
                column="driving_hours_per_day",
                hint="Ingresá un valor entre 1 y 24.",
                value=driving,
            )
            driving = None

        raw_units = row.get("units_available", "")
        if raw_units == "":
            if ownership == "own":
                problems.error(
                    "REQUIRED_EMPTY",
                    "La flota propia requiere disponibilidad.",
                    row=row["_row"],
                    column="units_available",
                    hint="Ingresá cuántos vehículos pertenecen a este pool.",
                )
                units = None
            else:
                units = None
        else:
            units = parse_number(
                row,
                "units_available",
                problems,
                integer=True,
                delimiter=delimiter,
            )

        parsed = {
            "capacity_kg": capacity,
            "cost_per_km": cost,
            "fixed_trip_cost": fixed,
            "avg_speed_kmh": speed,
            "driving_hours_per_day": driving,
            "fuel_l_per_100km": fuel,
            "co2_kg_per_km": co2,
            "units_available": units,
        }
        for key, value in parsed.items():
            if value is not None or key == "units_available":
                row[key] = value
        row["legacy_global_scope"] = bool(legacy_v1)

    valid = problems.error_count == 0
    profile = None
    suggested_label = None
    if valid and rows:
        own = [row for row in rows if row["ownership"] == "own"]
        by_base = defaultdict(lambda: {"units": 0, "capacity_kg_per_day": 0.0})
        for row in own:
            base = row["base_location"]
            units = row["units_available"] or 0
            by_base[base]["units"] += units
            by_base[base]["capacity_kg_per_day"] += row["capacity_kg"] * units

        profile = {
            "profile_version": 3,
            "fleet": rows,
            "pools": len(rows),
            "types": len({row["vehicle_type"] for row in rows}),
            "bases": sorted(
                {
                    row["base_location"]
                    for row in rows
                    if row["base_location"] != "*"
                }
            ),
            "spatially_scoped": not legacy_v1,
            "global_scope_pools": sum(
                row["base_location"] == "*"
                for row in rows
            ),
            "own_units_per_day": sum(
                row["units_available"] or 0
                for row in own
            ),
            "own_capacity_kg_per_day": sum(
                row["capacity_kg"] * (row["units_available"] or 0)
                for row in own
            ),
            "capacity_by_base": {
                key: value
                for key, value in sorted(by_base.items())
            },
            "has_third_party": any(
                row["ownership"] == "third_party"
                for row in rows
            ),
        }
        suggested_label = format_fleet_label()

    metadata = detected_metadata(
        contents,
        "fleet",
        columns,
    )
    if legacy_v1:
        metadata["aliases"].extend(
            [
                {"from": "(ausente)", "to": "fleet_pool_id"},
                {"from": "(ausente)", "to": "base_location"},
            ]
        )
        metadata["columns"] = raw_column_count

    return {
        "valid": valid,
        "detected_format": detected,
        "schema": "fleet_v1" if legacy_v1 else CONTRACTS["fleet"]["schema"],
        "rows": len(rows),
        "columns": raw_column_count if legacy_v1 else len(columns),
        "profile": profile,
        "preview": preview_payload(columns, rows),
        "detected": metadata,
        "suggested_label": suggested_label,
        "errors": problems.errors,
        "warnings": problems.warnings,
        "counts": {
            "errors": problems.error_count,
            "warnings": problems.warning_count,
        },
        "truncated": problems.truncated,
        "records": rows,
    }


def validate_fleet_csv(contents: bytes) -> dict:
    report = validate_fleet_report(contents)
    if report["errors"]:
        raise DispatchValidationError(issue_text(report["errors"][0]))
    return {
        "schema": report["schema"],
        "rows": report["rows"],
        "columns": report["columns"],
        "warnings": [
            {
                **warning,
                "detail": warning["message"],
            }
            for warning in report["warnings"]
        ],
        "records": report["records"],
        "profile": report["profile"],
        "preview": report["preview"],
        "detected": report["detected"],
        "suggested_label": report["suggested_label"],
    }
