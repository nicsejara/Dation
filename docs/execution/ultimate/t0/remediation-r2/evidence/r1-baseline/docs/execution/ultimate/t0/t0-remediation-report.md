# T0-R — Baseline Remediation

Estado: **STOP**. Baseline `main` / `ef997235a30251fbf7ae53690ed738092ee973d8`. Captura final: 2026-10-25T23:30:56.282452-03:00 (America/Buenos_Aires; evidencia UTC `2026-10-26T02:30:56.282452+00:00`).

El baseline mejoró mediante correcciones acotadas, pero no queda estabilizado. Se confirmó un defecto en la proyección SQL de atención del Home y queda un cluster nuevo de foco sin causa suficientemente aislada. No se ejecutó T1. No hubo commit, push, despliegue ni cambios remotos.

## Alcance y fuente de verdad

Se partió de las145 entradas de fallo de T0, agrupadas en18 clusters antes de modificar source; E=0 en ese punto. Se inspeccionaron tests/fixtures fallidos y sus callers/contratos actuales. Las prioridades fueron el Master Plan, `docs/domain-model.md`, aceptación vigente y comportamiento intencional trazable. No se hizo una nueva auditoría general.

Los dos planes siguen byte a byte: Master SHA256 `c7543ffa1ef26c79d9142797863fc8ba83613f6cb426cf1621eb0c11b5a27823`; plan anterior `ff824a2fae9566cfb4e1f77ae81e8806d0b76d179b208660b29e9bd00e9ab6d6`. Se conservaron todos los IDs de tests modificados por comparación AST contra HEAD. No se añadieron skips ni timeouts globales. Los28 archivos de source/tests quedaron congelados a 2026-10-25T22:42:48.873343+00:00 y sus hashes se verificaron al cerrar las suites.

## Root Cause Summary

Los IDs exactos, assertions, esperado/observado, contratos, evidencia y resolución se preservan en [clasificación](remediation/root-cause-classification.json) y [resultados por cluster](remediation/root-cause-results.json). Los conteos por cluster pueden solaparse; no son bugs independientes por assertion.

