"""CP-SAT dispatch model with lexicographic SLA-first optimization."""
from collections import defaultdict
from datetime import date
import math
from time import perf_counter

from ortools.sat.python import cp_model
import ortools

from .normalization import (
    D,
    capacity_units,
    departure_days,
    raw_cost,
    raw_co2,
    transit,
    cycle_days,
    lateness_days,
)
from .plans import (
    PRIORITY_WEIGHT,
    trip,
    add_load,
    canonical,
)

MAX_VARIABLES = 30000


def _solver(options):
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_deterministic_time = options[
        "deterministic_limit"
    ]
    solver.parameters.max_time_in_seconds = options[
        "solve_time_limit_s"
    ]
    return solver


def _extract_plan(solver, slots, orders):
    plan = []
    for vehicle, day, y, loads in slots:
        if not solver.value(y):
            continue
        selected = [
            (index, solver.value(variable))
            for index, variable, _ in loads
            if solver.value(variable)
        ]
        if not selected:
            continue
        current = trip(
            orders[selected[0][0]],
            vehicle,
            day,
        )
        for index, quantity in selected:
            add_load(
                current,
                orders[index],
                quantity,
            )
        plan.append(current)
    return canonical(plan)


def solve(
    orders,
    fleet,
    weights,
    scales,
    options,
    hint_plan=None,
):
    started = perf_counter()
    model = cp_model.CpModel()
    slots = []
    xs = defaultdict(list)
    resource_intervals = defaultdict(list)
    load_presence = defaultdict(list)
    hints = defaultdict(list)

    for current in hint_plan or []:
        hints[
            (
                (
                    current["origin"],
                    current["destination"],
                ),
                current["dispatch_date"],
                current["fleet_pool_id"],
            )
        ].append(
            {
                load["order_id"]: load["units"]
                for load in current["loads"]
            }
        )

    groups = defaultdict(list)
    for index, order in enumerate(orders):
        groups[
            (order["origin"], order["destination"])
        ].append(index)

    horizon_start = min(
        date.fromisoformat(order["dispatch_date"])
        for order in orders
    )
    variable_count = 0

    for route, indices in sorted(groups.items()):
        for vehicle in sorted(
            fleet,
            key=lambda item: (
                item["base_location"],
                item["vehicle_type"],
                item["fleet_pool_id"],
            ),
        ):
            days = defaultdict(list)
            for index in indices:
                order = orders[index]
                if (
                    not capacity_units(order, vehicle)
                    or vehicle["units_available"] == 0
                ):
                    continue
                for day in departure_days(
                    order,
                    vehicle,
                    fleet,
                    max_late_days=options["max_late_days"],
                ):
                    days[day].append(index)

            for day, eligible in sorted(days.items()):
                limit = sum(
                    math.ceil(
                        orders[index]["quantity_units"]
                        / capacity_units(
                            orders[index],
                            vehicle,
                        )
                    )
                    for index in eligible
                )
                if vehicle["units_available"] is not None:
                    limit = min(
                        limit,
                        vehicle["units_available"],
                    )

                variable_count += limit * (
                    2 * len(eligible) + 2
                )
                if variable_count > MAX_VARIABLES:
                    return None, {
                        "status": "timeout",
                        "method": "heuristic",
                        "reason": (
                            "Presupuesto de tamaño del modelo"
                        ),
                        "gap": None,
                        "sla_status": "not_run",
                        "sla_certified": False,
                        "wall_ms": int(
                            (perf_counter() - started) * 1000
                        ),
                    }

                previous = None
                for slot_index in range(limit):
                    y = model.new_bool_var(
                        f"y{len(slots)}"
                    )
                    loads = []
                    seed_rows = hints[
                        (
                            route,
                            day,
                            vehicle["fleet_pool_id"],
                        )
                    ]
                    seed = (
                        seed_rows[slot_index]
                        if slot_index < len(seed_rows)
                        else {}
                    )
                    if hint_plan is not None:
                        model.add_hint(
                            y,
                            int(bool(seed)),
                        )
                    if previous is not None:
                        model.add(y <= previous)
                    previous = y

                    for index in eligible:
                        order = orders[index]
                        upper = min(
                            order["quantity_units"],
                            capacity_units(
                                order,
                                vehicle,
                            ),
                        )
                        x = model.new_int_var(
                            0,
                            upper,
                            f"x{index}_{len(slots)}",
                        )
                        used = model.new_bool_var(
                            f"z{index}_{len(slots)}",
                        )
                        model.add(x <= upper * used)
                        model.add(x >= used)
                        model.add(used <= y)
                        xs[index].append(x)
                        late = lateness_days(
                            order,
                            vehicle,
                            day,
                        )
                        load_presence[index].append(
                            (used, late)
                        )
                        loads.append(
                            (index, x, used)
                        )
                        if hint_plan is not None:
                            model.add_hint(
                                x,
                                seed.get(
                                    order["order_id"],
                                    0,
                                ),
                            )

                    model.add(
                        sum(
                            int(
                                D(
                                    orders[index][
                                        "unit_weight_kg"
                                    ]
                                )
                                * 1000
                            )
                            * x
                            for index, x, _ in loads
                        )
                        <= int(
                            D(vehicle["capacity_kg"])
                            * 1000
                        )
                        * y
                    )
                    model.add(
                        sum(
                            x
                            for _, x, _ in loads
                        )
                        >= y
                    )

                    slots.append(
                        (vehicle, day, y, loads)
                    )

                    if (
                        vehicle["units_available"]
                        is not None
                    ):
                        duration = cycle_days(
                            orders[eligible[0]],
                            vehicle,
                        )
                        start_offset = (
                            date.fromisoformat(day)
                            - horizon_start
                        ).days
                        interval = (
                            model.new_optional_interval_var(
                                start_offset,
                                duration,
                                start_offset + duration,
                                y,
                                f"iv{len(slots) - 1}",
                            )
                        )
                        resource_intervals[
                            vehicle["fleet_pool_id"]
                        ].append(interval)

    for index, order in enumerate(orders):
        if not xs[index]:
            return None, {
                "status": "infeasible",
                "method": "cp_sat",
                "gap": None,
                "sla_status": "infeasible",
                "sla_certified": True,
                "reason": (
                    "Una orden no tiene slots de asignación "
                    "dentro del horizonte de recuperación."
                ),
                "wall_ms": int(
                    (perf_counter() - started) * 1000
                ),
            }
        model.add(
            sum(xs[index])
            == order["quantity_units"]
        )

    for vehicle in fleet:
        if vehicle["units_available"] is None:
            continue
        intervals = resource_intervals.get(
            vehicle["fleet_pool_id"],
            [],
        )
        if intervals:
            model.add_cumulative(
                intervals,
                [1] * len(intervals),
                vehicle["units_available"],
            )

    late_order_vars = []
    late_day_vars = []
    max_secondary = 0

    for index, order in enumerate(orders):
        late_candidates = [
            (used, late)
            for used, late in load_presence[index]
            if late > 0
        ]
        maximum = max(
            [late for _, late in late_candidates],
            default=0,
        )
        late_order = model.new_bool_var(
            f"late_order_{index}"
        )
        late_days = model.new_int_var(
            0,
            maximum,
            f"late_days_{index}",
        )

        if late_candidates:
            for used, late in late_candidates:
                model.add(late_order >= used)
                model.add(late_days >= late * used)
            model.add(
                late_order
                <= sum(
                    used
                    for used, _ in late_candidates
                )
            )
        else:
            model.add(late_order == 0)
            model.add(late_days == 0)

        late_order_vars.append(late_order)
        late_day_vars.append(late_days)
        max_secondary += (
            PRIORITY_WEIGHT[order["priority"]]
            * maximum
        )

    late_count = sum(late_order_vars)
    weighted_late_days = sum(
        PRIORITY_WEIGHT[orders[index]["priority"]]
        * late_day_vars[index]
        for index in range(len(orders))
    )
    late_count_multiplier = max_secondary + 1
    sla_score = (
        late_count * late_count_multiplier
        + weighted_late_days
    )

    # Stage 1: establish the best service level before considering business
    # economics. If optimality is not proven, the second stage may only keep
    # or improve the best SLA incumbent found.
    model.minimize(sla_score)
    sla_solver = _solver(options)
    sla_status = sla_solver.solve(model)
    sla_name = sla_solver.status_name(
        sla_status
    ).lower()

    base_meta = {
        "name": "OR-Tools CP-SAT",
        "version": ortools.__version__,
        "status": sla_name,
        "gap": None,
        "seed": 0,
        "time_limit_s": options[
            "solve_time_limit_s"
        ],
        "deterministic_limit": options[
            "deterministic_limit"
        ],
        "wall_ms": int(
            (perf_counter() - started) * 1000
        ),
        "method": "cp_sat",
        "sla_status": sla_name,
        "sla_certified": (
            sla_status == cp_model.OPTIMAL
        ),
    }

    if sla_status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        base_meta["status"] = (
            "infeasible"
            if sla_status == cp_model.INFEASIBLE
            else "timeout"
        )
        return None, base_meta

    best_sla_score = int(
        round(sla_solver.objective_value)
    )
    best_late_orders = sum(
        sla_solver.value(variable)
        for variable in late_order_vars
    )
    best_weighted_late_days = sum(
        PRIORITY_WEIGHT[
            orders[index]["priority"]
        ]
        * sla_solver.value(late_day_vars[index])
        for index in range(len(orders))
    )
    base_meta.update(
        {
            "sla_score": best_sla_score,
            "minimum_late_orders": (
                best_late_orders
            ),
            "minimum_priority_weighted_late_days": (
                best_weighted_late_days
            ),
        }
    )

    if sla_status == cp_model.OPTIMAL:
        model.add(sla_score == best_sla_score)
    else:
        model.add(sla_score <= best_sla_score)

    cost = sum(
        float(
            raw_cost(
                orders[loads[0][0]],
                vehicle,
            )
        )
        * y
        for vehicle, _, y, loads in slots
    )
    co2 = sum(
        float(
            raw_co2(
                orders[loads[0][0]],
                vehicle,
            )
        )
        * y
        for vehicle, _, y, loads in slots
    )
    trips = sum(
        y
        for _, _, y, _ in slots
    )
    units = sum(
        order["quantity_units"]
        for order in orders
    )
    time = sum(
        (
            (
                date.fromisoformat(day)
                - date.fromisoformat(
                    orders[index]["dispatch_date"]
                )
            ).days
            + transit(
                orders[index],
                vehicle,
            )
        )
        * x
        for vehicle, day, _, loads in slots
        for index, x, _ in loads
    )
    outsourced_weight = sum(
        float(
            D(orders[index]["unit_weight_kg"])
        )
        * x
        for vehicle, _, _, loads in slots
        if vehicle["ownership"] == "third_party"
        for index, x, _ in loads
    )

    business_terms = {
        "cost": cost,
        "time": time / max(units, 1),
        "utilization": outsourced_weight,
        "co2": co2,
    }
    business_score = sum(
        weights[key]
        / max(scales[key], 1e-9)
        * business_terms[key]
        for key in weights
    )
    # Trips are intentionally not a configurable objective anymore. This tiny
    # deterministic tie-break keeps equally scored solutions compact.
    model.minimize(
        business_score
        + 1e-8 * trips
    )

    business_solver = _solver(options)
    business_status = business_solver.solve(
        model
    )

    if business_status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        # The SLA incumbent is still a complete valid solution and is safer
        # than publishing a partial result when stage 2 times out.
        plan = _extract_plan(
            sla_solver,
            slots,
            orders,
        )
        return plan, {
            **base_meta,
            "status": "feasible",
            "method": "sla_incumbent",
            "business_status": (
                business_solver.status_name(
                    business_status
                ).lower()
            ),
            "gap": None,
            "wall_ms": int(
                (perf_counter() - started) * 1000
            ),
        }

    proto = business_solver.response_proto
    business_name = business_solver.status_name(
        business_status
    ).lower()
    gap = (
        abs(
            business_solver.objective_value
            - business_solver.best_objective_bound
        )
        / max(
            1,
            abs(business_solver.objective_value),
        )
    )
    plan = _extract_plan(
        business_solver,
        slots,
        orders,
    )
    return plan, {
        **base_meta,
        "status": business_name,
        "business_status": business_name,
        "gap": gap,
        "deterministic_time": (
            proto.deterministic_time
        ),
        "wall_ms": int(
            (perf_counter() - started) * 1000
        ),
        "method": "cp_sat_lexicographic",
    }
