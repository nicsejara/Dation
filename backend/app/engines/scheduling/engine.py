import hashlib
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from time import perf_counter

from app.models.scheduling_config import (
    SchedulingConfig,
    SchedulingOptions,
)
from app.validators.fleet_schema import validate_fleet_csv
from app.validators.orders_schema import validate_orders_csv

from .model import solve_schedule


ENGINE_NAME = "logistics-scheduling-engine"
ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "scheduling_v1"

TEMPORAL_REQUIREMENTS = {
    "orders": (
        "estimated_dispatch_date",
    ),
    "fleet": (
        "avg_speed_kmh",
        "driving_hours_per_day",
        "status",
        "available_from",
    ),
}


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def _date(value):
    return date.fromisoformat(value)


def _complete(report, column):
    return bool(
        report.get("completeness", {})
        .get(column, {})
        .get("complete")
    )


def _validate_temporal_evidence(orders_report, fleet_report):
    missing = []
    for column in TEMPORAL_REQUIREMENTS["orders"]:
        if not _complete(orders_report, column):
            missing.append(f"Orders.{column}")
    for column in TEMPORAL_REQUIREMENTS["fleet"]:
        if not _complete(fleet_report, column):
            missing.append(f"Fleet.{column}")
    if missing:
        raise ValueError(
            "Scheduling requiere datos temporales completos: "
            + ", ".join(missing)
            + "."
        )


def _validate_assignment_result(result):
    if not isinstance(result, dict):
        raise ValueError(
            "Scheduling requiere una corrida de Assignment aprobada."
        )
    if result.get("schema_version") != "assignment_v1":
        raise ValueError(
            "Scheduling sólo acepta Assignment V1 como entrada."
        )
    handoff = result.get("handoff") or {}
    if handoff.get("schema_version") != "scheduling_input_v1":
        raise ValueError(
            "El handoff de Assignment no es compatible con Scheduling."
        )
    selected = (
        result.get("scenarios", {})
        .get("selected", {})
    )
    trips = selected.get("trips")
    if not isinstance(trips, list) or not trips:
        raise ValueError(
            "Assignment no contiene viajes seleccionados para programar."
        )
    if handoff.get("trip_count") != len(trips):
        raise ValueError(
            "El handoff de Assignment no coincide con sus viajes seleccionados."
        )
    expected_ids = sorted(
        str(item.get("trip_id"))
        for item in trips
    )
    handoff_ids = sorted(
        str(value)
        for value in handoff.get("trip_ids", [])
    )
    if expected_ids != handoff_ids:
        raise ValueError(
            "Los IDs del handoff no coinciden con Assignment."
        )
    return selected, handoff


def _trip_signature(trip):
    return (
        trip["trip_id"],
        trip["vehicle_id"],
        trip["origin"],
        trip["destination"],
        tuple(
            sorted(
                (
                    load["order_id"],
                    int(load["units"]),
                    float(load["kg"]),
                )
                for load in trip["loads"]
            )
        ),
    )


