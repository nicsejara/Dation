# Final Polish + Run Lineage Saga

Fecha: 2026-10-24. Baseline real de `main` y `origin/main`: `735163216f97b832afebd3744dfa91d9009630f0`. Árbol inicial limpio; branch de trabajo: `fix/final-polish-run-lineage-saga`.

Se ejecutó el Master Prompt de esta saga sobre los componentes y contratos afectados. No se hizo una auditoría general ni se reabrieron las ilustraciones o la dirección visual aprobada. Fuente de verdad: architecture, domain-model, navigation, decision-runs, foundation-refactor-summary y los summaries visuales recientes de `/docs`.

## Implementación y archivos

1. `92764c8` — **Polish shared controls and new-run warning actions**. Primitive compartida para los selects nativos de responsabilidades en `cases/workflow-responsibility.mjs` y `workflow-context.css`. Supresión localizada del artwork decorativo del panel del Map mediante `panelArtwork` en `decision-config-ui.mjs` y `cases/decision-map.mjs`. Nuevo `runs/new-run-warning.mjs` con dialog nativo, lifecycle compartido y acciones equivalentes.
2. `2a704be` — **Normalize D1 and D2 dashboard hero media layout**. Nuevo `runs/dashboard-hero.mjs`; shells de Assignment/Scheduling, Assignment summary y approval trace usan zonas físicas de contenido y visual. `dashboard-toolbar.css` comparte grid, frame, toolbar y media slot; se retiran los posicionamientos absolutos y la ocultación móvil anteriores de ambos artworks.
3. `417b3eb` — **Fix contextual new-run routing and preserve run lineage**. `workspace.mjs` conserva Case, Data Pack y Decision de la Run, confirma la reapertura de una aprobación vigente y navega explícitamente a Config D1/D2. Un Data Pack incoherente produce un error visible sin crear otro Case. `dashboard-toolbar.mjs` restaura el foco al cancelar. Se incorporan pruebas de navegador y E2E reales de lineage.
4. **Stabilize final polish and lineage flows** — cierre de QA, aserción de foco visible por teclado y este documento. El SHA de este commit se informa en el reporte final.

Los archivos de aplicación cambiados están exclusivamente en `backend/app/static/css/` y `backend/app/static/js/dispatch/`. Se agregaron/ajustaron pruebas en `backend/tests/browser/` y `backend/tests/e2e/`. No se cambiaron Python de aplicación, SQL/migraciones, contratos API, engines, dependencias, assets ni infraestructura.

Se reutilizan sin cambios `assignment-isometric.webp` y `scheduling-isometric.webp`; los iconos SVG de DDA también conservan sus bytes.

## Hechos del baseline

- El icono lateral ya era transparente y su feedback pertenecía a la fila. F1 se verificó en todos los estados sin introducir otro cambio al asset o sidebar.
- En el baseline no existía un modal de advertencia de Nueva corrida. Se agregó el guard de UI solicitado para una Decision con aprobación vigente; no se atribuye al baseline una copia inexistente.
- En las fixtures afectadas, Nueva corrida ya llegaba a la Config correspondiente desde D1 y D2. No se reprodujo un salto al Map. La saga hace explícita esa resolución contextual, protege el Case persistido y agrega cobertura de regresión sobre la API y persistencia reales.

