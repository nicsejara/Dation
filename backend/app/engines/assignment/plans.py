from collections import Counter, defaultdict
from decimal import Decimal

from app.engines.dispatch.normalization import (
    D,
    capacity_units,
    raw_co2,
    raw_cost,
    vehicle_can_serve_origin,
)


def active_vehicle(vehicle):
    status = str(
        vehicle.get("status") or "available"
    ).strip()
    return status not in (
        "maintenance",
        "unavailable",
    )


def eligible_vehicles(order, fleet):
    return [
        vehicle
        for vehicle in fleet
        if (
            active_vehicle(vehicle)
            and vehicle_can_serve_origin(
                order,
                vehicle,
            )
            and capacity_units(
                order,
                vehicle,
            )
            > 0
        )
    ]


def new_trip(order, vehicle):
    return {
        "vehicle_id": vehicle["vehicle_id"],
        "vehicle_type": vehicle["vehicle_type"],
        "ownership": vehicle["ownership"],
        "provider_name": (
            vehicle.get("provider_name")
            or None
        ),
        "base_site": vehicle["base_site"],
        "origin": order["origin"],
        "destination": order["destination"],
        "distance_km": order["distance_km"],
        "capacity_kg": vehicle["capacity_kg"],
        "loads": [],
        "load_kg": 0.0,
    }


def add_load(current, order, units):
    kg = D(units) * D(
        order["unit_weight_kg"]
    )
    current["loads"].append(
        {
            "order_id": order["order_id"],
            "product": order["product"],
            "units": int(units),
            "kg": float(kg),
        }
    )
    current["load_kg"] = float(
        D(current["load_kg"]) + kg
    )


def _increment(
    objective,
    order,
    vehicle,
    units,
    *,
    opening_trip,
):
    kg = (
        D(order["unit_weight_kg"])
        * D(units)
    )
    trip_inc = int(opening_trip)
    cost_inc = (
        float(raw_cost(order, vehicle))
        if opening_trip
        else 0.0
    )
    co2_inc = (
        float(raw_co2(order, vehicle))
        if opening_trip
        else 0.0
    )
    outsourced_kg = (
        float(kg)
        if vehicle["ownership"]
        == "third_party"
        else 0.0
    )
    unused = float(
        D(vehicle["capacity_kg"])
        - kg
    )

    metric = {
        "min_trips": trip_inc,
        "min_cost": cost_inc,
        "max_own_fleet": outsourced_kg,
        "min_co2": co2_inc,
    }.get(
        objective,
        trip_inc,
    )

    return (
        metric,
        trip_inc,
        outsourced_kg,
        unused,
        vehicle["ownership"] != "own",
        str(vehicle["vehicle_id"]),
    )


def greedy(
    orders,
    fleet,
    objective="min_trips",
):
    """Deterministic non-temporal load packing candidate."""
    plan = []

    ordered = sorted(
        orders,
        key=lambda order: (
            order["origin"],
            order["destination"],
            -(
                D(order["unit_weight_kg"])
                * D(order["quantity_units"])
            ),
            -D(order["unit_weight_kg"]),
            order["order_id"],
        ),
    )

    for order in ordered:
        remaining = int(
            order["quantity_units"]
        )
        vehicles = eligible_vehicles(
            order,
            fleet,
        )

        while remaining:
            choices = []

            for vehicle in vehicles:
                vehicle_id = vehicle["vehicle_id"]

                for index, existing in enumerate(
                    plan
                ):
                    if (
                        existing["vehicle_id"],
                        existing["origin"],
                        existing["destination"],
                    ) != (
                        vehicle_id,
                        order["origin"],
                        order["destination"],
                    ):
                        continue

                    free_kg = (
                        D(existing["capacity_kg"])
                        - D(existing["load_kg"])
                    )
                    units = min(
                        remaining,
                        int(
                            free_kg
                            // D(
                                order[
                                    "unit_weight_kg"
                                ]
                            )
                        ),
                    )
                    if units <= 0:
                        continue

                    choices.append(
                        (
                            _increment(
                                objective,
                                order,
                                vehicle,
                                units,
                                opening_trip=False,
                            ),
                            index,
                            units,
                            vehicle,
                        )
                    )

                units = min(
                    remaining,
                    capacity_units(
                        order,
                        vehicle,
                    ),
                )
                if units <= 0:
                    continue

                choices.append(
                    (
                        _increment(
                            objective,
                            order,
                            vehicle,
                            units,
                            opening_trip=True,
                        ),
                        len(plan),
                        units,
                        vehicle,
                    )
                )

            if not choices:
                return None

            _, index, units, vehicle = min(
                choices,
                key=lambda item: (
                    item[0],
                    item[1],
                ),
            )

            if index == len(plan):
                if len(plan) >= 10000:
                    raise ValueError(
                        "La asignación supera el límite "
                        "operativo de 10.000 viajes."
                    )
                plan.append(
                    new_trip(
                        order,
                        vehicle,
                    )
                )

            add_load(
                plan[index],
                order,
                units,
            )
            remaining -= units

    return canonical(plan)


