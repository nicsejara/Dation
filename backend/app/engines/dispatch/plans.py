from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP
import math

from .normalization import (
    D,
    transit,
    capacity_units,
    raw_cost,
    raw_co2,
    departure_days,
    eligible_fleet,
    vehicle_can_serve_origin,
    cycle_days,
    resource_available_again,
    occupied_dates,
    lateness_days,
)


PRIORITY_WEIGHT = {
    "High": 9,
    "Normal": 3,
    "Low": 1,
}


def trip(order, vehicle, day):
    return {
        "fleet_pool_id": vehicle["fleet_pool_id"],
        "vehicle_type": vehicle["vehicle_type"],
        "ownership": vehicle["ownership"],
        "base_location": vehicle["base_location"],
        "dispatch_date": day,
        "arrival_date": (
            date.fromisoformat(day)
            + timedelta(days=transit(order, vehicle))
        ).isoformat(),
        "cycle_days": cycle_days(order, vehicle),
        "resource_available_again": resource_available_again(
            order,
            vehicle,
            day,
        ),
        "origin": order["origin"],
        "destination": order["destination"],
        "distance_km": order["distance_km"],
        "capacity_kg": vehicle["capacity_kg"],
        "loads": [],
        "load_kg": 0,
    }


def add_load(current_trip, order, units):
    kg = D(units) * D(order["unit_weight_kg"])
    current_trip["loads"].append(
        {
            "order_id": order["order_id"],
            "units": units,
            "kg": float(kg),
        }
    )
    current_trip["load_kg"] = float(
        D(current_trip["load_kg"]) + kg
    )


def _business_score(objective, order, vehicle, units, lead):
    cost_per_unit = float(raw_cost(order, vehicle)) / units
    co2_per_unit = float(raw_co2(order, vehicle)) / units
    load_kg = D(order["unit_weight_kg"]) * units
    unused_ratio = float(
        max(D(0), D(vehicle["capacity_kg"]) - load_kg)
        / D(vehicle["capacity_kg"])
    )

    if objective == "min_time":
        return (lead, cost_per_unit, co2_per_unit)
    if objective == "min_co2":
        return (co2_per_unit, cost_per_unit, lead)
    if objective == "max_utilization":
        return (
            vehicle["ownership"] != "own",
            unused_ratio if vehicle["ownership"] == "own" else 1,
            cost_per_unit,
            lead,
        )
    return (cost_per_unit, co2_per_unit, lead)


