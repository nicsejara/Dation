from collections import Counter, defaultdict
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
from app.validators.profile_utils import (
    detected_metadata,
    format_orders_label,
    preview_payload,
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
            # Historical assignment columns are accepted only for upload
            # compatibility. They never reach the decision engine.
            row.pop("current_vehicle_type", None)
            row.pop("vehicle_type", None)

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

            if row.get("priority") and row["priority"] not in (
                "High",
                "Normal",
                "Low",
            ):
                problems.error(
                    "INVALID_OPTION",
                    f"'{row['priority']}' no es una prioridad válida.",
                    row=row["_row"],
                    column="priority",
                    hint="Usá High, Normal o Low.",
                    value=row["priority"],
                )

            parsed_date = None
            raw_date = row.get("ready_date", "")
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
                        column="ready_date",
                        hint="Usá AAAA-MM-DD o d/m/AAAA; el día va primero.",
                        value=raw_date,
                    )

            route = (row.get("origin"), row.get("destination"))
            if route[0] and route[1] and distance is not None:
                if route in routes and routes[route] != distance:
                    problems.error(
                        "INCONSISTENT_ROUTE_DISTANCE",
                        "distancia inconsistente para la misma ruta.",
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
                row["ready_date"] = parsed_date.isoformat()
                # Internal compatibility for Dispatch Engine 1.x. The public
                # input contract no longer asks the user for a dispatch date:
                # the engine receives the availability date under its legacy
                # internal key until the temporal V2 solver replaces it.
                row["dispatch_date"] = row["ready_date"]
                row["deadline"] = (
                    parsed_date + timedelta(days=window)
                ).isoformat()

    valid = problems.error_count == 0
    profile = None
    suggested_label = None
    if valid and rows:
        route_keys = {
            (row["origin"], row["destination"])
            for row in rows
        }
        priority_mix = Counter(row["priority"] for row in rows)
        daily = defaultdict(lambda: {"orders": 0, "kg": 0.0})
        order_weights = []
        delivery_days = []

        for row in rows:
            order_kg = row["quantity_units"] * row["unit_weight_kg"]
            order_weights.append(order_kg)
            delivery_days.append(row["max_delivery_days"])
            item = daily[row["ready_date"]]
            item["orders"] += 1
            item["kg"] += order_kg

        date_from = min(row["ready_date"] for row in rows)
        date_to = max(row["ready_date"] for row in rows)
        profile = {
            "profile_version": 2,
            "total_units": sum(row["quantity_units"] for row in rows),
            "total_weight_kg": sum(order_weights),
            "routes": len(route_keys),
            "origins": len({row["origin"] for row in rows}),
            "destinations": len({row["destination"] for row in rows}),
            "date_from": date_from,
            "date_to": date_to,
            "max_order_kg": max(order_weights),
            "priority_mix": {
                key: priority_mix.get(key, 0)
                for key in ("High", "Normal", "Low")
            },
            "delivery_days": {
                "min": min(delivery_days),
                "max": max(delivery_days),
            },
            "daily": [
                {
                    "date": key,
                    "orders": value["orders"],
                    "kg": value["kg"],
                }
                for key, value in sorted(daily.items())
            ],
        }
        suggested_label = format_orders_label(date_from, date_to)

    return {
        "valid": valid,
        "detected_format": detected,
        "schema": CONTRACTS["orders"]["schema"],
        "rows": len(rows),
        "columns": len(columns),
        "profile": profile,
        "preview": preview_payload(columns, rows),
        "detected": detected_metadata(contents, "orders", columns),
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
        "preview": report["preview"],
        "detected": report["detected"],
        "suggested_label": report["suggested_label"],
    }
