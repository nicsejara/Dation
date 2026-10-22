from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "app" / "static"


class TraceabilityPhase3Contracts(unittest.TestCase):
    def test_landing_opens_global_center_filtered_to_logistics(self):
        source = (ROOT / "js" / "dda-logistics-landing.js").read_text(encoding="utf-8")
        self.assertIn("traceability-controller.mjs", source)
        self.assertIn("openDecisionCenter({dda:'logistics'})", source)
        self.assertIn("startNewDecision", source)
        self.assertNotIn("listDecisionCases", source)
        self.assertNotIn("openDecisionMap({trigger:map})", source)

    def test_controller_restores_data_pack_before_guarded_views(self):
        source = (ROOT / "js" / "dispatch" / "traceability-controller.mjs").read_text(encoding="utf-8")
        self.assertIn("['active','completed']", source)
        self.assertIn("/api/decision-cases?status=", source)
        self.assertIn("window.DationDispatch.openCase", source)
        self.assertNotIn("location.reload", source)
        self.assertNotIn("sessionStorage", source)
        workspace = (ROOT / "js" / "dispatch" / "workspace.mjs").read_text()
        self.assertIn("async function hydrateCase", workspace)
        self.assertIn("resourceUrl", workspace)

    def test_map_exposes_run_history_and_new_run_flow(self):
        source = (ROOT / "js" / "dispatch" / "traceability-controller.mjs").read_text(encoding="utf-8")
        self.assertIn("/runs?node_id=", source)
        self.assertIn("+ Nueva corrida", source)
        self.assertIn("Historial · ", source)
        ui = (ROOT / "js" / "dispatch" / "traceability-ui.mjs").read_text()
        self.assertIn("Alternativa", ui)
        self.assertIn("Aprobación anterior", ui)
        self.assertIn("openRunHistory", source)

    def test_history_distinguishes_current_candidate_and_superseded(self):
        source = (ROOT / "js" / "dispatch" / "traceability-ui.mjs").read_text(encoding="utf-8")
        for text in (
            "Aprobada vigente",
            "Alternativa",
            "Aprobación anterior",
            "Ver y decidir →",
            "Ver histórico →",
            "Ver análisis →",
        ):
            self.assertIn(text, source)
        self.assertIn("['approved','candidate','superseded','stale']", source)
        self.assertNotIn("['approved','candidate','superseded','running']", source)

    def test_traceability_ui_is_responsive(self):
        css = (ROOT / "css" / "decision-trace-v3.css").read_text(encoding="utf-8")
        self.assertIn(".dispatch-case-selector__grid", css)
        self.assertIn(".dispatch-run-history__item", css)
        self.assertIn(".dispatch-decision-node__tracebar", css)
        self.assertIn("@media(max-width:820px)", css)
        self.assertIn("@media(max-width:540px)", css)


if __name__ == "__main__":
    unittest.main()
