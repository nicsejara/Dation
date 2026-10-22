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
        cls.toolbar = (JS / "dashboard-toolbar.mjs").read_text()
        cls.toolbar_styles = (CSS / "dashboard-toolbar.css").read_text()
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

    def test_shell_keeps_technical_depth_without_product_badge(self):
        self.assertIn(
            "root.dataset.analysisDepth=depth.depth",
            self.shell,
        )
        self.assertNotIn("data-depth-badge", self.toolbar)
        self.assertNotIn("Profundidad", self.toolbar)
        self.assertNotIn("data-depth-toggle", self.shell)
        self.assertNotIn("data-analysis-depth-select", self.shell)
        self.assertNotIn("analysis_depth=", self.shell)

    def test_hero_is_the_only_approval_entry_using_the_existing_controller(self):
        self.assertIn("renderDashboardToolbar(run,caseActions,{placement:'hero'})",self.shell)
        self.assertIn('renderSchedulingShell(root,run,actions)',self.scheduling)
        self.assertIn("renderDashboardToolbar(run,caseActions,{placement:'hero'})",(JS/'scheduling-dashboard-shell.mjs').read_text())
        self.assertIn('data-export-menu',self.toolbar)
        self.assertIn('data-more-menu',self.toolbar)
        self.assertIn('data-approve-toolbar',self.toolbar)
        self.assertNotIn('approvalMarkup',self.shell)
        self.assertNotIn('data-approve-final',self.shell)
        self.assertNotIn('data-approve-final',(JS/'scheduling-dashboard-shell.mjs').read_text())
        self.assertNotIn('caseActions.onApprove()',self.shell)
        self.assertNotIn('data-rerun-validation',self.shell)
        self.assertIn('await caseActions.onApprove()',self.toolbar)
        self.assertNotIn('approveButton?.click()',self.toolbar)

    def test_export_downloads_audited_csv_and_json_artifacts(self):
        self.assertIn(
            "downloadRunExport",
            self.toolbar,
        )
        self.assertIn("downloadRunExport(run,'csv'", self.toolbar)
        self.assertIn(
            "downloadRunExport(run,'json'",
            self.toolbar,
        )
        export_source = (JS / "export.mjs").read_text()
        self.assertIn(
            "filename:'assignment-recomendada.csv'",
            export_source,
        )
        self.assertNotIn("comparativo.csv", self.shell)
        self.assertNotIn("pdf", self.shell.lower())

    def test_rerun_returns_to_existing_handler_without_auto_execution(self):
        self.assertIn("onRerun?.();", self.toolbar)
        self.assertNotIn("post('/api/runs", self.shell)
        self.assertNotIn("execute()", self.shell)

    def test_execution_drawer_closes_with_button_escape_and_backdrop(self):
        self.assertIn('data-run-drawer',self.toolbar)
        self.assertIn('aria-modal="true"',self.toolbar)
        self.assertIn("scope.listen(backdrop,'click'",self.toolbar)
        self.assertIn("scope.listen(closeButton,'click'",self.toolbar)
        self.assertIn("event.key==='Escape'",self.toolbar)
        self.assertIn('restoreFocus?.focus',self.toolbar)
        self.assertIn('scope.own(()=>closeDrawer({focus:false}))',self.toolbar)

    def test_review_and_approved_states_are_explicit(self):
        self.assertIn("review:{label:'En revisión'", self.selectors)
        self.assertIn("approved:{label:'Aprobada'", self.selectors)
        self.assertIn("data-status-badge", self.toolbar)
        self.assertIn("badge.textContent='Aprobada'", self.toolbar)
        self.assertIn("data-after-approve", self.toolbar)
        self.assertNotIn("Continuar en el mapa", self.shell)
        self.assertIn("bindDashboardActions", self.toolbar)

    def test_decision_case_rail_preserves_disabled_navigation_guard(self):
        self.assertIn("decisionRail(caseActions)", self.shell)
        self.assertIn("bindDecisionRail(root,caseActions)", self.shell)
        self.assertIn("if(button.disabled)return;", self.rail)
        self.assertIn("disabled", self.rail)

    def test_existing_assignment_content_modules_are_preserved(self):
        self.assertIn("assignmentSummary.render(nodes.hero,result,caseActions)", self.dashboard)
        self.assertIn(
            "renderModule(nodes.assignment,assignmentEvidence,result)",
            self.dashboard,
        )
        self.assertIn("renderModule(nodes.review,assignmentValidation,result)", self.dashboard)
        self.assertIn(
            "assignmentAiSummary.render(nodes.explanation,run)",
            self.dashboard,
        )

    def test_styles_are_scoped_responsive_and_focus_visible(self):
        self.assertIn(".assignment-dashboard-v2{", self.styles)
        self.assertIn("@media(max-width:980px)", self.toolbar_styles)
        self.assertIn("@media(max-width:760px)", self.toolbar_styles)
        self.assertIn("@media(max-width:520px)", self.toolbar_styles)
        self.assertIn(":focus-visible", self.styles)
        self.assertNotIn("transition:",self.toolbar_styles)
        self.assertIn(
            "ensureStylesheet(ASSIGNMENT_STYLE_ID,'/static/css/assignment-dashboard-v2.css')",
            self.dashboard,
        )


if __name__ == "__main__":
    unittest.main()
