"""Explicit converter from the historical mixed CSV to Orders V3."""
import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

COLUMNS = [
    "order_id",
    "product",
    "quantity_units",
    "unit_weight_kg",
    "origin",
    "destination",
    "distance_km",
    "estimated_dispatch_date",
    "priority",
    "delivery_due_date",
]


def convert(source: Path, target: Path):
    text = source.read_text(encoding="utf-8-sig")
    delimiter = ";" if ";" in text.splitlines()[0] else ","
    rows = list(csv.DictReader(text.splitlines(), delimiter=delimiter))
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=COLUMNS,
            delimiter=";",
        )
        writer.writeheader()

        for row in rows:
            dispatch = date.fromisoformat(row["dispatch_date"])
            delivery_days = int(row["max_delivery_days"])
            writer.writerow(
                {
                    "order_id": row["shipment_id"],
                    "product": row["product"],
                    "quantity_units": row["quantity_units"],
                    "unit_weight_kg": row["unit_weight_kg"],
                    "origin": row["origin"],
                    "destination": row["destination"],
                    "distance_km": row["distance_km"],
                    "estimated_dispatch_date": dispatch.isoformat(),
                    "priority": row["priority"],
                    "delivery_due_date": (
                        dispatch + timedelta(days=delivery_days)
                    ).isoformat(),
                }
            )

    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(f"{convert(args.source, args.target)} órdenes convertidas.")
