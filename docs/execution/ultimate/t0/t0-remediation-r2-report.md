# T0-R2 — Targeted Baseline Remediation

Estado final: **GO del baseline T0**. Captura final UTC: `2026-10-26T05:13:05.492404+00:00`. T1 no se ejecutó.

Baseline: `main` / `ef997235a30251fbf7ae53690ed738092ee973d8`. Se retomaron exclusivamente los blockers residuales documentados en T0/T0-R y la autorización específica T0-R2. No se ejecutó T1 ni se realizó una nueva auditoría general.

## Product fixes

La proyección de atención de Home usaba `approver_user_id`, retirado por el contrato vigente de Decision Owner. Una migración nueva reutiliza `dation_private.case_collaboration(...).can_approve` para reviews y comprueba elegibilidad actual del Decision Owner en handoffs. Home sigue siendo una proyección de trabajo; el endpoint de aprobación conserva toda la autoridad. No se amplían permisos ni se modifica el actor histórico.

Los cuatro fixes CSS de T0-R se conservan sin cambios adicionales. T0-R2 no modifica JS/Python de aplicación, motores, matemática D1/D2, APIs, DTOs, Data Pack, Decision Graph, assets ni infraestructura.

## Test / Fixture fixes

- El test de borrador cambiaba el Case ID sin registrar el snapshot de responsabilidades correspondiente. Se demostró el `KeyError` antes del fix y se agregó explícitamente el snapshot del segundo Case, conservando el primero.
- La fixture Browser registra sus excepciones y devuelve 500; teardown siempre cierra Chromium/Playwright y hace fallar el test si hubo errores. Sólo se reconocen las cancelaciones de rutas ya cerradas durante el cierre real.
- Los cinco E2E residuales conservan permisos negativos, aprobación efectiva, atribución histórica, CAS, paginación, historial y relaciones D1/D2. Sus precondiciones/locators/esperas se ajustan al contrato actual de Owner único, cuatro checks de Data y rerender posterior a la aprobación.
- Los residuales Browser ya documentados en T0-R usan el contexto compartido actual, atributos/Owner explícitos para Cases nuevos, escenarios de review independientes con upstream aprobado, controles actuales y tokens sólidos vigentes. No se elimina ningún test ni se agregan skips.

El inventario AST preserva los 235 IDs existentes en los 24 módulos de tests modificados. Se agregan únicamente tres tests E2E para la migración Home.

| E2E residual | Clasificación / relación con A–C | Reparación focal | Evidencia PASS |
| --- | --- | --- | --- |
| `CollaborationTests.test_02_assigned_approval_handoff_attribution_override_and_retry` | Defecto SQL A y expectativas retiradas de Owner; sincronización de rerender | Home usa autoridad actual; controles únicos, no-op/CAS y actor histórico se comprueban conforme al contrato vigente. | [focal de cinco](remediation-r2/evidence/five-e2e-current.log) |
| `TenancyTests.test_09_home_attention_tracks_real_versions_and_removes_approved_or_archived` | Locator histórico incorrectamente relativo; también consumer de A | Selección exacta de Run en su fila; preserva superseded/current, read purity y Cases archivados. | [focal de cinco](remediation-r2/evidence/five-e2e-current.log) |
| `WorkflowTests.test_browser_complete_workflow_at_mobile_width` | Fixtures/expectativas actuales y lifecycle de cola; sin causa de producto B/C | Cuatro checks, Owners explícitos, Map estable tras guardar, pending actual y worker real iniciado después de demostrar queued/reload; estilos actuales explícitos. | [mobile + desktop](remediation-r2/evidence/two-e2e-current.log) |
| `WorkflowTests.test_browser_creation_execution_approval_navigation_and_mobile_history` | Mismos callers del recorrido mobile; sin causa de producto B/C | Mismo fix compartido, conservando creación, review/cancel/confirm, aprobaciones, navegación e historial reales. | [mobile + desktop](remediation-r2/evidence/two-e2e-current.log) |
| `WorkflowTests.test_scheduling_dashboard_v21_preserves_assignment_and_temporal_relations` | Store aprobado antes del rerender; sin cambio de producto A/B/C | Esperar desaparición del control aprobado; conservar todas las comprobaciones de viajes, vehículos, cargas, fechas y fingerprint D1. | [focal de cinco](remediation-r2/evidence/five-e2e-current.log) |

Los cinco PASS focales se obtuvieron en las iteraciones indicadas: el focal de cinco aún conserva dos fallos de estilos que luego pasan en el focal mobile/desktop. No se reescriben esos intentos ni se presenta el log fallido como una corrida íntegramente verde.

