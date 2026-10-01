from app.validators.contracts import CONTRACTS
from app.validators.dispatch_common import (
    DispatchValidationError,
    ValidationProblems,
    duplicate_values,
    issue_text,
    parse_csv_report,
    parse_number,
)

COLUMNS = [
    column["name"]
    for column in CONTRACTS["fleet"]["columns"]
]


def validate_fleet_report(contents: bytes, max_problems: int = 100) -> dict:
    problems = ValidationProblems(max_problems)
    rows, columns, delimiter, detected = parse_csv_report(
        contents,
        "fleet",
        problems,
    )

    duplicate_values(rows, "vehicle_type", problems)

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
                    hint="Ingresá cuántos camiones pueden salir por día.",
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

    valid = problems.error_count == 0
    profile = None
    if valid and rows:
        profile = {
            "fleet": rows,
            "own_capacity_kg_per_day": sum(
                row["capacity_kg"] * row["units_available"]
                for row in rows
                if row["ownership"] == "own"
            ),
        }

    return {
        "valid": valid,
        "detected_format": detected,
        "schema": "fleet_v1",
        "rows": len(rows),
        "columns": len(columns),
        "profile": profile,
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
    }
