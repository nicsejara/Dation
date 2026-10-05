from pathlib import Path
import unittest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
LANDING_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "dda-logistics-landing.js"
)
APP_HTML = BACKEND_ROOT / "app" / "templates" / "app.html"


class LandingNavigationContractTests(unittest.TestCase):
    def setUp(self):
        self.landing = LANDING_JS.read_text(encoding="utf-8")
        self.html = APP_HTML.read_text(encoding="utf-8")

    def test_landing_map_is_informational_not_runtime_status(self):
        for marker in (
            "Cómo se encadenan las decisiones",
            "Una decisión alimenta a la siguiente.",
            "El estado real de cada caso se consulta en tu Decision Map.",
            "DECISIÓN ",
            "is-conceptual",
            "Cada resultado se revisa y se aprueba antes de alimentar",
        ):
            self.assertIn(marker, self.landing)

        for legacy_runtime in (
            "deriveMapStates",
            "statePresentation",
            "syncDecisionMap",
            "normalizedRuntimeStatus",
            "data-node-action",
            "data-node-lockcopy",
        ):
            self.assertNotIn(legacy_runtime, self.landing)

    def test_active_case_cta_goes_to_real_decision_map(self):
        for marker in (
            "hasActiveDecisionCase",
            "data-go-map",
            "Ir a mi Decision Map",
            "openActiveMap",
            'navigate("logistics-map")',
            "Iniciá una decisión para crear tu Decision Map",
        ):
            self.assertIn(marker, self.landing)

        self.assertIn("Iniciar nueva decisión", self.html)
        self.assertIn("data-scroll-decision-map", self.html)

    def test_state_legend_and_card_actions_are_removed_at_runtime(self):
        self.assertIn(".dda-landing__state-legend", self.landing)
        self.assertIn("legend&&legend.remove()", self.landing)
        self.assertIn("state&&state.remove()", self.landing)
        self.assertIn("footer&&footer.remove()", self.landing)

    def test_landing_keeps_only_case_existence_as_dynamic_state(self):
        self.assertIn("saved.decisionCase.id", self.landing)
        self.assertNotIn("decisionCase.nodes", self.landing)
        self.assertNotIn('status==="approved"', self.landing)
        self.assertNotIn('status==="review"', self.landing)


if __name__ == "__main__":
    unittest.main()
