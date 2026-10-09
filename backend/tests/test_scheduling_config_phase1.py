from pathlib import Path
import unittest

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
UI = (
    ROOT
    / "app"
    / "static"
    / "js"
    / "dispatch"
    / "scheduling-config-v2.mjs"
).read_text(encoding="utf-8")
SHARED_UI = (
    ROOT
    / "app"
    / "static"
    / "js"
    / "dispatch"
    / "decision-config-ui.mjs"
).read_text(encoding="utf-8")
SURFACE = UI + "\n" + SHARED_UI
CSS = (
    ROOT
    / "app"
    / "static"
    / "css"
    / "scheduling-config-v2.css"
).read_text(encoding="utf-8") + "\n" + (
    ROOT
    / "app"
    / "static"
    / "css"
    / "scheduling-config-shared-phase2.css"
).read_text(encoding="utf-8")
BOOTSTRAP = (
    ROOT
    / "app"
    / "static"
    / "js"
    / "dda-variable-config.js"
).read_text(encoding="utf-8")


def assignment_for(orders, fleet):
    helper = SchedulingEngineTests()
    return helper.assignment(orders, fleet)


def run_schedule(orders, fleet, assignment, configuration=None, options=None):
    return run_scheduling_engine(
        csv_bytes(ORDER_COLUMNS, orders),
        csv_bytes(FLEET_COLUMNS, fleet),
        assignment,
        configuration=configuration or {},
        options={
            "solve_time_limit_s": 5,
            "deterministic_limit": .05,
            **(options or {}),
        },
    )


class SchedulingConfigPhase1Tests(unittest.TestCase):
    def test_scheduling_window_is_part_of_canonical_configuration(self):
        config = SchedulingConfig.model_validate(
            {
                "strategy": "service_first",
                "planning_window_start": "2026-10-05",
                "planning_window_end": "2026-10-15",
            }
        )
        payload = config.model_dump(mode="json")
        self.assertEqual(payload["planning_window_start"], "2026-10-05")
        self.assertEqual(payload["planning_window_end"], "2026-10-15")

    def test_scheduling_window_rejects_reversed_dates(self):
        with self.assertRaises(ValidationError):
            SchedulingConfig.model_validate(
                {
                    "planning_window_start": "2026-10-20",
                    "planning_window_end": "2026-10-10",
                }
            )

    def test_custom_window_delays_dispatch_but_keeps_assignment(self):
        orders = [order("A", "Mendoza", ready="2026-10-01", due="2026-10-20")]
        fleet = [vehicle(available_from="2026-10-01", available_until="2026-10-31")]
        assignment = assignment_for(orders, fleet)

        result = run_schedule(
            orders,
            fleet,
            assignment,
            configuration={
                "strategy": "service_first",
                "planning_window_start": "2026-10-07",
                "planning_window_end": "2026-10-10",
            },
            options={"max_horizon_days": 3},
        )

        scheduled = result["scenarios"]["selected"]["trips"][0]
        source = assignment["scenarios"]["selected"]["trips"][0]
        self.assertEqual(scheduled["dispatch_date"], "2026-10-07")
        self.assertEqual(scheduled["vehicle_id"], source["vehicle_id"])
        self.assertEqual(scheduled["loads"], source["loads"])
        self.assertEqual(result["analysis"]["planning_window"]["start"], "2026-10-07")
        self.assertEqual(result["analysis"]["planning_window"]["end"], "2026-10-10")

    def test_custom_window_fails_if_all_dispatches_cannot_fit(self):
        orders = [
            order("A", "Mendoza", ready="2026-10-01", due="2026-10-20"),
            order("B", "Rosario", ready="2026-10-01", due="2026-10-20"),
        ]
        fleet = [vehicle(available_from="2026-10-01", available_until="2026-10-31")]
        assignment = assignment_for(orders, fleet)

        with self.assertRaisesRegex(ValueError, "ventana|planificación"):
            run_schedule(
                orders,
                fleet,
                assignment,
                configuration={
                    "strategy": "earliest_dispatch",
                    "planning_window_start": "2026-10-01",
                    "planning_window_end": "2026-10-01",
                },
                options={"max_horizon_days": 1},
            )

    def test_earliest_dispatch_strategy_does_not_use_due_dates(self):
        config = SchedulingConfig.model_validate(
            {
                "strategy": "earliest_dispatch",
                "use_delivery_due_dates": True,
            }
        )
        self.assertFalse(config.use_delivery_due_dates)

        orders = [order("A", "Mendoza", due="2026-10-01")]
        fleet = [vehicle()]
        assignment = assignment_for(orders, fleet)
        result = run_schedule(
            orders,
            fleet,
            assignment,
            configuration={"strategy": "earliest_dispatch"},
        )
        self.assertFalse(result["analysis"]["sla_enabled"])
        self.assertEqual(
            result["analysis"]["objective_hierarchy"],
            ["total_wait_days", "makespan"],
        )

    def test_phase1_scheduling_ui_matches_assignment_configuration_language(self):
        self.assertIn("DECISIÓN ", SURFACE)
        self.assertIn("Decision Case y Data Pack en uso", SURFACE)
        self.assertIn("Alcance temporal", UI)
        self.assertIn("Objetivo del calendario", UI)
        self.assertIn("Política de recursos", UI)
        self.assertIn("Profundidad del análisis", UI)
        self.assertIn("Ventana automática", UI)
        self.assertIn("Ventana personalizada", UI)
        self.assertIn('type=\"date\"', UI)
        self.assertIn("Servicio primero", UI)
        self.assertIn("Salida más temprana", UI)
        self.assertIn("Heredada y bloqueada", UI)

    def test_phase1_ui_is_loaded_and_responsive(self):
        self.assertIn('scheduling-config-v2.mjs?v=scheduling-shared-phase2-v1', BOOTSTRAP)
        self.assertIn(".scheduling-config-v2", CSS)
        self.assertIn("@media(max-width:620px)", CSS)
        self.assertIn("@media(max-width:760px)", CSS)
        self.assertIn("@media(prefers-reduced-motion:reduce)", CSS)

    def test_phase1_execution_sends_real_window_and_strategy(self):
        self.assertIn("planning_window_start", UI)
        self.assertIn("planning_window_end", UI)
        self.assertIn('strategy:config.strategy', UI)
        self.assertIn('node_id:\"logistics_scheduling\"', UI)
        self.assertIn("source_run_id:sourceRun.id", UI)


if __name__ == "__main__":
    unittest.main()
