from collections import Counter
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
    preview_payload,
)

COLUMNS = [
    column["name"]
    for column in CONTRACTS["orders"]["columns"]
    if column["required"]
]

COMPATIBILITY_READY_DATE = date(2000, 1, 1)
COMPATIBILITY_WINDOW_DAYS = 90


def _parse_optional_date(
    row,
    key,
    problems,
):
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
    for column in CONTRACTS["orders"]["columns"]:
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


def validate_orders_report(contents: bytes, max_problems: int = 100) -> dict:
    problems = ValidationProblems(max_problems)
    rows, columns, delimiter, detected = parse_csv_report(
        contents,
        "orders",
        problems,
    )

    source_completeness = _completeness(columns, rows)

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

            if row.get("origin") and row.get("origin") == row.get("destination"):
                problems.error(
                    "SAME_ORIGIN_DESTINATION",
                    "El destino debe ser distinto del origen.",
                    row=row["_row"],
                    column="destination",
                    hint="Revisá la ciudad de destino.",
                    value=row.get("destination"),
                )

            priority = row.get("priority", "")
            if priority and priority not in ("High", "Normal", "Low"):
                problems.error(
                    "INVALID_OPTION",
                    f"'{priority}' no es una prioridad válida.",
                    row=row["_row"],
                    column="priority",
                    hint="Usá High, Normal o Low.",
                    value=priority,
                )

            estimated = _parse_optional_date(
                row,
                "estimated_dispatch_date",
                problems,
            )
            due = _parse_optional_date(
                row,
                "delivery_due_date",
                problems,
            )
            if estimated and due and due < estimated:
                problems.error(
                    "INVALID_DATE_RANGE",
                    "La fecha objetivo de entrega no puede ser anterior al despacho estimado.",
                    row=row["_row"],
                    column="delivery_due_date",
                    hint="Revisá ambas fechas.",
                    value=row.get("delivery_due_date"),
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
            if estimated is not None:
                row["estimated_dispatch_date"] = estimated.isoformat()
            if due is not None:
                row["delivery_due_date"] = due.isoformat()

            # Compatibility adapter for the existing Dispatch 2.x engine.
            # These fields are internal only and are not part of Orders V3.
            compatibility_ready = estimated or COMPATIBILITY_READY_DATE
            compatibility_due = due or (
                compatibility_ready
                + timedelta(days=COMPATIBILITY_WINDOW_DAYS)
            )
            window = max(
                1,
                min(
                    90,
                    (compatibility_due - compatibility_ready).days,
                ),
            )
            row["priority"] = priority or "Normal"
            row["ready_date"] = compatibility_ready.isoformat()
            row["dispatch_date"] = compatibility_ready.isoformat()
            row["max_delivery_days"] = window
            row["deadline"] = (
                compatibility_ready + timedelta(days=window)
            ).isoformat()

    valid = problems.error_count == 0
    completeness = source_completeness
    profile = None
    suggested_label = None

    if valid and rows:
        order_weights = [
            row["quantity_units"] * row["unit_weight_kg"]
            for row in rows
        ]
        estimated_dates = [
            row.get("estimated_dispatch_date")
            for row in rows
            if row.get("estimated_dispatch_date")
        ]
        priorities = Counter(
            row.get("priority")
            for row in rows
            if row.get("priority")
        )
        profile = {
            "profile_version": 3,
            "orders": len(rows),
            "total_units": sum(row["quantity_units"] for row in rows),
            "total_weight_kg": sum(order_weights),
            "routes": len(
                {
                    (row["origin"], row["destination"])
                    for row in rows
                }
            ),
            "origins": sorted({row["origin"] for row in rows}),
            "destinations": len({row["destination"] for row in rows}),
            "products": len({row["product"] for row in rows}),
            "max_order_kg": max(order_weights),
            "estimated_dispatch_date_range": {
                "from": min(estimated_dates) if estimated_dates else None,
                "to": max(estimated_dates) if estimated_dates else None,
            },
            "priority_mix": dict(sorted(priorities.items())),
        }
        suggested_label = (
            f"Órdenes · {len(rows)} registros"
        )

    return {
        "valid": valid,
        "detected_format": detected,
        "schema": CONTRACTS["orders"]["schema"],
        "rows": len(rows),
        "columns": len(columns),
        "profile": profile,
        "completeness": completeness,
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
        "completeness": report["completeness"],
        "preview": report["preview"],
        "detected": report["detected"],
        "suggested_label": report["suggested_label"],
    }