def canonical(plan):
    result = sorted(
        plan,
        key=lambda current: (
            current["origin"],
            current["destination"],
            current["vehicle_id"],
            tuple(
                sorted(
                    (
                        load["order_id"],
                        load["units"],
                    )
                    for load in current[
                        "loads"
                    ]
                )
            ),
        ),
    )
    for index, current in enumerate(
        result,
        1,
    ):
        current["trip_id"] = (
            f"A-{index:05d}"
        )
        current["loads"].sort(
            key=lambda load: load[
                "order_id"
            ]
        )
    return result


def validate_assignment(
    plan,
    orders,
    fleet,
):
    by_order = {
        order["order_id"]: order
        for order in orders
    }
    by_vehicle = {
        vehicle["vehicle_id"]: vehicle
        for vehicle in fleet
    }
    counts = Counter()

    for current in plan:
        vehicle_id = current.get(
            "vehicle_id"
        )
        if vehicle_id not in by_vehicle:
            raise ValueError(
                "La asignación referencia un "
                "vehículo inexistente."
            )

        vehicle = by_vehicle[vehicle_id]
        if not active_vehicle(vehicle):
            raise ValueError(
                "La asignación usa un vehículo "
                "marcado como no disponible."
            )
        if not current.get("loads"):
            raise ValueError(
                "Viaje sin cargas."
            )
        if (
            current["vehicle_type"]
            != vehicle["vehicle_type"]
        ):
            raise ValueError(
                "Tipo de vehículo inconsistente."
            )
        if (
            current.get("base_site")
            != vehicle["base_site"]
        ):
            raise ValueError(
                "Site operativo inconsistente."
            )

        load_kg = D(0)
        for load in current["loads"]:
            order_id = load["order_id"]
            if order_id not in by_order:
                raise ValueError(
                    "La asignación contiene una "
                    "orden inexistente."
                )
            order = by_order[order_id]

            if (
                current["origin"]
                != order["origin"]
                or current["destination"]
                != order["destination"]
            ):
                raise ValueError(
                    "La ruta del viaje no coincide "
                    "con la orden."
                )

            if not vehicle_can_serve_origin(
                order,
                vehicle,
            ):
                raise ValueError(
                    "El vehículo no puede atender "
                    "el origen asignado."
                )

            units = load["units"]
            if (
                not isinstance(units, int)
                or units <= 0
            ):
                raise ValueError(
                    "La carga debe usar unidades "
                    "enteras positivas."
                )

            expected_kg = (
                D(units)
                * D(
                    order[
                        "unit_weight_kg"
                    ]
                )
            )
            if (
                abs(
                    D(load["kg"])
                    - expected_kg
                )
                > Decimal("0.001")
            ):
                raise ValueError(
                    "Peso de carga inconsistente."
                )

            counts[order_id] += units
            load_kg += expected_kg

        if (
            load_kg
            > D(vehicle["capacity_kg"])
        ):
            raise ValueError(
                "Capacidad del vehículo excedida."
            )
        if (
            abs(
                D(current["load_kg"])
                - load_kg
            )
            > Decimal("0.001")
        ):
            raise ValueError(
                "Carga total del viaje "
                "inconsistente."
            )

    for order in orders:
        if (
            counts[order["order_id"]]
            != order["quantity_units"]
        ):
            raise ValueError(
                "La asignación no conserva todas "
                "las unidades de la orden "
                + order["order_id"]
                + "."
            )

    return True


