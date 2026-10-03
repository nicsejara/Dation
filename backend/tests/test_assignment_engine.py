import csv
import io
import unittest

from app.engines.assignment import (
    run_assignment_engine,
)


ORDER_COLUMNS = [
    "order_id",
    "product",
    "quantity_units",
    "unit_weight_kg",
    "origin",
    "destination",
    "distance_km",
    "estimated_dispatch_date",
    "priority",
    "delivery_due_date",
]

FLEET_COLUMNS = [
    "vehicle_id",
    "license_plate",
    "vehicle_type",
    "ownership",
    "provider_name",
    "base_site",
    "capacity_kg",
    "capacity_m3",
    "cost_per_km",
    "fixed_trip_cost",
    "fuel_l_per_100km",
    "co2_kg_per_km",
    "avg_speed_kmh",
    "driving_hours_per_day",
    "status",
    "available_from",
    "available_until",
]


def csv_bytes(columns, rows):
    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=columns,
        delimiter=";",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def order(
    order_id,
    units=1,
    weight=600,
    destination="Mendoza",
    estimated="2026-10-01",
    due="2026-10-03",
):
    return {
        "order_id": order_id,
        "product": "Producto " + order_id,
        "quantity_units": units,
        "unit_weight_kg": weight,
        "origin": "Cordoba",
        "destination": destination,
        "distance_km": 650,
        "estimated_dispatch_date": estimated,
        "priority": "Normal",
        "delivery_due_date": due,
    }


def vehicle(
    vehicle_id,
    *,
    capacity=1000,
    ownership="own",
    cost=1,
    fixed=10,
    co2=.5,
    status="available",
):
    return {
        "vehicle_id": vehicle_id,
        "license_plate": "",
        "vehicle_type": "Truck",
        "ownership": ownership,
        "provider_name": (
            "Proveedor"
            if ownership == "third_party"
            else ""
        ),
        "base_site": (
            "*"
            if ownership == "third_party"
            else "Cordoba"
        ),
        "capacity_kg": capacity,
        "capacity_m3": "",
        "cost_per_km": cost,
        "fixed_trip_cost": fixed,
        "fuel_l_per_100km": 20,
        "co2_kg_per_km": co2,
        "avg_speed_kmh": 80,
        "driving_hours_per_day": 10,
        "status": status,
        "available_from": "2026-10-01",
        "available_until": "",
    }


