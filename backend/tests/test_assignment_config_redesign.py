from pathlib import Path
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DISPATCH_JS = BACKEND_ROOT / "app" / "static" / "js" / "dispatch"
CSS_ROOT = BACKEND_ROOT / "app" / "static" / "css"


class AssignmentConfigRedesignContractTests(unittest.TestCase):
    def setUp(self):
        self.config = (DISPATCH_JS / "assignment/assignment-config.mjs").read_text(encoding="utf-8")
        self.shared_ui = (DISPATCH_JS / "decision-config-ui.mjs").read_text(encoding="utf-8")
        self.surface = self.config + self.shared_ui
        self.workspace = (DISPATCH_JS / "workspace.mjs").read_text(encoding="utf-8")
        self.css = (CSS_ROOT / "assignment-config-v2.css").read_text(encoding="utf-8")

    def test_hero_case_and_four_sections(self):
        for marker in (
            "Definí cómo querés distribuir tu carga.",
            "ESTA DECISIÓN",
            "Contexto del Case",
            "Data Owner",
            "Órdenes + Flota",
            'number:"01",eyebrow:"ALCANCE"',
            'number:"02",eyebrow:"OBJETIVO"',
            'number:"03",eyebrow:"RECURSOS"',
            'number:"04",eyebrow:"OPCIONES AVANZADAS"',
            "Alcance de los datos",
            "Objetivo de la decisión",
            "Política de recursos",
            "Opciones avanzadas",
        ):
            self.assertIn(marker, self.surface)

    def test_scope_is_real_and_previewed_server_side(self):
        for marker in (
            "/api/runs/assignment-preview",
            "Últimas 2 semanas",
            "data-filter-category",
            "data-filter-number-min",
            "data-filter-date-preset",
            "Los filtros no dejan ninguna orden",
            "filterPayload(state.scopeFilters",
        ):
            self.assertIn(marker, self.config + self.workspace)

    def test_objective_custom_and_co2_policy(self):
        for marker in (
            "Personalizado",
            "Pesos de prioridad",
            "normalizeRawWeights",
            "En consolidación",
            "data-custom-weight",
            "Igualar pesos",
        ):
            self.assertIn(marker, self.config)

    def test_resource_policy_and_inert_advanced_options(self):
        for marker in (
            "Solo propia",
            "Mixta",
            "Solo tercerizada",
            "resource_mode:state.resourceMode",
            "Límite de tercerización",
            "Próximamente",
            "aria-disabled",
        ):
            self.assertIn(marker, self.surface + self.workspace)

    def test_summary_and_accessibility(self):
        for marker in (
            "Tu configuración",
            "Lista para revisar.",
            "d-workflow-action-bar--config",
            "aria-label=\"Opciones avanzadas\"",
            "aria-live=\"polite\"",
            "@media(prefers-reduced-motion:reduce)",
            "@media(max-width:760px)",
        ):
            self.assertIn(marker, self.surface + self.css)

    def test_old_assignment_composer_copy_is_not_visible_in_new_module(self):
        for legacy in (
            "Variables que intervienen",
            "Siempre activas",
            "Las fechas se deciden después",
            "Personalizar prioridades",
            "Permitir flota tercerizada",
            "Assignment listo para ejecutar",
        ):
            self.assertNotIn(legacy, self.config)


if __name__ == "__main__":
    unittest.main()
