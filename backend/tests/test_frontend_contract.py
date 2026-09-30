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

DECISION_STAGE_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "decision-stage.js"
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
        cls.data_stage_js = (
            DATA_STAGE_JS.read_text(
                encoding="utf-8"
            )
        )
        cls.decision_stage_js = (
            DECISION_STAGE_JS.read_text(
                encoding="utf-8"
            )
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
        javascript = (
            self.app_js
            + "\n"
            + self.ui_js
            + "\n"
            + self.data_stage_js
            + "\n"
            + self.decision_stage_js
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


    def test_decision_stage_contract(
        self,
    ):
        required_ids = (
            "decision-preset-grid",
            "decision-cost-slider",
            "decision-trips-slider",
            "decision-review-run",
            "decision-confirm-modal",
            "decision-confirm-run",
        )

        for element_id in required_ids:
            self.assertIn(
                f'id="{element_id}"',
                self.html,
            )

        self.assertIn(
            "dation:dataset-ready",
            self.decision_stage_js,
        )
        self.assertIn(
            "/api/runs/",
            self.decision_stage_js,
        )
        self.assertIn(
            "dationConsumeDecisionRun",
            self.app_js,
        )

    def test_data_stage_contract(
        self,
    ):
        self.assertIn(
            'id="upload-dropzone"',
            self.html,
        )
        self.assertIn(
            'id="dataset-file"',
            self.html,
        )
        self.assertIn(
            "Dation_Logistics_Template.csv",
            self.html,
        )
        self.assertIn(
            "/api/datasets/upload",
            self.data_stage_js,
        )
        self.assertIn(
            "dation:dataset-ready",
            self.data_stage_js,
        )


    def test_dashboard_stage_contract(
        self,
    ):
        required_ids = (
            "dashboard-execution-state",
            "dashboard-progress",
            "dashboard-content",
            "dashboard-impact-chart",
            "dashboard-comparison-select",
            "dashboard-comparison-chart",
            "dashboard-comparison-table-body",
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
        self.assertIn(
            "?run_id=",
            self.decision_stage_js,
        )
        self.assertIn(
            "dationDashboardStart",
            self.decision_stage_js,
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


    def test_dashboard_export_and_floating_chat_contract(
        self,
    ):
        self.assertEqual(
            self.html.count(
                'id="export-decision"'
            ),
            1,
        )
        self.assertNotIn(
            'id="download-json"',
            self.html,
        )
        self.assertNotIn(
            'id="back-to-config"',
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
        self.assertNotIn(
            "buildDecisionMarkdown(",
            self.app_js,
        )
        self.assertIn(
            'class="dation-floating-actions"',
            self.html,
        )
        self.assertIn(
            "dashboard-chat--floating",
            self.html,
        )
        self.assertNotIn(
            "chat-launch-panel",
            self.html,
        )
        self.assertIn(
            'id="chat-close"',
            self.html,
        )
        self.assertIn(
            "aria-expanded",
            self.interpreter_stage_js,
        )

    def test_dashboard_separates_objective_from_decision(
        self,
    ):
        self.assertIn(
            'id="dashboard-objective-label"',
            self.html,
        )
        self.assertIn(
            'id="dashboard-objective-detail"',
            self.html,
        )
        self.assertIn(
            'id="dashboard-assignment-distribution"',
            self.html,
        )
        self.assertIn(
            "objectiveLabel",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "decisionTitle",
            self.dashboard_stage_js,
        )
        self.assertIn(
            "Asignación de referencia",
            self.html,
        )
        self.assertNotIn(
            "Situación actual",
            self.html,
        )


if __name__ == "__main__":
    unittest.main()