class AssignmentEngineTests(
    unittest.TestCase
):
    def run_case(
        self,
        orders,
        fleet,
        configuration=None,
        options=None,
    ):
        return run_assignment_engine(
            csv_bytes(
                ORDER_COLUMNS,
                orders,
            ),
            csv_bytes(
                FLEET_COLUMNS,
                fleet,
            ),
            configuration=configuration,
            options={
                "analysis_depth": "essential",
                "solve_time_limit_s": 5,
                "deterministic_limit": .05,
                **(options or {}),
            },
        )

    def test_assignment_v1_is_non_temporal(self):
        result = self.run_case(
            [order("A")],
            [vehicle("VEH-001")],
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
        )

        self.assertEqual(
            result["schema_version"],
            "assignment_v1",
        )
        self.assertEqual(
            result["engine"]["version"],
            "1.0.0",
        )
        self.assertFalse(
            result["analysis"]["temporal"],
        )
        trip = result["scenarios"][
            "selected"
        ]["trips"][0]
        for field in (
            "dispatch_date",
            "arrival_date",
            "cycle_days",
            "resource_available_again",
        ):
            self.assertNotIn(
                field,
                trip,
            )
        self.assertEqual(
            trip["vehicle_id"],
            "VEH-001",
        )

    def test_dates_do_not_change_assignment(self):
        fleet = [
            vehicle("VEH-001"),
            vehicle(
                "VEH-002",
                ownership="third_party",
                cost=3,
            ),
        ]
        first = self.run_case(
            [
                order(
                    "A",
                    estimated="2026-10-01",
                    due="2026-10-02",
                ),
                order(
                    "B",
                    estimated="2026-10-05",
                    due="2026-10-06",
                ),
            ],
            fleet,
            configuration={
                "objective": "min_cost",
                "dimensions": [
                    "cost",
                ],
            },
        )
        second = self.run_case(
            [
                order(
                    "A",
                    estimated="2027-02-10",
                    due="2027-02-28",
                ),
                order(
                    "B",
                    estimated="2027-03-01",
                    due="2027-04-15",
                ),
            ],
            fleet,
            configuration={
                "objective": "min_cost",
                "dimensions": [
                    "cost",
                ],
            },
        )

        def signature(result):
            return [
                (
                    trip["vehicle_id"],
                    trip["origin"],
                    trip["destination"],
                    [
                        (
                            load["order_id"],
                            load["units"],
                        )
                        for load in trip["loads"]
                    ],
                )
                for trip in result[
                    "scenarios"
                ]["selected"]["trips"]
            ]

        self.assertEqual(
            signature(first),
            signature(second),
        )

    def test_one_vehicle_can_receive_multiple_abstract_trips(self):
        result = self.run_case(
            [
                order(
                    "A",
                    units=3,
                    weight=600,
                )
            ],
            [vehicle("VEH-001")],
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
        )
        trips = result["scenarios"][
            "selected"
        ]["trips"]
        self.assertEqual(
            len(trips),
            3,
        )
        self.assertEqual(
            {
                trip["vehicle_id"]
                for trip in trips
            },
            {"VEH-001"},
        )

    def test_min_trips_consolidates_same_route(self):
        result = self.run_case(
            [
                order(
                    "A",
                    weight=400,
                ),
                order(
                    "B",
                    weight=400,
                ),
            ],
            [vehicle("VEH-001")],
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
        )
        selected = result[
            "scenarios"
        ]["selected"]
        self.assertEqual(
            selected["metrics"][
                "total_trips"
            ],
            1,
        )
        self.assertEqual(
            len(
                selected["trips"][0][
                    "loads"
                ]
            ),
            2,
        )

    def test_own_fleet_and_co2_are_distinct_objectives(self):
        fleet = [
            vehicle(
                "OWN",
                cost=.2,
                co2=2,
            ),
            vehicle(
                "TP",
                ownership="third_party",
                cost=3,
                co2=.1,
            ),
        ]
        own = self.run_case(
            [order("A")],
            fleet,
            configuration={
                "objective": "max_own_fleet",
                "dimensions": [
                    "own_fleet",
                    "co2",
                ],
            },
        )
        co2 = self.run_case(
            [order("A")],
            fleet,
            configuration={
                "objective": "min_co2",
                "dimensions": [
                    "own_fleet",
                    "co2",
                ],
            },
        )

        self.assertEqual(
            own["scenarios"]["selected"][
                "trips"
            ][0]["vehicle_id"],
            "OWN",
        )
        self.assertEqual(
            co2["scenarios"]["selected"][
                "trips"
            ][0]["vehicle_id"],
            "TP",
        )

    def test_missing_cost_rejects_cost_dimension(self):
        incomplete = vehicle("VEH-001")
        incomplete["cost_per_km"] = ""
        incomplete["fixed_trip_cost"] = ""

        with self.assertRaisesRegex(
            ValueError,
            "sin datos completos",
        ):
            self.run_case(
                [order("A")],
                [incomplete],
                configuration={
                    "objective": "min_cost",
                    "dimensions": [
                        "cost",
                    ],
                },
            )

    def test_handoff_is_explicit(self):
        result = self.run_case(
            [order("A")],
            [vehicle("VEH-001")],
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
        )
        handoff = result["handoff"]

        self.assertEqual(
            handoff["schema_version"],
            "scheduling_input_v1",
        )
        self.assertEqual(
            handoff["next_decision"],
            "logistics_scheduling",
        )
        self.assertEqual(
            handoff["source_path"],
            "scenarios.selected.trips",
        )
        self.assertEqual(
            handoff["trip_count"],
            1,
        )

    def test_assignment_is_deterministic(self):
        args = (
            [
                order("A"),
                order("B"),
            ],
            [
                vehicle("VEH-001"),
                vehicle(
                    "VEH-002",
                    ownership="third_party",
                ),
            ],
        )
        first = self.run_case(
            *args,
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
        )
        second = self.run_case(
            *args,
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
        )
        self.assertEqual(
            first["result_fingerprint"],
            second["result_fingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
