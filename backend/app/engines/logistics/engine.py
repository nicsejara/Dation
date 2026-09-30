import csv
import io
import math
from datetime import datetime, timezone


ENGINE_NAME = "logistics-simple-engine"
ENGINE_VERSION = "0.2.0"


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
            raise ValueError(
                "No se pudo detectar el separador del archivo CSV."
            )

        return delimiter


def _read_rows(contents: bytes) -> list[dict]:
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "El archivo CSV debe utilizar codificación UTF-8."
        ) from exc

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
                "Se encontraron especificaciones inconsistentes para "
                f"vehicle_type={vehicle_type!r}."
            )

        catalog[vehicle_type] = specs

    if not catalog:
        raise ValueError(
            "No se encontraron tipos de vehículo en el dataset."
        )

    return catalog


def _evaluate_shipment(row: dict, vehicle: dict) -> dict:
    quantity = _number(row["quantity_units"])
    unit_weight = _number(row["unit_weight_kg"])
    one_way_distance = _number(row["distance_km"])

    total_weight = quantity * unit_weight
    capacity = vehicle["capacity_kg"]

    if capacity <= 0:
        raise ValueError(
            f"El vehículo {vehicle['vehicle_type']} tiene capacidad inválida."
        )

    trips = math.ceil(total_weight / capacity)

    # Supuesto MVP: cada viaje contempla ida y regreso.
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
        "total_units": sum(
            item["quantity_units"] for item in assignments
        ),
        "total_weight_kg": round(
            sum(item["total_weight_kg"] for item in assignments),
            2,
        ),
        "total_trips": sum(
            item["required_trips"] for item in assignments
        ),
        "total_distance_km": round(
            sum(item["total_distance_km"] for item in assignments),
            2,
        ),
        "total_cost": round(
            sum(item["total_cost"] for item in assignments),
            2,
        ),
    }


def _delta(candidate: dict, baseline: dict) -> dict:
    def change(current: float, base: float) -> float | None:
        if base == 0:
            return None
        return round(((current - base) / base) * 100, 2)

    return {
        "trips_pct": change(
            candidate["total_trips"],
            baseline["total_trips"],
        ),
        "distance_pct": change(
            candidate["total_distance_km"],
            baseline["total_distance_km"],
        ),
        "cost_pct": change(
            candidate["total_cost"],
            baseline["total_cost"],
        ),
    }


def _select_min_cost(alternatives: list[dict]) -> dict:
    return min(
        alternatives,
        key=lambda item: (
            item["total_cost"],
            item["required_trips"],
            item["total_distance_km"],
            item["vehicle_type"],
        ),
    )


def _select_min_trips(alternatives: list[dict]) -> dict:
    return min(
        alternatives,
        key=lambda item: (
            item["required_trips"],
            item["total_distance_km"],
            item["total_cost"],
            item["vehicle_type"],
        ),
    )


