import unittest
from pathlib import Path

from pydantic import ValidationError

from app.engines.scheduling import run_scheduling_engine
from app.models.scheduling_config import SchedulingConfig
from tests.test_scheduling_engine import (
    FLEET_COLUMNS,
    ORDER_COLUMNS,
    SchedulingEngineTests,
    csv_bytes,
    order,
    vehicle,
)


ROOT = Path(__file__).resolve().parents[1]


def assignment_for(orders, fleet):
    return SchedulingEngineTests().assignment(orders, fleet)


def run_schedule(orders, fleet, assignment, configuration):
    return run_scheduling_engine(
        csv_bytes(ORDER_COLUMNS, orders),
        csv_bytes(FLEET_COLUMNS, fleet),
        assignment,
        configuration=configuration,
        options={
            "solve_time_limit_s": 5,
            "deterministic_limit": .05,
            "max_horizon_days": 60,
        },
    )


class SchedulingPhase2EngineTests(unittest.TestCase):
    def test_prioritized_destination_dispatches_first_without_dropping_trips(self):
        orders = [
            order("A", "Mendoza", due="2026-10-20"),
            order("B", "Rosario", due="2026-10-20"),
        ]
        fleet = [vehicle()]
        assignment = assignment_for(orders, fleet)

        result = run_schedule(
            orders,
            fleet,
            assignment,
            {
                "strategy": "earliest_dispatch",
                "temporal_rules": [
                    {
                        "id": "rule-rosario",
                        "field": "destination",
                        "values": ["Rosario"],
                        "action": "prioritize",
                    }
                ],
            },
        )

        trips = result["scenarios"]["selected"]["trips"]
        by_destination = {
            item["destination"]: item
            for item in trips
        }
        self.assertLess(
            by_destination["Rosario"]["dispatch_date"],
            by_destination["Mendoza"]["dispatch_date"],
        )
        self.assertEqual(len(trips), 2)
        self.assertEqual(
            result["analysis"]["focused_trip_count"],
            1,
        )
        self.assertEqual(
            result["analysis"]["focus_rules"][0]["matched_trip_count"],
            1,
        )
        self.assertIn(
            "focus_priority_wait",
            result["analysis"]["objective_hierarchy"],
        )

    def test_filtered_window_is_enforced_for_matching_trip(self):
        orders = [
            order("A", "Mendoza", due="2026-10-20"),
            order("B", "Rosario", due="2026-10-20"),
        ]
        fleet = [vehicle()]
        assignment = assignment_for(orders, fleet)

        result = run_schedule(
            orders,
            fleet,
            assignment,
            {
                "strategy": "earliest_dispatch",
                "temporal_rules": [
                    {
                        "id": "rule-window",
                        "field": "destination",
                        "values": ["Rosario"],
                        "action": "window",
                        "planning_window_start": "2026-10-05",
                        "planning_window_end": "2026-10-05",
                    }
                ],
            },
        )

        rosario = next(
            item
            for item in result["scenarios"]["selected"]["trips"]
            if item["destination"] == "Rosario"
        )
        self.assertEqual(rosario["dispatch_date"], "2026-10-05")
        evidence = result["analysis"]["focus_rules"][0]
        self.assertEqual(evidence["action"], "window")
        self.assertEqual(evidence["matched_trip_count"], 1)

    def test_product_filter_uses_assignment_loads(self):
        orders = [
            order("A", "Mendoza", due="2026-10-20"),
            order("B", "Rosario", due="2026-10-20"),
        ]
        fleet = [vehicle()]
        assignment = assignment_for(orders, fleet)

        result = run_schedule(
            orders,
            fleet,
            assignment,
            {
                "strategy": "earliest_dispatch",
                "temporal_rules": [
                    {
                        "id": "rule-product",
                        "field": "product",
                        "values": ["Producto B"],
                        "action": "prioritize",
                    }
                ],
            },
        )
        evidence = result["analysis"]["focus_rules"][0]
        self.assertEqual(evidence["field"], "product")
        self.assertEqual(evidence["matched_trip_count"], 1)

    def test_rule_that_matches_no_trip_is_rejected(self):
        orders = [order("A", "Mendoza", due="2026-10-20")]
        fleet = [vehicle()]
        assignment = assignment_for(orders, fleet)

        with self.assertRaisesRegex(ValueError, "no coincide"):
            run_schedule(
                orders,
                fleet,
                assignment,
                {
                    "strategy": "earliest_dispatch",
                    "temporal_rules": [
                        {
                            "id": "rule-missing",
                            "field": "destination",
                            "values": ["Ushuaia"],
                            "action": "prioritize",
                        }
                    ],
                },
            )

    def test_specific_window_must_stay_inside_global_window(self):
        with self.assertRaises(ValidationError):
            SchedulingConfig.model_validate(
                {
                    "planning_window_start": "2026-10-05",
                    "planning_window_end": "2026-10-20",
                    "temporal_rules": [
                        {
                            "id": "rule-outside",
                            "field": "destination",
                            "values": ["Rosario"],
                            "action": "window",
                            "planning_window_start": "2026-10-01",
                            "planning_window_end": "2026-10-10",
                        }
                    ],
                }
            )

    def test_duplicate_rule_ids_are_rejected(self):
        with self.assertRaises(ValidationError):
            SchedulingConfig.model_validate(
                {
                    "temporal_rules": [
                        {
                            "id": "same",
                            "field": "destination",
                            "values": ["Rosario"],
                            "action": "prioritize",
                        },
                        {
                            "id": "same",
                            "field": "origin",
                            "values": ["Cordoba"],
                            "action": "prioritize",
                        },
                    ]
                }
            )


class SchedulingPhase2FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main_ui = (
            ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "scheduling-config-v2.mjs"
        ).read_text(encoding="utf-8")
        focus_ui = (
            ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "scheduling-focus-rules.mjs"
        ).read_text(encoding="utf-8")
        cls.ui = main_ui + "\n" + focus_ui
        cls.css = (
            ROOT
            / "app"
            / "static"
            / "css"
            / "scheduling-config-v2.css"
        ).read_text(encoding="utf-8")

    def test_filter_fields_are_derived_from_assignment_output(self):
        for value in (
            "destination",
            "origin",
            "vehicle_id",
            "ownership",
            "product",
        ):
            self.assertIn(value, self.ui)
        self.assertIn("REGLAS POR FOCO", self.ui)
        self.assertIn("VIAJES AFECTADOS", self.ui)
        self.assertIn("matchingTripIds", self.ui)

    def test_ui_exposes_priority_and_specific_window_actions(self):
        self.assertIn("Priorizar salida", self.ui)
        self.assertIn("Fijar ventana específica", self.ui)
        self.assertIn("data-scheduling-rule-window-start", self.ui)
        self.assertIn("data-scheduling-rule-window-end", self.ui)
        self.assertIn("data-scheduling-rule-add", self.ui)
        self.assertIn("data-scheduling-rule-remove", self.ui)

    def test_execution_sends_temporal_rules(self):
        self.assertIn("temporal_rules", self.ui)
        self.assertIn("config.temporalRules", self.ui)
        self.assertIn("executionRules(config)", self.ui)
        self.assertIn("hydrateExecutionRules", self.ui)

    def test_phase2_rules_are_responsive(self):
        self.assertIn("scheduling-rule-builder", self.css)
        self.assertIn("scheduling-rule-list", self.css)
        self.assertIn("@media(max-width:620px)", self.css)


if __name__ == "__main__":
    unittest.main()
