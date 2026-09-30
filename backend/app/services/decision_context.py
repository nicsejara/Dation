from app.models.decision_config import (
    normalize_stored_configuration,
)


def _index_assignments(
    scenario: dict,
) -> dict[str, dict]:
    return {
        item["shipment_id"]: item
        for item in scenario.get(
            "assignments",
            [],
        )
    }


def _top_changes(
    baseline: dict,
    candidate: dict,
    *,
    limit: int = 5,
) -> list[dict]:
    base = _index_assignments(baseline)
    alt = _index_assignments(candidate)
    changes: list[dict] = []

    for shipment_id, base_item in base.items():
        alt_item = alt.get(shipment_id)

        if not alt_item:
            continue

        cost_delta = round(
            alt_item["total_cost"]
            - base_item["total_cost"],
            2,
        )
        trips_delta = (
            alt_item["required_trips"]
            - base_item["required_trips"]
        )
        distance_delta = round(
            alt_item["total_distance_km"]
            - base_item["total_distance_km"],
            2,
        )

        if (
            base_item["vehicle_type"]
            != alt_item["vehicle_type"]
            or cost_delta != 0
            or trips_delta != 0
            or distance_delta != 0
        ):
            change = {
                "shipment_id": shipment_id,
                "origin": base_item["origin"],
                "destination": base_item[
                    "destination"
                ],
                "baseline_vehicle": base_item[
                    "vehicle_type"
                ],
                "candidate_vehicle": alt_item[
                    "vehicle_type"
                ],
                "baseline_cost": base_item[
                    "total_cost"
                ],
                "candidate_cost": alt_item[
                    "total_cost"
                ],
                "cost_delta": cost_delta,
                "baseline_trips": base_item[
                    "required_trips"
                ],
                "candidate_trips": alt_item[
                    "required_trips"
                ],
                "trips_delta": trips_delta,
                "distance_delta_km": (
                    distance_delta
                ),
            }

            if "decision_score" in alt_item:
                change["decision_score"] = (
                    alt_item[
                        "decision_score"
                    ]
                )
                change["normalized_cost"] = (
                    alt_item[
                        "normalized_cost"
                    ]
                )
                change["normalized_trips"] = (
                    alt_item[
                        "normalized_trips"
                    ]
                )

            changes.append(change)

    changes.sort(
        key=lambda item: abs(
            item["cost_delta"]
        ),
        reverse=True,
    )
    return changes[:limit]


def _count_vehicle_changes(
    baseline: dict,
    candidate: dict,
) -> int:
    base = _index_assignments(baseline)
    alt = _index_assignments(candidate)

    return sum(
        1
        for shipment_id, base_item in base.items()
        if shipment_id in alt
        and base_item["vehicle_type"]
        != alt[shipment_id][
            "vehicle_type"
        ]
    )


def _scenario_context(
    baseline: dict,
    scenario: dict,
) -> dict:
    return {
        "name": scenario.get("name"),
        "metrics": scenario.get("metrics"),
        "delta_vs_baseline": scenario.get(
            "delta_vs_baseline"
        ),
        "vehicle_changes_vs_baseline": (
            _count_vehicle_changes(
                baseline,
                scenario,
            )
        ),
        "top_changes_vs_baseline": (
            _top_changes(
                baseline,
                scenario,
            )
        ),
        "weights": scenario.get("weights"),
    }


def build_decision_context(
    result_json: dict,
    configuration_json: dict | None = None,
) -> dict:
    scenarios = result_json["scenarios"]
    baseline = scenarios["baseline"]

    configuration = (
        normalize_stored_configuration(
            configuration_json,
            result_json,
        )
    )

    scenario_context = {
        "baseline": {
            "name": "Asignación de referencia",
            "metrics": baseline.get(
                "metrics"
            ),
            "delta_vs_baseline": (
                baseline.get(
                    "delta_vs_baseline"
                )
            ),
            "vehicle_changes_vs_baseline": 0,
            "top_changes_vs_baseline": [],
        }
    }

    for key in (
        "min_cost",
        "min_trips",
        "custom",
    ):
        if key in scenarios:
            scenario_context[key] = (
                _scenario_context(
                    baseline,
                    scenarios[key],
                )
            )

    recommended = result_json.get(
        "recommended_scenario"
    )

    sensitivity = result_json.get(
        "sensitivity",
        {},
    )

    matches = sensitivity.get(
        "matches_scenario"
    )

    equivalent_scenarios: list[str] = []

    if matches == "both_extremes":
        equivalent_scenarios = [
            "min_cost",
            "min_trips",
        ]
    elif matches in {
        "min_cost",
        "min_trips",
    }:
        equivalent_scenarios = [
            matches
        ]

    if configuration["mode"] == "custom":
        selected_label = (
            "Configuración personalizada"
        )
        interpretation_rule = (
            "La decisión solicitada es personalizada. "
            "Nunca renombrarla como min_cost o min_trips. "
            "Si coincide con un extremo, describirlo "
            "únicamente como equivalencia de sensibilidad."
        )
    elif configuration["objective"] == "min_trips":
        selected_label = "Viajes mínimos"
        interpretation_rule = (
            "La decisión solicitada usa el preset "
            "de viajes mínimos."
        )
    else:
        selected_label = "Costo mínimo"
        interpretation_rule = (
            "La decisión solicitada usa el preset "
            "de costo mínimo."
        )

    return {
        "engine": result_json.get(
            "engine",
            {},
        ),
        "configuration": configuration,
        "objective": configuration[
            "objective"
        ],
        "recommended_scenario": recommended,
        "reference_semantics": {
            "label": "Asignación de referencia",
            "source": (
                "vehicle_type informado en cada fila "
                "del dataset"
            ),
            "meaning": (
                "Referencia comparativa para cuantificar "
                "deltas del modelo. No implica por sí "
                "misma que represente la situación "
                "operativa actual."
            ),
        },
        "selection_semantics": {
            "requested_mode": configuration[
                "mode"
            ],
            "requested_objective": configuration[
                "objective"
            ],
            "requested_weights": configuration[
                "weights"
            ],
            "selected_scenario": recommended,
            "selected_label": selected_label,
            "equivalent_scenarios": (
                equivalent_scenarios
            ),
            "interpretation_rule": (
                interpretation_rule
            ),
        },
        "selected_scenario": (
            scenario_context.get(recommended)
        ),
        "sensitivity": sensitivity,
        "model_assumptions": (
            result_json.get(
                "model_assumptions",
                [],
            )
        ),
        "vehicle_catalog": (
            result_json.get(
                "vehicle_catalog",
                [],
            )
        ),
        "scenarios": scenario_context,
    }