def _prepare_trips(
    orders,
    fleet,
    assignment_trips,
    *,
    sla_enabled,
):
    by_order = {
        item["order_id"]: item
        for item in orders
    }
    by_vehicle = {
        item["vehicle_id"]: item
        for item in fleet
    }
    prepared = []

    for source in assignment_trips:
        vehicle_id = source.get("vehicle_id")
        if vehicle_id not in by_vehicle:
            raise ValueError(
                f"Assignment referencia el vehículo inexistente {vehicle_id}."
            )
        vehicle = by_vehicle[vehicle_id]
        if vehicle.get("status") != "available":
            raise ValueError(
                f"{vehicle_id} ya no figura disponible en el Data Pack de este caso."
            )

        load_orders = []
        for load in source.get("loads", []):
            order_id = load.get("order_id")
            if order_id not in by_order:
                raise ValueError(
                    f"El viaje {source.get('trip_id')} referencia la orden inexistente {order_id}."
                )
            load_orders.append(by_order[order_id])

        if not load_orders:
            raise ValueError(
                f"El viaje {source.get('trip_id')} no contiene órdenes."
            )

        ready_date = max(
            _date(order["estimated_dispatch_date"])
            for order in load_orders
        )
        available_from = _date(vehicle["available_from"])
        earliest = max(
            ready_date,
            available_from,
        )
        available_until = (
            _date(vehicle["available_until"])
            if vehicle.get("available_until")
            else None
        )

        daily_distance = (
            float(vehicle["avg_speed_kmh"])
            * float(vehicle["driving_hours_per_day"])
        )
        if daily_distance <= 0:
            raise ValueError(
                f"{vehicle_id} no tiene velocidad/horas válidas para Scheduling."
            )

        distance = float(source["distance_km"])
        transit_days = max(
            1,
            math.ceil(distance / daily_distance),
        )
        cycle_days = max(
            1,
            math.ceil((2 * distance) / daily_distance),
        )

        due_dates = {
            order["order_id"]: (
                _date(order["delivery_due_date"])
                if (
                    sla_enabled
                    and order.get("delivery_due_date")
                )
                else None
            )
            for order in load_orders
        }
        strictest_due = min(
            (
                value
                for value in due_dates.values()
                if value is not None
            ),
            default=None,
        )

        prepared.append(
            {
                "trip_id": source["trip_id"],
                "vehicle_id": vehicle_id,
                "order_ids": [
                    order["order_id"]
                    for order in load_orders
                ],
                "ready_date": ready_date,
                "earliest_dispatch": earliest,
                "available_until": available_until,
                "transit_days": transit_days,
                "cycle_days": cycle_days,
                "due_dates": due_dates,
                "strictest_due": strictest_due,
                "source": source,
            }
        )

    return prepared


def _greedy_offsets(trips, horizon_start):
    by_vehicle = defaultdict(list)
    for item in trips:
        by_vehicle[item["vehicle_id"]].append(item)

    offsets = {}
    for vehicle_id, items in by_vehicle.items():
        remaining = list(items)
        free = min(
            item["earliest_dispatch"]
            for item in remaining
        )

        while remaining:
            available = [
                item
                for item in remaining
                if item["earliest_dispatch"] <= free
            ]
            if not available:
                next_ready = min(
                    item["earliest_dispatch"]
                    for item in remaining
                )
                free = max(free, next_ready)
                available = [
                    item
                    for item in remaining
                    if item["earliest_dispatch"] <= free
                ]

            current = min(
                available,
                key=lambda item: (
                    item["strictest_due"] or date.max,
                    item["earliest_dispatch"],
                    item["cycle_days"],
                    item["trip_id"],
                ),
            )
            dispatch = max(
                free,
                current["earliest_dispatch"],
            )
            resource_free = (
                dispatch
                + timedelta(
                    days=current["cycle_days"]
                )
            )
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


def _materialize(
    trips,
    offsets,
    horizon_start,
):
    by_id = {
        item["trip_id"]: item
        for item in trips
    }
    result = []

    for trip_id, start_offset in sorted(
        offsets.items(),
        key=lambda item: (
            item[1],
            item[0],
        ),
    ):
        item = by_id[trip_id]
        dispatch = (
            horizon_start
            + timedelta(days=start_offset)
        )
        arrival = (
            dispatch
            + timedelta(
                days=item["transit_days"]
            )
        )
        resource_free = (
            dispatch
            + timedelta(
                days=item["cycle_days"]
            )
        )

        source = item["source"]
        result.append(
            {
                **source,
                "ready_date": (
                    item["ready_date"].isoformat()
                ),
                "dispatch_date": (
                    dispatch.isoformat()
                ),
                "arrival_date": (
                    arrival.isoformat()
                ),
                "transit_days": (
                    item["transit_days"]
                ),
                "cycle_days": (
                    item["cycle_days"]
                ),
                "resource_available_again": (
                    resource_free.isoformat()
                ),
                "wait_days": (
                    dispatch
                    - item["ready_date"]
                ).days,
                "delivery_due_date": (
                    item["strictest_due"].isoformat()
                    if item["strictest_due"]
                    else None
                ),
            }
        )

    return result


