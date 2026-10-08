"""Scheduling configuration layer.

Keeps the scheduling_v1 result contract while adding explicit planning windows,
objective selection and filtered temporal rules without changing Assignment.
"""

import hashlib
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from time import perf_counter

from app.models.scheduling_config import SchedulingConfig, SchedulingOptions
from app.validators.fleet_schema import validate_fleet_csv
from app.validators.orders_schema import validate_orders_csv

from . import engine as core


ENGINE_NAME = core.ENGINE_NAME
ENGINE_VERSION = core.ENGINE_VERSION
SCHEMA_VERSION = core.SCHEMA_VERSION


def _as_date(value):
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _normalized(value):
    return str(value or "").strip().casefold()


def _source_values(source, field):
    if field == "product":
        return [
            load.get("product")
            for load in source.get("loads", [])
            if load.get("product") is not None
        ]
    value = source.get(field)
    return [] if value is None else [value]


def _matches_rule(source, rule):
    expected = {
        _normalized(value)
        for value in rule.get("values", [])
    }
    actual = {
        _normalized(value)
        for value in _source_values(source, rule["field"])
    }
    return bool(expected & actual)


def _apply_focus_rules(prepared, rules):
    evidence = []
    for rule in rules:
        matched = []
        start = _as_date(rule.get("planning_window_start"))
        end = _as_date(rule.get("planning_window_end"))

        for item in prepared:
            source = item["source"]
            if not _matches_rule(source, rule):
                continue

            matched.append(item["trip_id"])
            item.setdefault("focus_rule_ids", []).append(rule["id"])

            if rule["action"] == "prioritize":
                item["priority_rank"] = max(
                    int(item.get("priority_rank") or 0),
                    1,
                )
                continue

            if start and item["earliest_dispatch"] < start:
                item["earliest_dispatch"] = start
            if end:
                current_end = item.get("latest_dispatch")
                item["latest_dispatch"] = (
                    min(current_end, end)
                    if current_end
                    else end
                )
            if (
                item.get("latest_dispatch")
                and item["latest_dispatch"] < item["earliest_dispatch"]
            ):
                raise ValueError(
                    "La regla temporal "
                    + rule["id"]
                    + " deja al viaje "
                    + item["trip_id"]
                    + " sin una fecha de salida factible."
                )

        if not matched:
            raise ValueError(
                "La regla temporal "
                + rule["id"]
                + " no coincide con ningún viaje de la asignación aprobada."
            )

        evidence.append(
            {
                "id": rule["id"],
                "field": rule["field"],
                "values": list(rule["values"]),
                "action": rule["action"],
                "planning_window_start": rule.get("planning_window_start"),
                "planning_window_end": rule.get("planning_window_end"),
                "matched_trip_count": len(matched),
                "matched_trip_ids": sorted(matched),
            }
        )

    return evidence


def _apply_planning_window(prepared, config, options):
    start = _as_date(config.get("planning_window_start"))
    end = _as_date(config.get("planning_window_end"))

    if start:
        for item in prepared:
            if item["earliest_dispatch"] < start:
                item["earliest_dispatch"] = start

    horizon_start = min(item["earliest_dispatch"] for item in prepared)
    horizon_days = int(options["max_horizon_days"])

    if end:
        if horizon_start > end:
            raise ValueError(
                "La ventana de planificación termina antes de que exista un viaje disponible para despachar."
            )
        horizon_days = min(
            horizon_days,
            max(0, (end - horizon_start).days),
        )

    for item in prepared:
        if (
            item.get("latest_dispatch")
            and item["latest_dispatch"] < item["earliest_dispatch"]
        ):
            raise ValueError(
                f"{item['trip_id']} no tiene una ventana temporal factible."
            )

    return horizon_start, horizon_days, start, end


def _focused_greedy_offsets(trips, horizon_start):
    by_vehicle = defaultdict(list)
    for item in trips:
        by_vehicle[item["vehicle_id"]].append(item)

    offsets = {}
    for items in by_vehicle.values():
        remaining = list(items)
        free = min(item["earliest_dispatch"] for item in remaining)

        while remaining:
            available = [
                item
                for item in remaining
                if item["earliest_dispatch"] <= free
            ]
            if not available:
                free = max(
                    free,
                    min(item["earliest_dispatch"] for item in remaining),
                )
                available = [
                    item
                    for item in remaining
                    if item["earliest_dispatch"] <= free
                ]

            current = min(
                available,
                key=lambda item: (
                    item["strictest_due"] or date.max,
                    -int(item.get("priority_rank") or 0),
                    item["earliest_dispatch"],
                    item["cycle_days"],
                    item["trip_id"],
                ),
            )
            dispatch = max(free, current["earliest_dispatch"])
            if (
                current.get("latest_dispatch")
                and dispatch > current["latest_dispatch"]
            ):
                return None

            resource_free = dispatch + timedelta(days=current["cycle_days"])
            if (
                current["available_until"]
                and resource_free - timedelta(days=1)
                > current["available_until"]
            ):
                return None

            offsets[current["trip_id"]] = (
                dispatch - horizon_start
            ).days
            free = resource_free
            remaining.remove(current)

    return offsets