La ejecución E2E completa conserva además los reportes de [lineage A–F](remediation-r2/evidence/e2e-reports/lineage-report.json), [mobile](remediation-r2/evidence/e2e-reports/mobile/browser-report.json), [desktop](remediation-r2/evidence/e2e-reports/desktop/browser-report.json) y [golden con actores distintos](remediation-r2/evidence/e2e-reports/golden-v2/report.json).

## Harness / Environment fixes

Se mantiene el lock exclusivo entre suites Browser/Docker para evitar interferencia de bridges en Chromium. El journey de cola deja el worker real detenido, demuestra admisión `queued` y recuperación tras reload y luego inicia ese mismo worker mediante una señal owned. Así no retiene artificialmente una descarga Storage durante el presupuesto real de su dependencia. No se aumentan timeouts ni se fabrican resultados.

Todas las pruebas usan credenciales productivas vacías, APIs loopback y sandboxes propios descartables. No se aplican migraciones ni se realizan escrituras remotas/productivas. Los cuatro contenedores preexistentes quedan fuera del cleanup de la tarea.

## UI / Responsive fixes

| Before | After | Why |
| --- | --- | --- |
| A 320×256, el footer fijo dejaba 67–89px de área principal; un control de 169px no entraba en los 163px disponibles de 568×320. El foco nativo quedaba recortado. | Sólo para altura ≤360px, los comandos vuelven al flujo y el scroll principal conserva `100dvh` con padding de foco de 8px. | Permite ver y recorrer cada control completo conservando estilos, tokens y comportamiento de alturas normales. |

La matriz before/after de Data, Map, Config D1 y Config D2 cubre 32 estados: 320×568, 320×256, 568×320, 1440×1000, 1280×1000, 1024×1000, 768×1000 y 390×844. Pasó de cuatro estados con foco fuera/oculto a cero. Las 24 capturas de altura normal son idénticas píxel a píxel. Se añadieron 12 comprobaciones de foco/touch y zoom equivalente a 200%, con capturas de foco visible y sin overflow.

## SQL migration

- Nombre: `supabase/migrations/20261026010000_home_decision_owner_attention.sql`.
- Motivo: alinear atención Home con autoridad actual de aprobación / Decision Owner, sin grants nuevos.
- Objeto: sólo reemplazo de `public.platform_home(uuid,uuid)`; dos predicados respecto de la definición anterior. Se conservan OID, owner, SECURITY DEFINER, search_path y ACL.
- Pruebas focales: fresh schema; upgrade desde definición anterior exacta; Owner/Admin positivos; operador no asignado/Viewer negativos; pérdida de elegibilidad; handoff; aprobación actual e histórica; aislamiento de workspace y acceso directo RPC restringido.
- Integridad: hashes de siete tablas de negocio/historial antes/después del upgrade, identidad/ACL de función y actor aprobado histórico.
- Rollback: definición previa exacta archivada en `remediation-r2/evidence/platform_home.pre-r2.rollback.sql`. Es una referencia operativa; restauraría también el defecto anterior de atención. No implica reescribir datos ni una autorización para aplicarla remotamente.
- Producción: **NO aplicada**. No se toca migration history, baseline ni ninguna migración histórica.

## Skills

| Skill / guía | Objetivo | Archivo / frontera | Decisión validada |
| --- | --- | --- | --- |
| Supabase (`c0/supabase`) | Migración compatible y pruebas aisladas de permisos | `platform_home`, sandbox local | Reutilizar autoridad actual, sin ampliar roles/grants ni usar producción. |
| Supabase Postgres best practices (`c0/supabase-postgres-best-practices`, `security-privileges.md`) | Privilegio mínimo y función persistida | Función existente y su ACL | `CREATE OR REPLACE` mínimo; comprobar permisos positivos/negativos y conservar ACL. |
| [emil-design-eng](../../../../.agents/skills/emil-design-eng/SKILL.md) | Foco e interacción accesibles | Media query de baja altura y callers fallidos | Scroll nativo y preservación visual; ninguna nueva animación ni rediseño. |
| Cloud runtime (`c5/cloud-environment-runtime`, Docker/network refs) | Entorno y runners reproducibles | Docker owned / loopback / aislamiento | Lock serial y cleanup por identidad, sin cambios de red/configuración productiva. |

No se activaron Skills de auditoría transversal, branding o motion. Las guías no alteran el alcance ni autorizan instalación de plugins o acciones productivas.

## QA y gates

Las seis suites se ejecutaron completas después del freeze de source, con los comandos exactos y entorno registrados en [QA](remediation-r2/qa-summary.json) y el command ledger.

