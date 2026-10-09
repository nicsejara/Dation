from pathlib import Path
import json
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
JS = STATIC / "js" / "dispatch"
CSS = STATIC / "css"
FIXTURE = ROOT / "tests" / "fixtures" / "assignment_dashboard" / "assignment_comparative_run.json"


class AssignmentDashboardPhase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard = (JS / "dashboard.mjs").read_text()
        cls.selectors = (JS / "assignment-dashboard-selectors.mjs").read_text()
        cls.summary = (JS / "assignment-comparative-summary.mjs").read_text()
        cls.comparison = (JS / "assignment-comparison.mjs").read_text()
        cls.validation = (JS / "assignment-validation.mjs").read_text()
        cls.styles = (CSS / "assignment-dashboard-comparative.css").read_text()
        cls.fixture = json.loads(FIXTURE.read_text())

    def test_comparative_selectors_are_direction_aware_and_use_persisted_metrics(self):
        script = textwrap.dedent(
            f"""
            import {{
              getAnalysisDepth,
              getComparableScenarios,
              getDefaultComparisonKey,
              getComparisonContext,
              compareScenarioMetric,
            }} from './app/static/js/dispatch/assignment-dashboard-selectors.mjs';

            const run = {json.dumps(self.fixture)};
            const result = run.result_json;
            if (getAnalysisDepth(run) !== 'comparative') throw new Error('depth mismatch');

            const alternatives = getComparableScenarios(result);
            if (alternatives.length !== 5) throw new Error('scenario count mismatch');
            const samePlan = alternatives.find(item => item.key === 'min_trips');
            if (!samePlan?.samePlan) throw new Error('same-plan fingerprint not detected');

            const defaultKey = getDefaultComparisonKey(result);
            if (defaultKey !== 'balanced') throw new Error('unexpected default comparison');

            const balanced = getComparisonContext(result, 'balanced');
            const semantic = Object.fromEntries(balanced.rows.map(row => [row.key, row.semantic]));
            if (semantic.total_trips !== 'same') throw new Error('trips semantic mismatch');
            if (semantic.total_cost !== 'tradeoff') throw new Error('cost direction mismatch');
            if (semantic.own_weight_share !== 'improvement') throw new Error('own-fleet direction mismatch');
            if (semantic.co2_kg !== 'tradeoff') throw new Error('co2 direction mismatch');

            const missing = structuredClone(result);
            delete missing.scenarios.balanced.metrics.co2_kg;
            if (compareScenarioMetric(missing, 'balanced', 'co2_kg').semantic !== 'no_comparable') {{
              throw new Error('missing metric must be no_comparable');
            }}

            const infeasible = structuredClone(result);
            infeasible.scenarios.balanced.feasible = false;
            if (!getComparisonContext(infeasible, 'balanced').rows.every(row => row.semantic === 'no_comparable')) {{
              throw new Error('infeasible reference must not claim improvements');
            }}
            """
        )
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_comparative_composition_replaces_legacy_assignment_modules(self):
        self.assertIn("else if(depth==='comparative')", self.dashboard)
        self.assertIn("renderModule(nodes.hero,assignmentComparativeSummary,result)", self.dashboard)
        self.assertIn("renderModule(nodes.assignment,assignmentComparison,result)", self.dashboard)
        self.assertIn("renderModule(nodes.review,assignmentValidation,result)", self.dashboard)
        self.assertNotIn("Phase 3 will replace this comparative composition", self.dashboard)
        self.assertIn("assignment-dashboard-comparative.css?v=assignment-dashboard-phase3", self.dashboard)

    def test_comparison_explains_tradeoffs_without_reconstructing_alternative_detail(self):
        for label in (
            "RECOMENDACIÓN VS ALTERNATIVAS",
            "Compará la recomendación antes de aprobarla",
            "Mejora",
            "Trade-off",
            "Sin cambio",
            "No comparable",
            "Misma distribución",
            "Referencia no factible",
            "Prioridades configuradas → Qué implicó la elección",
        ):
            self.assertIn(label, self.comparison)
        self.assertIn("métricas agregadas", self.comparison)
        self.assertNotIn("order_outcomes", self.comparison)
        self.assertNotIn(".trips", self.comparison)
        self.assertNotIn("dispatch_date", self.comparison)
        self.assertNotIn("arrival_date", self.comparison)

    def test_comparative_summary_does_not_overclaim_solver_or_savings(self):
        self.assertIn("Estado del solver", self.summary)
        self.assertIn("solverStatusLabel", self.summary)
        self.assertIn("escenarios de referencia", self.summary)
        self.assertNotIn("ahorro", self.summary.lower())
        self.assertNotIn("óptim", self.summary.lower())

    def test_comparative_keeps_phase2_validation_as_final_review(self):
        self.assertIn("Evidencia del motor", self.validation)
        self.assertIn("Puntos de revisión humana", self.validation)
        self.assertIn("aprobar", self.validation.lower())
        self.assertNotIn("comparison", self.validation.lower())

    def test_phase3_css_is_scoped_responsive_and_does_not_touch_scheduling(self):
        self.assertIn('.assignment-dashboard-v2[data-analysis-depth="comparative"]', self.styles)
        self.assertIn("assignment-comparison__metrics", self.styles)
        self.assertIn("assignment-comparison__implications-grid", self.styles)
        self.assertIn("@media(max-width:980px)", self.styles)
        self.assertIn("@media(max-width:760px)", self.styles)
        self.assertIn("@media(max-width:520px)", self.styles)
        self.assertIn("prefers-reduced-motion", self.styles)
        scheduling = (JS / "scheduling-dashboard.mjs").read_text()
        self.assertNotIn("assignment-comparative-summary.mjs", scheduling)
        self.assertNotIn("assignment-comparison.mjs", scheduling)


if __name__ == "__main__":
    unittest.main()