def _validate_window_result(scheduled, start, end, focus_evidence):
    by_trip = {
        item["trip_id"]: date.fromisoformat(item["dispatch_date"])
        for item in scheduled
    }
    for dispatch in by_trip.values():
        if start and dispatch < start:
            raise ValueError(
                "La planificación generó un despacho anterior a la ventana configurada."
            )
        if end and dispatch > end:
            raise ValueError(
                "No existe una planificación factible que ubique todos los despachos dentro de la ventana configurada."
            )

    for rule in focus_evidence:
        if rule["action"] != "window":
            continue
        rule_start = _as_date(rule.get("planning_window_start"))
        rule_end = _as_date(rule.get("planning_window_end"))
        for trip_id in rule["matched_trip_ids"]:
            dispatch = by_trip[trip_id]
            if rule_start and dispatch < rule_start:
                raise ValueError(
                    f"{trip_id} quedó antes de la ventana definida por {rule['id']}."
                )
            if rule_end and dispatch > rule_end:
                raise ValueError(
                    f"{trip_id} quedó después de la ventana definida por {rule['id']}."
                )


def run_scheduling_engine(
    orders_bytes,
    fleet_bytes,
    assignment_result,
    configuration=None,
    options=None,
    inputs=None,
    progress=None,
):
    started = perf_counter()
    config_model = SchedulingConfig.model_validate(configuration or {})
    config = config_model.model_dump(mode="json")
    opts = SchedulingOptions.model_validate(options or {}).model_dump()

    def notify(stage):
        if perf_counter() - started > opts["total_time_limit_s"]:
            raise TimeoutError(
                "Se agotó el presupuesto global de Scheduling."
            )
        if progress:
            progress(stage)

    notify("validating")
    orders_report = validate_orders_csv(orders_bytes)
    fleet_report = validate_fleet_csv(fleet_bytes)
    core._validate_temporal_evidence(orders_report, fleet_report)
    selected_assignment, handoff = core._validate_assignment_result(
        assignment_result
    )

    sla_available = core._complete(
        orders_report,
        "delivery_due_date",
    )
    sla_enabled = bool(
        config["strategy"] == "service_first"
        and config["use_delivery_due_dates"]
        and sla_available
    )

    prepared = core._prepare_trips(
        orders_report["records"],
        fleet_report["records"],
        selected_assignment["trips"],
        sla_enabled=sla_enabled,
    )
    focus_evidence = _apply_focus_rules(
        prepared,
        config.get("temporal_rules") or [],
    )
    (
        horizon_start,
        effective_horizon_days,
        window_start,
        window_end,
    ) = _apply_planning_window(prepared, config, opts)

    notify("constructing")
    greedy_hint = _focused_greedy_offsets(
        prepared,
        horizon_start,
    )

    greedy_inside_window = bool(greedy_hint) and all(
        int(offset) <= effective_horizon_days
        for offset in greedy_hint.values()
    )

    notify(
        "optimizing:service"
        if sla_enabled
        else "optimizing:earliest"
    )
    solved, solver_meta = core.solve_schedule(
        prepared,
        horizon_start=horizon_start,
        max_horizon_days=effective_horizon_days,
        use_due_dates=sla_enabled,
        solve_time_limit_s=opts["solve_time_limit_s"],
        deterministic_limit=opts["deterministic_limit"],
        hint=greedy_hint if greedy_inside_window else None,
    )

    if solved:
        offsets = {
            item["trip_id"]: int(item["start_offset"])
            for item in solved
        }
    else:
        if solver_meta.get("status") == "infeasible":
            raise ValueError(
                solver_meta.get("reason")
                or "No existe una programación temporal factible dentro de las restricciones configuradas."
            )
        if not greedy_inside_window:
            raise ValueError(
                "No se encontró una planificación completa dentro de las restricciones temporales configuradas."
            )
        offsets = greedy_hint
        solver_meta = {
            **solver_meta,
            "status": "feasible",
            "method": "heuristic_fallback",
            "gap": None,
        }

    scheduled = core._materialize(
        prepared,
        offsets,
        horizon_start,
    )
    core._validate_schedule(
        scheduled,
        prepared,
        selected_assignment["trips"],
    )
    _validate_window_result(
        scheduled,
        window_start,
        window_end,
        focus_evidence,
    )

    notify("summarizing")
    summary = core._summarize(
        scheduled,
        orders_report["records"],
        sla_enabled=sla_enabled,
    )
    metrics = summary["metrics"]
    decision_status = (
        "recommended_with_exceptions"
        if metrics["late_orders"]
        else "recommended"
    )
    schedule_fingerprint = core._digest(
        core._schedule_signature(scheduled)
    )
    focused_trip_ids = sorted(
        {
            trip_id
            for rule in focus_evidence
            for trip_id in rule["matched_trip_ids"]
        }
    )
    has_priority_rules = any(
        rule["action"] == "prioritize"
        for rule in focus_evidence
    )

    objective_hierarchy = []
    if sla_enabled:
        objective_hierarchy.extend([
            "late_orders",
            "total_late_days",
        ])
    if has_priority_rules:
        objective_hierarchy.append("focus_priority_wait")
    objective_hierarchy.extend([
        "total_wait_days",
        "makespan",
    ])

    result = {
        "schema_version": SCHEMA_VERSION,
        "decision": {
            "id": "logistics_scheduling",
            "status": decision_status,
            "strategy": config["strategy"],
            "label": "Planificación recomendada",
        },
        "engine": {
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "solver": solver_meta,
        },
        "analysis": {
            "temporal": True,
            "assignment_locked": True,
            "sla_available": sla_available,
            "sla_enabled": sla_enabled,
            "planning_window": {
                "start": config.get("planning_window_start"),
                "end": config.get("planning_window_end"),
                "effective_horizon_start": horizon_start.isoformat(),
                "effective_horizon_days": effective_horizon_days,
            },
            "focus_rules": focus_evidence,
            "focused_trip_count": len(focused_trip_ids),
            "focused_trip_ids": focused_trip_ids,
            "objective_hierarchy": objective_hierarchy,
        },
        "inputs": {
            "orders": {
                "sha256": hashlib.sha256(orders_bytes).hexdigest(),
                "rows": orders_report["rows"],
                **(inputs or {}).get("orders", {}),
            },
            "fleet": {
                "sha256": hashlib.sha256(fleet_bytes).hexdigest(),
                "rows": fleet_report["rows"],
                **(inputs or {}).get("fleet", {}),
            },
            "assignment": {
                "schema_version": assignment_result["schema_version"],
                "result_fingerprint": assignment_result.get(
                    "result_fingerprint"
                ),
                "assignment_fingerprint": handoff[
                    "assignment_fingerprint"
                ],
                "trip_count": handoff["trip_count"],
                **(inputs or {}).get("assignment", {}),
            },
        },
        "configuration": {
            **config,
            "options": opts,
        },
        "decision_drivers": {
            "trips_sequenced": metrics["total_trips"],
            "vehicles_used": metrics["vehicles_used"],
            "late_orders": metrics["late_orders"],
            "total_late_days": metrics["total_late_days"],
            "total_wait_days": metrics["total_wait_days"],
            "makespan_days": metrics["makespan_days"],
            "temporal_rules": len(focus_evidence),
            "focused_trips": len(focused_trip_ids),
        },
        "exceptions": summary["exceptions"],
        "scenarios": {
            "selected": {
                "name": "Planificación recomendada",
                "feasible": True,
                "solver": solver_meta,
                "metrics": metrics,
                "trips": summary["trips"],
                "order_outcomes": summary["order_outcomes"],
                "schedule_fingerprint": schedule_fingerprint,
            }
        },
        "assumptions": [
            (
                "Scheduling conserva exactamente los viajes, cargas y vehicle_id "
                "aprobados en Assignment."
            ),
            (
                "Los filtros temporales nunca excluyen viajes: sólo priorizan o "
                "restringen la fecha de salida del subconjunto seleccionado."
            ),
            (
                "La fecha mínima de salida respeta disponibilidad de carga, "
                "disponibilidad del vehículo y las ventanas configuradas."
            ),
            (
                "La duración diaria usa distance_km, avg_speed_kmh y "
                "driving_hours_per_day."
            ),
            (
                "El vehículo queda ocupado hasta completar ida, entrega y "
                "retorno a su base."
            ),
            (
                "No se modelan horas intradía, descansos regulatorios detallados, "
                "tráfico, clima ni tiempos de carga/descarga."
            ),
            (
                "delivery_due_date participa sólo en Servicio primero y cuando "
                "está completo en Orders."
            ),
        ],
        "handoff": {
            "schema_version": "final_assignment_input_v1",
            "source_decision": "logistics_scheduling",
            "next_decision": "logistics_final_assignment",
            "source_path": "scenarios.selected.trips",
            "assignment_fingerprint": handoff[
                "assignment_fingerprint"
            ],
            "schedule_fingerprint": schedule_fingerprint,
            "trip_count": metrics["total_trips"],
            "trip_ids": [trip["trip_id"] for trip in scheduled],
        },
    }

    stable = {
        "schema_version": SCHEMA_VERSION,
        "version": ENGINE_VERSION,
        "configuration": result["configuration"],
        "orders_hash": result["inputs"]["orders"]["sha256"],
        "fleet_hash": result["inputs"]["fleet"]["sha256"],
        "assignment_fingerprint": handoff["assignment_fingerprint"],
        "schedule": core._schedule_signature(scheduled),
        "metrics": metrics,
    }
    result["result_fingerprint"] = core._digest(stable)
    result["engine"]["wall_ms"] = int(
        (perf_counter() - started) * 1000
    )
    return result