def greedy(
    orders,
    fleet,
    objective="min_cost",
    direct=False,
    current=False,
    max_late_days=0,
):
    """Deterministic candidate that always prioritizes SLA before business score."""
    plan = []
    occupied = Counter()
    priority_rank = {"High": 0, "Normal": 1, "Low": 2}
    ordered = sorted(
        orders,
        key=lambda order: (
            order["deadline"],
            priority_rank[order["priority"]],
            -order["unit_weight_kg"] * order["quantity_units"],
            order["order_id"],
        ),
    )

    for order in ordered:
        remaining = order["quantity_units"]
        vehicles = eligible_fleet(order, fleet)
        if current:
            vehicles = [
                vehicle
                for vehicle in vehicles
                if vehicle["vehicle_type"]
                == order.get("current_vehicle_type")
            ]

        while remaining:
            choices = []
            for vehicle in vehicles:
                days = (
                    [order["dispatch_date"]]
                    if direct
                    else departure_days(
                        order,
                        vehicle,
                        fleet,
                        max_late_days=max_late_days,
                    )
                )
                for day in days:
                    pool_id = vehicle["fleet_pool_id"]
                    late = lateness_days(order, vehicle, day)
                    sla_prefix = (
                        int(late > 0),
                        PRIORITY_WEIGHT[order["priority"]] * late,
                    )

                    if not direct:
                        for idx, existing in enumerate(plan):
                            if (
                                existing["fleet_pool_id"],
                                existing["dispatch_date"],
                                existing["origin"],
                                existing["destination"],
                            ) != (
                                pool_id,
                                day,
                                order["origin"],
                                order["destination"],
                            ):
                                continue
                            space = int(
                                (
                                    D(vehicle["capacity_kg"])
                                    - D(existing["load_kg"])
                                )
                                // D(order["unit_weight_kg"])
                            )
                            if not space:
                                continue
                            units = min(space, remaining)
                            lead = (
                                date.fromisoformat(
                                    existing["arrival_date"]
                                )
                                - date.fromisoformat(
                                    order["dispatch_date"]
                                )
                            ).days
                            choices.append(
                                (
                                    sla_prefix
                                    + _business_score(
                                        objective,
                                        order,
                                        vehicle,
                                        units,
                                        lead,
                                    ),
                                    day,
                                    pool_id,
                                    idx,
                                    units,
                                    vehicle,
                                )
                            )

                    if vehicle["units_available"] is not None:
                        if any(
                            occupied[(pool_id, busy_day)]
                            >= vehicle["units_available"]
                            for busy_day in occupied_dates(
                                order,
                                vehicle,
                                day,
                            )
                        ):
                            continue

                    units = min(
                        capacity_units(order, vehicle),
                        remaining,
                    )
                    lead = (
                        date.fromisoformat(day)
                        - date.fromisoformat(order["dispatch_date"])
                    ).days + transit(order, vehicle)

                    if direct:
                        business = (
                            vehicle["ownership"] != "own",
                            math.ceil(
                                remaining
                                / capacity_units(order, vehicle)
                            ),
                            vehicle["capacity_kg"],
                            float(raw_cost(order, vehicle)),
                        )
                    else:
                        business = _business_score(
                            objective,
                            order,
                            vehicle,
                            units,
                            lead,
                        )
                    choices.append(
                        (
                            sla_prefix + business,
                            day,
                            pool_id,
                            len(plan),
                            units,
                            vehicle,
                        )
                    )

            if not choices:
                return None

            _, day, _, idx, units, vehicle = min(
                choices,
                key=lambda choice: (
                    choice[0],
                    choice[1],
                    choice[2],
                    choice[3],
                ),
            )
            if idx == len(plan):
                if len(plan) >= 10000:
                    raise ValueError(
                        "La distribución supera el límite operativo de "
                        "10.000 viajes. Dividí el horizonte en lotes; "
                        "no se publica cobertura parcial."
                    )
                plan.append(trip(order, vehicle, day))
                for busy_day in occupied_dates(
                    order,
                    vehicle,
                    day,
                ):
                    occupied[
                        (vehicle["fleet_pool_id"], busy_day)
                    ] += 1

            add_load(plan[idx], order, units)
            remaining -= units

    return canonical(plan)


def canonical(plan):
    result = sorted(
        plan,
        key=lambda current: (
            current["dispatch_date"],
            current["origin"],
            current["destination"],
            current["fleet_pool_id"],
            tuple(
                sorted(
                    (load["order_id"], load["units"])
                    for load in current["loads"]
                )
            ),
        ),
    )
    for idx, current in enumerate(result, 1):
        current["trip_id"] = f"V-{idx:05d}"
        current["loads"].sort(
            key=lambda load: load["order_id"]
        )
    return result


