import re
import unittest
from pathlib import Path


BACKEND_ROOT = Path(
    __file__
).resolve().parents[1]

APP_HTML = (
    BACKEND_ROOT
    / "app"
    / "templates"
    / "app.html"
)

APP_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "app.js"
)

UI_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "ui.js"
)

DATA_STAGE_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "data-stage.js"
)

DASHBOARD_STAGE_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "dashboard-stage.js"
)

INTERPRETER_STAGE_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "interpreter-stage.js"
)


class FrontendContractTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.html = APP_HTML.read_text(
            encoding="utf-8"
        )
        cls.app_js = APP_JS.read_text(
            encoding="utf-8"
        )
        cls.ui_js = UI_JS.read_text(
            encoding="utf-8"
        )
        cls.dashboard_stage_js = (
            DASHBOARD_STAGE_JS.read_text(
                encoding="utf-8"
            )
        )
        cls.interpreter_stage_js = (
            INTERPRETER_STAGE_JS.read_text(
                encoding="utf-8"
            )
        )

    def test_javascript_referenced_ids_exist(
        self,
    ):
        # Validate the controllers that own the current DOM.
        # ui.js still contains legacy render helpers used only by
        # traceability/settings; obsolete dashboard helpers there are
        # intentionally excluded from this contract.
        javascript = (
            self.app_js
            + "\n"
            + self.dashboard_stage_js
            + "\n"
            + self.interpreter_stage_js
        )

        referenced_ids = set(
            re.findall(
                r'\$\("#([^"]+)"\)',
                javascript,
            )
        )

        missing = [
            element_id
            for element_id
            in sorted(
                referenced_ids
            )
            if (
                f'id="{element_id}"'
                not in self.html
            )
        ]

        self.assertEqual(
            missing,
            [],
            (
                "Hay IDs usados por "
                "JavaScript que no existen "
                f"en app.html: {missing}"
            ),
        )

    def test_legacy_english_ui_copy_removed(
        self,
    ):
        visible_sources = (
            self.html
            + "\n"
            + self.app_js
            + "\n"
            + self.ui_js
        )

        forbidden = [
            "Overview",
            "Run decision",
            "Waiting for dataset",
            "Minimum total cost",
            "Generate executive insight",
            "Dataset ready",
            "Decision History",
            "Settings",
            "Use dataset",
            "Select CSV file",
            "Current baseline",
        ]

        found = [
            term
            for term in forbidden
            if term in visible_sources
        ]

        self.assertEqual(
            found,
            [],
            (
                "Quedó copy visible legado "
                f"en inglés: {found}"
            ),
        )

    def test_primary_views_exist(
        self,
    ):
        for view in (
            "inicio",
            "logistics-overview",
            "logistics-data",
            "logistics-map",
            "logistics-config",
            "decision-dashboard",
            "traceability",
            "settings",
        ):
            self.assertIn(
                (
                    'data-view-panel="'
                    + view
                    + '"'
                ),
                self.html,
            )

    def test_accessibility_hooks_exist(
        self,
    ):
        self.assertIn(
            'aria-label="Navegación principal"',
            self.html,
        )
        self.assertIn(
            'aria-live="polite"',
            self.html,
        )
        self.assertIn(
            "prefers-reduced-motion",
            (
                BACKEND_ROOT
                / "app"
                / "static"
                / "css"
                / "app.css"
            ).read_text(
                encoding="utf-8"
            ),
        )


    def test_dispatch_configuration_has_single_renderer(
        self,
    ):
        workspace = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "workspace.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'data-view-panel="logistics-config"',
            self.html,
        )
        self.assertNotIn(
            "/static/js/decision-stage.js",
            self.html,
        )
        for legacy_id in (
            "decision-preset-grid",
            "decision-cost-slider",
            "decision-trips-slider",
            "decision-review-run",
            "decision-confirm-modal",
            "decision-confirm-run",
        ):
            self.assertNotIn(
                f'id="{legacy_id}"',
                self.html,
            )

        self.assertIn(
            "async function loadConfig()",
            workspace,
        )
        self.assertIn(
            "Configurar la decisión",
            workspace,
        )
        self.assertIn(
            "max_utilization",
            workspace,
        )
        self.assertIn(
            "min_co2",
            workspace,
        )
        self.assertIn(
            "SLA",
            workspace,
        )
        self.assertIn(
            "Dimensiones del modelo",
            workspace,
        )
        self.assertIn(
            "Profundidad del análisis",
            workspace,
        )
        self.assertIn(
            "analysis_depth",
            workspace,
        )
        self.assertNotIn(
            "Reglas de la distribución",
            workspace,
        )
        self.assertNotIn(
            "state.preflight.warnings",
            workspace,
        )
        self.assertNotIn(
            "Viajes mínimos",
            workspace,
        )


    def test_dispatch_workspace_is_loaded_once(
        self,
    ):
        workspace = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "workspace.mjs"
        ).read_text(encoding="utf-8")

        self.assertNotIn(
            "import('./dispatch/workspace.mjs')",
            self.app_js,
        )
        self.assertNotIn(
            "import('./dispatch/workspace.mjs')",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "/static/js/dispatch/workspace.mjs?v=decision-chain-v1",
            self.html,
        )
        self.assertIn(
            "window.DationDispatch?.show",
            self.app_js,
        )
        self.assertIn(
            "window.DationDispatch.show",
            self.dashboard_stage_js,
        )

        config_render = workspace.split(
            "async function loadConfig()",
            1,
        )[1].split(
            "function pending(",
            1,
        )[0]
        self.assertNotIn(
            "node.innerHTML+=",
            config_render,
        )
        self.assertIn(
            "dispatch-config-screen",
            config_render,
        )

    def test_focused_dispatch_dashboard_contract(
        self,
    ):
        dashboard = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "dashboard.mjs"
        ).read_text(encoding="utf-8")
        hero = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "hero.mjs"
        ).read_text(encoding="utf-8")
        assignment = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "assignment.mjs"
        ).read_text(encoding="utf-8")
        review = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "review.mjs"
        ).read_text(encoding="utf-8")
        explanation = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "explanation.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "Exportar distribución",
            dashboard,
        )
        self.assertIn(
            "assignment.mjs",
            dashboard,
        )
        self.assertIn(
            "review.mjs",
            dashboard,
        )
        self.assertNotIn(
            "kpis.mjs",
            dashboard,
        )
        self.assertNotIn(
            "compare.mjs",
            dashboard,
        )
        self.assertNotIn(
            "sensitivity.mjs",
            dashboard,
        )
        self.assertNotIn(
            "Ahorro estimado",
            hero,
        )
        self.assertNotIn(
            "Despacho directo",
            hero,
        )
        self.assertIn(
            "Cómo quedó distribuida la carga",
            assignment,
        )
        self.assertIn(
            "Qué productos lleva",
            assignment,
        )
        self.assertIn(
            "data-assignment-metric",
            assignment,
        )
        self.assertIn(
            "Revisar antes de ejecutar",
            review,
        )
        self.assertIn(
            "no recalcula el optimizador",
            explanation,
        )


    def test_single_ingestion_contract(
        self,
    ):
        workspace = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "workspace.mjs"
        ).read_text(encoding="utf-8")
        upload_root = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "upload"
        )
        upload_index = (upload_root / "index.mjs").read_text(
            encoding="utf-8"
        )
        dropcard = (upload_root / "dropcard.mjs").read_text(
            encoding="utf-8"
        )
        guide = (upload_root / "guide-drawer.mjs").read_text(
            encoding="utf-8"
        )
        quality = (upload_root / "preflight-panel.mjs").read_text(
            encoding="utf-8"
        )
        readiness = (upload_root / "readiness-panel.mjs").read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            'id="upload-dropzone"',
            self.html,
        )
        self.assertNotIn(
            "/static/js/data-stage.js",
            self.html,
        )
        self.assertIn(
            "mountUploadScreen",
            workspace,
        )
        self.assertIn(
            "renderDecisionMap",
            workspace,
        )
        self.assertIn(
            "navigate('logistics-map')",
            workspace,
        )
        self.assertIn(
            "decision_case",
            workspace,
        )
        self.assertIn(
            "/api/datasets/validate",
            upload_index,
        )
        self.assertIn(
            "Validación de archivos",
            quality,
        )
        self.assertIn(
            "Descargar plantilla",
            dropcard,
        )
        self.assertIn(
            "columnas mínimas",
            dropcard,
        )
        self.assertIn(
            "Qué decisiones habilitan estos datos",
            readiness,
        )
        self.assertIn(
            "Data Pack progresivo",
            readiness,
        )
        self.assertIn(
            "renderDecisionReadiness",
            upload_index,
        )
        self.assertNotIn(
            "fleet_pool_id",
            dropcard + guide + readiness,
        )
        self.assertNotIn(
            "Ver ejemplo",
            dropcard + guide + upload_index,
        )
        self.assertNotIn(
            "flota vigente",
            dropcard.lower() + upload_index.lower(),
        )
        self.assertNotIn(
            "llegarán tarde",
            quality.lower(),
        )
        self.assertNotIn(
            "demanda supera",
            quality.lower(),
        )


    def test_decision_chain_phase2_contract(self):
        workspace = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "workspace.mjs"
        ).read_text(encoding="utf-8")
        decision_map = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "decision-map.mjs"
        ).read_text(encoding="utf-8")
        decision_case = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "decision-case.mjs"
        ).read_text(encoding="utf-8")
        dashboard = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "dashboard.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'data-view-panel="logistics-map"',
            self.html,
        )
        self.assertIn(
            "Mapa de decisiones",
            decision_map,
        )
        self.assertIn(
            "Asignación de carga",
            decision_map,
        )
        self.assertIn(
            "Planificación",
            decision_map,
        )
        self.assertIn(
            "Asignación final",
            decision_map,
        )
        for state in (
            "available",
            "running",
            "review",
            "approved",
            "locked",
            "needs_data",
            "error",
            "stale",
        ):
            self.assertIn(
                '"' + state + '"',
                decision_case,
            )
        self.assertIn(
            "transitionNode",
            workspace,
        )
        self.assertIn(
            "STATUS.RUNNING",
            workspace,
        )
        self.assertIn(
            "STATUS.REVIEW",
            workspace,
        )
        self.assertIn(
            "STATUS.APPROVED",
            workspace,
        )
        self.assertIn(
            "Aprobar decisión",
            dashboard,
        )
        self.assertIn(
            "Mapa de decisiones",
            dashboard,
        )

    def test_dashboard_stage_contract(
        self,
    ):
        required_ids = (
            "dashboard-execution-state",
            "dashboard-progress",
            "dashboard-content",
            "dashboard-objective-chip",
            "dashboard-assignment-chart",
            "dashboard-kpi-grid",
            "dashboard-comparison-select",
            "dashboard-comparison-chart",
            "dashboard-comparison-table-body",
            "dashboard-flow-matrix",
            "dashboard-sensitivity-content",
            "generate-explanation",
            "chat-panel",
            "dashboard-retry-run",
        )

        for element_id in required_ids:
            self.assertIn(
                f'id="{element_id}"',
                self.html,
            )

        self.assertIn(
            "dationDashboardStart",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "dationDashboardCompleted",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "/api/runs/",
            self.dashboard_stage_js,
        )
        workspace = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "workspace.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "?run_id=",
            workspace,
        )
        self.assertIn(
            "pending(",
            workspace,
        )
        self.assertIn(
            "dationDashboardCompleted",
            self.app_js,
        )


    def test_sidebar_keeps_only_home_primary_nav(
        self,
    ):
        sidebar = self.html.split(
            '<aside class="sidebar">',
            1,
        )[1].split(
            "</aside>",
            1,
        )[0]

        primary_nav = sidebar.split(
            '<nav class="nav"',
            1,
        )[1].split(
            "</nav>",
            1,
        )[0]

        self.assertIn(
            ">Inicio<",
            primary_nav,
        )
        self.assertNotIn(
            ">Trazabilidad<",
            primary_nav,
        )
        self.assertNotIn(
            ">Configuración<",
            primary_nav,
        )
        self.assertNotIn(
            ">DDA Logística<",
            primary_nav,
        )
        self.assertIn(
            "Decision Data Assets",
            sidebar,
        )

    def test_latest_decision_access_contract(
        self,
    ):
        self.assertIn(
            'id="open-latest-logistics-decision"',
            self.html,
        )
        self.assertIn(
            "findLatestCompletedRun",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "dationOpenLatestDecision",
            self.dashboard_stage_js,
        )

    def test_interpreter_stage_contract(
        self,
    ):
        self.assertIn(
            "/api/system/llm-status",
            self.interpreter_stage_js,
        )
        self.assertIn(
            "/explain",
            self.interpreter_stage_js,
        )
        self.assertIn(
            "/chat",
            self.interpreter_stage_js,
        )
        self.assertIn(
            "dation:dashboard-completed",
            self.interpreter_stage_js,
        )


    def test_dashboard_export_and_drawer_chat_contract(
        self,
    ):
        self.assertEqual(
            self.html.count(
                'id="export-decision"'
            ),
            1,
        )
        self.assertIn(
            'class="dashboard-primary-actions"',
            self.html,
        )
        self.assertNotIn(
            'class="decision-command-bar"',
            self.html,
        )
        self.assertNotIn(
            'class="decision-anchor-nav"',
            self.html,
        )
        self.assertIn(
            'class="chat-panel dashboard-chat dashboard-chat--drawer is-hidden"',
            self.html,
        )
        self.assertIn(
            'id="dation-chat-fab"',
            self.html,
        )
        self.assertIn(
            "text/plain;charset=utf-8",
            self.dashboard_stage_js,
        )
        self.assertIn(
            ' + ".txt"',
            self.dashboard_stage_js,
        )
        self.assertIn(
            'id="chat-close"',
            self.html,
        )
        self.assertIn(
            "aria-expanded",
            self.interpreter_stage_js,
        )
        self.assertIn(
            'id="execution-details"',
            self.html,
        )
        self.assertIn(
            'id="copy-run-id"',
            self.html,
        )

        actions = self.html.split(
            'class="dashboard-primary-actions"',
            1,
        )[1].split(
            "</div>",
            1,
        )[0]

        self.assertLess(
            actions.index('id="dashboard-reexecute"'),
            actions.index('id="toggle-chat"'),
        )
        self.assertLess(
            actions.index('id="toggle-chat"'),
            actions.index('id="export-decision"'),
        )


    def test_dashboard_separates_objective_from_decision(
        self,
    ):
        self.assertIn(
            'id="dashboard-objective-chip"',
            self.html,
        )
        self.assertIn(
            'id="dashboard-recommendation-title"',
            self.html,
        )
        self.assertIn(
            'id="dashboard-assignment-chart"',
            self.html,
        )
        self.assertIn(
            "heroDecision",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "Asignación actual",
            self.html,
        )
        self.assertNotIn(
            "Situación actual",
            self.html,
        )

    def test_dashboard_has_required_executive_sections(
        self,
    ):
        for section_id in (
            "dashboard-decision",
            "dashboard-kpis",
            "dashboard-comparator",
            "dashboard-drivers",
            "dashboard-sensitivity",
            "dashboard-ai",
        ):
            self.assertIn(
                f'id="{section_id}"',
                self.html,
            )

        self.assertIn(
            "Ver reasignaciones",
            self.html,
        )
        self.assertIn(
            'id="reassignment-search"',
            self.html,
        )
        self.assertIn(
            'id="export-reassignments"',
            self.html,
        )

    def test_reassignment_detail_has_filters_sort_and_export(
        self,
    ):
        for element_id in (
            "reassignment-search",
            "reassignment-origin-filter",
            "reassignment-destination-filter",
            "reassignment-vehicle-filter",
            "reassignment-sort",
            "export-reassignments",
        ):
            self.assertIn(
                f'id="{element_id}"',
                self.html,
            )

        self.assertIn(
            "filteredDetailRows",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "impact_desc",
            self.dashboard_stage_js,
        )

    def test_chat_has_retryable_error_state(
        self,
    ):
        self.assertIn(
            'id="chat-error-state"',
            self.html,
        )
        self.assertIn(
            'id="chat-retry"',
            self.html,
        )
        self.assertIn(
            "lastFailedQuestion",
            self.interpreter_stage_js,
        )
        self.assertIn(
            "TODO(interpreter-streaming)",
            self.interpreter_stage_js,
        )


    def test_dashboard_hides_technical_metadata_from_hero(
        self,
    ):
        dashboard = self.html.split(
            '<!-- DASHBOARD -->',
            1,
        )[1].split(
            '<!-- TRAZABILIDAD -->',
            1,
        )[0]

        self.assertIn(
            "Detalles de la ejecución",
            dashboard,
        )
        self.assertNotIn(
            "run-context-id",
            dashboard,
        )
        self.assertNotIn(
            "ai-dashboard-meta",
            dashboard,
        )


if __name__ == "__main__":
    unittest.main()
