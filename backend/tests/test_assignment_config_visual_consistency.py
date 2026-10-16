from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "app" / "static" / "css" / "decision-trace-v3.css").read_text(encoding="utf-8")
DESIGN_SYSTEM = (ROOT / "app" / "static" / "css" / "dation-design-system.css").read_text(encoding="utf-8")


def test_decision_summary_reuses_case_visual_language():
    assert ".assignment-config-root .assignment-case-strip" in CSS
    assert 'grid-template-areas:"identity action" "pack pack"' in CSS
    assert ".assignment-config-root .assignment-case-strip__pack" in CSS
    assert "border-top:1px solid var(--d-border)" in CSS
    assert 'content:"✓  2 archivos · Datos validados"' in CSS
    assert 'content:"✓  Validado"' in CSS


def test_config_map_icons_keep_outline_svg_contract():
    assert ".assignment-config-root .dispatch-map-icon" in CSS
    assert "fill:none" in CSS
    assert "stroke:currentColor" in CSS
    assert "stroke-width:1.75" in CSS


def test_decision_panel_copy_wraps_instead_of_overflowing():
    assert ".d-page-hero--workflow .dispatch-pro-how-node :is(small,strong)" in DESIGN_SYSTEM
    assert "white-space:normal" in DESIGN_SYSTEM
    assert "overflow-wrap:anywhere" in DESIGN_SYSTEM
    assert "grid-template-columns:24px minmax(0,1fr)" in DESIGN_SYSTEM
    assert ".assignment-decision-panel" not in CSS


def test_mobile_case_summary_stacks_cleanly():
    assert "@media(max-width:760px)" in CSS
    assert 'grid-template-areas:"identity" "action" "pack"' in CSS


def load_tests(loader, tests, pattern):
    import unittest
    for name, value in sorted(globals().items()):
        if name.startswith("test_") and callable(value):
            tests.addTest(unittest.FunctionTestCase(value))
    return tests
