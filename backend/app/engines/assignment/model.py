"""CP-SAT model for non-temporal logistics Assignment."""

from collections import defaultdict
import math
from time import perf_counter

from ortools.sat.python import cp_model
import ortools

from app.engines.dispatch.normalization import (
    D,
    capacity_units,
    raw_co2,
    raw_cost,
    vehicle_can_serve_origin,
)

from .plans import (
    active_vehicle,
    add_load,
    canonical,
    new_trip,
)


MAX_VARIABLES = 30000


def _solver(options):
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_deterministic_time = (
        options["deterministic_limit"]
    )
    solver.parameters.max_time_in_seconds = (
        options["solve_time_limit_s"]
    )
    return solver


def _extract_plan(
    solver,
    slots,
    orders,
):
    plan = []
    for vehicle, y, loads in slots:
        if not solver.value(y):
            continue

        selected = [
            (
                index,
                solver.value(variable),
            )
            for index, variable in loads
            if solver.value(variable)
        ]
        if not selected:
            continue

        current = new_trip(
            orders[selected[0][0]],
            vehicle,
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
    """Solve Assignment without dates or temporal fleet occupancy."""
    started = perf_counter()
    model = cp_model.CpModel()
    slots = []
    xs = defaultdict(list)

    hints = defaultdict(list)
    for current in hint_plan or []:
        hints[
            (
                (
                    current["origin"],
                    current["destination"],
                ),
                current["vehicle_id"],
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
            (
                order["origin"],
                order["destination"],
            )
        ].append(index)

    variable_count = 0

    for route, indices in sorted(
        groups.items()
    ):
        for vehicle in sorted(
            fleet,
            key=lambda item: (
                item["base_site"],
                item["ownership"],
                item["vehicle_type"],
                item["vehicle_id"],
            ),
        ):
            if (
                not active_vehicle(vehicle)
                or not vehicle_can_serve_origin(
                    orders[indices[0]],
                    vehicle,
                )
            ):
                continue

            eligible = [
                index
                for index in indices
                if capacity_units(
                    orders[index],
                    vehicle,
                )
                > 0
            ]
            if not eligible:
                continue

            limit = sum(
                math.ceil(
                    orders[index][
                        "quantity_units"
                    ]
                    / capacity_units(
                        orders[index],
                        vehicle,
                    )
                )
                for index in eligible
            )
            if limit <= 0:
                continue

            variable_count += (
                limit
                * (
                    len(eligible)
                    + 1
                )
            )
            if (
                variable_count
                > MAX_VARIABLES
            ):
                return None, {
                    "name": "OR-Tools CP-SAT",
                    "version": ortools.__version__,
                    "status": "skipped",
                    "method": "heuristic",
                    "reason": (
                        "El modelo exacto supera el "
                        "presupuesto de variables."
                    ),
                    "gap": None,
                    "wall_ms": int(
                        (
                            perf_counter()
                            - started
                        )
                        * 1000
                    ),
                }

            previous = None
            seed_rows = hints[
                (
                    route,
                    vehicle["vehicle_id"],
                )
            ]

            for slot_index in range(
                limit
            ):
                y = model.new_bool_var(
                    f"y{len(slots)}"
                )
                if previous is not None:
                    model.add(
                        y <= previous
                    )
                previous = y

                seed = (
                    seed_rows[slot_index]
                    if slot_index
                    < len(seed_rows)
                    else {}
                )
                if hint_plan is not None:
                    model.add_hint(
                        y,
                        int(bool(seed)),
                    )

                loads = []
                for index in eligible:
                    order = orders[index]
                    upper = min(
                        int(
                            order[
                                "quantity_units"
                            ]
                        ),
                        capacity_units(
                            order,
                            vehicle,
                        ),
                    )
                    x = model.new_int_var(
                        0,
                        upper,
                        (
                            f"x{index}_"
                            f"{len(slots)}"
                        ),
                    )
                    model.add(
                        x <= upper * y
                    )
                    xs[index].append(x)
                    loads.append(
                        (index, x)
                    )
                    if hint_plan is not None:
                        model.add_hint(
                            x,
                            int(
                                seed.get(
                                    order[
                                        "order_id"
                                    ],
                                    0,
                                )
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
                        for index, x in loads
                    )
                    <= int(
                        D(
                            vehicle[
                                "capacity_kg"
                            ]
                        )
                        * 1000
                    )
                    * y
                )
                model.add(
                    sum(
                        x
                        for _, x in loads
                    )
                    >= y
                )
                slots.append(
                    (
                        vehicle,
                        y,
                        loads,
                    )
                )

    for index, order in enumerate(
        orders
    ):
        if not xs[index]:
            return None, {
                "name": "OR-Tools CP-SAT",
                "version": ortools.__version__,
                "status": "infeasible",
                "method": "cp_sat",
                "gap": None,
                "reason": (
                    "Una orden no tiene ningún "
                    "vehículo compatible."
                ),
                "wall_ms": int(
                    (
                        perf_counter()
                        - started
                    )
                    * 1000
                ),
            }
        model.add(
            sum(xs[index])
            == int(
                order[
                    "quantity_units"
                ]
            )
        )

    trips = sum(
        y
        for _, y, _ in slots
    )
    cost = sum(
        float(
            raw_cost(
                orders[loads[0][0]],
                vehicle,
            )
        )
        * y
        for vehicle, y, loads in slots
    )
    co2 = sum(
        float(
            raw_co2(
                orders[loads[0][0]],
                vehicle,
            )
        )
        * y
        for vehicle, y, loads in slots
    )
    outsourced_weight = sum(
        float(
            D(
                orders[index][
                    "unit_weight_kg"
                ]
            )
        )
        * x
        for vehicle, _, loads in slots
        if (
            vehicle["ownership"]
            == "third_party"
        )
        for index, x in loads
    )

    terms = {
        "trips": trips,
        "cost": cost,
        "own_fleet": outsourced_weight,
        "co2": co2,
    }
    score = sum(
        float(weights[key])
        / max(
            float(scales[key]),
            1e-9,
        )
        * terms[key]
        for key in weights
    )
    # Deterministic compactness tie-breaker. It is several orders of
    # magnitude below the configured business score.
    model.minimize(
        score
        + 1e-8 * trips
    )

    solver = _solver(options)
    status = solver.solve(model)
    name = solver.status_name(
        status
    ).lower()

    meta = {
        "name": "OR-Tools CP-SAT",
        "version": ortools.__version__,
        "status": name,
        "method": "cp_sat",
        "seed": 0,
        "time_limit_s": options[
            "solve_time_limit_s"
        ],
        "deterministic_limit": options[
            "deterministic_limit"
        ],
        "gap": None,
        "wall_ms": int(
            (
                perf_counter()
                - started
            )
            * 1000
        ),
    }

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        meta["status"] = (
            "infeasible"
            if status
            == cp_model.INFEASIBLE
            else "timeout"
        )
        return None, meta

    objective = float(
        solver.objective_value
    )
    bound = float(
        solver.best_objective_bound
    )
    meta["gap"] = (
        abs(objective - bound)
        / max(
            1.0,
            abs(objective),
        )
    )
    meta["deterministic_time"] = (
        solver.response_proto
        .deterministic_time
    )

    return (
        _extract_plan(
            solver,
            slots,
            orders,
        ),
        meta,
    )
