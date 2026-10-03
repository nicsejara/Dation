"""Decision readiness derived from Logistics Data Pack completeness."""

DECISIONS = (
    {
        "id": "logistics_assignment",
        "level": 1,
        "label": "Asignación de carga",
        "question": "¿Cómo conviene construir los viajes y distribuir la carga?",
        "dependency": None,
    },
    {
        "id": "logistics_scheduling",
        "level": 2,
        "label": "Planificación",
        "question": "¿Cuándo conviene ejecutar los viajes ya definidos?",
        "dependency": "logistics_assignment",
    },
    {
        "id": "logistics_final_assignment",
        "level": 3,
        "label": "Asignación final",
        "question": "¿Qué camión y patente ejecuta cada viaje programado?",
        "dependency": "logistics_scheduling",
    },
)

SCHEDULING_REQUIREMENTS = (
    ("orders", "estimated_dispatch_date", "Fecha estimada de despacho"),
    ("fleet", "avg_speed_kmh", "Velocidad media"),
    ("fleet", "driving_hours_per_day", "Horas de conducción por día"),
    ("fleet", "status", "Estado operativo"),
    ("fleet", "available_from", "Disponible desde"),
)

FINAL_ASSIGNMENT_REQUIREMENTS = (
    ("fleet", "license_plate", "Patente"),
)

CAPABILITIES = (
    {
        "id": "trips",
        "label": "Menor cantidad de viajes",
        "requirements": (),
    },
    {
        "id": "own_fleet",
        "label": "Priorizar flota propia",
        "requirements": (),
    },
    {
        "id": "cost",
        "label": "Optimizar costo",
        "requirements": (
            ("fleet", "cost_per_km", "Costo por km"),
            ("fleet", "fixed_trip_cost", "Costo fijo por viaje"),
        ),
    },
    {
        "id": "co2",
        "label": "Optimizar CO₂",
        "requirements": (
            ("fleet", "co2_kg_per_km", "CO₂ por km"),
        ),
    },
)


def _complete(reports, dataset, column):
    return bool(
        reports.get(dataset, {})
        .get("completeness", {})
        .get(column, {})
        .get("complete")
    )


def _missing(reports, requirements):
    return [
        {
            "dataset": dataset,
            "column": column,
            "label": label,
        }
        for dataset, column, label in requirements
        if not _complete(reports, dataset, column)
    ]


def build_decision_readiness(orders, fleet, compatibility=None):
    reports = {
        "orders": orders,
        "fleet": fleet,
    }

    compatibility = compatibility or {}
    assignment_blockers = [
        error
        for error in compatibility.get("errors", [])
        if error.get("code") in {
            "NO_FLEET_AT_ORIGIN",
            "UNIT_EXCEEDS_CAPACITY",
        }
    ]
    assignment_ready = bool(
        orders.get("profile")
        and fleet.get("profile")
        and not assignment_blockers
    )
    scheduling_missing = _missing(
        reports,
        SCHEDULING_REQUIREMENTS,
    )
    final_missing = _missing(
        reports,
        FINAL_ASSIGNMENT_REQUIREMENTS,
    )

    capabilities = []
    for capability in CAPABILITIES:
        missing = _missing(
            reports,
            capability["requirements"],
        )
        capabilities.append(
            {
                "id": capability["id"],
                "label": capability["label"],
                "available": not missing,
                "missing": missing,
            }
        )

    decisions = [
        {
            **DECISIONS[0],
            "data_ready": assignment_ready,
            "state": "available" if assignment_ready else "needs_data",
            "missing": [],
            "blockers": assignment_blockers,
            "capabilities": capabilities,
        },
        {
            **DECISIONS[1],
            "data_ready": not scheduling_missing,
            "state": "locked",
            "missing": scheduling_missing,
            "unlock_reason": (
                "Primero validá Asignación de carga."
                if not scheduling_missing
                else "Completá datos opcionales y validá Asignación de carga."
            ),
            "capabilities": [
                {
                    "id": "sla",
                    "label": "Evaluar fecha objetivo de entrega",
                    "available": _complete(
                        reports,
                        "orders",
                        "delivery_due_date",
                    ),
                    "missing": _missing(
                        reports,
                        (
                            (
                                "orders",
                                "delivery_due_date",
                                "Fecha objetivo de entrega",
                            ),
                        ),
                    ),
                }
            ],
        },
        {
            **DECISIONS[2],
            "data_ready": not final_missing,
            "state": "locked",
            "missing": final_missing,
            "unlock_reason": (
                "Primero validá Planificación."
                if not final_missing
                else "Completá la identificación física y validá Planificación."
            ),
            "capabilities": [],
        },
    ]

    return {
        "data_pack": "logistics_data_pack_v1",
        "orders_schema": orders.get("schema"),
        "fleet_schema": fleet.get("schema"),
        "decisions": decisions,
        "next_available": (
            "logistics_assignment"
            if assignment_ready
            else None
        ),
        "summary": {
            "available": sum(
                item["state"] == "available"
                for item in decisions
            ),
            "data_ready": sum(
                item["data_ready"]
                for item in decisions
            ),
            "locked": sum(
                item["state"] == "locked"
                for item in decisions
            ),
        },
    }
