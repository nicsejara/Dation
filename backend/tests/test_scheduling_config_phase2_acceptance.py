from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "app" / "static" / "js" / "dispatch" / "scheduling-config-v2.mjs").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "css" / "scheduling-config-shared-phase2.css").read_text(encoding="utf-8")


def test_phase2_keeps_same_four_section_anatomy_as_assignment():
    for marker in (
        'number:"01"',
        'eyebrow:"ALCANCE"',
        'number:"02"',
        'eyebrow:"OBJETIVO"',
        'number:"03"',
        'eyebrow:"RECURSOS"',
        'number:"04"',
        'eyebrow:"DASHBOARD"',
    ):
        assert marker in UI


def test_phase2_exposes_selected_disabled_and_locked_states():
    assert 'selected:auto' in UI
    assert 'disabled:!slaAvailable' in UI
    assert 'locked:true' in UI
    assert 'is-locked' in CSS


def test_phase2_summary_reuses_shared_assignment_bar():
    assert 'configSummaryBar({' in UI
    assert 'scheduling-summary-bar' in UI
    assert 'ready:!problem' in UI
    assert 'reason:problem?.reason||""' in UI


def test_phase2_progressive_disclosure_does_not_change_execution_payload():
    assert 'focusRulesOpen:false' in UI
    assert 'data-scheduling-focus-toggle' in UI
    assert 'temporal_rules:executionRules(config)' in UI
    assert 'planning_window_start:config.windowMode==="custom"?config.windowStart:null' in UI
    assert 'planning_window_end:config.windowMode==="custom"?config.windowEnd:null' in UI