def _validate_schedule(
    scheduled,
    prepared,
    source_trips,
):
    source_by_id = {
        trip["trip_id"]: trip
        for trip in source_trips
    }
    prepared_by_id = {
        trip["trip_id"]: trip
        for trip in prepared
    }

    if {
        trip["trip_id"]
        for trip in scheduled
    } != set(source_by_id):
        raise ValueError(
            "Scheduling debe conservar exactamente todos los viajes de Assignment."
        )

    occupied_until = {}
    for trip in sorted(
        scheduled,
        key=lambda item: (
            item["vehicle_id"],
            item["dispatch_date"],
            item["trip_id"],
        ),
    ):
        source = source_by_id[
            trip["trip_id"]
        ]
        prepared_trip = prepared_by_id[
            trip["trip_id"]
        ]
        if _trip_signature(trip) != _trip_signature(source):
            raise ValueError(
                "Scheduling modificó una asignación upstream."
            )

        dispatch = _date(
            trip["dispatch_date"]
        )
        arrival = _date(
            trip["arrival_date"]
        )
        resource_free = _date(
            trip[
                "resource_available_again"
            ]
        )
        if (
            dispatch
            < prepared_trip[
                "earliest_dispatch"
            ]
        ):
            raise ValueError(
                "Scheduling programó un viaje antes de que carga o vehículo estuvieran disponibles."
            )
        if (
            arrival
            != dispatch
            + timedelta(
                days=prepared_trip[
                    "transit_days"
                ]
            )
        ):
            raise ValueError(
                "Fecha de llegada inconsistente."
            )
        if (
            resource_free
            != dispatch
            + timedelta(
                days=prepared_trip[
                    "cycle_days"
                ]
            )
        ):
            raise ValueError(
                "Disponibilidad futura inconsistente."
            )

        previous_free = occupied_until.get(
            trip["vehicle_id"]
        )
        if (
            previous_free
            and dispatch < previous_free
        ):
            raise ValueError(
                f"El vehículo {trip['vehicle_id']} tiene viajes superpuestos."
            )
        occupied_until[
            trip["vehicle_id"]
        ] = resource_free

        available_until = prepared_trip[
            "available_until"
        ]
        if (
            available_until
            and resource_free
            - timedelta(days=1)
            > available_until
        ):
            raise ValueError(
                f"{trip['vehicle_id']} queda ocupado fuera de su ventana de disponibilidad."
            )

    return True