| Cluster ID | Categoría | Tests afectados | Causa | Cambio realizado | Archivos afectados | Tests focales | Resultado |
|---|---|---|---|---|---|---|---|
| C-NETWORK | C | 8 IDs / 8 entradas | Aislar redes Docker y Chromium; ERR_NETWORK_CHANGED abortaba imports locales. | flock exclusivo para todas las suites; sin reintentos/reloads que oculten fallos. | Harness de evidencia | [C-network-ready-focal.log](remediation/evidence/C-network-ready-focal.log) | PENDIENTE: 0 IDs con fallo final reportado; 7 sin identificación en log |
| C-READY | C | 1 IDs / 1 entradas | Un CTA del template no demuestra que el API SPA haya terminado boot. | wait_for_app espera DationDispatch y fin del estado de sesión. | test_navigation.py | [C-network-ready-focal.log](remediation/evidence/C-network-ready-focal.log) | PENDIENTE: 0 IDs con fallo final reportado; 1 sin identificación en log |
| B-VALIDATION | B | 1 IDs / 1 entradas | CSS heredado insertaba ✓ Validado aun con errores. | Especificidad mínima del selector actual; validación sigue el perfil real. | workflow-context.css | [B-css-final-focal.log](remediation/evidence/B-css-final-focal.log) | PENDIENTE: 0 IDs con fallo final reportado; 1 sin identificación en log |
| B-CONTRAST | B | 1 IDs / 1 entradas | Texto pequeño alcanzaba 4.40233 en hover, por debajo de 4.5. | Token text-secondary existente; umbral AA intacto. | dispatch.css | [B-css-final-focal.log](remediation/evidence/B-css-final-focal.log) | PENDIENTE: 0 IDs con fallo final reportado; 1 sin identificación en log |
| A-ROLES | A | 20 IDs / 21 entradas | Fixtures escribían Steward/Approver retirados y esperaban controles separados. | Roles canónicos y Owner único; CAS, negativos, atribución e idempotencia preservados. Queda blocker SQL B-HOME-ATTENTION. | Fixtures Browser/Team y tests E2E de roles | [A-roles-gates.log](remediation/evidence/A-roles-gates.log)<br>[A-roles-foundation-accepted.log](remediation/evidence/A-roles-foundation-accepted.log)<br>[A-roles-single-owner-alias.log](remediation/evidence/A-roles-single-owner-alias.log)<br>[A-D-workflow-context-related.log](remediation/evidence/A-D-workflow-context-related.log)<br>[A-roles-workflow-related.log](remediation/evidence/A-roles-workflow-related.log) | PENDIENTE: 1 IDs con fallo final reportado; 7 sin identificación en log |
| A-PREPARATION | A | 13 IDs / 18 entradas | Casos positivos sin atributos aplicados/Owner; Save independiente obsoleto. | Precondiciones explícitas y Apply conjunto; nuevos Cases siguen pendientes hasta cumplir cuatro checks. | test_navigation.py; test_workflow_context.py; workflow_fixture.py | [A-preparation-and-B-cascade-related.log](remediation/evidence/A-preparation-and-B-cascade-related.log)<br>[A-D-workflow-context-related.log](remediation/evidence/A-D-workflow-context-related.log) | PENDIENTE: 1 IDs con fallo final reportado; 9 sin identificación en log |
| A-CONTEXT | A | 14 IDs / 16 entradas | Hooks antiguos del Map/picker frente al contexto nativo compartido. | Selectors actuales; API legacy del selector probada directamente; progreso compacto de dos decisiones implementadas. Queda foco sin resolver. | test_navigation.py; test_saga4_ui.py; journeys | [A-home-context-hero-related.log](remediation/evidence/A-home-context-hero-related.log)<br>[A-D-workflow-context-related.log](remediation/evidence/A-D-workflow-context-related.log) | PENDIENTE: 0 IDs con fallo final reportado; 14 sin identificación en log |
| A-HOME | A | 14 IDs / 14 entradas | Catalog independiente/widgets Home/CTA Map reemplazados por Home→Center. | Rutas actuales y Center filtrado, manteniendo historial, revocación, recuperación, export y estado. | test_navigation.py; activity/onboarding/platform/entitlements journeys | [A-entry-lineage-focal.log](remediation/evidence/A-entry-lineage-focal.log)<br>[A-home-context-hero-related.log](remediation/evidence/A-home-context-hero-related.log) | PENDIENTE: 2 IDs con fallo final reportado; 8 sin identificación en log |
| A-ACTIONS | A | 9 IDs / 9 entradas | CTA final duplicado, More/errores/continuación de UI anterior. | Toolbar único; mismo Config contextual; coalescing, retry, fuente y evidencia se mantienen. | test_navigation.py; scheduling_dashboard_journey.py | [A-actions-rerun-related.log](remediation/evidence/A-actions-rerun-related.log) | PENDIENTE: 0 IDs con fallo final reportado; 9 sin identificación en log |
| A-INSIGHT | A | 8 IDs / 8 entradas | Controles inline/labels anteriores a las capacidades actuales. | Abrir capacidades actuales sin alterar caché, conteos, abort ni persistencia de DOM. | test_navigation.py | [A-insight-final-focal.log](remediation/evidence/A-insight-final-focal.log) | PENDIENTE: 0 IDs con fallo final reportado; 8 sin identificación en log |
| A-HERO | A | 5 IDs / 5 entradas | Paneles siempre expandidos, alturas fijas, metadata padded y asset retirado. | Disclosure nativo opcional, Data copy-only, media actual y texto no padded. Quedan expectativas visuales pendientes. | test_navigation.py; workflow_ui_audit.py | [A-home-context-hero-related.log](remediation/evidence/A-home-context-hero-related.log) | PENDIENTE: 0 IDs con fallo final reportado; 5 sin identificación en log |
| A-VISUAL | A | 8 IDs / 19 entradas | Tokens, gradients y geometría heredados. | Tokens actuales y roles semánticos; comparación D1/D2 respeta crecimiento natural y redondeo de tracks. | test_navigation.py; workflow_ui_audit.py | [A-preparation-and-B-cascade-related.log](remediation/evidence/A-preparation-and-B-cascade-related.log)<br>[B-kpi-and-hero-parity-accepted.log](remediation/evidence/B-kpi-and-hero-parity-accepted.log) | PENDIENTE: 0 IDs con fallo final reportado; 7 sin identificación en log |
| A-TERMINOLOGY | A | 1 IDs / 12 entradas | Review usaba Responsable anterior. | Decision Owner actual; etiquetas/valores/persistencia conservados. | test_navigation.py; workflow_ui_audit.py | [A-preparation-and-B-cascade-related.log](remediation/evidence/A-preparation-and-B-cascade-related.log) | PENDIENTE: 0 IDs con fallo final reportado; 1 sin identificación en log |
| A-RERUN | A | 4 IDs / 4 entradas | Rerun aprobado omitía confirmación explícita vigente. | Confirmar advertencia real, conservar upstream/Case/IDs y negativos de cancelación. | test_navigation.py; test_saga4_ui.py; golden_journey.py | [A-actions-rerun-related.log](remediation/evidence/A-actions-rerun-related.log)<br>[A-rerun-golden-real-stack.log](remediation/evidence/A-rerun-golden-real-stack.log) | PENDIENTE: 0 IDs con fallo final reportado; 3 sin identificación en log |
| A-MIGRATION | A | 3 IDs / 3 entradas | Tests esperaban bridges/gates anteriores a migraciones ya vigentes. | Assertions sobre datos históricos preservados + Owner canónico y gates actuales; ninguna migración nueva. | test_optimized_responsibilities.py; test_v2_foundation.py; test_workflow_gates.py | [A-migration-current-gates.log](remediation/evidence/A-migration-current-gates.log) | PASS en IDs afectados |
| A-LINEAGE | A | 2 IDs / 2 entradas | Tests preservaban aprobación vigente después de admitir un nuevo Run. | Historial aprobado permanece; current approval se supersede; cinco eventos exactos. Mock de admisión refleja invalidación downstream. Queda journey histórico pendiente. | test_navigation.py; test_workflow.py; test_tenancy.py; test_decision_center.py; home_resume_journey.py | [A-entry-lineage-focal.log](remediation/evidence/A-entry-lineage-focal.log)<br>[A-roles-workflow-related.log](remediation/evidence/A-roles-workflow-related.log) | PENDIENTE: 1 IDs con fallo final reportado |
| D-ATTRIBUTES | D | 2 IDs / 2 entradas | Dos IDs coinciden exactamente con deuda histórica de atributos. | Fixtures con Apply real y owners explícitos; lectura de Config preservada. | test_workflow_context.py | [A-D-workflow-context-related.log](remediation/evidence/A-D-workflow-context-related.log) | PENDIENTE: 0 IDs con fallo final reportado; 2 sin identificación en log |
| D-NAV-GEOMETRY | D | 1 IDs / 1 entradas | Un ID histórico pedía tres anchos idénticos tras aprobar narrativa natural. | Proporciones actuales .85/.85/1.3; foco, contexto, altura y trazabilidad conservados. | test_workflow_context.py | [A-D-workflow-context-related.log](remediation/evidence/A-D-workflow-context-related.log) | PENDIENTE: 0 IDs con fallo final reportado; 1 sin identificación en log |
| B-FOCUS-MARGIN | B | Hallazgo al desbloquear el escenario | Margin/padding de capability en viewport corto. | Scroll-margin scoped 8px y padding/gap compacto a altura≤360; sin cambios globales. | dispatch.css | [B-css-final-focal.log](remediation/evidence/B-css-final-focal.log) | Corregido; resto de foco separado en E-FOCUS-REMAINDER |
| B-KPI-CASCADE | B | Hallazgo al desbloquear el escenario | Regla D2 anterior a 1100px sobrevivía a la cascada actual. | Restablecer cuatro columnas en base; media 900/600 sigue vigente. Comparación antes/después de métricas y seis snapshots. | scheduling-dashboard-v21.css | [B-kpi-and-hero-parity-accepted.log](remediation/evidence/B-kpi-and-hero-parity-accepted.log) | PASS focal |
| B-CSV-CONTRAST | B | Hallazgo al desbloquear el escenario | Label CSV del drawer con contraste 4.40233 al hover. | Token text-secondary existente, sin rebajar 4.5. | dda-logistics-upload.css | [A-preparation-and-B-cascade-related.log](remediation/evidence/A-preparation-and-B-cascade-related.log) | PASS focal |
| B-HOME-ATTENTION | B | Hallazgo al desbloquear el escenario | SQL Home filtra por columna de Approver retirada; Owner actual se guarda en otra columna. | Ningún cambio; requiere migración versionada prohibida por el usuario. | platform_home / home.py inspeccionados, intactos | [B-home-attention-proof.log](remediation/evidence/B-home-attention-proof.log) | STOP; autorización real de aprobar conserva403 |
| E-FOCUS-REMAINDER | E | Hallazgo al desbloquear el escenario | Foco occluded/outside al recorrer Config en viewport corto; causa residual no aislada. | Ninguno tras observar el pendiente; freeze de implementación. | test_navigation.py / callers UI de foco | [A-home-context-hero-related.log](remediation/evidence/A-home-context-hero-related.log) | E; STOP antes de reparación especulativa |
| C-FIXTURE-SNAPSHOT | C | Hallazgo al desbloquear el escenario | Fixture cambia el Case ID sin actualizar el mapa de responsabilidades. | Ninguno tras STOP; dejó una request/teardown en espera y obligó a interrumpir Browser. | test_navigation.py fixtures | [B-BROWSER.log](remediation/evidence/B-BROWSER.log) | PENDIENTE; error introducido en fixtures, sin atribuir al motor |

