import csv
import io
import math
from collections import defaultdict
from datetime import datetime, timezone


ENGINE_NAME = "logistics-simple-engine"
ENGINE_VERSION = "0.1.0"


def _detect_delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        header = sample.splitlines()[0] if sample.splitlines() else ""
        candidates = {
            ",": header.count(","),
            ";": header.count(";"),
            "\t": header.count("\t"),
            "|": header.count("|"),
        }
        delimiter = max(candidates, key=candidates.get)
        if candidates[delimiter] == 0:
            raise ValueError("Could not detect CSV delimiter.")
        return delimiter


def _read_rows(contents: bytes) -> list[dict]:
    text = contents.decode("utf-8-sig")
    delimiter = _detect_delimiter(text)
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def _number(value: str) -> float:
    return float(str(value).strip().replace(",", "."))


def _vehicle_catalog(rows: list[dict]) -> dict[str, dict]:
    catalog: dict[str, dict] = {}

    for row in rows:
        vehicle_type = row["vehicle_type"].strip()
        specs = {
            "vehicle_type": vehicle_type,
            "capacity_kg": _number(row["vehicle_capacity_kg"]),
            "cost_per_km": _number(row["cost_per_km"]),
            "fixed_trip_cost": _number(row["fixed_trip_cost"]),
        }

        existing = catalog.get(vehicle_type)
        if existing and existing != specs:
            raise ValueError(
                f"Inconsistent specifications found for vehicle_type={vehicle_type!r}."
            )

        catalog[vehicle_type] = specs

    if not catalog:
        raise ValueError("No vehicle types were found in the dataset.")

    return catalog


def _evaluate_shipment(row: dict, vehicle: dict) -> dict:
    quantity = _number(row["quantity_units"])
    unit_weight = _number(row["unit_weight_kg"])
    one_way_distance = _number(row["distance_km"])

    total_weight = quantity * unit_weight
    capacity = vehicle["capacity_kg"]

    if capacity <= 0:
        raise ValueError(
            f"Vehicle {vehicle['vehicle_type']} has a non-positive capacity."
        )

    trips = math.ceil(total_weight / capacity)

    # MVP assumption: every trip includes outbound + return travel.
    total_distance = trips * one_way_distance * 2

    variable_cost = total_distance * vehicle["cost_per_km"]
    fixed_cost = trips * vehicle["fixed_trip_cost"]
    total_cost = variable_cost + fixed_cost

    return {
        "shipment_id": row["shipment_id"].strip(),
        "product": row["product"].strip(),
        "origin": row["origin"].strip(),
        "destination": row["destination"].strip(),
        "vehicle_type": vehicle["vehicle_type"],
        "quantity_units": int(quantity),
        "total_weight_kg": round(total_weight, 2),
        "required_trips": trips,
        "total_distance_km": round(total_distance, 2),
        "variable_cost": round(variable_cost, 2),
        "fixed_cost": round(fixed_cost, 2),
        "total_cost": round(total_cost, 2),
    }


def _aggregate(assignments: list[dict]) -> dict:
    return {
        "shipments": len(assignments),
        "total_units": sum(item["quantity_units"] for item in assignments),
        "total_weight_kg": round(
            sum(item["total_weight_kg"] for item in assignments), 2
        ),
        "total_trips": sum(item["required_trips"] for item in assignments),
        "total_distance_km": round(
            sum(item["total_distance_km"] for item in assignments), 2
        ),
        "total_cost": round(
            sum(item["total_cost"] for item in assignments), 2
        ),
    }


def _delta(candidate: dict, baseline: dict) -> dict:
    def change(current: float, base: float) -> float | None:
        if base == 0:
            return None
        return round(((current - base) / base) * 100, 2)

    return {
        "trips_pct": change(candidate["total_trips"], baseline["total_trips"]),
        "distance_pct": change(
            candidate["total_distance_km"],
            baseline["total_distance_km"],
        ),
        "cost_pct": change(candidate["total_cost"], baseline["total_cost"]),
    }


def run_logistics_engine(contents: bytes, objective: str = "min_cost") -> dict:
    rows = _read_rows(contents)
    if not rows:
        raise ValueError("The dataset contains no shipments.")

    catalog = _vehicle_catalog(rows)

    baseline_assignments = []
    min_cost_assignments = []
    min_trips_assignments = []

    for row in rows:
        current_vehicle = catalog[row["vehicle_type"].strip()]
        baseline_assignments.append(
            _evaluate_shipment(row, current_vehicle)
        )

        alternatives = [
            _evaluate_shipment(row, vehicle)
            for vehicle in catalog.values()
        ]

        min_cost_assignments.append(
            min(
                alternatives,
                key=lambda item: (
                    item["total_cost"],
                    item["required_trips"],
                    item["total_distance_km"],
                ),
            )
        )

        min_trips_assignments.append(
            min(
                alternatives,
                key=lambda item: (
                    item["required_trips"],
                    item["total_distance_km"],
                    item["total_cost"],
                ),
            )
        )

    baseline = _aggregate(baseline_assignments)
    min_cost = _aggregate(min_cost_assignments)
    min_trips = _aggregate(min_trips_assignments)

    scenarios = {
        "baseline": {
            "name": "Current CSV assignment",
            "metrics": baseline,
            "delta_vs_baseline": {
                "trips_pct": 0.0,
                "distance_pct": 0.0,
                "cost_pct": 0.0,
            },
            "assignments": baseline_assignments,
        },
        "min_cost": {
            "name": "Minimum total cost",
            "metrics": min_cost,
            "delta_vs_baseline": _delta(min_cost, baseline),
            "assignments": min_cost_assignments,
        },
        "min_trips": {
            "name": "Minimum trips",
            "metrics": min_trips,
            "delta_vs_baseline": _delta(min_trips, baseline),
            "assignments": min_trips_assignments,
        },
    }

    if objective not in {"min_cost", "min_trips"}:
        raise ValueError("objective must be 'min_cost' or 'min_trips'.")

    return {
        "engine": {
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        },
        "model_assumptions": [
            "Each CSV row is an independent shipment.",
            "All vehicle types observed in the dataset are available for every shipment.",
            "Every trip includes outbound and return travel.",
            "No cross-shipment consolidation is performed in engine v0.1.",
            "Minimum distance is equivalent to minimum trips under these assumptions.",
        ],
        "vehicle_catalog": list(catalog.values()),
        "objective": objective,
        "recommended_scenario": objective,
        "scenarios": scenarios,
    }
