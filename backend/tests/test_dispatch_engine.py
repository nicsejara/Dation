import copy
import csv
import io
import unittest

from app.engines.dispatch import run_dispatch_engine
from app.validators.orders_schema import COLUMNS
from app.validators.fleet_schema import COLUMNS as FC


def csv_bytes(cols, rows):
    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=cols,
        delimiter=";",
    )
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def order(
    id="A",
    units=1,
    weight=400,
    day="2026-10-01",
    window=2,
):
    return dict(
        zip(
            COLUMNS,
            [
                id,
                "Producto",
                units,
                weight,
                "Origen",
                "Destino",
                100,
                "Normal",
                window,
                day,
            ],
        )
    )


def fleet(
    own=1,
    third=True,
    base="Origen",
    *,
    own_cost=1,
    own_co2=.5,
    third_cost=2,
    third_co2=.5,
):
    rows = [
        {
            "fleet_pool_id": "OWN-S",
            "vehicle_type": "S",
            "ownership": "own",
            "base_location": base,
            "capacity_kg": 1000,
            "cost_per_km": own_cost,
            "fixed_trip_cost": 10,
            "units_available": own,
            "avg_speed_kmh": 100,
            "driving_hours_per_day": 10,
            "fuel_l_per_100km": 20,
            "co2_kg_per_km": own_co2,
        }
    ]
    if third:
        rows.append(
            {
                "fleet_pool_id": "TP-T",
                "vehicle_type": "T",
                "ownership": "third_party",
                "base_location": "*",
                "capacity_kg": 1000,
                "cost_per_km": third_cost,
                "fixed_trip_cost": 20,
                "units_available": "",
                "avg_speed_kmh": 100,
                "driving_hours_per_day": 10,
                "fuel_l_per_100km": 20,
                "co2_kg_per_km": third_co2,
            }
        )
    return csv_bytes(FC, rows)