def _normalize_metric(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    if maximum == minimum:
        return 0.0

    return (value - minimum) / (maximum - minimum)


def _score_alternatives(
    alternatives: list[dict],
    *,
    cost_weight: float,
    trips_weight: float,
) -> list[dict]:
    costs = [item["total_cost"] for item in alternatives]
    trips = [item["required_trips"] for item in alternatives]

    min_cost = min(costs)
    max_cost = max(costs)
    min_trips = min(trips)
    max_trips = max(trips)

    scored = []

    for item in alternatives:
        normalized_cost = _normalize_metric(
            item["total_cost"],
            min_cost,
            max_cost,
        )
        normalized_trips = _normalize_metric(
            item["required_trips"],
            min_trips,
            max_trips,
        )

        cost_component = cost_weight * normalized_cost
        trips_component = trips_weight * normalized_trips
        score = cost_component + trips_component

        scored.append(
            {
                **item,
                "normalized_cost": round(normalized_cost, 6),
                "normalized_trips": round(normalized_trips, 6),
                "decision_score": round(score, 6),
                "score_components": {
                    "cost": round(cost_component, 6),
                    "trips": round(trips_component, 6),
                },
                "weights": {
                    "cost": cost_weight,
                    "trips": trips_weight,
                },
            }
        )

    return scored


def _with_score_metadata(
    selected: dict,
    scored: list[dict],
) -> dict:
    match = next(
        item
        for item in scored
        if item["vehicle_type"] == selected["vehicle_type"]
    )
    return match


def _select_custom(
    alternatives: list[dict],
    *,
    cost_weight: float,
    trips_weight: float,
) -> dict:
    scored = _score_alternatives(
        alternatives,
        cost_weight=cost_weight,
        trips_weight=trips_weight,
    )

    if math.isclose(cost_weight, 1.0, abs_tol=1e-9):
        return _with_score_metadata(
            _select_min_cost(alternatives),
            scored,
        )

    if math.isclose(trips_weight, 1.0, abs_tol=1e-9):
        return _with_score_metadata(
            _select_min_trips(alternatives),
            scored,
        )

    if cost_weight >= trips_weight:
        tie_breaker = lambda item: (
            item["decision_score"],
            item["total_cost"],
            item["required_trips"],
            item["total_distance_km"],
            item["vehicle_type"],
        )
    else:
        tie_breaker = lambda item: (
            item["decision_score"],
            item["required_trips"],
            item["total_cost"],
            item["total_distance_km"],
            item["vehicle_type"],
        )

    return min(scored, key=tie_breaker)


def _canonical_configuration(
    *,
    objective: str | None = None,
    configuration: dict | None = None,
) -> dict:
    if configuration:
        mode = configuration.get("mode", "preset")
        configured_objective = configuration.get(
            "objective",
            objective or "min_cost",
        )
        weights = configuration.get("weights") or {}
    else:
        mode = "preset"
        configured_objective = objective or "min_cost"
        weights = {}

    if mode == "preset":
        if configured_objective == "min_trips":
            return {
                "mode": "preset",
                "objective": "min_trips",
                "weights": {"cost": 0.0, "trips": 1.0},
            }

        if configured_objective != "min_cost":
            raise ValueError(
                "El modo predefinido admite min_cost o min_trips."
            )

        return {
            "mode": "preset",
            "objective": "min_cost",
            "weights": {"cost": 1.0, "trips": 0.0},
        }

    if mode != "custom" or configured_objective != "custom":
        raise ValueError(
            "La configuración personalizada debe usar mode='custom' "
            "y objective='custom'."
        )

    try:
        cost_weight = float(weights["cost"])
        trips_weight = float(weights["trips"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "La configuración personalizada requiere pesos numéricos "
            "para costo y viajes."
        ) from exc

    if not (0.0 <= cost_weight <= 1.0):
        raise ValueError(
            "El peso de costo debe estar entre 0 y 1."
        )

    if not (0.0 <= trips_weight <= 1.0):
        raise ValueError(
            "El peso de viajes debe estar entre 0 y 1."
        )

    if not math.isclose(
        cost_weight + trips_weight,
        1.0,
        abs_tol=1e-6,
    ):
        raise ValueError(
            "Los pesos de costo y viajes deben sumar 1."
        )

    return {
        "mode": "custom",
        "objective": "custom",
        "weights": {
            "cost": round(cost_weight, 6),
            "trips": round(trips_weight, 6),
        },
    }


def _assignment_signature(assignments: list[dict]) -> list[tuple[str, str]]:
    return sorted(
        (
            item["shipment_id"],
            item["vehicle_type"],
        )
        for item in assignments
    )


def _assignment_difference_count(
    first: list[dict],
    second: list[dict],
) -> int:
    first_map = {
        item["shipment_id"]: item["vehicle_type"]
        for item in first
    }
    second_map = {
        item["shipment_id"]: item["vehicle_type"]
        for item in second
    }

    shipment_ids = set(first_map) | set(second_map)

    return sum(
        1
        for shipment_id in shipment_ids
        if first_map.get(shipment_id) != second_map.get(shipment_id)
    )


def _sensitivity_summary(
    *,
    configuration: dict,
    selected_assignments: list[dict],
    min_cost_assignments: list[dict],
    min_trips_assignments: list[dict],
) -> dict:
    matches_min_cost = (
        _assignment_signature(selected_assignments)
        == _assignment_signature(min_cost_assignments)
    )
    matches_min_trips = (
        _assignment_signature(selected_assignments)
        == _assignment_signature(min_trips_assignments)
    )

    if matches_min_cost and matches_min_trips:
        matches_scenario = "both_extremes"
        message = (
            "La configuración seleccionada produce la misma asignación que "
            "ambos extremos de sensibilidad."
        )
    elif matches_min_cost:
        matches_scenario = "min_cost"
        message = (
            "La configuración seleccionada produce la misma asignación que "
            "el escenario de costo mínimo."
        )
    elif matches_min_trips:
        matches_scenario = "min_trips"
        message = (
            "La configuración seleccionada produce la misma asignación que "
            "el escenario de viajes mínimos."
        )
    else:
        matches_scenario = None
        message = (
            "La configuración seleccionada produce una asignación diferente "
            "de ambos extremos de sensibilidad."
        )

    return {
        "selected_weights": configuration["weights"],
        "matches_scenario": matches_scenario,
        "message": message,
        "assignment_differences": {
            "vs_min_cost": _assignment_difference_count(
                selected_assignments,
                min_cost_assignments,
            ),
            "vs_min_trips": _assignment_difference_count(
                selected_assignments,
                min_trips_assignments,
            ),
        },
    }


def run_logistics_engine(
    contents: bytes,
    objective: str | None = None,
    configuration: dict | None = None,
) -> dict:
    config = _canonical_configuration(
        objective=objective,
        configuration=configuration,
    )

    rows = _read_rows(contents)

    if not rows:
        raise ValueError(
            "El dataset no contiene despachos."
        )

    catalog = _vehicle_catalog(rows)

    baseline_assignments = []
    min_cost_assignments = []
    min_trips_assignments = []
    custom_assignments = []

    for row in rows:
        current_vehicle = catalog[row["vehicle_type"].strip()]
        baseline_assignments.append(
            _evaluate_shipment(row, current_vehicle)
        )

        alternatives = [
            _evaluate_shipment(row, vehicle)
            for vehicle in catalog.values()
        ]

        min_cost_assignment = _select_min_cost(alternatives)
        min_trips_assignment = _select_min_trips(alternatives)

        min_cost_assignments.append(min_cost_assignment)
        min_trips_assignments.append(min_trips_assignment)

        if config["mode"] == "custom":
            custom_assignments.append(
                _select_custom(
                    alternatives,
                    cost_weight=config["weights"]["cost"],
                    trips_weight=config["weights"]["trips"],
                )
            )

    baseline = _aggregate(baseline_assignments)
    min_cost = _aggregate(min_cost_assignments)
    min_trips = _aggregate(min_trips_assignments)

    scenarios = {
        "baseline": {
            "name": "Situación actual",
            "metrics": baseline,
            "delta_vs_baseline": {
                "trips_pct": 0.0,
                "distance_pct": 0.0,
                "cost_pct": 0.0,
            },
            "assignments": baseline_assignments,
        },
        "min_cost": {
            "name": "Costo mínimo",
            "metrics": min_cost,
            "delta_vs_baseline": _delta(
                min_cost,
                baseline,
            ),
            "assignments": min_cost_assignments,
        },
        "min_trips": {
            "name": "Viajes mínimos",
            "metrics": min_trips,
            "delta_vs_baseline": _delta(
                min_trips,
                baseline,
            ),
            "assignments": min_trips_assignments,
        },
    }

    if config["mode"] == "custom":
        custom = _aggregate(custom_assignments)
        scenarios["custom"] = {
            "name": "Configuración personalizada",
            "metrics": custom,
            "delta_vs_baseline": _delta(
                custom,
                baseline,
            ),
            "assignments": custom_assignments,
            "weights": config["weights"],
        }
        recommended_scenario = "custom"
        selected_assignments = custom_assignments
    else:
        recommended_scenario = config["objective"]
        selected_assignments = scenarios[
            recommended_scenario
        ]["assignments"]

    sensitivity = _sensitivity_summary(
        configuration=config,
        selected_assignments=selected_assignments,
        min_cost_assignments=min_cost_assignments,
        min_trips_assignments=min_trips_assignments,
    )

    return {
        "engine": {
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "executed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
        "configuration": config,
        "model_assumptions": [
            "Cada fila del CSV representa un despacho independiente.",
            "Todos los tipos de vehículo observados en el dataset se consideran disponibles para cada despacho.",
            "Cada viaje incluye ida y regreso.",
            "El engine v0.2 no consolida despachos entre sí.",
            "La capacidad se modela por peso; no se modelan volumen ni dimensiones.",
            "No se modelan disponibilidad temporal de flota, ventanas horarias ni tiempos reales de transporte.",
            "Bajo la formulación actual, minimizar viajes también minimiza distancia recorrida para una distancia origen-destino fija.",
        ],
        "vehicle_catalog": list(catalog.values()),
        "objective": config["objective"],
        "recommended_scenario": recommended_scenario,
        "sensitivity": sensitivity,
        "scenarios": scenarios,
    }
