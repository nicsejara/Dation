import csv
import io
import unittest

from app.engines.assignment import run_assignment_engine
from app.engines.scheduling import run_scheduling_engine


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
    destination,
    *,
    ready="2026-10-01",
    due="2026-10-10",
    distance=600,
):
    return {
        "order_id": order_id,
        "product": "Producto " + order_id,
        "quantity_units": 1,
        "unit_weight_kg": 500,
        "origin": "Cordoba",
        "destination": destination,
        "distance_km": distance,
        "estimated_dispatch_date": ready,
        "priority": "Normal",
        "delivery_due_date": due,
    }


def vehicle(
    vehicle_id="VEH-001",
    *,
    available_from="2026-10-01",
    available_until="2026-10-31",
):
    return {
        "vehicle_id": vehicle_id,
        "license_plate": "AA123AA",
        "vehicle_type": "Truck",
        "ownership": "own",
        "provider_name": "",
        "base_site": "Cordoba",
        "capacity_kg": 1000,
        "capacity_m3": 20,
        "cost_per_km": 1,
        "fixed_trip_cost": 10,
        "fuel_l_per_100km": 20,
        "co2_kg_per_km": .5,
        "avg_speed_kmh": 100,
        "driving_hours_per_day": 10,
        "status": "available",
        "available_from": available_from,
        "available_until": available_until,
    }


