"""Bounded evidence for Scheduling V1 explanations."""


def build_scheduling_context(result):
    selected = result["scenarios"]["selected"]
    by_vehicle = {}

    for trip in selected.get("trips", []):
        vehicle_id = (
            trip.get("vehicle_id")
            or trip.get("vehicle_type")
            or "Recurso"
        )
        current = by_vehicle.setdefault(
            vehicle_id,
            {
                "vehicle_id": vehicle_id,
                "vehicle_type": trip.get(
                    "vehicle_type"
                ),
                "ownership": trip.get(
                    "ownership"
                ),
                "trips": [],
            },
        )
        current["trips"].append(
            {
                "trip_id": trip.get(
                    "trip_id"
                ),
                "origin": trip.get(
                    "origin"
                ),
                "destination": trip.get(
                    "destination"
                ),
                "ready_date": trip.get(
                    "ready_date"
                ),
                "dispatch_date": trip.get(
                    "dispatch_date"
                ),
                "arrival_date": trip.get(
                    "arrival_date"
                ),
                "resource_available_again": (
                    trip.get(
                        "resource_available_again"
                    )
                ),
                "wait_days": trip.get(
                    "wait_days"
                ),
                "cycle_days": trip.get(
                    "cycle_days"
                ),
                "orders": [
                    load.get("order_id")
                    for load in trip.get(
                        "loads",
                        [],
                    )
                ],
            }
        )

    sequence_by_vehicle = []
    for current in by_vehicle.values():
        current["trips"].sort(
            key=lambda item: (
                item.get(
                    "dispatch_date"
                )
                or "",
                item.get(
                    "trip_id"
                )
                or "",
            )
        )
        sequence_by_vehicle.append(
            current
        )

    sequence_by_vehicle.sort(
        key=lambda item: (
            item["vehicle_id"]
        )
    )

    return {
        "schema_version": (
            "scheduling_v1"
        ),
        "decision": result.get(
            "decision"
        ),
        "configuration": result.get(
            "configuration"
        ),
        "analysis": result.get(
            "analysis"
        ),
        "decision_drivers": (
            result.get(
                "decision_drivers"
            )
        ),
        "selected_metrics": (
            selected.get(
                "metrics"
            )
        ),
        "sequence_by_vehicle": (
            sequence_by_vehicle[:16]
        ),
        "order_outcomes": (
            selected.get(
                "order_outcomes",
                []
            )[:20]
        ),
        "exceptions": (
            result.get(
                "exceptions",
                []
            )[:20]
        ),
        "source_assignment": (
            result.get(
                "inputs",
                {},
            ).get(
                "assignment"
            )
        ),
        "handoff": result.get(
            "handoff"
        ),
        "assumptions": result.get(
            "assumptions",
            []
        ),
        "interpretation_boundary": {
            "assignment_locked": True,
            "can_change_vehicle": False,
            "can_change_loads": False,
            "temporal": True,
            "sla_evaluated": bool(
                result.get(
                    "analysis",
                    {},
                ).get(
                    "sla_enabled"
                )
            ),
            "next_decision": (
                "logistics_final_assignment"
            ),
        },
    }
