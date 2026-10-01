from collections import Counter
from datetime import date

from app.services.run_service import (
    download_dataset,
    get_dataset,
)
from app.validators.logistics_schema import (
    parse_logistics_csv,
    validate_logistics_csv,
)


def _number(value: str | None) -> float:
    return float(
        str(value or "0")
        .strip()
        .replace(",", ".")
    )


def _date_key(value: str) -> str:
    value = value.strip()

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return value


async def get_dataset_profile(
    dataset_id: str,
) -> dict:
    dataset = await get_dataset(dataset_id)

    if not dataset:
        raise LookupError(
            "No se encontró el dataset solicitado."
        )

    if dataset.get('dataset_type') in ('orders', 'fleet'):
        return {'dataset': dataset, **(dataset.get('profile_json') or {})}

    contents = await download_dataset(dataset)
    validation = validate_logistics_csv(contents)
    parsed = parse_logistics_csv(contents)
    rows = parsed["rows"]

    total_units = sum(
        _number(row.get("quantity_units"))
        for row in rows
    )
    total_weight_kg = sum(
        _number(row.get("quantity_units"))
        * _number(row.get("unit_weight_kg"))
        for row in rows
    )

    origins = {
        (row.get("origin") or "").strip()
        for row in rows
        if (row.get("origin") or "").strip()
    }
    destinations = {
        (row.get("destination") or "").strip()
        for row in rows
        if (row.get("destination") or "").strip()
    }
    vehicle_types = {
        (row.get("vehicle_type") or "").strip()
        for row in rows
        if (row.get("vehicle_type") or "").strip()
    }

    distances = [
        _number(row.get("distance_km"))
        for row in rows
    ]

    dispatch_dates = sorted(
        _date_key(
            (row.get("dispatch_date") or "").strip()
        )
        for row in rows
        if (row.get("dispatch_date") or "").strip()
    )

    priorities = Counter(
        (row.get("priority") or "").strip()
        for row in rows
        if (row.get("priority") or "").strip()
    )

    preview_columns = [
        "shipment_id",
        "product",
        "quantity_units",
        "origin",
        "destination",
        "distance_km",
        "vehicle_type",
        "priority",
        "dispatch_date",
    ]

    preview = [
        {
            column: row.get(column)
            for column in preview_columns
        }
        for row in rows[:5]
    ]

    return {
        "dataset": {
            "id": dataset["id"],
            "created_at": dataset["created_at"],
            "original_filename": dataset[
                "original_filename"
            ],
            "size_bytes": dataset.get(
                "size_bytes"
            ),
            "sha256": dataset.get("sha256"),
            "status": dataset.get("status"),
            "row_count": dataset.get(
                "row_count"
            ),
            "column_count": dataset.get(
                "column_count"
            ),
        },
        "validation": validation,
        "profile": {
            "shipments": len(rows),
            "total_units": int(total_units),
            "total_weight_kg": round(
                total_weight_kg,
                2,
            ),
            "origins": len(origins),
            "destinations": len(
                destinations
            ),
            "vehicle_types": len(
                vehicle_types
            ),
            "average_distance_km": round(
                sum(distances) / len(distances),
                2,
            )
            if distances
            else 0.0,
            "dispatch_date_range": {
                "from": (
                    dispatch_dates[0]
                    if dispatch_dates
                    else None
                ),
                "to": (
                    dispatch_dates[-1]
                    if dispatch_dates
                    else None
                ),
            },
            "priority_distribution": dict(
                sorted(priorities.items())
            ),
        },
        "preview": preview,
    }