class SchedulingEngineTests(
    unittest.TestCase
):
    def assignment(
        self,
        orders,
        fleet,
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
            configuration={
                "objective": "min_trips",
                "dimensions": [
                    "trips",
                    "own_fleet",
                ],
            },
            options={
                "analysis_depth": "essential",
                "solve_time_limit_s": 5,
                "deterministic_limit": .05,
            },
        )

    def schedule(
        self,
        orders,
        fleet,
        assignment,
        **options,
    ):
        return run_scheduling_engine(
            csv_bytes(
                ORDER_COLUMNS,
                orders,
            ),
            csv_bytes(
                FLEET_COLUMNS,
                fleet,
            ),
            assignment,
            options={
                "solve_time_limit_s": 5,
                "deterministic_limit": .05,
                **options,
            },
        )

    def test_scheduling_preserves_assignment_exactly(self):
        orders = [
            order("A", "Mendoza"),
            order("B", "Rosario"),
        ]
        fleet = [vehicle()]
        assignment = self.assignment(
            orders,
            fleet,
        )
        result = self.schedule(
            orders,
            fleet,
            assignment,
        )

        source = {
            trip["trip_id"]: (
                trip["vehicle_id"],
                sorted(
                    (
                        load["order_id"],
                        load["units"],
                    )
                    for load in trip["loads"]
                ),
            )
            for trip in assignment[
                "scenarios"
            ]["selected"]["trips"]
        }
        scheduled = {
            trip["trip_id"]: (
                trip["vehicle_id"],
                sorted(
                    (
                        load["order_id"],
                        load["units"],
                    )
                    for load in trip["loads"]
                ),
            )
            for trip in result[
                "scenarios"
            ]["selected"]["trips"]
        }

        self.assertEqual(
            result["schema_version"],
            "scheduling_v1",
        )
        self.assertEqual(
            result["engine"]["version"],
            "1.0.0",
        )
        self.assertEqual(
            source,
            scheduled,
        )
        self.assertTrue(
            result["analysis"][
                "assignment_locked"
            ]
        )

    def test_same_vehicle_trips_do_not_overlap(self):
        orders = [
            order("A", "Mendoza"),
            order("B", "Rosario"),
        ]
        fleet = [vehicle()]
        assignment = self.assignment(
            orders,
            fleet,
        )
        result = self.schedule(
            orders,
            fleet,
            assignment,
        )
        trips = sorted(
            result["scenarios"][
                "selected"
            ]["trips"],
            key=lambda item: item[
                "dispatch_date"
            ],
        )

        self.assertEqual(
            len(trips),
            2,
        )
        self.assertGreaterEqual(
            trips[1]["dispatch_date"],
            trips[0][
                "resource_available_again"
            ],
        )

    def test_service_first_prioritizes_urgent_trip(self):
        orders = [
            order(
                "A",
                "Alta Gracia",
                due="2026-10-10",
            ),
            order(
                "B",
                "Villa Maria",
                due="2026-10-02",
            ),
        ]
        fleet = [vehicle()]
        assignment = self.assignment(
            orders,
            fleet,
        )
        result = self.schedule(
            orders,
            fleet,
            assignment,
        )

        trips = result["scenarios"][
            "selected"
        ]["trips"]
        by_order = {
            load["order_id"]: trip
            for trip in trips
            for load in trip["loads"]
        }

        self.assertEqual(
            by_order["B"]["dispatch_date"],
            "2026-10-01",
        )
        self.assertGreater(
            by_order["A"]["dispatch_date"],
            by_order["B"]["dispatch_date"],
        )
        self.assertEqual(
            result["scenarios"][
                "selected"
            ]["metrics"]["late_orders"],
            0,
        )

    def test_vehicle_available_from_is_respected(self):
        orders = [
            order(
                "A",
                "Mendoza",
                ready="2026-10-01",
            ),
        ]
        fleet = [
            vehicle(
                available_from="2026-10-05",
            )
        ]
        assignment = self.assignment(
            orders,
            fleet,
        )
        result = self.schedule(
            orders,
            fleet,
            assignment,
        )
        trip = result["scenarios"][
            "selected"
        ]["trips"][0]

        self.assertEqual(
            trip["dispatch_date"],
            "2026-10-05",
        )
        self.assertEqual(
            trip["wait_days"],
            4,
        )

    def test_unavoidable_late_order_is_reported(self):
        orders = [
            order(
                "A",
                "Mendoza",
                ready="2026-10-01",
                due="2026-10-01",
            ),
        ]
        fleet = [vehicle()]
        assignment = self.assignment(
            orders,
            fleet,
        )
        result = self.schedule(
            orders,
            fleet,
            assignment,
        )

        self.assertEqual(
            result["decision"]["status"],
            "recommended_with_exceptions",
        )
        self.assertEqual(
            result["scenarios"][
                "selected"
            ]["metrics"]["late_orders"],
            1,
        )
        self.assertEqual(
            result["exceptions"][0][
                "order_id"
            ],
            "A",
        )

    def test_available_until_can_make_schedule_infeasible(self):
        orders = [
            order("A", "Mendoza"),
            order("B", "Rosario"),
        ]
        fleet = [
            vehicle(
                available_until="2026-10-02",
            )
        ]
        assignment = self.assignment(
            orders,
            fleet,
        )

        with self.assertRaisesRegex(
            ValueError,
            "ventana",
        ):
            self.schedule(
                orders,
                fleet,
                assignment,
            )

    def test_handoff_to_final_assignment_is_versioned(self):
        orders = [
            order("A", "Mendoza")
        ]
        fleet = [vehicle()]
        assignment = self.assignment(
            orders,
            fleet,
        )
        result = self.schedule(
            orders,
            fleet,
            assignment,
        )

        self.assertEqual(
            result["handoff"][
                "schema_version"
            ],
            "final_assignment_input_v1",
        )
        self.assertEqual(
            result["handoff"][
                "next_decision"
            ],
            "logistics_final_assignment",
        )
        self.assertEqual(
            result["handoff"][
                "assignment_fingerprint"
            ],
            assignment["handoff"][
                "assignment_fingerprint"
            ],
        )

    def test_scheduling_is_deterministic(self):
        orders = [
            order("A", "Mendoza"),
            order("B", "Rosario"),
        ]
        fleet = [vehicle()]
        assignment = self.assignment(
            orders,
            fleet,
        )
        first = self.schedule(
            orders,
            fleet,
            assignment,
        )
        second = self.schedule(
            orders,
            fleet,
            assignment,
        )

        self.assertEqual(
            first["result_fingerprint"],
            second["result_fingerprint"],
        )


if __name__ == "__main__":
    unittest.main()