## Acceptance F1–F12

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| F1 | PASS | SVG transparente, feedback de la fila; normal, hover, active, focus y selected en seis anchos. |
| F2 | PASS | Data Owner y Decision Owner comparten select nativo: alto mínimo 44 px, padding, borde, fondo, radio, tipografía, chevron y estados default/hover/focus/disabled. Selección y guardado conservados. |
| F3 | PASS | Sin camión/watermark ni imagen sustitutiva en “Cómo avanza el caso”; permanecen ELEGÍ, CONFIGURÁ y APROBÁ. |
| F4 | PASS | Cancelar/Confirmar nueva corrida con igual geometría, tipografía, radio y padding. Primario teal, secundario visible, Tab atrapado, Escape/cancelación, foco visible y restaurado; cleanup al navegar. |
| F5 | PASS | Contenido y visual separados; mismo grid, padding, min-height, approval y toolbar. Media slot idéntico por resolución, `contain` centrado y estable ante narrativa corta/media/larga sin reducir la fuente. |
| F6 | PASS | D1 pendiente → Config D1 → otra Run del mismo Case/Decision, sin warning innecesario. |
| F7 | PASS | D2 con cadena aprobada → warning → Config D2; nueva D2 conserva D1 aprobada como upstream. |
| F8 | PASS | D1 con downstream aprobado → warning → Config D1; la admisión de la nueva Run retira vigencia propia/downstream y conserva evidencia histórica. |
| F9 | PASS | Relaciones existentes de Run/Case/Decision y upstream; ninguna entidad Branch nueva. |
| F10 | PASS | Historial completo, aprobaciones históricas, Run elegida, reload, Back/Forward y selección canónica del Decision Navigator conservados. |
| F11 | PASS | Case, Data Pack, owners, permisos, tenancy, idempotencia, motores, APIs y persistencia sin cambios de contrato. |
| F12 | PASS | Responsive y teclado a 1440×900, 1024×768, 768×1024, 375×812 y 320×640; sin overflow horizontal ni fallos de contraste muestreados. |

Frame desktop D1/D2: 600 px de min-height compartido. Media: 440×300 px a 1440; 285,45×240 px a 1024; 440×240 px a 768; 241×225 px a 375; 186×192 px a 320. En móvil se apilan contenido → visual → acciones y el alto total crece con el contenido; no se oculta la ilustración.

## Routing, lineage e invalidación

Nueva corrida toma `case_id`, `node_id` y configuración de la Run, hidrata el Case y recupera sus perfiles. Para un Case persistido comprueba que coincida el Data Pack y no invoca una creación implícita de Case. La ruta final es Config del mismo nodo, sin `run_id`; no pasa por Map cuando se cumplen los gates actuales.

La confirmación sólo abre Config. No crea Runs ni invalida aprobaciones. La autoridad sigue siendo la admisión existente de `/api/runs` y su transacción SQL: la nueva D2 retira su aprobación vigente/downstream, conserva D1; la nueva D1 retira su aprobación vigente/downstream. No se cambiaron `enqueue`, `validate_upstream_run`, `invalidate_run_lineage`, `decision_runs_reopen` ni la proyección canónica del historial.

`decision_case_id`, `node_id` y `upstream_run_id` ya expresan el lineage requerido. Permanecen results, fingerprints, configuración, actor y fecha de aprobación de Runs históricas, junto con la evidencia de supersession. Scheduling consume el D1 aprobado actual y no reasigna viajes, vehículos, cargas o rutas.

## Escenarios A–F

Una prueba Chromium contra API, worker, PostgreSQL 17 y PostgREST aislados ejecutó siete Runs de un único Case, sin interceptar las APIs del journey:

| Escenario | Estado | Resultado verificado |
| --- | --- | --- |
| A | PASS | D1 pendiente → Nueva corrida → Config D1 → segunda D1. Sin invalidación al abrir Config. |
| B | PASS | D1 A + D2 A aprobadas → Nueva corrida D2 → warning → Config D2. D1 A sigue vigente. |
| C | PASS | Misma cadena → Nueva corrida D1 → Config D1 → ejecutar D1 B. Recién en la admisión quedan superseded D1 A y las D2 dependientes. |
| D | PASS | Tres D1 sucesivas antes de aprobar, todas en el mismo Case/Decision, sin Branch artificial. |
| E | PASS | D2 A y D2 B conservan ambas `upstream_run_id = D1 A`; reejecutar D2 no invalida D1 A. |
| F | PASS | D1 B aprobada habilita D2 C con upstream D1 B. Las D2 anteriores y sus approvals siguen consultables. |

