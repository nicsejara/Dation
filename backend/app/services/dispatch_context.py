"""Bounded evidence and numeric guard for dispatch explanations."""
import json
import re


def build_assignment_context(result):
    """Bounded evidence for Assignment V1; deliberately excludes time/SLA."""
    selected = result["scenarios"]["selected"]
    resources = {}

    for trip in selected.get("trips", []):
        resource_id = (
            trip.get("vehicle_id")
            or trip.get("fleet_pool_id")
            or trip.get("vehicle_type")
            or "legacy"
        )
        current = resources.setdefault(
            resource_id,
            {
                "vehicle_id": resource_id,
                "vehicle_type": trip.get("vehicle_type"),
                "ownership": trip.get("ownership"),
                "provider_name": trip.get("provider_name"),
                "base_site": (
                    trip.get("base_site")
                    or trip.get("base_location")
                ),
                "trips": 0,
                "load_kg": 0.0,
                "capacity_kg": 0.0,
                "orders": set(),
                "products": {},
            },
        )
        current["trips"] += 1
        current["load_kg"] += float(
            trip.get("load_kg") or 0
        )
        current["capacity_kg"] += float(
            trip.get("capacity_kg") or 0
        )
        for load in trip.get("loads", []):
            current["orders"].add(
                load.get("order_id")
            )
            product = (
                load.get("product")
                or "Producto no registrado"
            )
            current["products"][product] = (
                current["products"].get(
                    product,
                    0.0,
                )
                + float(
                    load.get("kg") or 0
                )
            )

    assignment_by_vehicle = []
    for current in resources.values():
        capacity = current.pop(
            "capacity_kg"
        )
        current["orders"] = len(
            current["orders"]
        )
        current["utilization"] = (
            current["load_kg"]
            / capacity
            if capacity
            else 0
        )
        current["products"] = dict(
            sorted(
                current["products"].items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        )
        assignment_by_vehicle.append(
            current
        )

    assignment_by_vehicle.sort(
        key=lambda item: (
            -item["load_kg"],
            item["vehicle_id"],
        )
    )

    return {
        "schema_version": "assignment_v1",
        "decision": result.get("decision"),
        "configuration": result.get(
            "configuration"
        ),
        "capabilities": result.get(
            "capabilities"
        ),
        "decision_drivers": result.get(
            "decision_drivers"
        ),
        "selected_metrics": selected.get(
            "metrics"
        ),
        "assignment_by_vehicle": (
            assignment_by_vehicle[:16]
        ),
        "order_examples": (
            selected.get(
                "order_outcomes",
                []
            )[:8]
        ),
        "alternatives": [
            {
                "scenario": item.get(
                    "scenario"
                ),
                "label": item.get(
                    "label"
                ),
                "metrics": item.get(
                    "metrics"
                ),
            }
            for item in result.get(
                "sensitivity",
                {},
            ).get(
                "frontier",
                [],
            )[:8]
        ],
        "handoff": result.get("handoff"),
        "anomalies": (
            result.get(
                "inputs",
                {},
            ).get(
                "anomalies",
                []
            )[:10]
        ),
        "assumptions": result.get(
            "assumptions",
            []
        ),
        "interpretation_boundary": {
            "temporal": False,
            "dates_are_decided_here": False,
            "sla_is_decided_here": False,
            "next_decision": (
                "logistics_scheduling"
            ),
        },
    }


def build_dispatch_context(result):
    if result.get("schema_version") == "assignment_v1":
        return build_assignment_context(result)
    selected = result["scenarios"]["selected"]
    assignment = {}
    for trip in selected.get("trips", []):
        pool_id = trip.get("fleet_pool_id") or trip.get("vehicle_type") or "legacy"
        current = assignment.setdefault(
            pool_id,
            {
                "fleet_pool_id": pool_id,
                "vehicle_type": trip.get("vehicle_type"),
                "ownership": trip.get("ownership"),
                "base_location": trip.get("base_location"),
                "trips": 0,
                "load_kg": 0.0,
                "capacity_kg": 0.0,
                "products": {},
                "orders": set(),
            },
        )
        current["trips"] += 1
        current["load_kg"] += float(trip.get("load_kg") or 0)
        current["capacity_kg"] += float(trip.get("capacity_kg") or 0)
        for load in trip.get("loads", []):
            current["orders"].add(load.get("order_id"))
            product = load.get("product") or "Producto no registrado"
            current["products"][product] = (
                current["products"].get(product, 0.0)
                + float(load.get("kg") or 0)
            )

    assignment_by_pool = []
    for current in assignment.values():
        capacity = current.pop("capacity_kg")
        current["orders"] = len(current["orders"])
        current["utilization"] = (
            current["load_kg"] / capacity
            if capacity
            else 0
        )
        current["products"] = dict(
            sorted(
                current["products"].items(),
                key=lambda item: (-item[1], item[0]),
            )
        )
        assignment_by_pool.append(current)
    assignment_by_pool.sort(
        key=lambda item: (
            -item["load_kg"],
            item["fleet_pool_id"],
        )
    )

    context = {
        "schema_version": result.get("schema_version", "dispatch_v1"),
        "decision": result.get("decision"),
        "feasibility": result.get("feasibility"),
        "decision_drivers": result.get("decision_drivers"),
        "assignment_by_pool": assignment_by_pool[:12],
        "exceptions": (result.get("exceptions") or [])[:10],
        "configuration": result["configuration"],
        "solver": selected["solver"],
        "normalization": result["normalization"],
        "scenarios": {
            scenario["name"]: {
                "metrics": scenario.get("metrics"),
                "feasible": scenario.get("feasible"),
                "delta_vs_baseline": scenario.get(
                    "delta_vs_baseline"
                ),
            }
            for scenario in result["scenarios"].values()
        },
        "fleet": result["fleet"],
        "anomalies": result["inputs"]["anomalies"][:10],
        "changes": {
            "consolidated": sum(
                bool(outcome.get("consolidated"))
                for outcome in selected["order_outcomes"]
            ),
            "split": sum(
                bool(outcome.get("split"))
                for outcome in selected["order_outcomes"]
            ),
            "outsourced": sum(
                bool(outcome.get("outsourced"))
                for outcome in selected["order_outcomes"]
            ),
            "postponed": sum(
                outcome.get("postponed_days", 0) > 0
                for outcome in selected["order_outcomes"]
            ),
            "late": sum(
                outcome.get("late_days", 0) > 0
                for outcome in selected["order_outcomes"]
            ),
        },
        "examples": sorted(
            selected["order_outcomes"],
            key=lambda outcome: (
                -outcome.get("late_days", 0),
                -outcome.get("postponed_days", 0),
                outcome["order_id"],
            ),
        )[:5],
        "sensitivity": [
            {
                "scenario": point.get("scenario"),
                "label": point.get("label"),
                "weights": point["weights"],
                "metrics": point["metrics"],
                "orders_changed": point[
                    "orders_changed_vs_selected"
                ],
            }
            for point in result["sensitivity"]["weight_sweep"]
        ],
        "assumptions": result["assumptions"],
    }

    def bounded(value):
        if isinstance(value, str):
            return value[:240]
        if isinstance(value, list):
            return [
                bounded(item)
                for item in value[:20]
            ]
        if isinstance(value, dict):
            return {
                str(key)[:120]: bounded(item)
                for key, item in list(
                    value.items()
                )[:30]
            }
        return value

    context = bounded(context)

    if len(
        json.dumps(
            context,
            ensure_ascii=False,
        )
    ) > 18000:
        context["examples"] = []
        context["fleet"] = []
        context["sensitivity"] = []
        for scenario in context["scenarios"].values():
            metrics = scenario.get("metrics")
            if metrics:
                metrics.pop(
                    "trips_by_vehicle_type",
                    None,
                )
                metrics.pop(
                    "trips_by_fleet_pool",
                    None,
                )
        context["context_note"] = (
            "Se omitieron ejemplos, detalle de flota y "
            "sensibilidad para acotar el contexto."
        )

    if len(
        json.dumps(
            context,
            ensure_ascii=False,
        )
    ) > 18000:
        context = {
            "schema_version": result.get(
                "schema_version",
                "dispatch_v1",
            ),
            "decision": bounded(
                result.get("decision")
            ),
            "feasibility": bounded(
                result.get("feasibility")
            ),
            "decision_drivers": bounded(
                result.get("decision_drivers")
            ),
            "assignment_by_pool": bounded(
                assignment_by_pool[:8]
            ),
            "configuration": {
                key: result["configuration"][key]
                for key in (
                    "mode",
                    "objective",
                    "weights",
                )
            },
            "selected_metrics": {
                key: value
                for key, value in selected[
                    "metrics"
                ].items()
                if isinstance(
                    value,
                    (int, float),
                )
            },
            "assumptions": bounded(
                result["assumptions"]
            ),
            "context_note": (
                "Contexto reducido: consultar el dashboard "
                "para comparaciones y detalle."
            ),
        }

    return context


def verify_numbers(text, context):
    """Conservative presence check, not proof of semantic correctness."""
    allowed = set()

    def collect(value):
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (float, int)):
            for number in (
                value,
                value * 100
                if abs(value) <= 1
                else value,
            ):
                for precision in (
                    0,
                    1,
                    2,
                    3,
                    6,
                ):
                    allowed.add(
                        round(
                            float(number),
                            precision,
                        )
                    )
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(context)

    cleaned = re.sub(
        r"\b\d{4}-\d{2}-\d{2}\b|\b[A-Za-z]+-\d+\b",
        "",
        text,
    )
    for token in re.findall(
        r"(?<![\w])\d+(?:[.,]\d+)*",
        cleaned,
    ):
        variants = []
        try:
            variants.append(
                float(
                    token.replace(
                        ".",
                        "",
                    ).replace(
                        ",",
                        ".",
                    )
                )
            )
        except ValueError:
            pass
        try:
            variants.append(
                float(
                    token.replace(
                        ",",
                        "",
                    )
                )
            )
        except ValueError:
            pass

        if not any(
            any(
                abs(value - allowed_value)
                <= 1e-6
                for allowed_value in allowed
            )
            for value in variants
        ):
            return False

    return True