## Blocker que exige STOP

`public.platform_home(uuid,uuid)` todavía usa `a.approver_user_id` en el filtro de review de `20261019130000_platform_onboarding_demo.sql`. El contrato Owner vigente de `20261022030000_case_ownership_readiness.sql` inserta `owner_user_id`; la columna retirada queda NULL. La conversión de approvals/Center no convirtió este filtro de Home.

La [reproducción aislada](remediation/evidence/B-home-attention-proof.log) usa únicamente el stack descartable: Owner=USER_B, operador=USER3, approver raw=NULL, `attention.total=1`, `scope=assigned_work`. A la vez `collaboration.can_approve=false`, POST approve=403 y `approved_at=NULL`. Esto demuestra un ítem de atención asignado incorrectamente; **no demuestra un bypass de aprobación ni de tenancy**.

La corrección de esa función persistida debe versionarse como migración. La instrucción del usuario es explícita: **«NO hacer migraciones.»** No se modificó una migración histórica, no se parchó la DB local para fabricar PASS y no se agregó un filtro Python parcial que alterase totales/paginación. Hace falta un alcance SQL autorizado por separado.

Después de desbloquear las expectativas UI antiguas, el recorrido de teclado también observa foco occluded/outside en viewport corto. Queda `E-FOCUS-REMAINDER`: no se atribuye a deuda histórica sin prueba ni se relajan los checks. No hubo más cambios de implementación tras detener el trabajo.

