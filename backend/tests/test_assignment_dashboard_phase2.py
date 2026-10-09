from pathlib import Path
import json
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
JS = STATIC / "js" / "dispatch"
CSS = STATIC / "css"
FIXTURE = ROOT / "tests" / "fixtures" / "assignment_dashboard" / "assignment_essential_run.json"


class AssignmentDashboardPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard = (JS / "dashboard.mjs").read_text()
        cls.shell = (JS / "assignment-dashboard-shell.mjs").read_text()
        cls.selectors = (JS / "assignment-dashboard-selectors.mjs").read_text()
        cls.summary = (JS / "assignment-summary.mjs").read_text()
        cls.evidence = (JS / "assignment-evidence.mjs").read_text()
        cls.validation = (JS / "assignment-validation.mjs").read_text()
        cls.styles = (CSS / "assignment-dashboard-essential.css").read_text()
        cls.fixture = json.loads(FIXTURE.read_text())

    def test_essential_selectors_use_persisted_assignment_contract(self):
        script = textwrap.dedent(
            f"""
            import {{
              getAssignmentSummary,
              getObjectiveWeights,
              getOperationalKpis,
              getAssignmentTrips,
              getAssignmentVehicles,
              getAssignmentOrders,
              getApprovalWarnings,
            }} from './app/static/js/dispatch/assignment-dashboard-selectors.mjs';

            const run = {json.dumps(self.fixture)};
            const result = run.result_json;
            const summary = getAssignmentSummary(result);
            if (summary.orders !== 2 || summary.trips !== 2) throw new Error('summary mismatch');
            if (summary.objectiveLabel !== 'Minimizar viajes') throw new Error('objective mismatch');

            const weights = getObjectiveWeights(result);
            if (weights.length !== 1 || weights[0].dimension !== 'trips' || weights[0].weight !== 1) {{
              throw new Error('weights mismatch');
            }}

            const kpis = getOperationalKpis(result);
            const objectiveKeys = kpis.filter(item => item.objective).map(item => item.key);
            if (objectiveKeys.length !== 1 || objectiveKeys[0] !== 'total_trips') {{
              throw new Error('objective KPI mismatch');
            }}
            if (kpis.find(item => item.key === 'load_utilization').objective) {{
              throw new Error('utilization must stay descriptive');
            }}
            if (kpis.find(item => item.key === 'vehicles_used').objective) {{
              throw new Error('vehicles used must stay descriptive');
            }}

            const trips = getAssignmentTrips(result);
            if (trips.length !== 2 || trips[0].order_count !== 2) throw new Error('trip evidence mismatch');

            const vehicles = getAssignmentVehicles(result);
            if (vehicles.length !== 1 || vehicles[0].id !== 'VEH-001' || vehicles[0].trips !== 2) {{
              throw new Error('vehicle aggregation mismatch');
            }}
            if (Math.abs(vehicles[0].load_share - 1) > 1e-9) throw new Error('vehicle share mismatch');

            const orders = getAssignmentOrders(result);
            if (orders.length !== 2 || !orders.find(item => item.order_id === 'ORD-002').split) {{
              throw new Error('order evidence mismatch');
            }}

            const warnings = getApprovalWarnings(result);
            if (warnings.length !== 1 || warnings[0].key !== 'split_orders') {{
              throw new Error('approval warning mismatch');
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

    def test_essential_composition_is_selected_only_by_persisted_depth(self):
        self.assertIn("const depth=getAnalysisDepth(run)", self.dashboard)
        self.assertIn("if(depth==='essential')", self.dashboard)
        self.assertIn("renderModule(nodes.hero,assignmentSummary,result)", self.dashboard)
        self.assertIn("renderModule(nodes.assignment,assignmentEvidence,result)", self.dashboard)
        self.assertIn("renderModule(nodes.review,assignmentValidation,result)", self.dashboard)
        self.assertIn("renderModule(nodes.hero,hero,result)", self.dashboard)
        self.assertIn("Phase 3 will replace this comparative composition", self.dashboard)
        self.assertNotIn("data-depth-toggle", self.dashboard)

    def test_summary_separates_objective_metrics_from_descriptive_kpis(self):
        self.assertIn("Parte del objetivo", self.summary)
        self.assertIn("KPI del resultado", self.summary)
        self.assertIn("Objetivo de la corrida", self.summary)
        self.assertIn("objectiveWeights", self.summary)
        self.assertNotIn("variables activas", self.summary.lower())
        self.assertNotIn("ahorro", self.summary.lower())
        self.assertNotIn("óptim", self.summary.lower())

    def test_evidence_is_trip_centric_without_large_chart(self):
        for label in ("Viajes", "Vehículos", "Órdenes"):
            self.assertIn(label, self.evidence)
        self.assertIn("data-trip-detail-button", self.evidence)
        self.assertIn("Carga total", self.evidence)
        self.assertIn("Capacidad", self.evidence)
        self.assertIn("Utilización", self.evidence)
        self.assertIn("Proveedor:", self.evidence)
        self.assertIn("Órdenes y productos", self.evidence)
        self.assertIn("Frontera de esta decisión", self.evidence)
        self.assertIn("posibles superposiciones", self.evidence)
        self.assertNotIn("chart(", self.evidence)
        self.assertNotIn("ECharts", self.evidence)
        self.assertNotIn("fecha", self.evidence.lower())
        self.assertNotIn("sla", self.evidence.lower())

    def test_single_vehicle_has_compact_summary_instead_of_bar_chart(self):
        self.assertIn("assignment-evidence__single-vehicle", self.evidence)
        self.assertIn("concentra ", self.evidence)
        self.assertIn("utilización media", self.evidence)
        self.assertNotIn("dispatch-assignment-chart", self.evidence)

    def test_orders_are_auditable_from_persisted_order_outcomes(self):
        for field in ("order_id", "product", "trip_ids", "vehicle_ids", "split", "consolidated", "outsourced"):
            self.assertIn(field, self.selectors)
        self.assertIn("Dividida", self.evidence)
        self.assertIn("Consolidada", self.evidence)
        self.assertIn("Tercerizada", self.evidence)

    def test_validation_does_not_fake_engine_checklist(self):
        self.assertIn("Evidencia del motor", self.validation)
        self.assertIn("Puntos de revisión humana", self.validation)
        self.assertIn("no replica las validaciones internas del motor", self.validation)
        self.assertIn("no se simulan validaciones", self.validation)
        for forbidden in (
            "capacity_respected",
            "route_consistency",
            "origin_site_compatibility",
            "ningún viaje supera la capacidad",
            "las rutas son consistentes",
        ):
            self.assertNotIn(forbidden, self.validation.lower())

    def test_approval_is_final_action_and_approved_state_has_no_dead_disabled_cta(self):
        self.assertIn("Reconfigurar decisión", self.shell)
        self.assertIn("Aprobar asignación →", self.shell)
        self.assertIn("Esta decisión quedó congelada como entrada para Planificación.", self.shell)
        self.assertIn("approveButton.hidden=true", self.shell)
        self.assertIn("rerunValidation.hidden=true", self.shell)
        self.assertIn("continuation.hidden=false", self.shell)
        self.assertIn("caseActions.onApprovalComplete?.()", self.shell)
        self.assertIn("data-after-approve", self.shell)

    def test_phase2_css_is_depth_scoped_responsive_and_does_not_touch_scheduling(self):
        self.assertIn('.assignment-dashboard-v2[data-analysis-depth="essential"]', self.styles)
        self.assertIn("assignment-essential__kpi-strip", self.styles)
        self.assertIn("assignment-evidence__tabs", self.styles)
        self.assertIn("assignment-validation__grid", self.styles)
        self.assertIn("@media(max-width:980px)", self.styles)
        self.assertIn("@media(max-width:760px)", self.styles)
        self.assertIn("@media(max-width:520px)", self.styles)
        self.assertIn("prefers-reduced-motion", self.styles)
        self.assertIn("ASSIGNMENT_ESSENTIAL_STYLE_HREF='/static/css/assignment-dashboard-essential.css?v=assignment-dashboard-phase2'", self.dashboard)
        scheduling = (JS / "scheduling-dashboard.mjs").read_text()
        self.assertNotIn("assignment-summary.mjs", scheduling)
        self.assertNotIn("assignment-evidence.mjs", scheduling)
        self.assertNotIn("assignment-validation.mjs", scheduling)


if __name__ == "__main__":
    unittest.main()
