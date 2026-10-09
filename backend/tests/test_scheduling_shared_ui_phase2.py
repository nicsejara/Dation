from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "app" / "static" / "js" / "dispatch"
CSS_ROOT = ROOT / "app" / "static" / "css"


class SchedulingSharedUiPhase2Tests(unittest.TestCase):
    def setUp(self):
        self.ui = (DISPATCH / "scheduling-config-v2.mjs").read_text(encoding="utf-8")
        self.focus = (DISPATCH / "scheduling-focus-rules.mjs").read_text(encoding="utf-8")
        self.shared = (DISPATCH / "decision-config-ui.mjs").read_text(encoding="utf-8")
        self.css = (CSS_ROOT / "scheduling-config-shared-phase2.css").read_text(encoding="utf-8")

    def test_scheduling_uses_assignment_reference_shell(self):
        self.assertIn('decision-config-ui.mjs?v=scheduling-shared-phase2-v1', self.ui)
        for marker in (
            "decisionHero(",
            "decisionCaseCard(",
            "decisionDataFileCard(",
            "decisionSectionHeader(",
            "configSummaryBar(",
            'assignment-config-root scheduling-config-root',
            'assignment-config-v2',
            'assignment-config-sections',
        ):
            self.assertIn(marker, self.ui)
        self.assertNotIn("function sectionHead(", self.ui)
        self.assertNotIn("function choice(", self.ui)

    def test_temporal_scope_uses_progressive_disclosure_without_changing_rules(self):
        for marker in (
            'data-scheduling-window-mode',
            'data-scheduling-window-editor',
            'focusRulesOpen',
            'data-scheduling-focus-toggle',
            'aria-expanded',
            'focusRulesMarkup(config,stats.trips)',
            'bindFocusRuleEvents(root',
            'executionRules(config)',
        ):
            self.assertIn(marker, self.ui)
        self.assertIn("scheduling-focus-disclosure__body[hidden]", self.css)
        self.assertIn("REGLAS POR FOCO", self.ui + self.focus)
        self.assertIn("Ninguna regla puede eliminar viajes", self.ui)

    def test_objective_uses_shared_selected_and_disabled_cards(self):
        for marker in (
            'data-scheduling-objective',
            'title:"Servicio primero"',
            'disabled:!slaAvailable',
            'title:"Salida más temprana"',
            'decisionChoiceCard({',
        ):
            self.assertIn(marker, self.ui)
        self.assertIn('selected?"is-selected":""', self.shared)
        self.assertIn('disabled?"is-disabled":""', self.shared)

    def test_resources_are_inherited_and_locked(self):
        for marker in (
            'current:"Heredada y bloqueada"',
            'data-scheduling-resource-policy',
            'selected:true',
            'locked:true',
            'tags:["Bloqueada"]',
        ):
            self.assertIn(marker, self.ui)
        self.assertIn('locked?"is-locked":""', self.shared)
        self.assertIn("scheduling-resource-card.is-locked", self.css)

    def test_dashboard_depth_keeps_only_essential_active(self):
        for marker in (
            'key:"essential"',
            'selected:config.analysisDepth==="essential"',
            'key:"comparative"',
            'key:"deep"',
            'disabled:true',
            'tag:"Próximamente"',
            'analysisDepth:"essential"',
        ):
            self.assertIn(marker, self.ui)

    def test_summary_chips_are_reactive_and_validate_before_review(self):
        for marker in (
            'target:"scheduling-scope"',
            'target:"scheduling-objective"',
            'target:"scheduling-resources"',
            'target:"scheduling-dashboard"',
            'data-summary-target',
            'configProblem(config,slaAvailable,trips)',
            'scrollToProblem(problem)',
            'reviewHook:"data-scheduling-review"',
        ):
            self.assertIn(marker, self.ui)

    def test_phase2_keeps_engine_contract_untouched(self):
        for marker in (
            'strategy:config.strategy',
            'planning_window_start',
            'planning_window_end',
            'temporal_rules:executionRules(config)',
            'source_run_id:sourceRun.id',
            'node_id:"logistics_scheduling"',
        ):
            self.assertIn(marker, self.ui)

    def test_phase2_is_responsive_and_reduced_motion_safe(self):
        self.assertIn("@media(max-width:820px)", self.css)
        self.assertIn("@media(max-width:760px)", self.css)
        self.assertIn("@media(max-width:560px)", self.css)
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.css)


if __name__ == "__main__":
    unittest.main()
