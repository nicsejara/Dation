def _index_assignments(scenario: dict) -> dict[str, dict]:
    return {
        item["shipment_id"]: item
        for item in scenario.get("assignments", [])
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
            alt_item["total_cost"] - base_item["total_cost"],
            2,
        )
        trips_delta = (
            alt_item["required_trips"] - base_item["required_trips"]
        )
        distance_delta = round(
            alt_item["total_distance_km"]
            - base_item["total_distance_km"],
            2,
        )

        if (
            base_item["vehicle_type"] != alt_item["vehicle_type"]
            or cost_delta != 0
            or trips_delta != 0
            or distance_delta != 0
        ):
            changes.append(
                {
                    "shipment_id": shipment_id,
                    "origin": base_item["origin"],
                    "destination": base_item["destination"],
                    "baseline_vehicle": base_item["vehicle_type"],
                    "candidate_vehicle": alt_item["vehicle_type"],
                    "baseline_cost": base_item["total_cost"],
                    "candidate_cost": alt_item["total_cost"],
                    "cost_delta": cost_delta,
                    "baseline_trips": base_item["required_trips"],
                    "candidate_trips": alt_item["required_trips"],
                    "trips_delta": trips_delta,
                    "distance_delta_km": distance_delta,
                }
            )

    changes.sort(key=lambda item: abs(item["cost_delta"]), reverse=True)
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
        != alt[shipment_id]["vehicle_type"]
    )


def build_decision_context(result_json: dict) -> dict:
    scenarios = result_json["scenarios"]
    baseline = scenarios["baseline"]
    min_cost = scenarios["min_cost"]
    min_trips = scenarios["min_trips"]

    return {
        "engine": result_json.get("engine", {}),
        "objective": result_json.get("objective"),
        "recommended_scenario": result_json.get(
            "recommended_scenario"
        ),
        "model_assumptions": result_json.get(
            "model_assumptions",
            [],
        ),
        "vehicle_catalog": result_json.get(
            "vehicle_catalog",
            [],
        ),
        "scenarios": {
            "baseline": {
                "name": baseline.get("name"),
                "metrics": baseline.get("metrics"),
                "delta_vs_baseline": baseline.get(
                    "delta_vs_baseline"
                ),
            },
            "min_cost": {
                "name": min_cost.get("name"),
                "metrics": min_cost.get("metrics"),
                "delta_vs_baseline": min_cost.get(
                    "delta_vs_baseline"
                ),
                "vehicle_changes_vs_baseline": (
                    _count_vehicle_changes(
                        baseline,
                        min_cost,
                    )
                ),
                "top_changes_vs_baseline": _top_changes(
                    baseline,
                    min_cost,
                ),
            },
            "min_trips": {
                "name": min_trips.get("name"),
                "metrics": min_trips.get("metrics"),
                "delta_vs_baseline": min_trips.get(
                    "delta_vs_baseline"
                ),
                "vehicle_changes_vs_baseline": (
                    _count_vehicle_changes(
                        baseline,
                        min_trips,
                    )
                ),
                "top_changes_vs_baseline": _top_changes(
                    baseline,
                    min_trips,
                ),
            },
        },
    }
