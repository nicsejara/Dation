"""Bounded CP-SAT slot formulation. All hard constraints use integer grams/units."""
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
    transit,
    cycle_days,
)
from .plans import trip, add_load, canonical

MAX_VARIABLES = 25000


def solve(orders, fleet, weights, scales, options, hint_plan=None):
    started = perf_counter()
    model = cp_model.CpModel()
    slots = []
    xs = defaultdict(list)
    resource_intervals = defaultdict(list)
    hints = defaultdict(list)

    for t in hint_plan or []:
        hints[
            (
                (t['origin'], t['destination']),
                t['dispatch_date'],
                t['fleet_pool_id'],
            )
        ].append(
            {l['order_id']: l['units'] for l in t['loads']}
        )

    groups = defaultdict(list)
    for i, order in enumerate(orders):
        groups[(order['origin'], order['destination'])].append(i)

    horizon_start = min(
        date.fromisoformat(order['dispatch_date'])
        for order in orders
    )

    count = 0
    for route, indices in sorted(groups.items()):
        for vehicle in sorted(
            fleet,
            key=lambda v: (
                v['base_location'],
                v['vehicle_type'],
                v['fleet_pool_id'],
            ),
        ):
            days = defaultdict(list)
            for i in indices:
                order = orders[i]
                if (
                    not capacity_units(order, vehicle)
                    or vehicle['units_available'] == 0
                ):
                    continue
                for day in departure_days(order, vehicle, fleet):
                    days[day].append(i)

            for day, eligible in sorted(days.items()):
                limit = sum(
                    math.ceil(
                        orders[i]['quantity_units']
                        / capacity_units(orders[i], vehicle)
                    )
                    for i in eligible
                )
                if vehicle['units_available'] is not None:
                    limit = min(limit, vehicle['units_available'])
                count += limit * (len(eligible) + 1)
                if count > MAX_VARIABLES:
                    return None, {
                        'status': 'timeout',
                        'method': 'heuristic',
                        'reason': 'Presupuesto de tamaño del modelo',
                        'gap': None,
                        'wall_ms': int((perf_counter() - started) * 1000),
                    }

                previous = None
                for j in range(limit):
                    y = model.new_bool_var(f'y{len(slots)}')
                    loads = []
                    seeds = hints[
                        (route, day, vehicle['fleet_pool_id'])
                    ]
                    seed = seeds[j] if j < len(seeds) else {}
                    if hint_plan is not None:
                        model.add_hint(y, int(bool(seed)))
                    if previous is not None:
                        model.add(y <= previous)
                    previous = y

                    for i in eligible:
                        order = orders[i]
                        upper = min(
                            order['quantity_units'],
                            capacity_units(order, vehicle),
                        )
                        x = model.new_int_var(
                            0,
                            upper,
                            f'x{i}_{len(slots)}',
                        )
                        model.add(x <= upper * y)
                        xs[i].append(x)
                        loads.append((i, x))
                        if hint_plan is not None:
                            model.add_hint(
                                x,
                                seed.get(order['order_id'], 0),
                            )

                    model.add(
                        sum(
                            int(D(orders[i]['unit_weight_kg']) * 1000) * x
                            for i, x in loads
                        )
                        <= int(D(vehicle['capacity_kg']) * 1000) * y
                    )
                    model.add(sum(x for _, x in loads) >= y)
                    slots.append((vehicle, day, y, loads))
                    if vehicle['units_available'] is not None:
                        duration = cycle_days(orders[eligible[0]], vehicle)
                        start_offset = (
                            date.fromisoformat(day) - horizon_start
                        ).days
                        interval = model.new_optional_interval_var(
                            start_offset,
                            duration,
                            start_offset + duration,
                            y,
                            f'iv{len(slots) - 1}',
                        )
                        resource_intervals[
                            vehicle['fleet_pool_id']
                        ].append(interval)

    for i, order in enumerate(orders):
        model.add(sum(xs[i]) == order['quantity_units'])

    for vehicle in fleet:
        if vehicle['units_available'] is None:
            continue
        intervals = resource_intervals.get(vehicle['fleet_pool_id'], [])
        if intervals:
            model.add_cumulative(
                intervals,
                [1] * len(intervals),
                vehicle['units_available'],
            )

    cost = sum(
        float(raw_cost(orders[loads[0][0]], vehicle)) * y
        for vehicle, day, y, loads in slots
    )
    trips = sum(y for _, _, y, _ in slots)
    units = sum(order['quantity_units'] for order in orders)
    time = sum(
        (
            (
                date.fromisoformat(day)
                - date.fromisoformat(orders[i]['dispatch_date'])
            ).days
            + transit(orders[i], vehicle)
        )
        * x
        for vehicle, day, y, loads in slots
        for i, x in loads
    )
    score = (
        weights['cost'] / scales['cost'] * cost
        + weights['trips'] / scales['trips'] * trips
        + weights['time'] / scales['time'] / units * time
    )
    model.minimize(score)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_deterministic_time = options['deterministic_limit']
    solver.parameters.max_time_in_seconds = options['solve_time_limit_s']
    status = solver.solve(model)
    proto = solver.response_proto
    name = solver.status_name(status).lower()
    meta = {
        'name': 'OR-Tools CP-SAT',
        'version': ortools.__version__,
        'status': name,
        'gap': None,
        'seed': 0,
        'time_limit_s': options['solve_time_limit_s'],
        'deterministic_limit': options['deterministic_limit'],
        'deterministic_time': proto.deterministic_time,
        'wall_ms': int((perf_counter() - started) * 1000),
        'method': 'cp_sat',
    }
    if (
        status == cp_model.UNKNOWN
        and proto.deterministic_time + 1e-6
        < options['deterministic_limit']
    ):
        raise TimeoutError(
            'El tiempo de reloj fue insuficiente para completar '
            'el presupuesto determinístico.'
        )
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        meta['status'] = (
            'infeasible'
            if status == cp_model.INFEASIBLE
            else 'timeout'
        )
        return None, meta

    if (
        status != cp_model.OPTIMAL
        and proto.deterministic_time + 1e-6
        < options['deterministic_limit']
    ):
        raise TimeoutError(
            'El límite de reloj interrumpió la búsqueda determinística. '
            'Aumentá el tiempo por escenario.'
        )

    meta['gap'] = (
        abs(solver.objective_value - solver.best_objective_bound)
        / max(1, abs(solver.objective_value))
    )
    plan = []
    for vehicle, day, y, loads in slots:
        if not solver.value(y):
            continue
        selected = [
            (i, solver.value(x))
            for i, x in loads
            if solver.value(x)
        ]
        current = trip(orders[selected[0][0]], vehicle, day)
        for i, quantity in selected:
            add_load(current, orders[i], quantity)
        plan.append(current)
    return canonical(plan), meta