Se comprobaron además: siete Runs únicas; un solo Case; owners y datasets idénticos antes/después; cuatro eventos de aprobación; replay idempotente de una intención anterior sin Run adicional ni invalidación de la cadena nueva; rechazo 409 de upstream retirado; rechazo 403 para Viewer; snapshots históricos de resultados/configuración/fingerprints/actor/fecha sin alteraciones.

## QA y límites

- Python completo: **383/383 PASS**. La primera ejecución sin loopback se interrumpió; la ejecución con red local de pruebas habilitada terminó correctamente (`unit-final.log`).
- Node: **20/20 PASS**, sin fallos (`node-final.log`).
- Chromium: **30 pruebas distintas PASS**: ocho nuevas de esta saga, nueve FinalPolish, tres UnifiedHero, tres FoundationComponents, dos Saga3, dos Navigation de toolbar/export/approval, un modal compartido, un Viewer y un Decision Navigator. La aserción adicional de foco visible del modal se ejecutó nuevamente y pasó.
- E2E real: **A–F PASS**, siete ejecuciones de motor, sin errores JavaScript (`phase3-e2e-accepted.log`). Dos intentos previos corrigieron únicamente suposiciones del test: history exige `node_id`; tras reload debe esperarse el bootstrap de `window.DationDispatch`. Ningún contrato de aplicación se alteró para acomodarlos.
- Tres pruebas antiguas de `WorkflowContextTests` fallan también en la copia aislada exacta de `7351632`: `test_map_assignment_is_consumed_readonly_by_config_and_review` y `test_dda_navigation_resolves_canonical_runs_without_losing_context` esperan Config con una fixture que no cumple el gate vigente de atributos; `test_dashboard_trace_shares_the_copy_row_and_context_pills_are_equal` espera geometría anterior del navigator (diferencia de anchos 162,609375 px en ambos snapshots). Se conservaron sin debilitarlas. La corrida amplia fue 25/27 PASS y el grupo crítico 4/5 PASS; los tres fallos son preexistentes, no nuevos. El test canónico de selección aprobada del Navigator pasó por separado.
- Capturas BEFORE a 1440/375 y revisión AFTER de 35 capturas a cinco tamaños. Contraste mínimo muestreado **5,43:1**, cero overflow, cero ejecuciones accidentales y cero errores de consola en esa captura.
- Taste aplicado como app existente: se conservó Dation Precision/data-terminal, seed `2039572090`, sin nuevo draw. Lint de las adiciones CSS: cero findings. Probe/judgeApp en diez vistas dashboard: cero FAIL; WARN de bordes/radios/densidad/escala y espacio del frame compartido se mantienen dentro de la dirección aprobada, sin ampliar el alcance. El adaptador de medición excluye vistas ocultas y fills SVG invisibles.
- Verificación SHA256 contra baseline: ningún Python de aplicación, engine, migración, infraestructura o asset modificado. Sintaxis de los once módulos JS afectados: PASS. `git diff --check`: PASS.

Artefactos de esta sesión fuera del repositorio: `/workspace/work/run-lineage/` (logs, capturas, mediciones, trace Chromium y `e2e/lineage-report.json`). Los tests versionados permiten repetir la validación sin escribir en producción. No se hizo una auditoría transversal ni una afirmación de que todos los tests browser históricos estén verdes.

## Entrega

No se encontró ninguna STOP CONDITION: no hicieron falta cambios de schema, API, Branch, dominio, aprobación, invalidación o engine. `origin/main` seguía en el baseline tras el fetch de cierre. Integración autorizada únicamente mediante fast-forward limpio, preservando los cuatro commits; sin squash, force o rebase. El SHA final y los resultados efectivos de merge/push se informan en el reporte de cierre.

Cloud Build, Cloud Run, Supabase, secrets, variables, Docker de producción y triggers no se modificaron. El pipeline existente debe reaccionar al push de `main`; observarlo es una consulta de sólo lectura y no equivale a desplegar manualmente.
