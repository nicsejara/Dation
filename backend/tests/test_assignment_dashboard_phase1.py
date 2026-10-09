from pathlib import Path
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
JS = STATIC / "js" / "dispatch"
CSS = STATIC / "css"


class AssignmentDashboardPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard = (JS / "dashboard.mjs").read_text()
        cls.shell = (
            JS / "assignment-dashboard-shell.mjs"
        ).read_text()
        cls.selectors = (
            JS / "assignment-dashboard-selectors.mjs"
        ).read_text()
        cls.rail = (JS / "decision-nav.mjs").read_text()
        cls.scheduling = (
            JS / "scheduling-dashboard.mjs"
        ).read_text()
        cls.styles = (
            CSS / "assignment-dashboard-v2.css"
        ).read_text()

    def test_analysis_depth_selector_reads_persisted_contract(self):
        script = textwrap.dedent(
            """
            import {
              getAnalysisDepth,
              analysisDepthUi,
            } from './app/static/js/dispatch/assignment-dashboard-selectors.mjs';

            const cases = [
              [{result_json:{analysis:{depth:'essential'}}}, 'essential'],
              [{result_json:{configuration:{options:{analysis_depth:'comparative'}}}}, 'comparative'],
              [{configuration_json:{options:{analysis_depth:'essential'}}}, 'essential'],
              [{result_json:{}}, 'comparative'],
              [{result_json:{analysis:{depth:'unknown'}}}, 'comparative'],
            ];
            for (const [run, expected] of cases) {
              if (getAnalysisDepth(run) !== expected) {
                throw new Error('depth mismatch: ' + expected);
              }
            }
            if (analysisDepthUi('essential').label !== 'Esencial') {
              throw new Error('missing essential label');
            }
            if (analysisDepthUi('comparative').label !== 'Comparativo') {
              throw new Error('missing comparative label');
            }
            """
        )
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr,
        )

    def test_assignment_v2_is_schema_scoped_and_scheduling_stays_separate(self):
        self.assertIn(
            "result?.schema_version==='scheduling_v1'",
            self.dashboard,
        )
        self.assertIn(
            "schedulingDashboard.render(",
            self.dashboard,
        )
        self.assertIn(
            "result?.schema_version==='assignment_v1'",
            self.dashboard,
        )
        self.assertIn(
            "renderAssignmentDashboard(root,run,onRerun,caseActions)",
            self.dashboard,
        )
        self.assertNotIn(
            "assignment-dashboard-v2",
            self.scheduling,
        )

    def test_shell_exposes_persisted_depth_as_badge_not_editable_switch(self):
        self.assertIn(
            "root.dataset.analysisDepth=depth.depth",
            self.shell,
        )
        self.assertIn("data-depth-badge", self.shell)
        self.assertNotIn("data-depth-toggle", self.shell)
        self.assertNotIn("data-analysis-depth-select", self.shell)
        self.assertNotIn("analysis_depth=", self.shell)

    def test_toolbar_keeps_tools_and_moves_approval_to_validation(self):
        self.assertIn(
            "assignment-dashboard-v2__toolbar",
            self.shell,
        )
        self.assertIn("data-export-menu", self.shell)
        self.assertIn("data-more-menu", self.shell)
        self.assertIn(
            "assignment-dashboard-v2__approval",
            self.shell,
        )
        self.assertIn("data-approve", self.shell)
        self.assertIn(
            "Dation IA no es requisito para aprobar.",
            self.shell,
        )

    def test_export_reuses_existing_csv_and_json_helpers(self):
        self.assertIn(
            "exportDecision,exportDecisionJson",
            self.shell,
        )
        self.assertIn("exportDecision(result)", self.shell)
        self.assertIn(
            "exportDecisionJson(result,run.id)",
            self.shell,
        )
        export_source = (JS / "export.mjs").read_text()
        self.assertIn(
            "filename:'assignment-recomendada.csv'",
            export_source,
        )
        self.assertNotIn("comparativo.csv", self.shell)
        self.assertNotIn("pdf", self.shell.lower())

    def test_rerun_returns_to_existing_handler_without_auto_execution(self):
        self.assertIn("onRerun?.();", self.shell)
        self.assertNotIn("post('/api/runs", self.shell)
        self.assertNotIn("execute()", self.shell)

    def test_execution_drawer_closes_with_button_escape_and_backdrop(self):
        self.assertIn("data-run-drawer", self.shell)
        self.assertIn("aria-modal=\"true\"", self.shell)
        self.assertIn(
            "backdrop?.addEventListener('click',closeDrawer)",
            self.shell,
        )
        self.assertIn(
            "closeButton?.addEventListener('click',closeDrawer)",
            self.shell,
        )
        self.assertIn("event.key==='Escape'", self.shell)
        self.assertIn("restoreFocus?.focus?.()", self.shell)

    def test_review_and_approved_states_are_explicit(self):
        self.assertIn("review:{label:'En revisión'", self.selectors)
        self.assertIn("approved:{label:'Aprobada'", self.selectors)
        self.assertIn("data-status-badge", self.shell)
        self.assertIn("statusBadge.textContent='Aprobada'", self.shell)
        self.assertIn("data-after-approve", self.shell)
        self.assertIn("Continuar en el mapa", self.shell)

    def test_decision_case_rail_preserves_disabled_navigation_guard(self):
        self.assertIn("decisionRail(caseActions)", self.shell)
        self.assertIn("bindDecisionRail(root,caseActions)", self.shell)
        self.assertIn("if(button.disabled)return;", self.rail)
        self.assertIn("disabled", self.rail)

    def test_existing_assignment_content_modules_are_preserved(self):
        self.assertIn("renderModule(nodes.hero,hero,result)", self.dashboard)
        self.assertIn(
            "renderModule(nodes.assignment,assignment,result)",
            self.dashboard,
        )
        self.assertIn("renderModule(nodes.review,review,result)", self.dashboard)
        self.assertIn(
            "renderModule(nodes.explanation,explanation,run)",
            self.dashboard,
        )

    def test_styles_are_scoped_responsive_and_focus_visible(self):
        self.assertIn(".assignment-dashboard-v2{", self.styles)
        self.assertIn("@media(max-width:980px)", self.styles)
        self.assertIn("@media(max-width:760px)", self.styles)
        self.assertIn("@media(max-width:520px)", self.styles)
        self.assertIn(":focus-visible", self.styles)
        self.assertIn("prefers-reduced-motion", self.styles)
        self.assertIn(
            "ASSIGNMENT_STYLE_HREF='/static/css/assignment-dashboard-v2.css?v=assignment-dashboard-phase1'",
            self.dashboard,
        )


if __name__ == "__main__":
    unittest.main()