| Suite | Estado | Tests | Failures | Errors | Skips | Duración | Evidencia |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| B-PY | PASS | 383 | 0 | 0 | 0 | 18.835s | [log](remediation-r2/evidence/B-PY.log) |
| B-NODE | PASS | 128 | 0 | 0 | 0 | 2.69s | [log](remediation-r2/evidence/B-NODE.log) |
| B-BROWSER | PASS | 251 | 0 | 0 | 0 | 1428.501s | [log](remediation-r2/evidence/B-BROWSER.log) |
| B-SQL | PASS | 46 | 0 | 0 | 0 | 43.756s | [log](remediation-r2/evidence/B-SQL.log) |
| B-E2E | PASS | 86 | 0 | 0 | 0 | 946.193s | [log](remediation-r2/evidence/B-E2E.log) |
| B-FOCUS | PASS | 9 | 0 | 0 | 0 | 62.514s | [log](remediation-r2/evidence/B-FOCUS.log) |

Node ejecutó los mismos 20 archivos y reporta 128 casos; no se confunde ese conteo con las 20 unidades por archivo del reporte T0. Browser conserva sus 251 tests. E2E pasó de 83 a 86 por los tres tests nuevos de Home. B-FOCUS repite intencionalmente cobertura de lineage y no sustituye las demás suites.

B-SQL conserva el alcance del SQLSandbox histórico indicado por §22.1. La nueva migración se prueba además contra todas las migraciones vigentes en el sandbox E2E, incluyendo fresh y upgrade real.

Se conservan todos los intentos fallidos: el primer Browser completo corrió 251 tests con 3 failures y 6 errors; los focales aislaron los residuales sin una nueva auditoría. Los dos timeouts intermitentes de Home/toolbar pasaron sin cambiar producto en su focal y en la suite completa final; no se les atribuye una causa no demostrada ni se les otorga una exención. Los cinco E2E originales tienen focal PASS y pasan también en la suite final de 86. [Causas](remediation-r2/evidence/root-causes.json), [focales](remediation-r2/evidence/focal-ledger.json), [primer Browser](remediation-r2/evidence/B-BROWSER.attempt1.log).

| Gate | Resultado / alcance |
| --- | --- |
| G-B | PASS — six complete suites, zero failures/errors/skips; all original failing IDs covered. |
| G-C | PASS at T0 — no contract/DTO/engine/graph changes or new incompatibility. |
| G-D | PASS at T0 — authorized additive Home migration, owned fresh+upgrade, unchanged business rows and function ACL; no baseline/history repair. |
| G-R | PASS at T0 — existing result/consumer/exports and real engine regressions green; Ultimate packages remain future work. |
| G-L | PASS at T0 — current/historical approvals, upstream/downstream, races/retries/recovery and read purity covered by existing full suites. |
| G-S | PASS at T0 — Owner/Admin/nonowner/Viewer/tenant and RPC/ACL negatives; Home never grants approval. |
| G-ENV | PASS — all runners available, tests >0, local owned infrastructure, zero skips. |
| G-A | PASS — only R2 residual scope; T1 not executed, no remote writes or release actions. |
| G-UI | PASS — 32 before/after states, 24 pixel-identical normal-height captures, 12 focus/touch/zoom checks, full Browser green. |

Los PASS corresponden a T0 y su baseline vigente. No certifican entregables de fases Ultimate futuras ni autorizan release productivo.

## Integridad y estado Git

Los planes permanecen intactos. El historial de T0/T0-R y sus reportes/manifiestos se conserva; los resultados R2 se incorporan en campos separados y evidencia propia. No hay commit, staging, push, merge, despliegue ni escritura productiva. T1 sigue fuera de alcance.


Las 31 piezas de source/tests pendientes respecto de HEAD (incluidas las heredadas de T0-R) coinciden con el freeze. T0-R2 modificó 13 archivos respecto del estado inicial: una corrección CSS de baja altura, una migración nueva y soporte/tests relacionados. [Scope y diff](remediation-r2/evidence/r2-scope-diff.json), [freeze](remediation-r2/evidence/final-source-freeze.json), [preservación](remediation-r2/evidence/preservation-checks.json). No se modificaron migraciones existentes, skips ni valores de timeout.

Los 84 registros del manifiesto histórico T0-R se resuelven a archivos intactos o a sus bytes exactos archivados. Los planes conservan sus hashes originales. [Resolución histórica](remediation-r2/evidence/r1-integrity-resolution.json); [integridad R2](remediation-r2/artifact-integrity.json).

## FINAL DECISION

**GO — T0 baseline estabilizado. T1 puede ser solicitado.**
