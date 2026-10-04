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


class DecisionMapMicroPolishTests(unittest.TestCase):
    def test_active_cta_is_larger_and_has_clear_hover_feedback(self):
        for marker in (
            "font-size:16px",
            "font-weight:800",
            "transform:translateY(-2px)",
            "box-shadow:0 17px 36px",
            "transform:translateX(3px)",
        ):
            self.assertIn(marker, CSS)

    def test_global_state_legend_is_hidden(self):
        self.assertIn(
            ".dispatch-decision-map--case-v2 .dispatch-map-chain-heading .dispatch-map-legend",
            CSS,
        )
        self.assertIn("display:none!important", CSS)

    def test_progress_uses_numbered_milestones_without_labels(self):
        for marker in (
            'content:"1"',
            'content:"2"',
            'content:"3"',
            ".dispatch-case-progress__grid::before",
            ".dispatch-case-progress__item.is-approved:not(:last-child)::before",
            "height:30px!important",
            ".dispatch-case-progress__label",
            "display:none!important",
        ):
            self.assertIn(marker, CSS)

    def test_reduced_motion_removes_cta_translation(self):
        self.assertIn("@media(prefers-reduced-motion:reduce)", CSS)
        self.assertIn("transform:none", CSS)


if __name__ == "__main__":
    unittest.main()