def _summarize(
    scheduled,
    orders,
    *,
    sla_enabled,
):
    by_order = {
        item["order_id"]: item
        for item in orders
    }
    trips_by_order = defaultdict(list)

    for trip in scheduled:
        for load in trip["loads"]:
            trips_by_order[
                load["order_id"]
            ].append(trip)

    outcomes = []
    late_exceptions = []
    for order_id in sorted(
        trips_by_order
    ):
        source_order = by_order[order_id]
        trips = trips_by_order[order_id]
        arrival = max(
            _date(item["arrival_date"])
            for item in trips
        )
        first_dispatch = min(
            _date(item["dispatch_date"])
            for item in trips
        )
        ready = _date(
            source_order[
                "estimated_dispatch_date"
            ]
        )
        due = (
            _date(
                source_order[
                    "delivery_due_date"
                ]
            )
            if (
                sla_enabled
                and source_order.get(
                    "delivery_due_date"
                )
            )
            else None
        )
        late_days = (
            max(
                0,
                (arrival - due).days,
            )
            if due
            else None
        )

        outcome = {
            "order_id": order_id,
            "priority": source_order.get(
                "priority"
            ),
            "ready_date": (
                ready.isoformat()
            ),
            "first_dispatch_date": (
                first_dispatch.isoformat()
            ),
            "arrival_date": (
                arrival.isoformat()
            ),
            "delivery_due_date": (
                due.isoformat()
                if due
                else None
            ),
            "late_days": late_days,
            "on_time": (
                late_days == 0
                if late_days is not None
                else None
            ),
            "trip_ids": sorted(
                item["trip_id"]
                for item in trips
            ),
            "vehicle_ids": sorted(
                {
                    item["vehicle_id"]
                    for item in trips
                }
            ),
            "lead_time_days": (
                arrival - ready
            ).days,
        }
        outcomes.append(outcome)
        if late_days:
            late_exceptions.append(
                {
                    "order_id": order_id,
                    "priority": (
                        source_order.get(
                            "priority"
                        )
                    ),
                    "deadline": (
                        due.isoformat()
                    ),
                    "arrival_date": (
                        arrival.isoformat()
                    ),
                    "late_days": late_days,
                    "trip_ids": (
                        outcome["trip_ids"]
                    ),
                }
            )

    due_outcomes = [
        item
        for item in outcomes
        if item["late_days"] is not None
    ]
    dispatches = [
        _date(item["dispatch_date"])
        for item in scheduled
    ]
    returns = [
        _date(
            item[
                "resource_available_again"
            ]
        )
        for item in scheduled
    ]
    waits = [
        int(item["wait_days"])
        for item in scheduled
    ]
    cycle_days = [
        int(item["cycle_days"])
        for item in scheduled
    ]
    lead_times = [
        int(item["lead_time_days"])
        for item in outcomes
    ]

    metrics = {
        "orders": len(outcomes),
        "total_trips": len(
            scheduled
        ),
        "vehicles_used": len(
            {
                item["vehicle_id"]
                for item in scheduled
            }
        ),
        "schedule_start": (
            min(dispatches).isoformat()
            if dispatches
            else None
        ),
        "schedule_end": (
            max(returns).isoformat()
            if returns
            else None
        ),
        "makespan_days": (
            (
                max(returns)
                - min(dispatches)
            ).days
            if dispatches
            else 0
        ),
        "total_wait_days": sum(
            waits
        ),
        "avg_wait_days": (
            sum(waits) / len(waits)
            if waits
            else 0
        ),
        "max_wait_days": max(
            waits,
            default=0,
        ),
        "total_busy_days": sum(
            cycle_days
        ),
        "avg_cycle_days": (
            sum(cycle_days)
            / len(cycle_days)
            if cycle_days
            else 0
        ),
        "avg_lead_time_days": (
            sum(lead_times)
            / len(lead_times)
            if lead_times
            else 0
        ),
        "due_orders": len(
            due_outcomes
        ),
        "on_time_orders": sum(
            item["on_time"] is True
            for item in due_outcomes
        ),
        "late_orders": len(
            late_exceptions
        ),
        "on_time_rate": (
            sum(
                item["on_time"] is True
                for item in due_outcomes
            )
            / len(due_outcomes)
            if due_outcomes
            else None
        ),
        "total_late_days": sum(
            item["late_days"] or 0
            for item in due_outcomes
        ),
        "max_late_days": max(
            (
                item["late_days"] or 0
                for item in due_outcomes
            ),
            default=0,
        ),
    }

    return {
        "metrics": metrics,
        "trips": scheduled,
        "order_outcomes": outcomes,
        "exceptions": late_exceptions,
    }


