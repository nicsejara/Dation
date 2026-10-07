from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILTER_JS = (ROOT / "app" / "static" / "js" / "dispatch" / "assignment-filter-collapse.mjs").read_text(encoding="utf-8")
VARIABLE_BOOTSTRAP = (ROOT / "app" / "static" / "js" / "dda-variable-config.js").read_text(encoding="utf-8")


def test_collapsible_filter_behavior_is_loaded_by_assignment_workspace():
    assert 'assignment-filter-collapse.mjs?v=scope-filter-collapse-v1' in VARIABLE_BOOTSTRAP


def test_applied_filters_have_independent_expand_and_remove_actions():
    assert 'data-filter-collapse-toggle' in FILTER_JS
    assert 'data-filter-remove' in FILTER_JS
    assert 'head.insertBefore(toggle,remove||null)' in FILTER_JS
    assert 'aria-expanded' in FILTER_JS
    assert 'Cerrar filtro' in FILTER_JS
    assert 'Abrir filtro' in FILTER_JS


def test_filter_open_state_survives_config_rerenders():
    assert 'const expandedKeys=new Set()' in FILTER_JS
    assert 'const knownKeys=new Set()' in FILTER_JS
    assert 'if(firstSeen)expandedKeys.add(key)' in FILTER_JS
    assert 'setExpanded(row,key,expandedKeys.has(key))' in FILTER_JS
    assert 'MutationObserver(scheduleReconcile)' in FILTER_JS


def test_collapsed_filter_keeps_a_compact_summary():
    assert 'assignment-filter-row__summary' in FILTER_JS
    assert 'categorySummary(row)' in FILTER_JS
    assert 'dateSummary(row)' in FILTER_JS
    assert 'numberSummary(row)' in FILTER_JS
    assert 'is-collapsed>:not(.assignment-filter-row__head)' in FILTER_JS


def test_filter_toggle_has_responsive_and_reduced_motion_styles():
    assert '@media(max-width:560px)' in FILTER_JS
    assert '@media(prefers-reduced-motion:reduce)' in FILTER_JS
    assert 'assignment-filter-toggle svg' in FILTER_JS
