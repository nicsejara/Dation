from pathlib import Path

import pytest
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
CSS = (
    ROOT
    / "app"
    / "static"
    / "css"
    / "scheduling-config-v2.css"
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


def test_scheduling_window_is_part_of_canonical_configuration():
    config = SchedulingConfig.model_validate(
        {
            "strategy": "service_first",
            "planning_window_start": "2026-10-05",
            "planning_window_end": "2026-10-15",
        }
    )
    payload = config.model_dump(mode="json")
    assert payload["planning_window_start"] == "2026-10-05"
    assert payload["planning_window_end"] == "2026-10-15"


def test_scheduling_window_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        SchedulingConfig.model_validate(
            {
                "planning_window_start": "2026-10-20",
                "planning_window_end": "2026-10-10",
            }
        )


def test_custom_window_delays_dispatch_but_keeps_assignment():
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
    assert scheduled["dispatch_date"] == "2026-10-07"
    assert scheduled["vehicle_id"] == source["vehicle_id"]
    assert scheduled["loads"] == source["loads"]
    assert result["analysis"]["planning_window"]["start"] == "2026-10-07"
    assert result["analysis"]["planning_window"]["end"] == "2026-10-10"


def test_custom_window_fails_if_all_dispatches_cannot_fit():
    orders = [
        order("A", "Mendoza", ready="2026-10-01", due="2026-10-20"),
        order("B", "Rosario", ready="2026-10-01", due="2026-10-20"),
    ]
    fleet = [vehicle(available_from="2026-10-01", available_until="2026-10-31")]
    assignment = assignment_for(orders, fleet)

    with pytest.raises(ValueError, match="ventana|planificación"):
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


def test_earliest_dispatch_strategy_does_not_use_due_dates():
    config = SchedulingConfig.model_validate(
        {
            "strategy": "earliest_dispatch",
            "use_delivery_due_dates": True,
        }
    )
    assert config.use_delivery_due_dates is False

    orders = [order("A", "Mendoza", due="2026-10-01")]
    fleet = [vehicle()]
    assignment = assignment_for(orders, fleet)
    result = run_schedule(
        orders,
        fleet,
        assignment,
        configuration={"strategy": "earliest_dispatch"},
    )
    assert result["analysis"]["sla_enabled"] is False
    assert result["analysis"]["objective_hierarchy"] == [
        "total_wait_days",
        "makespan",
    ]


def test_phase1_scheduling_ui_matches_assignment_configuration_language():
    assert "DECISIÓN 02 DE 3" in UI
    assert "Decision Case y Data Pack en uso" in UI
    assert "Alcance temporal" in UI
    assert "Objetivo del calendario" in UI
    assert "Política de recursos" in UI
    assert "Profundidad del análisis" in UI
    assert "Ventana automática" in UI
    assert "Ventana personalizada" in UI
    assert 'type="date"' in UI
    assert "Servicio primero" in UI
    assert "Salida más temprana" in UI
    assert "Heredada y bloqueada" in UI


def test_phase1_ui_is_loaded_and_responsive():
    assert 'scheduling-config-v2.mjs?v=scheduling-config-phase1' in BOOTSTRAP
    assert ".scheduling-config-v2" in CSS
    assert "@media(max-width:620px)" in CSS
    assert "@media(prefers-reduced-motion:reduce)" in CSS


def test_phase1_execution_sends_real_window_and_strategy():
    assert "planning_window_start" in UI
    assert "planning_window_end" in UI
    assert 'strategy:config.strategy' in UI
    assert 'node_id:"logistics_scheduling"' in UI
    assert "source_run_id:sourceRun.id" in UI
