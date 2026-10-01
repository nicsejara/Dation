from datetime import date, datetime, timedelta

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
    for column in CONTRACTS["orders"]["columns"]
    if column["required"]
]


def validate_orders_report(contents: bytes, max_problems: int = 100) -> dict:
    problems = ValidationProblems(max_problems)
    rows, columns, delimiter, detected = parse_csv_report(
        contents,
        "orders",
        problems,
    )

    if detected != "legacy_mixed":
        duplicate_values(rows, "order_id", problems)

        routes = {}
        products = {}
        for row in rows:
            quantity = parse_number(
                row,
                "quantity_units",
                problems,
                positive=True,
                integer=True,
                delimiter=delimiter,
            )
            window = parse_number(
                row,
                "max_delivery_days",
                problems,
                positive=True,
                integer=True,
                delimiter=delimiter,
            )
            weight = parse_number(
                row,
                "unit_weight_kg",
                problems,
                positive=True,
                delimiter=delimiter,
            )
            distance = parse_number(
                row,
                "distance_km",
                problems,
                positive=True,
                delimiter=delimiter,
            )

            if window is not None and window > 90:
                problems.error(
                    "OUT_OF_RANGE",
                    "El horizonte máximo del MVP es 90 días.",
                    row=row["_row"],
                    column="max_delivery_days",
                    hint="Ingresá un valor entre 1 y 90.",
                    value=window,
                )
                window = None

            if row.get("origin") and row.get("origin") == row.get("destination"):
                problems.error(
                    "SAME_ORIGIN_DESTINATION",
                    "El destino debe ser distinto del origen.",
                    row=row["_row"],
                    column="destination",
                    hint="Revisá la ciudad de destino.",
                    value=row.get("destination"),
                )

            if row.get("priority") and row["priority"] not in ("High", "Normal", "Low"):
                problems.error(
                    "INVALID_OPTION",
                    f"'{row['priority']}' no es una prioridad válida.",
                    row=row["_row"],
                    column="priority",
                    hint="Usá High, Normal o Low.",
                    value=row["priority"],
                )

            parsed_date = None
            raw_date = row.get("dispatch_date", "")
            if raw_date:
                try:
                    parsed_date = (
                        datetime.strptime(raw_date, "%d/%m/%Y").date()
                        if "/" in raw_date
                        else date.fromisoformat(raw_date)
                    )
                except ValueError:
                    problems.error(
                        "INVALID_DATE",
                        f"La fecha '{raw_date}' no es válida.",
                        row=row["_row"],
                        column="dispatch_date",
                        hint="Usá AAAA-MM-DD o d/m/AAAA; el día va primero.",
                        value=raw_date,
                    )

            route = (row.get("origin"), row.get("destination"))
            if route[0] and route[1] and distance is not None:
                if route in routes and routes[route] != distance:
                    problems.error(
                        "INCONSISTENT_ROUTE_DISTANCE",
                        "La distancia es inconsistente para la misma ruta.",
                        row=row["_row"],
                        column="distance_km",
                        hint=f"Usá la misma distancia para {route[0]} → {route[1]}.",
                        value=distance,
                    )
                else:
                    routes[route] = distance

            product = row.get("product")
            if product and weight is not None:
                if product in products and products[product] != weight:
                    problems.warning(
                        "PRODUCT_WEIGHT_VARIATION",
                        f"El producto '{product}' aparece con pesos distintos.",
                        row=row["_row"],
                        column="unit_weight_kg",
                        hint="Confirmá que el peso por unidad sea correcto.",
                        value=weight,
                    )
                products[product] = weight

            if quantity is not None:
                row["quantity_units"] = quantity
            if weight is not None:
                row["unit_weight_kg"] = weight
            if distance is not None:
                row["distance_km"] = distance
            if window is not None:
                row["max_delivery_days"] = window
            if parsed_date is not None and window is not None:
                row["dispatch_date"] = parsed_date.isoformat()
                row["deadline"] = (
                    parsed_date + timedelta(days=window)
                ).isoformat()

    valid = problems.error_count == 0
    profile = None
    if valid and rows:
        route_keys = {
            (row["origin"], row["destination"])
            for row in rows
        }
        profile = {
            "total_units": sum(row["quantity_units"] for row in rows),
            "total_weight_kg": sum(
                row["quantity_units"] * row["unit_weight_kg"]
                for row in rows
            ),
            "routes": len(route_keys),
            "date_from": min(row["dispatch_date"] for row in rows),
            "date_to": max(row["dispatch_date"] for row in rows),
        }

    return {
        "valid": valid,
        "detected_format": detected,
        "schema": "orders_v1",
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


def validate_orders_csv(contents: bytes) -> dict:
    report = validate_orders_report(contents)
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