def _schedule_signature(scheduled):
    return [
        (
            trip["trip_id"],
            trip["vehicle_id"],
            trip["dispatch_date"],
            trip["arrival_date"],
            trip[
                "resource_available_again"
            ],
        )
        for trip in sorted(
            scheduled,
            key=lambda item: item[
                "trip_id"
            ],
        )
    ]


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
    config = (
        SchedulingConfig.model_validate(
            configuration or {}
        ).model_dump()
    )
    opts = (
        SchedulingOptions.model_validate(
            options or {}
        ).model_dump()
    )

    def notify(stage):
        if (
            perf_counter() - started
            > opts["total_time_limit_s"]
        ):
            raise TimeoutError(
                "Se agotó el presupuesto global de Scheduling."
            )
        if progress:
            progress(stage)

    notify("validating")
    orders_report = validate_orders_csv(
        orders_bytes
    )
    fleet_report = validate_fleet_csv(
        fleet_bytes
    )
    _validate_temporal_evidence(
        orders_report,
        fleet_report,
    )
    selected_assignment, handoff = (
        _validate_assignment_result(
            assignment_result
        )
    )

    sla_available = _complete(
        orders_report,
        "delivery_due_date",
    )
    sla_enabled = bool(
        config[
            "use_delivery_due_dates"
        ]
        and sla_available
    )

    prepared = _prepare_trips(
        orders_report["records"],
        fleet_report["records"],
        selected_assignment["trips"],
        sla_enabled=sla_enabled,
    )
    horizon_start = min(
        item["earliest_dispatch"]
        for item in prepared
    )

    notify("constructing")
    greedy_hint = _greedy_offsets(
        prepared,
        horizon_start,
    )
    if greedy_hint is None:
        raise ValueError(
            "No existe una secuencia temporal factible dentro de las ventanas de disponibilidad."
        )

    notify("optimizing:service")
    solved, solver_meta = solve_schedule(
        prepared,
        horizon_start=horizon_start,
        max_horizon_days=opts[
            "max_horizon_days"
        ],
        use_due_dates=sla_enabled,
        solve_time_limit_s=opts[
            "solve_time_limit_s"
        ],
        deterministic_limit=opts[
            "deterministic_limit"
        ],
        hint=greedy_hint,
    )

    if solved:
        offsets = {
            item["trip_id"]: int(
                item["start_offset"]
            )
            for item in solved
        }
    else:
        if solver_meta.get("status") == "infeasible":
            raise ValueError(
                solver_meta.get(
                    "reason"
                )
                or "No existe una programación temporal factible."
            )
        offsets = greedy_hint
        solver_meta = {
            **solver_meta,
            "status": "feasible",
            "method": "heuristic_fallback",
            "gap": None,
        }

    scheduled = _materialize(
        prepared,
        offsets,
        horizon_start,
    )
    _validate_schedule(
        scheduled,
        prepared,
        selected_assignment[
            "trips"
        ],
    )

    notify("summarizing")
    summary = _summarize(
        scheduled,
        orders_report[
            "records"
        ],
        sla_enabled=sla_enabled,
    )
    metrics = summary["metrics"]
    decision_status = (
        "recommended_with_exceptions"
        if metrics["late_orders"]
        else "recommended"
    )
    schedule_fingerprint = _digest(
        _schedule_signature(
            scheduled
        )
    )

    result = {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "decision": {
            "id": (
                "logistics_scheduling"
            ),
            "status": decision_status,
            "strategy": config[
                "strategy"
            ],
            "label": (
                "Planificación recomendada"
            ),
        },
        "engine": {
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "executed_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "solver": solver_meta,
        },
        "analysis": {
            "temporal": True,
            "assignment_locked": True,
            "sla_available": (
                sla_available
            ),
            "sla_enabled": (
                sla_enabled
            ),
            "objective_hierarchy": (
                [
                    "late_orders",
                    "total_late_days",
                    "total_wait_days",
                    "makespan",
                ]
                if sla_enabled
                else [
                    "total_wait_days",
                    "makespan",
                ]
            ),
        },
        "inputs": {
            "orders": {
                "sha256": (
                    hashlib.sha256(
                        orders_bytes
                    ).hexdigest()
                ),
                "rows": (
                    orders_report[
                        "rows"
                    ]
                ),
                **(
                    inputs
                    or {}
                ).get(
                    "orders",
                    {},
                ),
            },
            "fleet": {
                "sha256": (
                    hashlib.sha256(
                        fleet_bytes
                    ).hexdigest()
                ),
                "rows": (
                    fleet_report[
                        "rows"
                    ]
                ),
                **(
                    inputs
                    or {}
                ).get(
                    "fleet",
                    {},
                ),
            },
            "assignment": {
                "schema_version": (
                    assignment_result[
                        "schema_version"
                    ]
                ),
                "result_fingerprint": (
                    assignment_result.get(
                        "result_fingerprint"
                    )
                ),
                "assignment_fingerprint": (
                    handoff[
                        "assignment_fingerprint"
                    ]
                ),
                "trip_count": (
                    handoff[
                        "trip_count"
                    ]
                ),
                **(
                    inputs
                    or {}
                ).get(
                    "assignment",
                    {},
                ),
            },
        },
        "configuration": {
            **config,
            "options": opts,
        },
        "decision_drivers": {
            "trips_sequenced": (
                metrics[
                    "total_trips"
                ]
            ),
            "vehicles_used": (
                metrics[
                    "vehicles_used"
                ]
            ),
            "late_orders": (
                metrics[
                    "late_orders"
                ]
            ),
            "total_late_days": (
                metrics[
                    "total_late_days"
                ]
            ),
            "total_wait_days": (
                metrics[
                    "total_wait_days"
                ]
            ),
            "makespan_days": (
                metrics[
                    "makespan_days"
                ]
            ),
        },
        "exceptions": summary[
            "exceptions"
        ],
        "scenarios": {
            "selected": {
                "name": (
                    "Planificación recomendada"
                ),
                "feasible": True,
                "solver": solver_meta,
                "metrics": metrics,
                "trips": summary[
                    "trips"
                ],
                "order_outcomes": (
                    summary[
                        "order_outcomes"
                    ]
                ),
                "schedule_fingerprint": (
                    schedule_fingerprint
                ),
            }
        },
        "assumptions": [
            (
                "Scheduling conserva exactamente "
                "los viajes, cargas y vehicle_id "
                "aprobados en Assignment."
            ),
            (
                "La fecha mínima de salida de un viaje "
                "es la más tardía entre sus órdenes y "
                "la disponibilidad inicial del vehículo."
            ),
            (
                "La duración diaria usa distance_km, "
                "avg_speed_kmh y driving_hours_per_day."
            ),
            (
                "El vehículo queda ocupado hasta "
                "completar ida, entrega y retorno "
                "a su base."
            ),
            (
                "No se modelan horas intradía, "
                "descansos regulatorios detallados, "
                "tráfico, clima ni tiempos de carga/descarga."
            ),
            (
                "delivery_due_date participa sólo "
                "cuando está completo en Orders."
            ),
        ],
        "handoff": {
            "schema_version": (
                "final_assignment_input_v1"
            ),
            "source_decision": (
                "logistics_scheduling"
            ),
            "next_decision": (
                "logistics_final_assignment"
            ),
            "source_path": (
                "scenarios.selected.trips"
            ),
            "assignment_fingerprint": (
                handoff[
                    "assignment_fingerprint"
                ]
            ),
            "schedule_fingerprint": (
                schedule_fingerprint
            ),
            "trip_count": (
                metrics[
                    "total_trips"
                ]
            ),
            "trip_ids": [
                trip["trip_id"]
                for trip in scheduled
            ],
        },
    }

    stable = {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "version": (
            ENGINE_VERSION
        ),
        "configuration": result[
            "configuration"
        ],
        "orders_hash": result[
            "inputs"
        ]["orders"]["sha256"],
        "fleet_hash": result[
            "inputs"
        ]["fleet"]["sha256"],
        "assignment_fingerprint": (
            handoff[
                "assignment_fingerprint"
            ]
        ),
        "schedule": (
            _schedule_signature(
                scheduled
            )
        ),
        "metrics": metrics,
    }
    result[
        "result_fingerprint"
    ] = _digest(stable)
    result["engine"]["wall_ms"] = int(
        (
            perf_counter()
            - started
        )
        * 1000
    )
    return result