## Files Modified

### Product code

- `backend/app/static/css/dda-logistics-upload.css`
- `backend/app/static/css/dispatch.css`
- `backend/app/static/css/scheduling-dashboard-v21.css`
- `backend/app/static/css/workflow-context.css`

Son correcciones CSS puntuales: estado de validación veraz, contraste AA, margen/espaciado de foco en capacidades de pantalla corta y cascada de columnas KPI D2. No hay cambios en JS de aplicación, Python productivo, engines, API, persistencia, SQL, assets, configuración o infraestructura.

### Fixtures

- `backend/tests/e2e/browser_auth.py`
- `backend/tests/e2e/workflow_fixture.py`

Además, las fixtures sintéticas integradas en `test_navigation.py` y `test_workflow_context.py` representan ahora atributos/Owner/versiones y admisión actuales; los casos negativos conservan sus precondiciones faltantes.

### Tests y journeys

- `backend/tests/browser/test_navigation.py`
- `backend/tests/browser/test_saga4_ui.py`
- `backend/tests/browser/test_workflow_context.py`
- `backend/tests/e2e/activity_journey.py`
- `backend/tests/e2e/browser_journey.py`
- `backend/tests/e2e/collaboration_approval_journey.py`
- `backend/tests/e2e/collaboration_journey.py`
- `backend/tests/e2e/entitlements_journey.py`
- `backend/tests/e2e/golden_journey.py`
- `backend/tests/e2e/home_resume_journey.py`
- `backend/tests/e2e/onboarding_journey.py`
- `backend/tests/e2e/platform_journey.py`
- `backend/tests/e2e/scheduling_dashboard_journey.py`
- `backend/tests/e2e/test_collaboration.py`
- `backend/tests/e2e/test_decision_center.py`
- `backend/tests/e2e/test_optimized_responsibilities.py`
- `backend/tests/e2e/test_tenancy.py`
- `backend/tests/e2e/test_v2_foundation.py`
- `backend/tests/e2e/test_workflow.py`
- `backend/tests/e2e/test_workflow_gates.py`
- `backend/tests/e2e/workspace_settings_journey.py`

