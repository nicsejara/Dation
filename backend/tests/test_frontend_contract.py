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

DDA_LANDING_JS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "js"
    / "dda-logistics-landing.js"
)

DDA_LANDING_CSS = (
    BACKEND_ROOT
    / "app"
    / "static"
    / "css"
    / "dda-logistics-landing.css"
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
        cls.dda_landing_js = (
            DDA_LANDING_JS.read_text(
                encoding="utf-8"
            )
        )
        cls.dda_landing_css = (
            DDA_LANDING_CSS.read_text(
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
            "Configurar Assignment",
            workspace,
        )
        self.assertIn(
            "min_trips",
            workspace,
        )
        self.assertIn(
            "max_own_fleet",
            workspace,
        )
        self.assertIn(
            "min_co2",
            workspace,
        )
        config_render = workspace.split(
            "async function loadConfig()",
            1,
        )[1].split(
            "function pending(",
            1,
        )[0]
        self.assertNotIn(
            "Tiempo mínimo",
            config_render,
        )
        self.assertNotIn(
            "Horizonte máximo de recuperación SLA",
            config_render,
        )
        self.assertNotIn(
            "ocupación temporal",
            config_render,
        )
        self.assertIn(
            "Variables que intervienen",
            config_render,
        )
        self.assertIn(
            "Las fechas se deciden después",
            config_render,
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
            "/static/js/dispatch/workspace.mjs?v=upload-finalbar-v2",
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
            "Exportar decisión",
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
            "Qué vehículo toma cada carga",
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
            "Revisar antes de aprobar",
            review,
        )
        self.assertIn(
            "La IA no recalcula",
            explanation,
        )


    def test_assignment_phase3_is_non_temporal_in_frontend(self):
        workspace = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "workspace.mjs"
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
        plan = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "plan.mjs"
        ).read_text(encoding="utf-8")
        exporter = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "export.mjs"
        ).read_text(encoding="utf-8")

        config_render = workspace.split(
            "async function loadConfig()",
            1,
        )[1].split(
            "function pending(",
            1,
        )[0]

        for forbidden in (
            "Tiempo mínimo",
            "max_late_days",
            "Horizonte máximo",
            "SLA protegido",
            "ocupación temporal",
        ):
            self.assertNotIn(
                forbidden,
                config_render,
            )

        self.assertIn(
            "Assignment no define fechas",
            assignment,
        )
        self.assertIn(
            "Planificación",
            hero,
        )
        self.assertIn(
            "exportDecision",
            plan,
        )
        self.assertIn(
            "assignment-recomendada.csv",
            exporter,
        )
        self.assertIn(
            "Vehicle ID",
            exporter,
        )
        self.assertIn(
            "assignment_v1",
            workspace,
        )

    def test_scheduling_phase4_frontend_contract(self):
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
        scheduling = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "scheduling-dashboard.mjs"
        ).read_text(encoding="utf-8")
        exporter = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "export.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "Configurar Planificación",
            decision_map,
        )
        self.assertIn(
            "async function loadSchedulingConfig()",
            workspace,
        )
        self.assertIn(
            "source_run_id",
            workspace,
        )
        self.assertIn(
            "use_delivery_due_dates",
            workspace,
        )
        self.assertIn(
            "Assignment queda congelada",
            workspace,
        )
        self.assertIn(
            "logistics_scheduling",
            workspace,
        )
        self.assertIn(
            "scheduling_v1",
            dashboard,
        )
        self.assertIn(
            "scheduling-dashboard.mjs",
            dashboard,
        )
        self.assertIn(
            "Aprobar planificación",
            scheduling,
        )
        self.assertIn(
            "exportDecision",
            scheduling,
        )
        self.assertIn(
            "planificacion-recomendada.csv",
            exporter,
        )
        self.assertIn(
            "resource_available_again",
            scheduling,
        )
        self.assertIn(
            "CALENDARIO OPERATIVO",
            scheduling,
        )
        self.assertIn(
            "STATUS.REVIEW",
            decision_case,
        )
        self.assertIn(
            "STATUS.APPROVED",
            decision_case,
        )
        self.assertIn(
            "scheduling_v1",
            self.app_js,
        )
        self.assertIn(
            "scheduling_v1",
            self.dashboard_stage_js,
        )

    def test_export_and_ai_ux_contract(self):
        dispatch_root = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
        )
        shared = (
            dispatch_root / "shared.mjs"
        ).read_text(encoding="utf-8")
        exporter = (
            dispatch_root / "export.mjs"
        ).read_text(encoding="utf-8")
        dashboard = (
            dispatch_root / "dashboard.mjs"
        ).read_text(encoding="utf-8")
        scheduling = (
            dispatch_root
            / "scheduling-dashboard.mjs"
        ).read_text(encoding="utf-8")
        explanation = (
            dispatch_root / "explanation.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "document.body.append(anchor)",
            shared,
        )
        self.assertIn(
            "anchor.remove()",
            shared,
        )
        self.assertIn(
            "export function exportDecision",
            exporter,
        )
        self.assertIn(
            "assignment-recomendada.csv",
            exporter,
        )
        self.assertIn(
            "planificacion-recomendada.csv",
            exporter,
        )
        self.assertIn(
            "dispatch-action-menu",
            dashboard,
        )
        self.assertIn(
            "data-export-decision",
            dashboard,
        )
        self.assertIn(
            "Exportar decisión",
            dashboard,
        )
        self.assertIn(
            "Carga total viaje (kg)",
            exporter,
        )
        self.assertIn(
            "dispatch-ai-fab",
            dashboard,
        )
        self.assertIn(
            "<strong>Dation IA</strong>",
            dashboard,
        )
        self.assertIn(
            "dispatch-action-menu",
            scheduling,
        )
        self.assertIn(
            "Eventos clave",
            explanation,
        )
        self.assertIn(
            "Por qué ocurrió",
            explanation,
        )
        self.assertIn(
            "Si una causa no está demostrada",
            explanation,
        )
        self.assertIn(
            "data-starter",
            explanation,
        )
        self.assertIn(
            "Enter para enviar",
            explanation,
        )
        self.assertIn(
            "hero-upload-v1",
            self.html,
        )

    def test_brand_assets_contract(self):
        self.assertIn(
            "/static/assets/dation-logo.png",
            self.html,
        )
        self.assertIn(
            "/static/assets/dda-logistics.svg",
            self.html,
        )
        self.assertIn(
            "/static/assets/dda-production.svg",
            self.html,
        )
        self.assertIn(
            "/static/assets/dation-logo.png",
            self.html,
        )
        self.assertNotIn(
            '<div class="brand-mark" aria-hidden="true">\n          <span></span>',
            self.html,
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
        library = (upload_root / "library.mjs").read_text(
            encoding="utf-8"
        )
        selectors = (upload_root / "selectors.mjs").read_text(
            encoding="utf-8"
        )
        upload_css = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "css"
            / "dda-logistics-upload.css"
        ).read_text(encoding="utf-8")

        self.assertNotIn(
            'id="upload-dropzone"',
            self.html,
        )
        self.assertNotIn(
            "/static/js/data-stage.js",
            self.html,
        )
        self.assertIn(
            "/static/css/dda-logistics-upload.css?v=upload-finalbar-v2",
            self.html,
        )
        self.assertIn(
            "/static/js/dispatch/workspace.mjs?v=upload-finalbar-v2",
            self.html,
        )
        self.assertIn(
            "./upload/index.mjs?v=upload-canonical-v1",
            workspace,
        )

        for module_version in (
            "./dropcard.mjs?v=upload-unified-v2",
            "./guide-drawer.mjs?v=upload-unified-v2",
            "./library.mjs?v=canonical-names-v1",
            "./preflight-panel.mjs?v=upload-unified-v2",
            "./selectors.mjs?v=upload-unified-v2",
        ):
            self.assertIn(
                module_version,
                upload_index,
            )

        for copy in (
            "Cargá tus datos y habilitá tu mapa de decisiones.",
            "Elegí cómo cargar tus datos.",
            "Subí archivos nuevos o reutilizá una carga anterior.",
            "las columnas opcionales no bloquean este paso.",
            "Todo listo para continuar.",
            "Seleccioná tu decisión →",
        ):
            self.assertIn(
                copy,
                upload_index,
            )

        for copy in (
            "Cada fila es una orden, con sus productos, cantidades, origen, destino y fechas.",
            "Cada fila es un vehículo, con su capacidad, disponibilidad, costos y velocidad.",
            "1 · CARGAR ARCHIVO",
            "2 · VALIDACIÓN",
            "Empieza apenas cargás el archivo.",
            "Subir nuevo",
            "Reutilizar anterior",
            "Descargar plantilla",
            "Arrastrá tu archivo de órdenes",
            "Arrastrá tu archivo de flota",
            ".CSV",
            "Hasta 10 MB",
            "Reemplazar",
            "Ver columnas",
            "Quitar",
            "Ver historial completo →",
        ):
            self.assertIn(
                copy,
                dropcard,
            )

        self.assertNotIn(
            "Una fila por vehículo.",
            dropcard,
        )
        self.assertNotIn(
            "reviewProblems",
            dropcard,
        )
        self.assertIn(
            "requiredCount",
            dropcard,
        )
        self.assertIn(
            "optionalCount",
            dropcard,
        )
        self.assertIn(
            "setReuseCount",
            dropcard,
        )

        for copy in (
            "Estructura del archivo",
            "Columnas mínimas",
            "Tipos de datos",
            "Columnas opcionales:",
            "Todos los controles correctos",
            "Reemplazar archivo",
            "Descargar plantilla",
            "Entre archivos",
            "Compatibilidad correcta entre Órdenes y Flota.",
        ):
            self.assertIn(
                copy,
                quality,
            )

        self.assertIn(
            "renderInlineValidation",
            quality,
        )
        self.assertIn(
            "renderCompatibilityStrip",
            quality,
        )
        self.assertIn(
            "aria-live",
            dropcard,
        )
        self.assertIn(
            "technicalPreflightErrors",
            quality,
        )
        self.assertNotIn(
            "0 correctos",
            quality,
        )
        self.assertNotIn(
            "dispatch-pro-validation-counters",
            quality,
        )

        for behavior in (
            "clientFileProblem",
            "Este archivo no es un CSV.",
            "El archivo supera los 10 MB.",
            "El archivo no tiene datos.",
            "No pudimos subir el archivo.",
            "AbortController",
            "cancelCurrent",
            "renderInlineValidation",
            "renderCompatibilityStrip",
            "setReuseCount",
        ):
            self.assertIn(
                behavior,
                upload_index,
            )

        self.assertIn(
            'event.key === "Enter"',
            upload_index,
        )
        self.assertIn(
            'event.key === " "',
            upload_index,
        )
        self.assertIn(
            "/api/datasets/validate",
            upload_index,
        )
        self.assertIn(
            "IntersectionObserver",
            upload_index,
        )
        self.assertIn(
            "prefers-reduced-motion",
            upload_index,
        )
        self.assertIn(
            "dispatch-pro-sticky",
            upload_index,
        )

        for final_copy in (
            "Completá tu Data Pack.",
            "Todo listo para continuar.",
            "Seleccioná tu decisión →",
        ):
            self.assertIn(
                final_copy,
                upload_index,
            )

        for removed_final_copy in (
            "Faltan 2 archivos",
            "Revisar mis datos",
            "ESTO VAS A VER",
            "Datos pendientes",
            "Datos listos · con avisos",
            "Datos por corregir",
            "PRÓXIMA ETAPA",
            "Seleccioná tu próxima decisión",
            "Ir al mapa de decisiones →",
        ):
            self.assertNotIn(
                removed_final_copy,
                upload_index,
            )

        self.assertIn(
            ".dispatch-pro-next-button",
            upload_css,
        )
        self.assertNotIn(
            ".dispatch-pro-final-status",
            upload_css,
        )
        self.assertNotIn(
            ".dispatch-pro-next-stage",
            upload_css,
        )

        for history_copy in (
            "Historial completo de Órdenes",
            "Historial completo de Flota",
            "Archivo",
            "Fecha",
            "Datos",
            "Estado",
            "Usar",
        ):
            self.assertIn(
                history_copy,
                library,
            )

        self.assertIn(
            "Encontrada",
            guide,
        )
        self.assertIn(
            "Opcional pendiente",
            guide,
        )
        self.assertIn(
            'label: "Subiendo"',
            selectors,
        )
        self.assertIn(
            'label: "Validando"',
            selectors,
        )
        self.assertIn(
            'label: "Pendiente"',
            selectors,
        )
        self.assertIn(
            'kind: warningCount ? "warning" : "success"',
            selectors,
        )

        for selector in (
            ".dispatch-pro-file-grid",
            ".dispatch-pro-file-card",
            ".dispatch-pro-requirements-row",
            ".dispatch-pro-template-button",
            ".dispatch-pro-source-switch",
            ".dispatch-pro-drop-halo",
            ".dispatch-pro-format-pill",
            ".dispatch-pro-inline-validation",
            ".dispatch-pro-validation-connector",
            ".dispatch-pro-validation-row",
            ".dispatch-pro-validation-success",
            ".dispatch-pro-optional-note",
            ".dispatch-pro-compatibility",
            ".dispatch-pro-history-table",
        ):
            self.assertIn(
                selector,
                upload_css,
            )

        for css_contract in (
            "grid-template-columns:repeat(2,minmax(0,1fr))",
            "gap:24px",
            "min-height:122px",
            "min-height:222px",
            "font-size:13px",
            "border:1.5px dashed",
            "min-height:218px",
            "prefers-reduced-motion:reduce",
        ):
            self.assertIn(
                css_contract,
                upload_css,
            )

        for source_selector_contract in (
            "height:46px",
            "border:1px solid #cfdade",
            "cursor:pointer",
            "transform:translateY(-1px)",
            "button:focus-visible",
        ):
            self.assertIn(
                source_selector_contract,
                upload_css,
            )

        self.assertNotIn(
            "renderValidationPanel",
            upload_index,
        )
        self.assertNotIn(
            "validationRoot",
            upload_index,
        )
        self.assertNotIn(
            ".dispatch-pro-validation-counters",
            upload_css.split("UNIFIED DATA PACK v1", 1)[1],
        )
        self.assertNotIn(
            "makeStepper",
            upload_index,
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
            "dispatch-node-map",
            decision_map,
        )
        self.assertIn(
            "deriveNodePresentationState",
            decision_map,
        )
        self.assertNotIn(
            "renderDecisionReadiness",
            decision_map,
        )
        self.assertNotIn(
            "JERARQUÍA DE DECISIONES",
            decision_map,
        )
        self.assertNotIn(
            "SIGUIENTE PASO",
            decision_map,
        )
        self.assertIn(
            "Bloqueada por jerarquía",
            decision_map,
        )
        self.assertIn(
            "Output aprobado",
            decision_map,
        )
        self.assertIn(
            "Requiere aprobación",
            decision_map,
        )
        self.assertIn(
            'slice(0,10)',
            decision_map,
        )
        self.assertNotIn(
            "assignmentEvidence()?.data_ready",
            workspace.split("function ready()", 1)[1].split("function ensureDecisionCase", 1)[0],
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
            "decisionRail",
            dashboard,
        )
        self.assertIn(
            "dispatch-ai-fab",
            dashboard,
        )

    def test_decision_flow_continues_after_approval(self):
        dispatch_root = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
        )
        workspace = (
            dispatch_root / "workspace.mjs"
        ).read_text(encoding="utf-8")
        decision_map = (
            dispatch_root / "decision-map.mjs"
        ).read_text(encoding="utf-8")
        decision_nav = (
            dispatch_root / "decision-nav.mjs"
        ).read_text(encoding="utf-8")
        dashboard = (
            dispatch_root / "dashboard.mjs"
        ).read_text(encoding="utf-8")
        scheduling = (
            dispatch_root
            / "scheduling-dashboard.mjs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "unlockNextNode(nodeId)",
            workspace,
        )
        self.assertIn(
            "onApprovalComplete",
            workspace,
        )
        self.assertIn(
            "unlockNextNode(nodeId)",
            workspace,
        )
        self.assertIn(
            "dispatch-dashboard-map-back",
            dashboard,
        )
        self.assertIn(
            "SIGUIENTE DECISIÓN",
            decision_map,
        )
        self.assertIn(
            "Configurar Planificación",
            decision_map,
        )
        self.assertIn(
            "open-result",
            decision_map,
        )
        self.assertIn(
            "state.decisionCase?.nodes?.[nodeId]?.run_id",
            workspace,
        )
        self.assertIn(
            "Decisiones del análisis",
            decision_nav,
        )
        self.assertIn(
            "data-decision-node",
            decision_nav,
        )
        self.assertIn(
            "Explorar mapa",
            decision_nav,
        )
        self.assertIn(
            "bindDecisionRail",
            dashboard,
        )
        self.assertIn(
            "bindDecisionRail",
            scheduling,
        )
        self.assertIn(
            "dispatch-ai-fab",
            dashboard,
        )
        self.assertIn(
            "dispatch-ai-fab",
            scheduling,
        )
        self.assertNotIn(
            "dispatch-ai-action",
            dashboard,
        )
        self.assertNotIn(
            "dispatch-ai-action",
            scheduling,
        )
        self.assertIn(
            "dispatch-dashboard-map-back",
            scheduling,
        )
        self.assertIn(
            "dationSetDecisionContext",
            workspace,
        )

    def test_nodal_map_unifies_readiness_and_hierarchy(self):
        decision_map = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "decision-map.mjs"
        ).read_text(encoding="utf-8")
        css = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "css"
            / "dispatch.css"
        ).read_text(encoding="utf-8")

        for marker in (
            "dispatch-decision-node__readiness",
            "dispatch-decision-edge",
            "dispatch-map-datapack",
            "dependencyReady",
            "dataReady",
            "missingData",
        ):
            self.assertIn(marker, decision_map)

        self.assertIn(
            "grid-template-columns:minmax(0,1fr) 92px",
            css,
        )
        self.assertIn(
            "@media(max-width:820px)",
            css,
        )
        self.assertIn(
            "height:46px",
            css,
        )
        self.assertNotIn(
            "data-map-readiness",
            decision_map,
        )
        self.assertNotIn(
            "dispatch-map-chain-head",
            decision_map,
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

    def test_dda_internal_navigation_contract(
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
        upload = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "js"
            / "dispatch"
            / "upload"
            / "index.mjs"
        ).read_text(encoding="utf-8")
        app_css = (
            BACKEND_ROOT
            / "app"
            / "static"
            / "css"
            / "app.css"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'aria-label="Navegación global"',
            self.html,
        )
        self.assertIn(
            'id="dda-workspace-nav-shell"',
            self.html,
        )
        self.assertIn(
            'id="dda-workspace-nav"',
            self.html,
        )
        self.assertIn(
            "window.dationRenderWorkspaceNav",
            self.html,
        )
        self.assertIn(
            "/static/js/dda-workflow-config.js?v=hero-upload-v1",
            self.html,
        )
        self.assertIn(
            "workflowStep('data'",
            self.html,
        )

        for label in (
            "Carga de datos",
            "Mapa de decisiones",
            "Configurar decisión",
            "Dashboard",
        ):
            self.assertIn(
                label,
                self.html,
            )

        self.assertIn(
            "journeyButton('Inicio'",
            self.html,
        )
        self.assertIn(
            "journeySeparator()",
            self.html,
        )
        self.assertIn(
            "journeyButton('DDA Logística'",
            self.html,
        )
        self.assertIn(
            "configContext",
            self.html,
        )
        self.assertIn(
            "dashboardContext",
            self.html,
        )
        self.assertIn(
            "currentView === 'logistics-config'",
            self.html,
        )
        self.assertIn(
            "currentView === 'decision-dashboard'",
            self.html,
        )
        self.assertIn(
            "window.DationDispatch.openActiveDecisionResult",
            self.html,
        )

        for css_class in (
            ".dda-workspace-nav-shell",
            ".dda-workspace-nav",
            ".dda-workspace-step",
            ".dda-workspace-step__context",
        ):
            self.assertIn(
                css_class,
                app_css,
            )

        self.assertIn(
            "const NAV_VERSION='workspace-nav-v1'",
            workspace,
        )
        self.assertIn(
            "saved.navigationVersion===NAV_VERSION",
            workspace,
        )
        self.assertIn(
            "?(saved.activeNode||null)",
            workspace,
        )
        self.assertIn(
            "window.dationSetDecisionContext?.({",
            workspace,
        )
        self.assertIn(
            "openActiveDecisionResult",
            workspace,
        )
        self.assertIn(
            "Primero elegí una decisión.",
            workspace,
        )
        self.assertIn(
            "state.activeNode=null",
            workspace,
        )
        self.assertNotIn(
            "makeStepper",
            upload,
        )
        self.assertIn(
            "/static/css/app.css?v=workspace-nav-v2",
            self.html,
        )
        self.assertIn(
            "/static/js/dispatch/workspace.mjs?v=upload-finalbar-v2",
            self.html,
        )

    def test_latest_decision_access_contract(
        self,
    ):
        self.assertNotIn(
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


    def test_home_dda_selector_copy_contract(self):
        self.assertIn(
            "Elegí el Decision Data Asset que querés utilizar",
            self.html,
        )
        self.assertIn(
            "Decisiones operativas que podés explicar, comparar y repetir.",
            self.html,
        )
        self.assertIn(
            "Decision Data Asset (DDA)",
            self.html,
        )
        self.assertIn(
            "datos → análisis → recomendación → evidencia trazable",
            self.html,
        )
        self.assertIn(
            "/static/css/home-dda.css?v=home-dda-hero-v4",
            self.html,
        )
        self.assertIn(
            "antes de comprometer recursos",
            self.html,
        )
        self.assertIn(
            "listas para compartir y auditar",
            self.html,
        )
        self.assertIn(
            "DDA Producción",
            self.html,
        )
        self.assertIn(
            "Próximamente",
            self.html,
        )


    def test_dda_logistics_landing_contract(self):
        overview = self.html.split(
            "<!-- OVERVIEW DDA LOGÍSTICA -->",
            1,
        )[1].split(
            "<!-- CARGAR DATOS:",
            1,
        )[0]

        for copy in (
            "DDA LOGÍSTICA · PLANIFICACIÓN DE DESPACHOS",
            "Decidí tus despachos más rápido y con mejor análisis.",
            "Dation compara alternativas de asignación, planificación y ejecución",
            "Menos tiempo armando análisis, más tiempo para decidir.",
            "Iniciar nueva decisión",
            "Ver Decision Map",
            "VOS APORTÁS",
            "Tus órdenes y tu flota",
            "DATION ANALIZA",
            "Compara alternativas y optimiza",
            "VOS DECIDÍS",
            "Con recomendación y evidencia",
            "De tus datos a una decisión, en 4 pasos.",
            "Cada decisión se arma en un",
            "Dation valida y arma el caso",
            "Elegí tu prioridad",
            "Aprobá y exportá",
            "Lo hacés vos",
            "Lo hace Dation",
            "Empezás con el núcleo mínimo de datos.",
            "Qué variables optimiza el motor hoy.",
            "Tu mapa de decisiones, desbloqueado paso a paso.",
            "Un DDA no resuelve una sola decisión: resuelve una cadena.",
            "Lo que necesitás y lo que obtenés.",
            "Una vista rápida de los datos mínimos, el resultado que entrega el DDA y los límites que conviene conocer antes de aprobar una decisión.",
            "Lo que necesitás para empezar",
            "Lo que recibís",
            "Lo que conviene saber",
            "¿Listo para tomar tu primera decisión?",
        ):
            self.assertIn(copy, overview)

        for step in (
            "Paso 1",
            "Paso 2",
            "Paso 3",
            "Paso 4",
        ):
            self.assertIn(
                f">{step}<",
                overview,
            )

        for forbidden in (
            "dda-landing__progress",
            "dda-logistics-example-result",
            "Así se ve una decisión con evidencia.",
            "Consolidá las 24 órdenes en 12 viajes.",
            "Ver evidencia completa (JSON)",
            "data-example-csv",
            "Supuestos del plan",
            "dda-landing__io",
            "Evidencia exportable (CSV + JSON)",
            "Dispatch 2.2.0",
            "dda-landing__value-strip",
            "dda-landing__features",
            "dda-landing__result-kpis",
            "dda-landing__heatmap",
            'id="open-latest-logistics-decision"',
            'id="latest-logistics-meta"',
            "Motor 0.2.0",
        ):
            self.assertNotIn(
                forbidden,
                overview,
            )

        self.assertIn(
            'data-scroll-decision-map',
            overview,
        )
        self.assertIn(
            'data-variables-inline',
            overview,
        )
        self.assertIn(
            'id="dda-logistics-decision-map"',
            overview,
        )
        self.assertIn(
            "Data Pack progresivo.",
            overview,
        )
        self.assertIn(
            "dda-landing__summary-grid",
            overview,
        )
        self.assertIn(
            "dda-landing__section-head--summary",
            overview,
        )
        self.assertIn(
            "dda-landing__faq-grid",
            overview,
        )
        self.assertIn(
            ".dda-landing__section--plain{",
            self.dda_landing_css,
        )
        self.assertIn(
            "padding:8px 32px",
            self.dda_landing_css,
        )
        self.assertEqual(
            overview.count("<details>"),
            4,
        )
        self.assertIn(
            "<code class=\"dda-landing__file-chip\">Orders</code>",
            overview,
        )
        self.assertIn(
            "<code class=\"dda-landing__file-chip\">Fleet</code>",
            overview,
        )

        self.assertIn(
            "/static/css/dda-logistics-landing.css?v=dda-logistics-landing-v8",
            self.html,
        )
        self.assertIn(
            "/static/js/dda-logistics-landing.js?v=dda-logistics-landing-v7",
            self.html,
        )
        self.assertIn(
            "/static/js/dashboard-stage.js?v=dda-logistics-landing-v7",
            self.html,
        )

        for variable in (
            'label:"Costo"',
            'label:"Viajes"',
            'label:"Tiempo"',
            'label:"CO₂"',
            'label:"Riesgo"',
            'label:"Servicio"',
        ):
            self.assertIn(
                variable,
                self.dda_landing_js,
            )

        self.assertIn(
            "dda-landing__variable-pill",
            self.dda_landing_js,
        )
        self.assertIn(
            "dationScrollToDecisionMap",
            self.dda_landing_js,
        )
        self.assertIn(
            "[data-scroll-decision-map]",
            self.dda_landing_js,
        )
        self.assertNotIn(
            "syncProgress",
            self.dda_landing_js,
        )
        self.assertNotIn(
            "syncPrimaryCopy",
            self.dda_landing_js,
        )
        self.assertNotIn(
            "scrollToExample",
            self.dda_landing_js,
        )
        self.assertNotIn(
            "downloadExampleCsv",
            self.dda_landing_js,
        )
        self.assertIn(
            "deriveMapStates",
            self.dda_landing_js,
        )
        self.assertIn(
            'logistics_assignment:"pending"',
            self.dda_landing_js,
        )
        self.assertIn(
            'logistics_scheduling:"locked"',
            self.dda_landing_js,
        )
        self.assertIn(
            'logistics_final_assignment:"locked"',
            self.dda_landing_js,
        )


if __name__ == "__main__":
    unittest.main()