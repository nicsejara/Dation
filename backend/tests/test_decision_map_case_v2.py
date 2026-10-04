from pathlib import Path
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DISPATCH_JS = BACKEND_ROOT / "app" / "static" / "js" / "dispatch"
CSS_ROOT = BACKEND_ROOT / "app" / "static" / "css"


class DecisionMapCaseV2ContractTests(unittest.TestCase):
    def setUp(self):
        self.decision_map = (DISPATCH_JS / "decision-map.mjs").read_text(
            encoding="utf-8"
        )
        self.decision_ui = (DISPATCH_JS / "decision-ui.mjs").read_text(
            encoding="utf-8"
        )
        self.css = (CSS_ROOT / "decision-map-case-v2.css").read_text(
            encoding="utf-8"
        )

    def test_case_identity_and_progress(self):
        for marker in (
            'return "DC-"+String(value).slice(0,8).toUpperCase()',
            "Todo lo que decidas queda registrado en este caso.",
            "data-copy-case-id",
            "aria-live=\"polite\"",
            "dispatch-case-progress__label",
            "progressLabel",
            "Con revisión pendiente",
            "Completo",
        ):
            self.assertIn(marker, self.decision_map + self.decision_ui)

    def test_data_pack_reuses_real_dataset_metadata(self):
        for marker in (
            "canonical_filename",
            "created_at",
            "middleEllipsis",
            "data-map-columns",
            "createGuideDrawer",
            "Datos validados",
            "Cargado ",
        ):
            self.assertIn(marker, self.decision_map)

    def test_decision_cards_and_connectors_are_clean(self):
        self.assertIn("DECISIÓN ", self.decision_map)
        self.assertIn("SIGUIENTE DECISIÓN", self.decision_map)
        self.assertIn("dispatch-decision-node__waiting", self.decision_map)
        self.assertNotIn(
            '<span class="dispatch-decision-edge__label">',
            self.decision_map,
        )
        self.assertIn("chevronRight", self.decision_map)
        self.assertIn("Se habilita al aprobar ", self.decision_map)

    def test_visual_alignment_and_responsive_contract(self):
        for marker in (
            "grid-template-columns:minmax(0,1fr) 64px",
            "grid-template-rows:54px 58px 58px 86px 62px 20px 48px",
            "background:transparent",
            "top:-14px",
            "font-size:14px",
            "@media(max-width:1099px)",
            "@media(prefers-reduced-motion:reduce)",
        ):
            self.assertIn(marker, self.css)

    def test_change_data_discloses_available_impact(self):
        for marker in (
            "Decisiones aprobadas afectadas",
            "va a crear un nuevo Decision Case",
            "conservará el historial del caso actual",
        ):
            self.assertIn(marker, self.decision_map)


if __name__ == "__main__":
    unittest.main()
