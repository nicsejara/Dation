from pathlib import Path
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
CSS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "css"
    / "decision-map-case-v2.css"
).read_text(encoding="utf-8")
DESIGN_SYSTEM = (BACKEND_ROOT / "app/static/css/dation-design-system.css").read_text(encoding="utf-8")
MAP_UI = (BACKEND_ROOT / "app/static/js/dispatch/cases/decision-map.mjs").read_text(encoding="utf-8")


class DecisionMapMicroPolishTests(unittest.TestCase):
    def test_active_cta_uses_shared_sizing_and_hover_feedback(self):
        for marker in (
            ".d-button--workflow",
            "min-height: var(--workflow-action-height)",
            "background: var(--color-action-primary-hover)",
            "box-shadow: none",
        ):
            self.assertIn(marker, DESIGN_SYSTEM)
        self.assertIn('WORKFLOW_ACTION_CLASS',MAP_UI)
        self.assertNotRegex(CSS,r'\.dispatch-decision-node__action\b[^{}]*\{')

    def test_global_state_legend_is_hidden(self):
        self.assertIn(
            ".dispatch-decision-map--case-v2 .dispatch-map-chain-heading .dispatch-map-legend",
            CSS,
        )
        self.assertIn("display:none!important", CSS)

    def test_progress_uses_numbered_milestones_without_labels(self):
        for marker in (
            "repeat(var(--decision-count),minmax(0,1fr))",
            ".dispatch-case-progress__item:not(:first-child)::before",
            ".dispatch-case-progress__item.is-reached::before",
            "height:22px!important",
            ".dispatch-case-progress__label",
            "clip-path:inset(50%)",
        ):
            self.assertIn(marker, CSS)
        self.assertIn("(index+1)", MAP_UI)
        self.assertIn("DECISION_ORDER.length", MAP_UI)

    def test_reduced_motion_removes_cta_translation(self):
        self.assertIn("@media(prefers-reduced-motion:reduce)", DESIGN_SYSTEM)
        self.assertIn("transform: none", DESIGN_SYSTEM)


if __name__ == "__main__":
    unittest.main()
