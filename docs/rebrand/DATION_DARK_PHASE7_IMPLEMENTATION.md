# Dark Rebrand / Grow-Up — Fase 7: cleanup y cierre

## A. Diagnóstico

El grafo de los dos templates y sus imports estáticos/dinámicos tenía siete módulos de producto sin consumidor: configurador anterior, comparación/KPI/plan/sensibilidad genéricos, sus selectores y readiness retirado de Upload. Los estilos de esos owners y de depth/footers anteriores seguían descargándose. Map añadía su CSS por ID sin esperar su carga; Config usaba otra versión de la misma URL. Los filtros aplicados inyectaban una hoja desde JavaScript. Biblioteca y configuración técnica eran las dos últimas rutas con boundary light.

`decisionDepthCard` y `DEPTH_LABELS` ya estaban retirados en Fase 4. `analysisDepthUi` mantiene un consumidor real en el shell actual y lectura de históricos essential/comparative/deep. Los bridges de dashboard/interpreter y la ocultación de markup anterior también conservan consumidores.

## B. Intención

Cerrar la saga sin duplicar renderers ni cambiar las decisiones. El código descargado debe corresponder a rutas activas; los estilos tienen un propietario y las respuestas tardías respetan el ciclo de vida de la SPA. Se conservan navegación/aliases, datos, drafts, callbacks, comparativa, históricos, exportaciones y aprobación. No se modifica API, motor, permisos, Supabase, dependencias ni el contrato essential vigente desde Fase 4.

## C. Implementación

- Retirados `decision-stage.js`, `dispatch/{compare,kpis,plan,selectors,sensitivity}.mjs` y `upload/readiness-panel.mjs`, después de auditar templates, imports y referencias en JS/MJS/Python. Sus fuentes suman más de 40 KB; no se atribuye esa cifra a ahorro de red porque ya no se cargaban.
- Eliminadas 159 ramas de selectores sin markup consumidor: configurador anterior, depth, readiness y footers sustituidos. El barrido recursivo conserva ramas compartidas dentro de media queries y no elimina reglas sólo por contener blanco. Los estilos retirados del CSS global sí dejan de descargarse.
- Retirados los dos atributos `legacy-light` y su hoja puente. Biblioteca, tabs, tablas, evidencia JSON y settings usan roles semánticos en `app.css`. Su estructura, contenido y navegación permanecen.
- `ensureDecisionCaseStyles()` fija ID/path/version compartidos por Map y ambas Config sobre el loader común. Map espera load, permite retry y comprueba scope/generación antes de renderizar o decorar. Se cubre navegación fuera de la vista mientras el CSS sigue pendiente.
- Los 3798 bytes de estilos de filtros aplicados pasan a `assignment-config-v2.css`; el módulo conserva comportamiento, estado, teclado y atributos. No crea otro nodo style. Se retira el argumento sin consumidor `scheduling-summary-bar`.
- El DS pasa de propuesta de Fase 0 a documentación del sistema vigente: tokens/buttons/heroes/footer/toolbar/surfaces/spacing/responsive, owners, compatibilidad y límites. El inventario original queda identificado como baseline histórico.

El test unitario exclusivo del selector genérico retirado se elimina junto a su módulo. Permanecen las pruebas de selectores actuales y métricas/comparación, pesos, filtros, exportaciones y esquemas históricos. No se cambia una expectativa funcional para ocultar un fallo: las comprobaciones de source que apuntaban al plan retirado pasan al exportador activo; las de estilos de filtros apuntan a su CSS y la de «TU DECISION CASE» al texto publicado «DECISION CASE».

## D. Archivos

- `backend/app/static/css/app.css`
- `backend/app/static/css/assignment-config-v2.css`
- `backend/app/static/css/dation-design-system.css`
- `backend/app/static/css/dation-legacy-surfaces.css`
- `backend/app/static/css/dispatch.css`
- `backend/app/static/css/scheduling-config-v2.css`
- `backend/app/static/js/decision-stage.js`
- `backend/app/static/js/dispatch/assignment-config.mjs`
- `backend/app/static/js/dispatch/assignment-filter-collapse.mjs`
- `backend/app/static/js/dispatch/compare.mjs`
- `backend/app/static/js/dispatch/decision-map.mjs`
- `backend/app/static/js/dispatch/kpis.mjs`
- `backend/app/static/js/dispatch/plan.mjs`
- `backend/app/static/js/dispatch/scheduling-config-v2.mjs`
- `backend/app/static/js/dispatch/selectors.mjs`
- `backend/app/static/js/dispatch/sensitivity.mjs`
- `backend/app/static/js/dispatch/styles.mjs`
- `backend/app/static/js/dispatch/upload/readiness-panel.mjs`
- `backend/app/static/js/dispatch/workspace.mjs`
- `backend/app/templates/app.html`
- `backend/tests/browser/test_navigation.py`
- `backend/tests/test_assignment_filter_collapse.py`
- `backend/tests/test_dispatch_selectors.mjs`
- `backend/tests/test_frontend_contract.py`
- `backend/tests/test_frontend_import_graph.py`
- `backend/tests/test_scheduling_config_phase2_acceptance.py`
- `docs/rebrand/DATION_COMPONENT_INVENTORY_V1.md`
- `docs/rebrand/DATION_DARK_PHASE7_IMPLEMENTATION.md`
- `docs/rebrand/DATION_DESIGN_SYSTEM_V1.md`
- `docs/rebrand/DATION_USER_ACCEPTANCE_CHECKLIST.md`