class DispatchEngineTests(unittest.TestCase):
    def run_case(self, rows, f=None, **kwargs):
        options = {
            "sensitivity": False,
            "deterministic_limit": .05,
            "solve_time_limit_s": 5,
        }
        options.update(kwargs.pop("options", {}))
        return run_dispatch_engine(
            csv_bytes(COLUMNS, rows),
            f or fleet(),
            options=options,
            **kwargs,
        )

    def test_consolidation_and_integer_capacity(self):
        result = self.run_case(
            [order("A"), order("B")],
            configuration={"objective": "min_cost"},
        )
        self.assertEqual(
            result["scenarios"]["selected"]["metrics"][
                "total_trips"
            ],
            1,
        )

        result = self.run_case(
            [order(units=3, weight=600)]
        )
        self.assertEqual(
            result["scenarios"]["selected"]["metrics"][
                "total_trips"
            ],
            3,
        )
        self.assertEqual(
            result["scenarios"]["selected"]["metrics"][
                "units_delivered"
            ],
            3,
        )

    def test_physical_late_is_reported(self):
        current = order(window=1)
        current["distance_km"] = 2500
        result = self.run_case([current])
        selected = result["scenarios"]["selected"]

        self.assertEqual(
            selected["metrics"]["late_orders_unavoidable"],
            1,
        )
        self.assertEqual(
            selected["trips"][0]["dispatch_date"],
            "2026-10-01",
        )
        self.assertEqual(
            selected["order_outcomes"][0]["late_days"],
            2,
        )
        self.assertEqual(
            result["decision"]["status"],
            "recommended_with_exceptions",
        )
        self.assertEqual(
            result["feasibility"]["physical_sla_violations"],
            1,
        )

    def test_dispatch_v2_contract_and_determinism(self):
        rows = [
            order("A"),
            order("B", day="2026-10-02"),
        ]
        first = self.run_case(rows)
        second = self.run_case(rows)

        self.assertEqual(
            first["schema_version"],
            "dispatch_v2",
        )
        self.assertEqual(
            first["engine"]["version"],
            "2.1.0",
        )
        self.assertEqual(
            first["result_fingerprint"],
            second["result_fingerprint"],
        )
        for name in (
            "min_cost",
            "min_time",
            "max_utilization",
            "min_co2",
            "balanced",
        ):
            result = self.run_case(
                rows,
                configuration={"objective": name},
            )
            self.assertEqual(
                result["scenarios"][name]["metrics"],
                result["scenarios"]["selected"]["metrics"],
            )

    def test_finite_fleet_returns_sla_exception_instead_of_error(self):
        result = self.run_case(
            [
                order(
                    units=3,
                    weight=600,
                    window=1,
                )
            ],
            fleet(third=False),
            configuration={"objective": "min_cost"},
        )
        selected = result["scenarios"]["selected"]
        self.assertEqual(
            selected["metrics"]["units_delivered"],
            3,
        )
        self.assertEqual(
            selected["metrics"]["late_orders"],
            1,
        )
        self.assertEqual(
            result["decision"]["status"],
            "recommended_with_exceptions",
        )
        self.assertGreaterEqual(
            result["feasibility"][
                "capacity_or_policy_sla_violations"
            ],
            1,
        )

    def test_outlier_requires_decision(self):
        with self.assertRaisesRegex(
            ValueError,
            "anomalía",
        ):
            self.run_case([order(units=51)])

    def test_reprogramming(self):
        result = self.run_case(
            [
                order(
                    units=2,
                    weight=600,
                    window=2,
                )
            ],
            fleet(third=False),
        )
        self.assertEqual(
            result["scenarios"]["selected"]["metrics"][
                "units_delivered"
            ],
            2,
        )
        self.assertEqual(
            len(
                {
                    trip["dispatch_date"]
                    for trip in result[
                        "scenarios"
                    ]["selected"]["trips"]
                }
            ),
            2,
        )

    def test_custom_four_weight_score_respects_sla_first(self):
        rows = [
            order("A", 3, 600),
            order("B", 2, 400),
        ]
        result = self.run_case(
            rows,
            configuration={
                "mode": "custom",
                "objective": "custom",
                "weights": {
                    "cost": .4,
                    "time": .2,
                    "utilization": .2,
                    "co2": .2,
                },
            },
        )

        for scenario in result["scenarios"].values():
            if scenario.get("feasible"):
                self.assertEqual(
                    scenario["metrics"]["units_delivered"],
                    5,
                )

        selected = result["scenarios"]["selected"]
        baseline = result["scenarios"]["baseline_direct"]
        if baseline["feasible"]:
            selected_sla = (
                selected["metrics"]["late_orders"],
                selected["metrics"][
                    "priority_weighted_late_days"
                ],
            )
            baseline_sla = (
                baseline["metrics"]["late_orders"],
                baseline["metrics"][
                    "priority_weighted_late_days"
                ],
            )
            self.assertLessEqual(
                selected_sla,
                baseline_sla,
            )

    def test_anomalies_include_and_exclude(self):
        data = csv_bytes(
            COLUMNS,
            [
                order("A", 51),
                order("B"),
            ],
        )
        for decision, units in (
            ("include", 52),
            ("exclude", 1),
        ):
            result = run_dispatch_engine(
                data,
                fleet(),
                options={
                    "sensitivity": False,
                    "anomaly_decisions": {
                        "A": decision,
                    },
                },
            )
            self.assertEqual(
                result["scenarios"]["selected"]["metrics"][
                    "units_delivered"
                ],
                units,
            )
            self.assertEqual(
                result["inputs"]["anomalies"][0][
                    "decision"
                ],
                decision,
            )

    def test_historical_vehicle_assignment_is_ignored(self):
        row = {
            **order(),
            "current_vehicle_type": "missing",
        }
        data = csv_bytes(
            COLUMNS + ["current_vehicle_type"],
            [row],
        )
        result = run_dispatch_engine(
            data,
            fleet(),
            options={"sensitivity": False},
        )
        self.assertNotIn(
            "baseline_current",
            result["scenarios"],
        )
        self.assertEqual(
            result["scenarios"]["selected"]["metrics"][
                "units_delivered"
            ],
            1,
        )

    def test_spatial_pool_cannot_serve_another_origin(self):
        with self.assertRaisesRegex(
            ValueError,
            "No hay flota habilitada",
        ):
            self.run_case(
                [order()],
                fleet(
                    own=1,
                    third=False,
                    base="Otra Base",
                ),
            )

    def test_trip_exposes_pool_and_base(self):
        result = self.run_case(
            [order()],
            fleet(
                own=1,
                third=False,
                base="Origen",
            ),
        )
        trip = result["scenarios"]["selected"]["trips"][0]
        self.assertEqual(
            trip["fleet_pool_id"],
            "OWN-S",
        )
        self.assertEqual(
            trip["base_location"],
            "Origen",
        )

    def test_multiday_cycle_blocks_own_fleet_until_return(self):
        first = order(
            "A",
            weight=600,
            day="2026-10-01",
            window=3,
        )
        second = order(
            "B",
            weight=600,
            day="2026-10-02",
            window=2,
        )
        first["distance_km"] = 600
        second["distance_km"] = 600

        result = self.run_case(
            [first, second],
            fleet(third=False),
            configuration={"objective": "min_cost"},
        )
        trips = result["scenarios"]["selected"]["trips"]

        self.assertEqual(
            [
                trip["dispatch_date"]
                for trip in trips
            ],
            [
                "2026-10-01",
                "2026-10-03",
            ],
        )
        self.assertEqual(
            trips[0]["cycle_days"],
            2,
        )
        self.assertEqual(
            trips[0]["resource_available_again"],
            "2026-10-03",
        )

    def test_sla_first_outsources_even_under_min_cost(self):
        first = order(
            "A",
            weight=600,
            day="2026-10-01",
            window=3,
        )
        second = order(
            "B",
            weight=600,
            day="2026-10-02",
            window=1,
        )
        first["distance_km"] = 600
        second["distance_km"] = 600

        result = self.run_case(
            [first, second],
            fleet(third=True),
            configuration={"objective": "min_cost"},
        )
        selected = result["scenarios"]["selected"]

        self.assertEqual(
            selected["metrics"]["late_orders"],
            0,
        )
        self.assertEqual(
            selected["metrics"]["outsourced_trips"],
            1,
        )
        self.assertEqual(
            result["decision"]["status"],
            "recommended",
        )

    def test_max_utilization_prefers_own_weight(self):
        data = fleet(
            third=True,
            own_cost=5,
            third_cost=.2,
        )
        result = self.run_case(
            [order()],
            data,
            configuration={
                "objective": "max_utilization",
            },
        )
        selected = result["scenarios"]["selected"]

        self.assertEqual(
            selected["metrics"]["own_weight_share"],
            1,
        )
        self.assertEqual(
            selected["metrics"]["outsourced_weight_share"],
            0,
        )

    def test_min_co2_prefers_cleaner_vehicle(self):
        data = fleet(
            third=True,
            own_cost=.2,
            own_co2=2,
            third_cost=3,
            third_co2=.1,
        )
        cost = self.run_case(
            [order()],
            data,
            configuration={"objective": "min_cost"},
        )
        co2 = self.run_case(
            [order()],
            data,
            configuration={"objective": "min_co2"},
        )

        self.assertEqual(
            cost["scenarios"]["selected"]["metrics"][
                "own_weight_share"
            ],
            1,
        )
        self.assertEqual(
            co2["scenarios"]["selected"]["metrics"][
                "own_weight_share"
            ],
            0,
        )
        self.assertLess(
            co2["scenarios"]["selected"]["metrics"]["co2_kg"],
            cost["scenarios"]["selected"]["metrics"]["co2_kg"],
        )

    def test_validation_rejects_temporal_double_booking(self):
        from app.engines.dispatch.plans import validate_plan
        from app.validators.orders_schema import validate_orders_csv
        from app.validators.fleet_schema import validate_fleet_csv

        first = order(
            "A",
            weight=600,
            day="2026-10-01",
            window=3,
        )
        second = order(
            "B",
            weight=600,
            day="2026-10-02",
            window=2,
        )
        first["distance_km"] = 600
        second["distance_km"] = 600

        orders_bytes = csv_bytes(
            COLUMNS,
            [first, second],
        )
        fleet_bytes = fleet(
            third=False
        )
        result = run_dispatch_engine(
            orders_bytes,
            fleet_bytes,
            configuration={"objective": "min_cost"},
            options={"sensitivity": False},
        )
        plan = copy.deepcopy(
            result["scenarios"]["selected"]["trips"]
        )
        plan[1]["dispatch_date"] = "2026-10-02"
        plan[1]["arrival_date"] = "2026-10-03"
        plan[1]["resource_available_again"] = "2026-10-04"

        with self.assertRaisesRegex(
            ValueError,
            "Disponibilidad temporal",
        ):
            validate_plan(
                plan,
                validate_orders_csv(
                    orders_bytes
                )["records"],
                validate_fleet_csv(
                    fleet_bytes
                )["records"],
                max_late_days=30,
            )

    def test_sensitivity_is_standard_objective_set(self):
        result = run_dispatch_engine(
            csv_bytes(
                COLUMNS,
                [
                    order("A"),
                    order("B"),
                ],
            ),
            fleet(),
            options={
                "analysis_depth": "deep",
                "deterministic_limit": .05,
                "solve_time_limit_s": 5,
            },
        )
        points = result["sensitivity"]["weight_sweep"]

        self.assertEqual(
            [
                point["scenario"]
                for point in points
            ],
            [
                "min_cost",
                "min_time",
                "max_utilization",
                "min_co2",
                "balanced",
            ],
        )
        self.assertIsNone(
            points[0][
                "orders_changed_vs_previous"
            ]
        )
        self.assertTrue(
            all(
                0
                <= point[
                    "orders_changed_vs_previous"
                ]
                <= 2
                for point in points[1:]
            )
        )

    def test_active_dimensions_limit_comparative_scenarios(self):
        result = self.run_case(
            [order("A"), order("B")],
            configuration={
                "objective": "balanced",
                "dimensions": ["cost", "time"],
            },
            options={
                "analysis_depth": "comparative",
                "sensitivity": None,
            },
        )

        self.assertEqual(
            result["analysis"]["active_dimensions"],
            ["cost", "time"],
        )
        self.assertEqual(
            result["configuration"]["weights"],
            {
                "cost": .5,
                "time": .5,
                "utilization": 0,
                "co2": 0,
            },
        )
        self.assertIn("min_cost", result["scenarios"])
        self.assertIn("min_time", result["scenarios"])
        self.assertIn("balanced", result["scenarios"])
        self.assertNotIn("min_co2", result["scenarios"])
        self.assertNotIn("max_utilization", result["scenarios"])
        self.assertEqual(
            result["sensitivity"]["weight_sweep"],
            [],
        )

    def test_essential_depth_solves_only_required_preset(self):
        result = self.run_case(
            [order("A"), order("B")],
            configuration={
                "objective": "min_cost",
                "dimensions": [
                    "cost",
                    "time",
                    "utilization",
                    "co2",
                ],
            },
            options={
                "analysis_depth": "essential",
                "sensitivity": None,
            },
        )

        self.assertEqual(
            result["analysis"]["depth"],
            "essential",
        )
        self.assertEqual(
            result["analysis"]["scenario_count"],
            1,
        )
        self.assertIn("min_cost", result["scenarios"])
        self.assertNotIn("min_time", result["scenarios"])
        self.assertNotIn("balanced", result["scenarios"])

    def test_validation_rejects_corrupt_plan(self):
        from app.engines.dispatch.plans import validate_plan
        from app.validators.orders_schema import validate_orders_csv
        from app.validators.fleet_schema import validate_fleet_csv

        data = csv_bytes(
            COLUMNS,
            [order()],
        )
        result = run_dispatch_engine(
            data,
            fleet(),
            options={"sensitivity": False},
        )
        plan = result["scenarios"]["selected"]["trips"]
        plan[0]["arrival_date"] = "2026-12-01"

        with self.assertRaisesRegex(
            ValueError,
            "Llegada",
        ):
            validate_plan(
                plan,
                validate_orders_csv(data)["records"],
                validate_fleet_csv(
                    fleet()
                )["records"],
                max_late_days=30,
            )


if __name__ == "__main__":
    unittest.main()
