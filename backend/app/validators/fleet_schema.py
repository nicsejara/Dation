import csv
import io
from collections import Counter
from datetime import date, datetime

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
    preview_payload,
)

COLUMNS = [
    column["name"]
    for column in CONTRACTS["fleet"]["columns"]
]

LEGACY_POOL_COLUMNS = {
    "fleet_pool_id",
    "vehicle_type",
    "ownership",
    "base_location",
    "capacity_kg",
    "cost_per_km",
    "fixed_trip_cost",
    "units_available",
    "avg_speed_kmh",
    "driving_hours_per_day",
    "fuel_l_per_100km",
    "co2_kg_per_km",
}


def _upgrade_legacy_pool_fleet(contents: bytes) -> tuple[bytes, bool, int]:
    """Expand historical pool rows into unit-level rows in memory."""
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

    if "vehicle_id" in raw_columns:
        return contents, False, len(raw_columns)
    if not LEGACY_POOL_COLUMNS.issubset(set(raw_columns)):
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
        try:
            requested_units = int(row.get("units_available") or "1")
        except ValueError:
            requested_units = 1
        units = max(1, requested_units)
        pool_id = row.get("fleet_pool_id") or row.get("vehicle_type") or "FLEET"

        for index in range(1, units + 1):
            writer.writerow(
                {
                    "vehicle_id": f"LEGACY-{pool_id}-{index:02d}",
                    "license_plate": "",
                    "vehicle_type": row.get("vehicle_type", ""),
                    "ownership": row.get("ownership", ""),
                    "provider_name": "",
                    "base_site": row.get("base_location", ""),
                    "capacity_kg": row.get("capacity_kg", ""),
                    "capacity_m3": "",
                    "cost_per_km": row.get("cost_per_km", ""),
                    "fixed_trip_cost": row.get("fixed_trip_cost", ""),
                    "fuel_l_per_100km": row.get("fuel_l_per_100km", ""),
                    "co2_kg_per_km": row.get("co2_kg_per_km", ""),
                    "avg_speed_kmh": row.get("avg_speed_kmh", ""),
                    "driving_hours_per_day": row.get("driving_hours_per_day", ""),
                    "status": "available",
                    "available_from": "",
                    "available_until": "",
                }
            )

    return buffer.getvalue().encode("utf-8"), True, len(raw_columns)


def _parse_optional_date(row, key, problems):
    raw = row.get(key, "")
    if not raw:
        return None
    try:
        return (
            datetime.strptime(raw, "%d/%m/%Y").date()
            if "/" in raw
            else date.fromisoformat(raw)
        )
    except ValueError:
        problems.error(
            "INVALID_DATE",
            f"La fecha '{raw}' no es válida.",
            row=row["_row"],
            column=key,
            hint="Usá AAAA-MM-DD o d/m/AAAA; el día va primero.",
            value=raw,
        )
        return None


def _completeness(columns, rows):
    result = {}
    for column in CONTRACTS["fleet"]["columns"]:
        name = column["name"]
        filled = sum(bool(row.get(name, "")) for row in rows)
        result[name] = {
            "present": name in columns,
            "filled_rows": filled,
            "total_rows": len(rows),
            "complete": bool(rows) and filled == len(rows),
            "required": bool(column["required"]),
            "used_by": column.get("used_by", []),
            "unlock_label": column.get("unlock_label"),
        }
    return result