def safe_explanation(result):
    if result.get("schema_version") == "scheduling_v1":
        metrics = result["scenarios"]["selected"]["metrics"]
        sla_enabled = bool(
            result.get("analysis", {}).get("sla_enabled")
        )
        return {
            "executive_summary": (
                "Scheduling secuenció "
                f"{metrics['total_trips']} viajes con "
                f"{metrics['vehicles_used']} vehículos."
            ),
            "recommendation": (
                "Revisá el calendario, las esperas y las excepciones "
                "antes de aprobar la planificación."
            ),
            "why_recommended": (
                "El motor mantuvo intacta Assignment y ordenó los viajes "
                "respetando ready date, disponibilidad del vehículo y "
                "ocupación hasta su retorno."
            ),
            "business_impact": {
                "cost": (
                    "Scheduling no recalcula costos ni reasigna vehículos."
                ),
                "trips": (
                    f"Los {metrics['total_trips']} viajes provienen "
                    "sin cambios de Assignment."
                ),
                "distance": (
                    "La distancia participa en tránsito y ciclo temporal "
                    "junto con velocidad y horas de conducción."
                ),
            },
            "key_drivers": [
                (
                    f"La espera media es {metrics['avg_wait_days']:.2f} días."
                ),
                (
                    (
                        f"{metrics['late_orders']} órdenes quedan fuera "
                        "de fecha objetivo."
                    )
                    if sla_enabled
                    else "La fecha objetivo no participó en esta corrida."
                ),
            ],
            "tradeoffs": [
                (
                    "Cuando SLA está activo, menos órdenes tardías domina "
                    "sobre espera y compactación del calendario."
                )
                if sla_enabled
                else (
                    "Sin SLA, el motor prioriza menor espera y un calendario compacto."
                )
            ],
            "assumptions": result.get("assumptions", []),
            "caveats": [
                (
                    "No se modelan tráfico, clima, horas intradía, "
                    "carga/descarga ni descansos regulatorios detallados."
                )
            ],
            "suggested_questions": [
                "¿Por qué este viaje sale en esa fecha?",
                "¿Qué vehículo tiene la secuencia más ajustada?",
                "¿Qué órdenes llegan fuera de fecha objetivo?",
            ],
        }

    if result.get("schema_version") == "assignment_v1":
        metrics = result["scenarios"]["selected"]["metrics"]
        drivers = result.get("decision_drivers", {})
        cost = metrics.get("total_cost")
        co2 = metrics.get("co2_kg")
        return {
            "executive_summary": (
                "Assignment distribuye "
                f"{metrics['orders']} órdenes en "
                f"{metrics['total_trips']} viajes abstractos."
            ),
            "recommendation": (
                "Revisá qué vehículo recibe cada viaje y aprobá "
                "la asignación si la distribución es operativamente aceptable. "
                "Las fechas se decidirán en Planificación."
            ),
            "why_recommended": (
                "El motor aplicó el objetivo configurado respetando "
                "capacidad por viaje, origen/site, ruta y unidades enteras."
            ),
            "business_impact": {
                "cost": (
                    f"Costo estimado de la asignación: {cost}."
                    if cost is not None
                    else "No se calculó costo porque el Data Pack no tiene costos completos."
                ),
                "trips": (
                    f"La asignación usa {metrics['total_trips']} viajes "
                    f"y {metrics['vehicles_used']} vehículos."
                ),
                "distance": (
                    "La distancia de ruta participa en costo y CO₂ cuando "
                    "esas dimensiones están disponibles; no se programan fechas."
                ),
            },
            "key_drivers": [
                (
                    f"{drivers.get('orders_consolidated', 0)} órdenes "
                    "quedaron consolidadas y "
                    f"{drivers.get('orders_split', 0)} divididas."
                ),
                (
                    f"La flota propia transporta "
                    f"{metrics.get('own_weight_share', 0) * 100:.1f} % "
                    "del peso."
                ),
            ],
            "tradeoffs": [
                (
                    "Viajes, costo, uso de flota propia y CO₂ pueden "
                    "competir entre sí según la configuración elegida."
                )
            ],
            "assumptions": result.get("assumptions", []),
            "caveats": [
                (
                    "Assignment no evalúa disponibilidad futura, "
                    "solapamientos temporales, SLA ni fechas de salida."
                ),
                (
                    "El CO₂ es estimado con factores informados."
                    if co2 is not None
                    else "CO₂ no está disponible con este Data Pack."
                ),
            ],
            "suggested_questions": [
                "¿Por qué este vehículo recibe más carga?",
                "¿Por qué se utiliza flota tercerizada?",
                "¿Qué cambia si priorizo menos viajes?",
            ],
        }

    metrics = result[
        "scenarios"
    ]["selected"]["metrics"]
    drivers = result.get(
        "decision_drivers",
        {},
    )
    feasibility = result.get(
        "feasibility",
        {},
    )
    return {
        "executive_summary": (
            "Distribución validada para "
            f"{metrics['orders']} órdenes y "
            f"{metrics['total_trips']} viajes."
        ),
        "recommendation": (
            "Revisá la distribución, las excepciones de SLA "
            "y los trade-offs del objetivo elegido antes de "
            "aprobar el despacho."
        ),
        "why_recommended": (
            "El motor protegió primero el mejor nivel de "
            "servicio encontrado y luego aplicó la prioridad "
            "de negocio seleccionada, respetando capacidad, "
            "base y ocupación temporal."
        ),
        "business_impact": {
            "cost": (
                "El costo corresponde a la distribución calculada; "
                "no representa ahorro real frente a una operación histórica."
            ),
            "trips": (
                "Consultá la asignación de carga para revisar viajes, "
                "pools, productos y participación propia/tercerizada."
            ),
            "distance": (
                "Costo y emisiones contemplan ida y vuelta."
            ),
        },
        "key_drivers": [
            (
                "La decisión usa evidencia determinística de "
                f"{drivers.get('orders_consolidated', 0)} "
                "órdenes consolidadas y "
                f"{drivers.get('orders_split', 0)} divididas."
            ),
            (
                "El nivel de servicio resultante deja "
                f"{feasibility.get('late_orders', 0)} "
                "órdenes fuera de SLA."
            ),
        ],
        "tradeoffs": [
            (
                "Costo, tiempo, uso de flota propia y CO₂ "
                "sólo se comparan después de proteger SLA."
            )
        ],
        "assumptions": result["assumptions"],
        "caveats": [
            (
                "La respuesta de IA no superó la comprobación "
                "de cifras. Se muestra una explicación "
                "determinística de respaldo."
            )
        ],
        "suggested_questions": [
            "¿Qué órdenes quedan fuera de SLA?",
            "¿Por qué se utilizó flota tercerizada?",
        ],
    }