## E. Tests y gate

Desde `backend`, tras activar `/workspace/.dation-cloud/activate.sh`:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_*.js tests/test_*.mjs
CHROMIUM_EXECUTABLE=/usr/bin/chromium DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python .browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_navigation.py'
```

Matriz prevista: **350 Python + 39 Node + 102 Chromium + 46 SQL + 7 E2E = 544 casos**. El resultado efectivo, incluyendo local/CI, commit y enlaces, se registra en el PR. La comprobación nueva de grafo verifica entrypoints, imports estáticos/lazy, archivos presentes y ausencia de módulos huérfanos. Las tres nuevas regresiones Chromium comprueban biblioteca/settings dark a cinco anchos, retry/deduplicación Map→Config y estilos de filtros, y CSS de Map tardío tras abandonar la ruta.

También compilación, sintaxis frontend, pip check, diff y auditorías de dependencias de CI. Se exige verde en head exacto y merge de main. SQL sobre PostgreSQL 17 y E2E con API/worker/base/storage reales desechables se acreditan por CI del mismo head; no se repiten localmente por rutina después de pasar ese gate. No se usan escrituras productivas para probar ejecución/aprobaciones.

## F. Visual QA y publicación

Se conserva la matriz de 165 estados de Fase 6 y se añaden 25 estados de biblioteca/settings (datasets, historial, evidencia vacía/poblada, estado técnico), a 1440/1280/1024/768/390 px. Reflujo/autofill/diálogos mantienen sus 20 estados. AA compuesto, overflow, contraste nativo, foco y capas se verifican con datos sintéticos; capturas en `/workspace/dation-audit/rebrand-phase7-visual/` y `rebrand-phase7-support/`.

Reflujo equivalente a 200/400% mediante CDP sobre CSS720×500/DPR2 y CSS360×250/DPR4. La evidencia corresponde a Chromium/Linux; no certifica UI externa de zoom, pickers de todos los sistemas, lectores de pantalla u otros motores. No se presenta como certificación WCAG completa.

Publicación por Cloud Build enlazado a GitHub: comprobar source/pasos, revisiones API/worker, tráfico, template y todos los assets por SHA-256, cache/ETag, acceso privado, readiness y heartbeat. QA productiva: recorrido de SPA y rutas de soporte, con GET y preflight/preview computacional; bloquear toda escritura persistente y comparar hashes de casos, corridas y comparativa revisados. URLs de archivos retirados deben responder 404; las rutas históricas activas deben seguir funcionando. Evidencia concreta y recuentos finales en el PR y `/workspace/dation-audit/rebrand-phase7-production-final.json`.

## G. Deuda y riesgos concretos

La migración del configurador a essential en Fase 4 puede alterar el plan; ver [mediciones y límites](DATION_DARK_PHASE4_IMPLEMENTATION.md). Esta limpieza no cambia motor ni vuelve equivalentes esos contratos. `analysisDepthUi`, aliases de tokens, markup oculto y bridges con consumidores permanecen. No se hace una segunda limpieza masiva para reducir líneas a costa de los históricos.

Rollback: revertir el merge y desplegar ese commit mediante Cloud Build. No hay migraciones ni datos que revertir. El borrador del entorno se fija al commit publicado y preserva instalación, red y bindings; guardarlo no publica el entorno de desarrollo.

## H. Cierre de saga

**FASE 7 COMPLETA — SAGA 0–7 FINALIZADA** sólo después de suites verdes, integración y verificación productiva del commit exacto registradas en el PR. El siguiente paso es la prueba end to end del usuario y un nuevo plan de ajustes; no existe una Fase 8 de esta saga. El checklist completo del resultado está en [Design System vigente](DATION_DESIGN_SYSTEM_V1.md#estado-final-y-gate-de-la-saga).

Guía para ese recorrido: [validación end to end](DATION_USER_ACCEPTANCE_CHECKLIST.md).