### Harness

- `backend/tests/e2e/workflow_ui_audit.py`

Runner de evidencia: [dation-t0r-run-suite.py](remediation/evidence/dation-t0r-run-suite.py), batch serial y reproducción local archivados. `flock /tmp/dation-t0r-suite.lock` serializa Chromium y la creación/eliminación de bridges Docker. En T0, Browser/E2E/SQL se solapaban y Chromium registró `ERR_NETWORK_CHANGED`; las66 inicializaciones de red quieta y los5 focales separaron esa causa de fallos de producto. No se añadió reload/retry automático.

### Documentación y evidencia

Se creó este reporte y `remediation/`; se añadieron campos T0-R a debt register/ledger/command ledger y una sección al Markdown de deuda. Se conservaron los valores originales de T0 y los bytes exactos en [original-metadata](remediation/evidence/original-metadata/sha256.json). Los logs y el reporte T0 original no se reescribieron. El manifiesto `artifact-integrity.json` sigue siendo la captura histórica; sus hashes de metadatos anteriores corresponden a esas copias archivadas. El manifiesto T0-R certifica los archivos actuales por separado.

## Tests

**Resultado final:** Python383 PASS; Node128 PASS en20 archivos; Focus9 PASS; E2E83 ejecutados,78 PASS/5 FAIL/0errores/0skips; Browser251 esperados,24 terminados OK y el test25 bloqueado. No se declara el resto ejecutado ni PASS.

Reruns finales sobre el mismo freeze de source/tests. **B-BROWSER fue intentada completa pero no pudo finalizar**: la fixture lanzó KeyError y el teardown quedó bloqueado más de cinco minutos. Se envió SIGINT únicamente al proceso owned verificado; se conserva [registro de interrupción](remediation/evidence/B-BROWSER.interruption.json). No se certifican251 tests ejecutados; los conteos observados no sustituyen una suite completa. Cada suite usó credenciales productivas vacías; Docker/Auth/REST/worker/storage de E2E fueron owned y descartables. No se reemplazan resultados amplios por focales.

| Suite | Estado | Tests | Entradas FAIL/ERROR | IDs únicos fallidos | Skips | Duración | Evidencia |
|---|---|---:|---:|---:|---:|---:|---|
| B-PY | PASS | 383 | 0 | 0 | 0 | 14.895s | [log](remediation/evidence/B-PY.log) |
| B-NODE | PASS | 128 | 0 | 0 | 0 | 1.387s | [log](remediation/evidence/B-NODE.log) |
| B-FOCUS | PASS | 9 | 0 | 0 | 0 | 54.381s | [log](remediation/evidence/B-FOCUS.log) |
| B-BROWSER | BLOCKED | 24 observados /251 esperados (incompleta) | — | — | 0 observados | 534.812s | [log](remediation/evidence/B-BROWSER.log) |
| B-E2E | FAIL | 83 | 5 | 5 | 0 | 843.227s | [log](remediation/evidence/B-E2E.log) |

B-NODE ejecutó los mismos20 archivos y el runner reportó128 casos `node:test`; T0 había reportado20 unidades a nivel de archivo. No se agregaron tests Node ni se comparan ambos conteos como si fueran la misma unidad. B-SQL no se repitió: ningún archivo SQL/migración se modificó; se mantiene la ejecución T0 de46 tests PASS/0skips, con su evidencia original. E2E sí volvió a reconstruir y usar el stack real completo actual.

Los focales y sus iteraciones (incluidas las fallidas) están archivados. Destacan Golden real2 PASS, WorkflowContext+atributos21 PASS, acciones/rerun14 PASS, preparación/cascada12 PASS, Insight9 PASS, roles Foundation4/Gates4/compatibilidad3 PASS y migraciones históricas3 PASS. Hubo corridas diagnósticas iniciales interrumpidas expresamente al confirmar interferencia de bridges; no cuentan como validación final. Los fallos del focal Home/Context/Hero y del relacionado de workflow no se ocultaron.

IDs con FAIL/ERROR final reportado en las suites completas (Browser incompleta se registra por separado; no se infiere que el resto haya pasado):

