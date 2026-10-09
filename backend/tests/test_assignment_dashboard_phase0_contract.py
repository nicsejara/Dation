import csv
import io
import json
from pathlib import Path
import unittest

from app.engines.assignment import run_assignment_engine


HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "assignment_dashboard"

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


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def analysis_depth(run):
    result = run.get("result_json") or {}
    return (
        (result.get("analysis") or {}).get("depth")
        or ((result.get("configuration") or {}).get("options") or {}).get(
            "analysis_depth"
        )
        or ((run.get("configuration_json") or {}).get("options") or {}).get(
            "analysis_depth"
        )
        or "comparative"
    )


def csv_bytes(columns, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=columns,
        delimiter=";",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def engine_inputs():
    orders = [
        {
            "order_id": "ORD-001",
            "product": "Producto A",
            "quantity_units": 4,
            "unit_weight_kg": 1000,
            "origin": "Cordoba",
            "destination": "Rosario",
            "distance_km": 400,
            "estimated_dispatch_date": "2026-10-10",
            "priority": "Normal",
            "delivery_due_date": "2026-10-13",
        },
        {
            "order_id": "ORD-002",
            "product": "Producto B",
            "quantity_units": 3,
            "unit_weight_kg": 1000,
            "origin": "Cordoba",
            "destination": "Rosario",
            "distance_km": 400,
            "estimated_dispatch_date": "2026-10-10",
            "priority": "Normal",
            "delivery_due_date": "2026-10-13",
        },
    ]
    fleet = [
        {
            "vehicle_id": "VEH-001",
            "license_plate": "AA000AA",
            "vehicle_type": "Truck",
            "ownership": "own",
            "provider_name": "",
            "base_site": "Cordoba",
            "capacity_kg": 6000,
            "capacity_m3": "",
            "cost_per_km": 1.5,
            "fixed_trip_cost": 100,
            "fuel_l_per_100km": 20,
            "co2_kg_per_km": 0.8,
            "avg_speed_kmh": 80,
            "driving_hours_per_day": 10,
            "status": "available",
            "available_from": "2026-10-09",
            "available_until": "",
        },
        {
            "vehicle_id": "TP-001",
            "license_plate": "",
            "vehicle_type": "Truck",
            "ownership": "third_party",
            "provider_name": "Transportes Demo",
            "base_site": "*",
            "capacity_kg": 5000,
            "capacity_m3": "",
            "cost_per_km": 1.0,
            "fixed_trip_cost": 50,
            "fuel_l_per_100km": 18,
            "co2_kg_per_km": 0.5,
            "avg_speed_kmh": 80,
            "driving_hours_per_day": 10,
            "status": "available",
            "available_from": "2026-10-09",
            "available_until": "",
        },
    ]
    return (
        csv_bytes(ORDER_COLUMNS, orders),
        csv_bytes(FLEET_COLUMNS, fleet),
    )


def execute(depth, configuration):
    orders, fleet = engine_inputs()
    return run_assignment_engine(
        orders,
        fleet,
        configuration=configuration,
        options={
            "analysis_depth": depth,
            "resource_mode": "mixed",
            "solve_time_limit_s": 1,
            "deterministic_limit": 0.02,
            "total_time_limit_s": 30,
        },
    )


class AssignmentDashboardPhase0FixtureTests(unittest.TestCase):
    def test_fixtures_distinguish_depth_from_three_persisted_paths(self):
        for filename, expected in (
            ("assignment_essential_run.json", "essential"),
            ("assignment_comparative_run.json", "comparative"),
        ):
            with self.subTest(filename=filename):
                run = load_fixture(filename)
                result = run["result_json"]
                self.assertEqual(analysis_depth(run), expected)
                self.assertEqual(result["analysis"]["depth"], expected)
                self.assertEqual(
                    result["configuration"]["options"]["analysis_depth"],
                    expected,
                )
                self.assertEqual(
                    run["configuration_json"]["options"]["analysis_depth"],
                    expected,
                )

    def test_essential_fixture_has_one_reference_and_no_frontier(self):
        result = load_fixture("assignment_essential_run.json")["result_json"]
        self.assertEqual(set(result["scenarios"]), {"min_trips", "selected"})
        self.assertEqual(result["analysis"]["scenario_count"], 1)
        self.assertEqual(result["sensitivity"]["frontier"], [])

    def test_comparative_fixture_exposes_metric_level_references(self):
        result = load_fixture("assignment_comparative_run.json")["result_json"]
        references = {
            "min_trips",
            "min_cost",
            "max_own_fleet",
            "min_co2",
            "balanced",
        }
        self.assertEqual(set(result["scenarios"]) - {"selected"}, references)
        self.assertEqual(result["analysis"]["scenario_count"], 5)
        self.assertEqual(
            {item["scenario"] for item in result["sensitivity"]["frontier"]},
            references,
        )

    def test_only_selected_scenario_contains_operational_detail(self):
        for filename in (
            "assignment_essential_run.json",
            "assignment_comparative_run.json",
        ):
            result = load_fixture(filename)["result_json"]
            selected = result["scenarios"]["selected"]
            self.assertTrue(selected["trips"])
            self.assertTrue(selected["order_outcomes"])
            for key, scenario in result["scenarios"].items():
                if key == "selected":
                    continue
                self.assertNotIn("trips", scenario)
                self.assertNotIn("order_outcomes", scenario)

    def test_assignment_fixtures_never_claim_temporal_output(self):
        forbidden = {
            "dispatch_date",
            "arrival_date",
            "cycle_days",
            "resource_available_again",
            "wait_days",
        }
        for filename in (
            "assignment_essential_run.json",
            "assignment_comparative_run.json",
        ):
            result = load_fixture(filename)["result_json"]
            self.assertFalse(result["analysis"]["temporal"])
            for trip in result["scenarios"]["selected"]["trips"]:
                self.assertTrue(forbidden.isdisjoint(trip))

    def test_comparative_fixture_covers_same_plan_fingerprint(self):
        result = load_fixture("assignment_comparative_run.json")["result_json"]
        self.assertEqual(
            result["scenarios"]["selected"]["plan_fingerprint"],
            result["scenarios"]["min_trips"]["plan_fingerprint"],
        )


class AssignmentDashboardPhase0EngineContractTests(unittest.TestCase):
    ALL_EXTREMES = {
        "min_trips",
        "min_cost",
        "max_own_fleet",
        "min_co2",
    }

    def assert_published_contract(self, result, expected_depth):
        self.assertEqual(result["schema_version"], "assignment_v1")
        self.assertEqual(result["analysis"]["depth"], expected_depth)
        self.assertEqual(
            result["configuration"]["options"]["analysis_depth"],
            expected_depth,
        )
        self.assertFalse(result["analysis"]["temporal"])
        self.assertIn("trips", result["scenarios"]["selected"])
        self.assertIn("order_outcomes", result["scenarios"]["selected"])
        for key, scenario in result["scenarios"].items():
            if key != "selected":
                self.assertNotIn("trips", scenario)
                self.assertNotIn("order_outcomes", scenario)

    def test_essential_simple_preset_publishes_only_requested_reference(self):
        result = execute(
            "essential",
            {
                "mode": "preset",
                "objective": "min_trips",
                "dimensions": ["trips", "cost", "own_fleet", "co2"],
            },
        )
        self.assert_published_contract(result, "essential")
        self.assertEqual(set(result["scenarios"]), {"min_trips", "selected"})
        self.assertEqual(result["analysis"]["scenario_count"], 1)
        self.assertEqual(result["sensitivity"]["frontier"], [])

    def test_essential_balanced_keeps_extremes_but_hides_frontier(self):
        result = execute(
            "essential",
            {
                "mode": "preset",
                "objective": "balanced",
                "dimensions": ["trips", "cost", "own_fleet", "co2"],
            },
        )
        self.assert_published_contract(result, "essential")
        self.assertEqual(
            set(result["scenarios"]),
            self.ALL_EXTREMES | {"balanced", "selected"},
        )
        self.assertEqual(result["analysis"]["scenario_count"], 5)
        self.assertEqual(result["sensitivity"]["frontier"], [])

    def test_essential_custom_keeps_extremes_without_balanced_reference(self):
        result = execute(
            "essential",
            {
                "mode": "custom",
                "objective": "custom",
                "dimensions": ["trips", "cost", "own_fleet", "co2"],
                "weights": {
                    "trips": 0.4,
                    "cost": 0.2,
                    "own_fleet": 0.3,
                    "co2": 0.1,
                },
            },
        )
        self.assert_published_contract(result, "essential")
        self.assertEqual(
            set(result["scenarios"]),
            self.ALL_EXTREMES | {"selected"},
        )
        self.assertEqual(result["analysis"]["scenario_count"], 4)
        self.assertEqual(result["sensitivity"]["frontier"], [])

    def test_comparative_simple_preset_publishes_extremes_and_balanced(self):
        result = execute(
            "comparative",
            {
                "mode": "preset",
                "objective": "min_trips",
                "dimensions": ["trips", "cost", "own_fleet", "co2"],
            },
        )
        self.assert_published_contract(result, "comparative")
        expected = self.ALL_EXTREMES | {"balanced", "selected"}
        self.assertEqual(set(result["scenarios"]), expected)
        self.assertEqual(result["analysis"]["scenario_count"], 5)
        self.assertEqual(
            {item["scenario"] for item in result["sensitivity"]["frontier"]},
            expected - {"selected"},
        )

    def test_comparative_balanced_has_same_reference_shape(self):
        result = execute(
            "comparative",
            {
                "mode": "preset",
                "objective": "balanced",
                "dimensions": ["trips", "cost", "own_fleet", "co2"],
            },
        )
        self.assert_published_contract(result, "comparative")
        expected = self.ALL_EXTREMES | {"balanced", "selected"}
        self.assertEqual(set(result["scenarios"]), expected)
        self.assertEqual(result["analysis"]["scenario_count"], 5)

    def test_comparative_custom_adds_balanced_reference(self):
        result = execute(
            "comparative",
            {
                "mode": "custom",
                "objective": "custom",
                "dimensions": ["trips", "cost", "own_fleet", "co2"],
                "weights": {
                    "trips": 0.4,
                    "cost": 0.2,
                    "own_fleet": 0.3,
                    "co2": 0.1,
                },
            },
        )
        self.assert_published_contract(result, "comparative")
        expected = self.ALL_EXTREMES | {"balanced", "selected"}
        self.assertEqual(set(result["scenarios"]), expected)
        self.assertEqual(result["analysis"]["scenario_count"], 5)
        self.assertEqual(
            {item["scenario"] for item in result["sensitivity"]["frontier"]},
            expected - {"selected"},
        )


if __name__ == "__main__":
    unittest.main()