def validate_fleet_report(contents: bytes, max_problems: int = 100) -> dict:
    normalized_contents, legacy_pool, raw_column_count = _upgrade_legacy_pool_fleet(
        contents
    )
    problems = ValidationProblems(max_problems)
    rows, columns, delimiter, detected = parse_csv_report(
        normalized_contents,
        "fleet",
        problems,
    )

    if legacy_pool:
        detected = "fleet_v2_legacy"
        problems.warning(
            "LEGACY_FLEET_POOL_FORMAT",
            (
                "Esta flota usa el formato anterior por grupos. "
                "Dation la adaptó temporalmente a vehículos individuales."
            ),
            row=1,
            hint="Para nuevas cargas usá Fleet V3: una fila por camión real.",
        )

    duplicate_values(rows, "vehicle_id", problems)

    seen_plates = {}
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

        base_site = row.get("base_site", "")
        if base_site == "*" and ownership == "own" and not legacy_pool:
            problems.error(
                "INVALID_BASE_SITE",
                "La flota propia debe indicar un site concreto.",
                row=row["_row"],
                column="base_site",
                hint="Por ejemplo: Cordoba.",
                value=base_site,
            )

        plate = row.get("license_plate", "")
        if plate:
            key = plate.replace(" ", "").upper()
            if key in seen_plates:
                problems.error(
                    "DUPLICATE_LICENSE_PLATE",
                    f"La patente '{plate}' está repetida.",
                    row=row["_row"],
                    column="license_plate",
                    hint=f"Ya aparece en la fila {seen_plates[key]}.",
                    value=plate,
                )
            else:
                seen_plates[key] = row["_row"]

        capacity = parse_number(
            row,
            "capacity_kg",
            problems,
            positive=True,
            delimiter=delimiter,
        )
        capacity_m3 = parse_number(
            row,
            "capacity_m3",
            problems,
            positive=True,
            allow_empty=True,
            delimiter=delimiter,
        )
        cost = parse_number(
            row,
            "cost_per_km",
            problems,
            allow_empty=True,
            delimiter=delimiter,
        )
        fixed = parse_number(
            row,
            "fixed_trip_cost",
            problems,
            allow_empty=True,
            delimiter=delimiter,
        )
        fuel = parse_number(
            row,
            "fuel_l_per_100km",
            problems,
            allow_empty=True,
            delimiter=delimiter,
        )
        co2 = parse_number(
            row,
            "co2_kg_per_km",
            problems,
            allow_empty=True,
            delimiter=delimiter,
        )
        speed = parse_number(
            row,
            "avg_speed_kmh",
            problems,
            positive=True,
            allow_empty=True,
            delimiter=delimiter,
        )
        driving = parse_number(
            row,
            "driving_hours_per_day",
            problems,
            minimum=1,
            allow_empty=True,
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

        status = row.get("status", "")
        if status and status not in ("available", "maintenance", "unavailable"):
            problems.error(
                "INVALID_OPTION",
                f"'{status}' no es un estado válido.",
                row=row["_row"],
                column="status",
                hint="Usá available, maintenance o unavailable.",
                value=status,
            )

        available_from = _parse_optional_date(row, "available_from", problems)
        available_until = _parse_optional_date(row, "available_until", problems)
        if (
            available_from
            and available_until
            and available_until < available_from
        ):
            problems.error(
                "INVALID_DATE_RANGE",
                "available_until no puede ser anterior a available_from.",
                row=row["_row"],
                column="available_until",
                hint="Revisá el rango de disponibilidad.",
                value=row.get("available_until"),
            )

        parsed = {
            "capacity_kg": capacity,
            "capacity_m3": capacity_m3,
            "cost_per_km": cost,
            "fixed_trip_cost": fixed,
            "fuel_l_per_100km": fuel,
            "co2_kg_per_km": co2,
            "avg_speed_kmh": speed,
            "driving_hours_per_day": driving,
        }
        for key, value in parsed.items():
            if value is not None:
                row[key] = value

        if available_from:
            row["available_from"] = available_from.isoformat()
        if available_until:
            row["available_until"] = available_until.isoformat()

        # Compatibility adapter for Dispatch 2.x. The user-facing contract has
        # no pools; each physical vehicle is temporarily exposed as one finite
        # internal resource until Assignment and Scheduling are split.
        row["fleet_pool_id"] = row["vehicle_id"]
        row["base_location"] = row["base_site"]
        row["units_available"] = (
            0 if status in ("maintenance", "unavailable") else 1
        )
        row["avg_speed_kmh"] = speed if speed is not None else 70.0
        row["driving_hours_per_day"] = (
            driving if driving is not None else 10.0
        )
        row["cost_per_km"] = cost if cost is not None else 0.0
        row["fixed_trip_cost"] = fixed if fixed is not None else 0.0
        row["fuel_l_per_100km"] = fuel if fuel is not None else 0.0
        row["co2_kg_per_km"] = co2 if co2 is not None else 0.0
        row["legacy_global_scope"] = bool(legacy_pool)

    valid = problems.error_count == 0
    completeness = _completeness(columns, rows)
    profile = None
    suggested_label = None

    if valid and rows:
        ownership_mix = Counter(row["ownership"] for row in rows)
        sites = sorted(
            {
                row["base_site"]
                for row in rows
                if row.get("base_site") and row["base_site"] != "*"
            }
        )
        profile = {
            "profile_version": 4,
            "fleet": rows,
            "vehicles": len(rows),
            "own_vehicles": ownership_mix.get("own", 0),
            "third_party_vehicles": ownership_mix.get("third_party", 0),
            "types": len({row["vehicle_type"] for row in rows}),
            "sites": sites,
            "available_now": sum(
                row.get("status", "available") in ("", "available")
                for row in rows
            ),
            "total_capacity_kg": sum(row["capacity_kg"] for row in rows),
            "has_third_party": ownership_mix.get("third_party", 0) > 0,
        }
        suggested_label = f"Flota · {len(rows)} vehículos"

    metadata = detected_metadata(
        contents,
        "fleet",
        columns,
    )
    metadata["source_format"] = "fleet_v2_legacy" if legacy_pool else "fleet_v3"

    return {
        "valid": valid,
        "detected_format": detected,
        "schema": "fleet_v2" if legacy_pool else CONTRACTS["fleet"]["schema"],
        "rows": len(rows),
        "columns": raw_column_count if legacy_pool else len(columns),
        "profile": profile,
        "completeness": completeness,
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
        "completeness": report["completeness"],
        "preview": report["preview"],
        "detected": report["detected"],
        "suggested_label": report["suggested_label"],
    }