- `test_collaboration.CollaborationTests.test_02_assigned_approval_handoff_attribution_override_and_retry`
- `test_tenancy.TenancyTests.test_09_home_attention_tracks_real_versions_and_removes_approved_or_archived`
- `test_workflow.WorkflowTests.test_browser_complete_workflow_at_mobile_width`
- `test_workflow.WorkflowTests.test_browser_creation_execution_approval_navigation_and_mobile_history`
- `test_workflow.WorkflowTests.test_scheduling_dashboard_v21_preserves_assignment_and_temporal_relations`

IDs nuevos con FAIL final reportado en suites completas (el bloqueo Browser C-FIXTURE-SNAPSHOT se registra aparte):

- Ninguno.

Entre los pendientes aparece un error de fixture `KeyError` al cambiar un Case ID sin actualizar el snapshot de responsabilidades. Es un problema de soporte del test, no evidencia de una regresión del motor. No se declara que los cambios de fixtures estén listos para integrar; se conservaron sin commit al activar STOP.

## Remaining Debt

- **B-HOME-ATTENTION**: regresión confirmada, exige reparación SQL fuera de la prohibición actual; bloquea cierre global.
- **E-FOCUS-REMAINDER**: foco de Config/navegador en viewport corto sin causa final aislada; bloquea G-B.
- Los fallos finales de fixtures/journeys/expectativas listados arriba siguen pendientes. Incluyen adaptaciones parciales que no pueden presentarse como PASS (p.ej. bar con cuatro checks, sincronización tras rerender y selección histórica). No se atribuyen al producto sin investigación. El error C-FIXTURE-SNAPSHOT fue introducido durante T0-R y bloqueó un test que antes pasaba; se registra por separado de los cinco FAIL finales E2E. Los cambios quedan sin commit para revisión/continuación controlada.
- Los3 IDs históricos WorkflowContext se conservaron y revalidaron conforme al contrato actual; esa deuda no sirve como exención para los nuevos fallos.
- Los límites T0 de observación remota (Cloud Run admin401, defaults/grants administrados, history remoto incompleto) siguen documentados. No se repitieron consultas remotas ni se alteró producción. El bloque de implementación Ultimate continúa fuera de alcance.

La deuda restante **sí compromete autorizar T1**. No se declara baseline verde.

## Gate Reevaluation

| Gate | T0-R | Evidencia / límite |
|---|---|---|
| G-B | FAIL | Persisten fallos completos y un cluster E nuevo; sin exención global. |
| G-R | BLOCKED | Golden focal PASS no sustituye E2E amplio; resultados/reportes y recorridos pendientes. |
| G-L | BLOCKED | Focus y casos reales de historial pasan en su alcance; quedan journeys y suite amplia pendientes. |
| G-S | BLOCKED en cobertura amplia | Reproducción conserva403 y autorización Owner; atención SQL incorrecta y escenarios amplios sin cierre. No se afirma bypass. |
| G-ENV | BLOCKED en completitud | Stack owned y aislamiento serial disponibles; PY/Node/Focus/E2E ejecutadas,0skips. Browser quedó incompleta por fixture/teardown y se interrumpió. No se certifica ejecución completa de las tres suites obligatorias. |

## Skills utilizadas

- `cloud-environment:cloud-environment-runtime` (`c5/cloud-environment-runtime`, incluida referencia Docker): entorno administrado, socket/red, CA y sandboxes locales.
- [emil-design-eng](../../../../.agents/skills/emil-design-eng/SKILL.md): interacción, accesibilidad/lifecycle y foco únicamente en callers fallidos; diseño actual preservado, sin auditoría ni rediseño.
- `supabase:supabase` (`c0/supabase`): interpretar roles/checked SQL/migraciones vigentes y limitar pruebas al stack owned. No impuso una aprobación adicional ni autorizó escritura remota.

## Estado final e integridad

HEAD continúa `ef997235a30251fbf7ae53690ed738092ee973d8` en `main...origin/main`; árbol con cambios T0-R y documentación previa untracked, sin staging/commit/push. No T1, contracts Ultimate, engines nuevos, entidades nuevas, migraciones, Supabase productivo, permisos productivos ni infraestructura. Los cuatro contenedores preexistentes se preservaron. Recursos locales creados por las suites cerrados mediante cleanup del sandbox. El snapshot de Git y hashes finales se guarda en `remediation/final-workspace.json`; [integridad T0-R](remediation/artifact-integrity.json) incluye logs y originales.

## FINAL DECISION

**STOP — persisten blockers. T1 continúa prohibido.**