def validate_plan(
    plan,
    orders,
    fleet,
    *,
    direct=False,
    max_late_days=0,
):
    by_id = {order["order_id"]: order for order in orders}
    pools = {
        vehicle["fleet_pool_id"]: vehicle
        for vehicle in fleet
    }
    counts = Counter()
    occupancy = Counter()

    for current in plan:
        if current["fleet_pool_id"] not in pools:
            raise ValueError("Pool de flota inexistente.")
        if not current.get("loads"):
            raise ValueError("Viaje sin cargas.")

        vehicle = pools[current["fleet_pool_id"]]
        first_order = by_id[current["loads"][0]["order_id"]]

        if current["vehicle_type"] != vehicle["vehicle_type"]:
            raise ValueError(
                "Tipo de vehículo inconsistente con el pool."
            )
        if current.get("base_location") != vehicle["base_location"]:
            raise ValueError(
                "Base operativa inconsistente con el pool."
            )

        expected_cycle = cycle_days(first_order, vehicle)
        expected_available = resource_available_again(
            first_order,
            vehicle,
            current["dispatch_date"],
        )
        if current.get("cycle_days") != expected_cycle:
            raise ValueError("Duración de ciclo inconsistente.")
        if (
            current.get("resource_available_again")
            != expected_available
        ):
            raise ValueError(
                "Disponibilidad futura inconsistente."
            )

        for busy_day in occupied_dates(
            first_order,
            vehicle,
            current["dispatch_date"],
        ):
            occupancy[
                (vehicle["fleet_pool_id"], busy_day)
            ] += 1

        load_kg = D(0)
        for load in current["loads"]:
            order = by_id[load["order_id"]]
            if (
                not isinstance(load["units"], int)
                or load["units"] <= 0
            ):
                raise ValueError("Carga no entera.")
            if (
                current["origin"],
                current["destination"],
            ) != (
                order["origin"],
                order["destination"],
            ):
                raise ValueError("Ruta inconsistente.")
            if not vehicle_can_serve_origin(order, vehicle):
                raise ValueError(
                    "El pool no está disponible en el origen del viaje."
                )

            days = (
                [order["dispatch_date"]]
                if direct
                else departure_days(
                    order,
                    vehicle,
                    fleet,
                    max_late_days=max_late_days,
                )
            )
            if current["dispatch_date"] not in days:
                raise ValueError(
                    "Salida fuera del horizonte de planificación."
                )

            kg = D(order["unit_weight_kg"]) * load["units"]
            expected_arrival = (
                date.fromisoformat(current["dispatch_date"])
                + timedelta(days=transit(order, vehicle))
            ).isoformat()
            if (
                current["arrival_date"] != expected_arrival
                or D(load["kg"]) != kg
            ):
                raise ValueError(
                    "Llegada o peso de carga inconsistente."
                )
            if D(current["distance_km"]) != D(
                order["distance_km"]
            ):
                raise ValueError("Distancia inconsistente.")

            load_kg += kg
            counts[order["order_id"]] += load["units"]

        if (
            D(current["load_kg"]) != load_kg
            or D(current["capacity_kg"])
            != D(vehicle["capacity_kg"])
        ):
            raise ValueError(
                "Carga o capacidad declarada inconsistente."
            )
        if load_kg > D(vehicle["capacity_kg"]):
            raise ValueError("Capacidad excedida.")

    if counts != Counter(
        {
            order["order_id"]: order["quantity_units"]
            for order in orders
        }
    ):
        raise ValueError("No se conservan las unidades.")

    for (pool_id, day), quantity in occupancy.items():
        limit = pools[pool_id]["units_available"]
        if limit is not None and quantity > limit:
            raise ValueError(
                "Disponibilidad temporal del pool de flota "
                f"excedida en {day}."
            )


def rounded(value):
    return float(
        D(value).quantize(
            D(".01"),
            rounding=ROUND_HALF_UP,
        )
    )


