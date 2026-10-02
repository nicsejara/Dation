"""Bounded evidence and numeric guard for dispatch explanations."""
import json
import re


def build_dispatch_context(result):
    selected = result["scenarios"]["selected"]
    context = {
        "schema_version": result.get("schema_version", "dispatch_v1"),
        "decision": result.get("decision"),
        "feasibility": result.get("feasibility"),
        "decision_drivers": result.get("decision_drivers"),
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
                "Consultá el costo calculado en los KPIs."
            ),
            "trips": (
                "Consultá la distribución de viajes y "
                "la participación propia/tercerizada."
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