def summarize(
    plan,
    orders,
    fleet,
    capabilities,
):
    by_order = {
        order["order_id"]: order
        for order in orders
    }
    by_vehicle = {
        vehicle["vehicle_id"]: vehicle
        for vehicle in fleet
    }

    total_weight = sum(
        D(order["quantity_units"])
        * D(order["unit_weight_kg"])
        for order in orders
    )
    assigned_weight = D(0)
    own_weight = D(0)
    outsourced_weight = D(0)
    total_capacity = D(0)
    total_cost = D(0)
    total_co2 = D(0)
    own_trips = 0
    outsourced_trips = 0
    used_vehicles = set()

    enriched = []
    order_trip_ids = defaultdict(list)
    order_vehicle_ids = defaultdict(set)
    order_outsourced = defaultdict(bool)

    for current in plan:
        vehicle = by_vehicle[
            current["vehicle_id"]
        ]
        trip_weight = D(
            current["load_kg"]
        )
        assigned_weight += trip_weight
        total_capacity += D(
            current["capacity_kg"]
        )
        used_vehicles.add(
            current["vehicle_id"]
        )

        is_outsourced = (
            current["ownership"]
            == "third_party"
        )
        if is_outsourced:
            outsourced_weight += trip_weight
            outsourced_trips += 1
        else:
            own_weight += trip_weight
            own_trips += 1

        cost = (
            raw_cost(
                {
                    "distance_km": current[
                        "distance_km"
                    ]
                },
                vehicle,
            )
            if capabilities["cost"]
            else None
        )
        co2 = (
            raw_co2(
                {
                    "distance_km": current[
                        "distance_km"
                    ]
                },
                vehicle,
            )
            if capabilities["co2"]
            else None
        )
        if cost is not None:
            total_cost += cost
        if co2 is not None:
            total_co2 += co2

        enriched_trip = {
            **current,
            "utilization": float(
                trip_weight
                / D(
                    current[
                        "capacity_kg"
                    ]
                )
            ),
            "estimated_cost": (
                float(cost)
                if cost is not None
                else None
            ),
            "estimated_co2_kg": (
                float(co2)
                if co2 is not None
                else None
            ),
        }
        enriched.append(
            enriched_trip
        )

        for load in current["loads"]:
            order_trip_ids[
                load["order_id"]
            ].append(
                current["trip_id"]
            )
            order_vehicle_ids[
                load["order_id"]
            ].add(
                current["vehicle_id"]
            )
            if is_outsourced:
                order_outsourced[
                    load["order_id"]
                ] = True

    outcomes = []
    for order in sorted(
        orders,
        key=lambda item: item[
            "order_id"
        ],
    ):
        trip_ids = sorted(
            order_trip_ids[
                order["order_id"]
            ]
        )
        outcomes.append(
            {
                "order_id": order[
                    "order_id"
                ],
                "product": order[
                    "product"
                ],
                "units": order[
                    "quantity_units"
                ],
                "kg": float(
                    D(
                        order[
                            "quantity_units"
                        ]
                    )
                    * D(
                        order[
                            "unit_weight_kg"
                        ]
                    )
                ),
                "trip_ids": trip_ids,
                "vehicle_ids": sorted(
                    order_vehicle_ids[
                        order[
                            "order_id"
                        ]
                    ]
                ),
                "split": len(
                    trip_ids
                ) > 1,
                "consolidated": any(
                    len(
                        next(
                            trip["loads"]
                            for trip in enriched
                            if trip[
                                "trip_id"
                            ] == trip_id
                        )
                    )
                    > 1
                    for trip_id in trip_ids
                ),
                "outsourced": bool(
                    order_outsourced[
                        order[
                            "order_id"
                        ]
                    ]
                ),
            }
        )

    metrics = {
        "orders": len(orders),
        "units_assigned": sum(
            int(
                order[
                    "quantity_units"
                ]
            )
            for order in orders
        ),
        "total_weight_kg": float(
            total_weight
        ),
        "total_trips": len(
            enriched
        ),
        "vehicles_used": len(
            used_vehicles
        ),
        "own_trips": own_trips,
        "outsourced_trips": (
            outsourced_trips
        ),
        "load_utilization": (
            float(
                assigned_weight
                / total_capacity
            )
            if total_capacity
            else 0
        ),
        "own_weight_kg": float(
            own_weight
        ),
        "outsourced_weight_kg": float(
            outsourced_weight
        ),
        "own_weight_share": (
            float(
                own_weight
                / total_weight
            )
            if total_weight
            else 0
        ),
        "outsourced_weight_share": (
            float(
                outsourced_weight
                / total_weight
            )
            if total_weight
            else 0
        ),
        "total_cost": (
            float(total_cost)
            if capabilities["cost"]
            else None
        ),
        "co2_kg": (
            float(total_co2)
            if capabilities["co2"]
            else None
        ),
    }

    return {
        "metrics": metrics,
        "trips": enriched,
        "order_outcomes": outcomes,
    }
