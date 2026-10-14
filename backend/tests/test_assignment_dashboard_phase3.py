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
            if (semantic.avg_cost_per_trip !== 'tradeoff') throw new Error('cost direction mismatch');
            if (semantic.own_weight_share !== 'improvement') throw new Error('own-fleet direction mismatch');
            if (semantic.load_utilization !== 'improvement') throw new Error('utilization direction mismatch');

            const missing = structuredClone(result);
            delete missing.scenarios.balanced.metrics.total_cost;
            if (compareScenarioMetric(missing, 'balanced', 'avg_cost_per_trip').semantic !== 'no_comparable') {{
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

    def test_comparative_composition_extends_essential_in_the_same_dashboard(self):
        self.assertIn("renderModule(nodes.hero,assignmentSummary,result)", self.dashboard)
        self.assertIn("renderModule(nodes.assignment,assignmentEvidence,result)", self.dashboard)
        widget=(JS/'comparative-upgrade.mjs').read_text()
        self.assertIn("assignment-comparative-summary.mjs",widget)
        self.assertIn("assignment-comparison.mjs",widget)
        self.assertIn("assignment-dashboard-comparative.css?v=assignment-dashboard-phase3", self.dashboard)

    def test_comparison_is_quantitative_without_narrative_or_reference_trip_reconstruction(self):
        for label in ('Misma distribución','Referencia no factible'):
            self.assertIn(label,self.comparison)
        for label in ('Mejora','Trade-off','Sin cambio','No comparable'):
            self.assertIn(label,self.selectors)
        for forbidden in ('prioritiesMarkup','implicationText','LECTURA DE LA ELECCIÓN','order_outcomes','.trips','dispatch_date','arrival_date'):
            self.assertNotIn(forbidden,self.comparison)
        self.assertIn('data-comparison-select',self.comparison)

    def test_comparative_summary_focuses_on_the_four_indicators(self):
        self.assertIn('Compará la decisión con otros escenarios',self.summary)
        self.assertIn('cuatro indicadores principales',self.summary)
        for forbidden in ('Estado del solver','Objetivo original','solverStatusLabel','escenarios de referencia'):
            self.assertNotIn(forbidden,self.summary)
        widget=(JS/'comparative-upgrade.mjs').read_text()
        self.assertNotIn('data-comparative-trace',widget)
        self.assertNotIn('Trazabilidad del análisis',widget)
        self.assertIn('onEvidenceReady?.(artifact)',widget)

    def test_comparative_keeps_real_validation_as_final_review(self):
        self.assertIn('getApprovalWarnings(result)',self.validation)
        self.assertNotIn('engineEvidence',self.validation)
        self.assertNotIn('capacity_respected',self.validation)
        self.assertNotIn('origin_site_compatibility',self.validation)

    def test_phase3_css_is_scoped_responsive_and_does_not_touch_scheduling(self):
        self.assertIn('.assignment-dashboard-v2 .assignment-comparative-layer',self.styles)
        self.assertIn('assignment-comparison__metrics',self.styles)
        self.assertIn('assignment-comparison__metric-delta',self.styles)
        self.assertIn('@container(max-width:850px)',self.styles)
        self.assertIn('@container(max-width:480px)',self.styles)
        for orphan in ('implications','priorities','outcomes','layer__trace'):
            self.assertNotIn(orphan,self.styles)
        scheduling=(JS/'scheduling-dashboard.mjs').read_text()
        self.assertNotIn('assignment-comparison.mjs',scheduling)
        self.assertNotIn('assignment-comparative-summary.mjs',scheduling)


if __name__ == "__main__":
    unittest.main()
