from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
DISPATCH = STATIC / "js" / "dispatch"

LIFECYCLE = (DISPATCH / "scheduling-execution-phase4.mjs").read_text(encoding="utf-8")
CONFIG = (DISPATCH / "scheduling-config-v2.mjs").read_text(encoding="utf-8")
FOCUS = (DISPATCH / "scheduling-focus-rules.mjs").read_text(encoding="utf-8")
BOOTSTRAP = (STATIC / "js" / "dda-variable-config.js").read_text(encoding="utf-8")
SHELL = (STATIC / "js" / "dda-workflow-config.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "scheduling-execution-phase4.css").read_text(encoding="utf-8")


class SchedulingConfigPhase4LifecycleTests(unittest.TestCase):
    def test_shell_bootstraps_shared_configuration_layer_explicitly(self):
        self.assertIn(
            'import("./dda-variable-config.js?v=scheduling-execution-phase4-v1")',
            SHELL,
        )
        self.assertIn(
            'scheduling-config-v2.mjs?v=scheduling-execution-phase4-v1',
            BOOTSTRAP,
        )
        self.assertIn(
            'scheduling-execution-phase4.mjs?v=scheduling-execution-phase4-v1',
            BOOTSTRAP,
        )

    def test_phase4_reuses_phase3_validation_and_execution_contract(self):
        self.assertIn("executionConfiguration", LIFECYCLE)
        self.assertIn("executionOptions", LIFECYCLE)
        self.assertIn("validateConfig", LIFECYCLE)
        self.assertIn("configuration:executionConfiguration(config)", LIFECYCLE)
        self.assertIn("options:executionOptions(config)", LIFECYCLE)
        self.assertIn("source_run_id:sourceId", LIFECYCLE)
        self.assertIn("node_id:NODE_ID", LIFECYCLE)
        self.assertIn('const NODE_ID="logistics_scheduling"', LIFECYCLE)
        self.assertIn('const SCHEMA="scheduling_v1"', LIFECYCLE)

    def test_phase4_owns_final_execute_click_without_changing_rule_editor(self):
        self.assertIn('document.addEventListener("click",interceptExecute,true)', LIFECYCLE)
        self.assertIn('[data-scheduling-execute]', LIFECYCLE)
        self.assertIn("event.stopImmediatePropagation()", LIFECYCLE)
        self.assertIn(".scheduling-config-v2", LIFECYCLE)
        self.assertIn("data-scheduling-rule-add", FOCUS)
        self.assertIn("data-scheduling-rule-edit", FOCUS)
        self.assertIn("bindFocusRuleEvents", CONFIG)

    def test_decision_case_moves_running_review_and_error(self):
        self.assertIn("STATUS.RUNNING", LIFECYCLE)
        self.assertIn("STATUS.REVIEW", LIFECYCLE)
        self.assertIn("STATUS.ERROR", LIFECYCLE)
        self.assertIn("persistNodeStatus", LIFECYCLE)
        self.assertIn("syncDecisionContext", LIFECYCLE)
        self.assertIn("run_id:runId", LIFECYCLE)
        self.assertIn("run_id:run.id", LIFECYCLE)

    def test_lifecycle_supports_polling_and_network_recovery(self):
        self.assertIn("function pollRun", LIFECYCLE)
        self.assertIn("recoverAfterPostError", LIFECYCLE)
        self.assertIn('api("/api/runs/"+runId)', LIFECYCLE)
        self.assertIn("POLL_MS", LIFECYCLE)
        self.assertIn('run?.status==="completed"', LIFECYCLE)
        self.assertIn('run?.status==="error"', LIFECYCLE)
        self.assertIn('run?.status==="running"', LIFECYCLE)
        self.assertIn("El Run ID permite recuperar esta misma corrida", LIFECYCLE)

    def test_error_state_preserves_config_and_offers_retry(self):
        self.assertIn("Reintentar ejecución", LIFECYCLE)
        self.assertIn("Volver a configuración", LIFECYCLE)
        self.assertIn("La configuración de ventana, objetivo y reglas por foco sigue guardada", LIFECYCLE)
        self.assertIn("data-phase4-retry", LIFECYCLE)
        self.assertIn("data-phase4-config", LIFECYCLE)
        self.assertNotIn("sessionStorage.removeItem(CONFIG_KEY)", LIFECYCLE)

    def test_pending_state_does_not_fake_percentage(self):
        self.assertIn('role=\"progressbar\"', LIFECYCLE)
        self.assertIn("La barra es indeterminada", LIFECYCLE)
        self.assertNotIn("aria-valuenow", LIFECYCLE)
        self.assertIn("Validar", LIFECYCLE)
        self.assertIn("Secuenciar", LIFECYCLE)
        self.assertIn("Consolidar", LIFECYCLE)
        self.assertIn("Persistir", LIFECYCLE)

    def test_dashboard_exposes_persisted_configuration_evidence(self):
        self.assertIn("CONFIGURACIÓN EJECUTADA", LIFECYCLE)
        self.assertIn("Qué produjo este calendario", LIFECYCLE)
        self.assertIn("analysis.focus_rules", LIFECYCLE)
        self.assertIn("analysis.focused_trip_count", LIFECYCLE)
        self.assertIn("result.inputs?.assignment?.run_id", LIFECYCLE)
        self.assertIn("Assignment permanece bloqueada", LIFECYCLE)
        self.assertIn("injectExecutionEvidence", LIFECYCLE)
        self.assertIn("enhanceHistoricalDashboard", LIFECYCLE)

    def test_legacy_scheduling_renderer_never_becomes_visible(self):
        self.assertIn("scheduling-phase4-lifecycle", LIFECYCLE)
        self.assertIn(
            ".scheduling-phase4-lifecycle .dispatch-config-screen.dispatch-scheduling-config",
            CSS,
        )
        self.assertIn("visibility:hidden", CSS)

    def test_phase4_is_responsive_and_motion_safe(self):
        self.assertIn("@media(max-width:760px)", CSS)
        self.assertIn("@media(max-width:520px)", CSS)
        self.assertIn("@media(prefers-reduced-motion:reduce)", CSS)
        self.assertIn("animation:none!important", CSS)


if __name__ == "__main__":
    unittest.main()
