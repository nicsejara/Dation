"""Temporal CP-SAT model for Scheduling.

The upstream Assignment is immutable: this model only chooses start dates.
"""

from collections import defaultdict
from datetime import date
import math
from time import perf_counter

from ortools.sat.python import cp_model
import ortools


def _days(value, origin):
    return (value - origin).days


def solve_schedule(
    trips,
    *,
    horizon_start,
    max_horizon_days,
    use_due_dates,
    solve_time_limit_s,
    deterministic_limit,
    hint=None,
):
    started = perf_counter()
    if not trips:
        return [], {
            "name": "OR-Tools CP-SAT",
            "version": ortools.__version__,
            "status": "optimal",
            "method": "cp_sat",
            "gap": 0.0,
            "wall_ms": 0,
        }

    model = cp_model.CpModel()
    max_cycle = max(item["cycle_days"] for item in trips)
    max_transit = max(item["transit_days"] for item in trips)
    horizon_end = max_horizon_days + max_cycle + max_transit + 2

    variables = []
    intervals_by_vehicle = defaultdict(list)
    arrivals_by_order = defaultdict(list)

    for index, item in enumerate(trips):
        earliest = _days(item["earliest_dispatch"], horizon_start)
        latest_start = max_horizon_days
        if item.get("available_until"):
            latest_resource_end = (
                _days(item["available_until"], horizon_start) + 1
            )
            latest_start = min(
                latest_start,
                latest_resource_end - item["cycle_days"],
            )

        if latest_start < earliest:
            return None, {
                "name": "OR-Tools CP-SAT",
                "version": ortools.__version__,
                "status": "infeasible",
                "method": "cp_sat",
                "gap": None,
                "reason": (
                    f"{item['vehicle_id']} no tiene una ventana temporal "
                    f"suficiente para {item['trip_id']}."
                ),
                "wall_ms": int((perf_counter() - started) * 1000),
            }

        start = model.new_int_var(
            earliest,
            latest_start,
            f"start_{index}",
        )
        end = model.new_int_var(
            earliest + item["cycle_days"],
            latest_start + item["cycle_days"],
            f"end_{index}",
        )
        model.add(end == start + item["cycle_days"])
        interval = model.new_interval_var(
            start,
            item["cycle_days"],
            end,
            f"interval_{index}",
        )
        arrival = model.new_int_var(
            earliest + item["transit_days"],
            latest_start + item["transit_days"],
            f"arrival_{index}",
        )
        model.add(arrival == start + item["transit_days"])

        if hint and item["trip_id"] in hint:
            hinted = hint[item["trip_id"]]
            if earliest <= hinted <= latest_start:
                model.add_hint(start, hinted)

        intervals_by_vehicle[item["vehicle_id"]].append(interval)
        for order_id in item["order_ids"]:
            arrivals_by_order[order_id].append(arrival)

        variables.append(
            {
                "trip": item,
                "start": start,
                "end": end,
                "arrival": arrival,
                "earliest": earliest,
            }
        )

    for intervals in intervals_by_vehicle.values():
        if len(intervals) > 1:
            model.add_no_overlap(intervals)

    wait_terms = [
        row["start"] - row["earliest"]
        for row in variables
    ]
    total_wait = sum(wait_terms) if wait_terms else 0

    makespan = model.new_int_var(
        0,
        horizon_end,
        "makespan",
    )
    model.add_max_equality(
        makespan,
        [row["end"] for row in variables],
    )

    late_bools = []
    late_days_vars = []
    late_day_bounds = []
    if use_due_dates:
        order_due = {}
        for item in trips:
            for order_id, due in item["due_dates"].items():
                if due is not None:
                    order_due[order_id] = due

        for order_id, due in sorted(order_due.items()):
            arrivals = arrivals_by_order[order_id]
            order_arrival = model.new_int_var(
                0,
                horizon_end,
                f"order_arrival_{order_id}",
            )
            model.add_max_equality(order_arrival, arrivals)
            due_offset = _days(due, horizon_start)

            late_upper = max(
                0,
                horizon_end - due_offset,
            )
            late_days = model.new_int_var(
                0,
                late_upper,
                f"late_days_{order_id}",
            )
            late_day_bounds.append(
                late_upper
            )
            model.add_max_equality(
                late_days,
                [order_arrival - due_offset, 0],
            )
            is_late = model.new_bool_var(
                f"late_{order_id}"
            )
            model.add(late_days >= 1).only_enforce_if(is_late)
            model.add(late_days == 0).only_enforce_if(is_late.Not())

            late_days_vars.append(late_days)
            late_bools.append(is_late)

    max_wait = len(trips) * max_horizon_days
    wait_weight = horizon_end + 1
    lower_max = max_wait * wait_weight + horizon_end

    if late_days_vars:
        total_late_days = sum(late_days_vars)
        max_late_sum = sum(
            late_day_bounds
        )
        late_days_weight = lower_max + 1
        late_count_weight = (
            max_late_sum * late_days_weight
            + lower_max
            + 1
        )
        objective = (
            sum(late_bools) * late_count_weight
            + total_late_days * late_days_weight
            + total_wait * wait_weight
            + makespan
        )
    else:
        objective = (
            total_wait * wait_weight
            + makespan
        )

    # Guard against integer overflow in unusually large inputs.
    if late_days_vars and late_count_weight * max(1, len(late_bools)) > 8_000_000_000_000_000_000:
        return None, {
            "name": "OR-Tools CP-SAT",
            "version": ortools.__version__,
            "status": "skipped",
            "method": "cp_sat",
            "gap": None,
            "reason": "El modelo temporal supera el rango seguro del objetivo entero.",
            "wall_ms": int((perf_counter() - started) * 1000),
        }

    model.minimize(objective)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = solve_time_limit_s
    solver.parameters.max_deterministic_time = deterministic_limit

    status = solver.solve(model)
    status_name = solver.status_name(status).lower()
    meta = {
        "name": "OR-Tools CP-SAT",
        "version": ortools.__version__,
        "status": status_name,
        "method": "cp_sat",
        "seed": 0,
        "time_limit_s": solve_time_limit_s,
        "deterministic_limit": deterministic_limit,
        "gap": None,
        "wall_ms": int((perf_counter() - started) * 1000),
    }

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        meta["status"] = (
            "infeasible"
            if status == cp_model.INFEASIBLE
            else "timeout"
        )
        return None, meta

    objective_value = float(solver.objective_value)
    bound = float(solver.best_objective_bound)
    meta["gap"] = (
        abs(objective_value - bound)
        / max(1.0, abs(objective_value))
    )
    meta["deterministic_time"] = (
        solver.response_proto.deterministic_time
    )

    scheduled = []
    for row in variables:
        item = row["trip"]
        scheduled.append(
            {
                "trip_id": item["trip_id"],
                "start_offset": solver.value(row["start"]),
            }
        )

    return scheduled, meta