def summarize(plan, orders, fleet):
    pools = {
        vehicle["fleet_pool_id"]: vehicle
        for vehicle in fleet
    }
    by_id = {
        order["order_id"]: order
        for order in orders
    }
    outcomes = defaultdict(list)

    cost = D(0)
    fuel = D(0)
    co2 = D(0)
    capacity = D(0)
    load = D(0)
    distance = D(0)
    own_capacity = D(0)
    own_load = D(0)
    outsourced_load = D(0)
    lead_units = 0

    for current in plan:
        vehicle = pools[current["fleet_pool_id"]]
        reference_order = by_id[
            current["loads"][0]["order_id"]
        ]
        current_cost = raw_cost(reference_order, vehicle)
        km = D(reference_order["distance_km"]) * 2
        current_fuel = (
            km
            * D(vehicle["fuel_l_per_100km"])
            / 100
        )
        current_co2 = raw_co2(reference_order, vehicle)

        cost += current_cost
        fuel += current_fuel
        co2 += current_co2
        capacity += D(vehicle["capacity_kg"])
        load += D(current["load_kg"])
        distance += km

        if vehicle["ownership"] == "own":
            own_capacity += D(vehicle["capacity_kg"])
            own_load += D(current["load_kg"])
        else:
            outsourced_load += D(current["load_kg"])

        current.update(
            cost=rounded(current_cost),
            fuel_l=rounded(current_fuel),
            co2_kg=rounded(current_co2),
            utilization=float(
                D(current["load_kg"])
                / D(vehicle["capacity_kg"])
            ),
        )

        for item in current["loads"]:
            outcomes[item["order_id"]].append(current)
            lead_units += item["units"] * (
                date.fromisoformat(current["arrival_date"])
                - date.fromisoformat(
                    by_id[item["order_id"]]["dispatch_date"]
                )
            ).days

    order_outcomes = []
    for order in orders:
        trips = outcomes[order["order_id"]]
        arrival = max(
            current["arrival_date"]
            for current in trips
        )
        departure = min(
            current["dispatch_date"]
            for current in trips
        )
        late = max(
            0,
            (
                date.fromisoformat(arrival)
                - date.fromisoformat(order["deadline"])
            ).days,
        )
        order_outcomes.append(
            {
                "order_id": order["order_id"],
                "priority": order["priority"],
                "trip_ids": [
                    current["trip_id"]
                    for current in trips
                ],
                "fleet_pool_ids": sorted(
                    {
                        current["fleet_pool_id"]
                        for current in trips
                    }
                ),
                "dispatch_date": departure,
                "arrival_date": arrival,
                "deadline": order["deadline"],
                "late_days": late,
                "postponed_days": (
                    date.fromisoformat(
                        max(
                            current["dispatch_date"]
                            for current in trips
                        )
                    )
                    - date.fromisoformat(
                        order["dispatch_date"]
                    )
                ).days,
                "consolidated": any(
                    len(current["loads"]) > 1
                    for current in trips
                ),
                "split": len(trips) > 1,
                "outsourced": any(
                    current["ownership"] == "third_party"
                    for current in trips
                ),
            }
        )

    units = sum(
        order["quantity_units"]
        for order in orders
    )
    physical_unavoidable = sum(
        min(
            transit(order, vehicle)
            for vehicle in eligible_fleet(order, fleet)
        )
        > order["max_delivery_days"]
        for order in orders
    )
    late_orders = [
        outcome
        for outcome in order_outcomes
        if outcome["late_days"] > 0
    ]
    total_weight = load
    outsourced_share = (
        float(outsourced_load / total_weight)
        if total_weight
        else 0
    )
    own_weight_share = (
        float(own_load / total_weight)
        if total_weight
        else 0
    )

    metrics = {
        "total_cost": rounded(cost),
        "total_trips": len(plan),
        "avg_lead_time_days": round(
            lead_units / units,
            6,
        ),
        "on_time_rate": (
            sum(
                outcome["late_days"] == 0
                for outcome in order_outcomes
            )
            / len(orders)
        ),
        "late_orders": len(late_orders),
        "total_late_days": sum(
            outcome["late_days"]
            for outcome in late_orders
        ),
        "priority_weighted_late_days": sum(
            PRIORITY_WEIGHT[outcome["priority"]]
            * outcome["late_days"]
            for outcome in late_orders
        ),
        "late_orders_unavoidable": physical_unavoidable,
        "units_delivered": units,
        "load_utilization": float(load / capacity),
        "own_load_utilization": (
            float(own_load / own_capacity)
            if own_capacity
            else 0
        ),
        "own_weight_share": own_weight_share,
        "outsourced_weight_kg": rounded(outsourced_load),
        "outsourced_weight_share": outsourced_share,
        "trips_by_vehicle_type": dict(
            sorted(
                Counter(
                    current["vehicle_type"]
                    for current in plan
                ).items()
            )
        ),
        "trips_by_fleet_pool": dict(
            sorted(
                Counter(
                    current["fleet_pool_id"]
                    for current in plan
                ).items()
            )
        ),
        "own_trips": sum(
            current["ownership"] == "own"
            for current in plan
        ),
        "outsourced_trips": sum(
            current["ownership"] == "third_party"
            for current in plan
        ),
        "outsourced_trips_share": (
            sum(
                current["ownership"] == "third_party"
                for current in plan
            )
            / len(plan)
        ),
        "avg_cycle_days": round(
            sum(
                current["cycle_days"]
                for current in plan
            )
            / len(plan),
            6,
        ),
        "fuel_l": rounded(fuel),
        "co2_kg": rounded(co2),
        "total_weight_kg": rounded(load),
        "total_distance_km": rounded(distance),
        "orders": len(orders),
    }
    return {
        "metrics": metrics,
        "trips": plan,
        "order_outcomes": sorted(
            order_outcomes,
            key=lambda outcome: outcome["order_id"],
        ),
    }
