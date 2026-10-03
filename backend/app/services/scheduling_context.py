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

    key_events = []
    for vehicle in sequence_by_vehicle:
        previous = None
        for trip in vehicle["trips"]:
            wait_days = int(
                trip.get("wait_days") or 0
            )
            if wait_days > 0:
                if (
                    previous
                    and previous.get(
                        "resource_available_again"
                    )
                    == trip.get("dispatch_date")
                ):
                    cause = (
                        f"{vehicle['vehicle_id']} recién volvió a quedar "
                        f"disponible el {trip.get('dispatch_date')} después "
                        f"de {previous.get('trip_id')}."
                    )
                    cause_status = "derived"
                else:
                    cause = (
                        "La salida quedó después del ready date. La evidencia "
                        "resumida no permite atribuir una única causa si no "
                        "proviene de la ocupación inmediatamente anterior."
                    )
                    cause_status = "not_determined"

                key_events.append(
                    {
                        "type": "wait",
                        "title": (
                            f"{trip.get('trip_id')} espera "
                            f"{wait_days} días"
                        ),
                        "fact": (
                            f"Ready {trip.get('ready_date')} · salida "
                            f"{trip.get('dispatch_date')} · vehículo "
                            f"{vehicle['vehicle_id']}."
                        ),
                        "cause_status": cause_status,
                        "cause": cause,
                        "trip_id": trip.get("trip_id"),
                        "vehicle_id": vehicle["vehicle_id"],
                    }
                )
            elif (
                previous
                and previous.get(
                    "resource_available_again"
                )
                == trip.get("dispatch_date")
            ):
                key_events.append(
                    {
                        "type": "tight_sequence",
                        "title": (
                            f"{vehicle['vehicle_id']} encadena "
                            f"{previous.get('trip_id')} y {trip.get('trip_id')}"
                        ),
                        "fact": (
                            f"{trip.get('trip_id')} sale el mismo día "
                            "en que el vehículo vuelve a estar disponible."
                        ),
                        "cause_status": "derived",
                        "cause": (
                            "Scheduling compactó la secuencia sin superponer "
                            "la ocupación del recurso."
                        ),
                        "trip_id": trip.get("trip_id"),
                        "vehicle_id": vehicle["vehicle_id"],
                    }
                )
            previous = trip

    for exception in (result.get("exceptions") or [])[:6]:
        key_events.append(
            {
                "type": "late_order",
                "title": (
                    f"{exception.get('order_id')} queda fuera "
                    "de fecha objetivo"
                ),
                "fact": (
                    f"Llega {exception.get('arrival_date')} con "
                    f"{exception.get('late_days')} días de tardanza."
                ),
                "cause_status": "model_result",
                "cause": (
                    "La excepción permanece después de aplicar la jerarquía "
                    "de Scheduling. No atribuir una causa externa no modelada."
                ),
                "order_id": exception.get("order_id"),
            }
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
        "key_events": key_events[:10],
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
