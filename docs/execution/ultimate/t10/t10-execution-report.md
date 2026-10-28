# T10 — Dashboards, Detailed Analysis, Export y Dation IA / Approval Copilot

Implementación y validación completas del alcance T10 sobre el baseline T9 aprobado. Dashboard, detalle, CSV, JSON completo, Copilot y Review leen hechos publicados de la misma Run y conservan su `result_fingerprint`. No se ejecutó T11 ni se realizaron staging, commits, merge, push, despliegues o cambios de infraestructura.

## 1. Autorización, baseline y checkpoint

Fuentes de ejecución: [autorización exclusiva T10](evidence/T10-user-request.txt), [Master Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), especialmente §3.1, T10, §22, §23 y R1–R18, y [reporte oficial T9](../t9/t9-execution-report.md). No se hizo otra auditoría end-to-end ni se repitieron T0–T9 como fases.

HEAD conservado: `ef997235a30251fbf7ae53690ed738092ee973d8`; branch `main`. El working tree ya contenía las implementaciones aprobadas anteriores; HEAD por sí solo no representa ese baseline. Las **88 entradas del manifiesto T9** se verificaron antes de modificar consumidores.

Checkpoint inmediato post-T9: **920 archivos / 43.794.290 bytes**, copias en `/workspace/work/dation-t10/post-t9/`, inventario y patch tracked. SHA256 del inventario: `042274bb505a265b072121a281cd5d33a15e4d22bc6ecfe6d279181ef8bf15e8`. El [estado inicial](evidence/initial-state.json) conserva hashes/tamaños, branch, HEAD, staging vacío y estado Git. SHA256 del Master Plan, sin cambios: `c7543ffa1ef26c79d9142797863fc8ba83613f6cb426cf1621eb0c11b5a27823`.

Hubo una interrupción operacional del entorno durante W10. Se reanudó desde los archivos existentes: **0 archivos perdidos de los 920** y sólo tres archivos previamente pendientes extendidos por T10 (`routes/results.py`, `navigation/resource.mjs`, `workspace.mjs`). No hubo reset, clean, descarte, recuperación inventada ni reconstrucción de fases anteriores. El [registro de recuperación](evidence/environment-recovery.json) describe los resultados parciales de ese momento; los conteos definitivos son los de este reporte y del test ledger, después de completar las repeticiones necesarias.

El [control final de preservación](preservation.json) conserva las preimágenes de los diez archivos extendidos. El árbol queda pendiente de revisión, como al inicio, más los cambios T10; el índice sigue vacío. No se afirma que el working tree esté limpio.

## 2. Alcance, Skills y preservación del diseño

Se inspeccionaron exclusivamente lectores/resultados, dashboards, selectores/callers de navegación, toolbar, charts, Details, drawers, exports, contexto/interpreter, Review y tests afectados. La frontera SQL se amplió sólo para persistir provenance/historial del Copilot usando columnas T2 existentes.

El [ledger de Skills](skills-ledger.json) registra nombre exacto, versión o SHA256, referencia leída, aplicación concreta, evidencia y recomendaciones omitidas. Se aplicaron `design-system`, `emil-design-eng`, `ui-ux-pro-max`, `break-ui`, Supabase/Postgres y runtime cloud. No se invocaron `review-animations` ni `improve-animations`, ni se delegó una auditoría de motion. Playwright/unittest/Node son herramientas; no se inventaron Skills de browser/testing ausentes.

La búsqueda focal de `ui-ux-pro-max` fue `"chart keyboard accessibility" --domain ux -n 3`; se verificó su pertinencia: Skip Links, Keyboard Navigation y Focus Not Obscured Enhanced. Se reutilizó el skip link existente y se comprobaron teclado/foco/controles no tapados. No se generaron otro sistema visual, palette, fuentes, framework o componentes desde ejemplos de una Skill.

Referencias reales: `d-dashboard-hero`, `d-dashboard-hero__grid`, `d-dashboard-hero__media`, `d-dashboard-section`, `d-kpi`, `d-card`, `d-btn`, toolbar/dropdowns de `runs/dashboard-toolbar.mjs`, launcher de `runs/contextual-assistant.mjs`, focus helpers y shell del workspace. Se conservaron los assets aprobados `assignment-isometric.webp` y `scheduling-isometric.webp`.

Se agregaron renderers porque el Sankey publicado D1 y el Day Gantt D2 requieren semánticas distintas de los dashboards v1. Comparten shell, tokens, cards, botones, toolbar, Details, drawer, Review y Copilot. `ultimate-results.css` está acotado a los resultados nuevos y sus necesidades de layout/estado; no define otra escala visual ni cambia tokens/global CSS. Las capturas y medidas reales están en [W10](evidence/w10/measurements.json), [referencias iniciales](evidence/ui-before/measurements.json) y [comparación legacy](evidence/legacy-preservation/comparison.json).

| Before | After | Why |
|---|---|---|
| Runs Ultimate llegaban a una vista provisional sin representación completa de las proyecciones publicadas. | Hero nativo, cinco KPIs certificados, visual del nodo, un Details colapsado, IA contextual y Review compacto. | Conectar la nueva funcionalidad prevista sin reabrir la dirección visual. |
| Drawers y consumers legacy no conocían el binding completo de entidad Ultimate. | Selección lazy ligada a Run/FP/tipo/ID, cancelación y descarte de respuestas anteriores. | Evitar evidencia de otra Run y conservar foco/navegación. |
| El launcher flotante podía superponerse a acciones de la toolbar nueva en pantallas estrechas. | Opción `avoidSelector` aplicada sólo al dashboard nuevo; acciones y menús quedan libres. | Preservar controles accesibles sin cambiar el comportamiento legacy por defecto. |
| Viajes simultáneos del mismo recurso podían ocultarse en una única fila visual del Gantt. | Subfilas visuales por Trip bajo el mismo recurso publicado. | Hacer todos los viajes seleccionables sin inferir unidades, patentes, asignaciones ni fechas. |
| Un cambio de modo/pregunta durante una respuesta podía presentar el resultado bajo otro contexto de formulario. | Controles bloqueados mientras espera, binding de generación/intent y limpieza de respuesta al cambiar contexto. | Mantener pregunta, modo, evidencia y respuesta en el mismo turno. |
| Una captura tomada antes de decodificar la imagen podía aparentar un Hero sin ilustración. | Harness espera `img.decode()` y valida dimensiones/visibilidad antes de comparar. | Medir el producto renderizado, sin sustituir ni editar sus assets. |

## 3. Archivos creados y modificados

Delta **respecto del checkpoint post-T9**, no respecto de HEAD: **28 archivos fuente/tests/migración: 18 creados y 10 modificados**. Documentación/evidencia T10 se contabiliza aparte. Inventario exhaustivo, bytes y hashes en [source-manifest.json](source-manifest.json); SHA256 del archivo: `42e0c094608a0b82d0007789f424ce517f7e75a648fcf45cc40c05628447908b`.

| Área | Creados | Modificados |
|---|---|---|
| Consumers backend / IA | `services/result_consumer_service.py`, `services/ultimate_decision_context.py` | `platform/exports.py`, `routes/results.py`, `services/decision_context.py`, `services/decision_interpreter_service.py` |
| Frontend | `css/ultimate-results.css`; `js/dispatch/results/{dashboard,details,mount,package,visuals}.mjs` | `dispatch/dashboard.mjs`, `navigation/resource.mjs`, `runs/{contextual-assistant,dashboard-toolbar,export}.mjs`, `workspace.mjs` |
| Tests/harness | `test_decision_context_v1.py`, `test_ultimate_result_consumers.mjs`, `consumer_fixtures.py`, `browser/test_ultimate_result_consumers.py`, `e2e/{test_ultimate_consumers,ultimate_consumer_fixture}.py` | Ninguno |
| Fixtures | `fixtures/ultimate/{consumers,consumer_alternatives,consumer_null_context}.json` | Ninguno |
| SQL | `20261027190121_ultimate_copilot_consumers.sql` | Ninguna migración anterior |

No se modificaron engines, asignaciones/costos D1, fechas/status D2, assemblers, DTOs/registry/catálogos T1, metadata pública congelada, Model/Pack históricos, assets, tokens/CSS globales, infraestructura, Docker, secrets o pipelines. Los cambios previos visibles en esos archivos dentro del working tree pertenecen al baseline y se preservaron.

## 4. Result Reader y contexto de navegación

`results/package.mjs` acepta explícitamente `transport_plan_v1` y `day_scheduling_v1`; valida headers/binding y rechaza schema desconocido o inconsistente. No existe fallback `unknown → Dispatch`. Los caminos de export/context/interpreter v1 también rechazan un package nuevo/desconocido antes de invocar el comparativo legacy o un proveedor.

`results/mount.mjs` conecta el dashboard al grafo/Run explícita y autorización real. `workspace.mjs` recibe únicamente el branch mínimo de montaje; Map/Config/Case Data mantienen sus contratos. La navegación y Nueva corrida conservan el destino contextual del backend: D1→Config D1, D2→Config D2, y selección aprobada frente a una candidata posterior. No se infiere el resultado desde el Case actual o el estado de una sesión.

Queued/running muestran estado liviano y polling acotado; sólo al publicarse atómicamente se monta el resultado. Cambiar de Run limpia el DOM anterior inmediatamente, aborta requests y descarta generaciones tardías. W10 ejercita publicación en espera y respuesta de entidad recibida después de cambiar de Run.

## 5. D1 Dashboard y Sankey

Hero corto “Plan de transporte recomendado”, contexto secundario de Transport Plan/policy/horizonte/Model Version/status y cinco KPIs: costo recomendado, viajes, cobertura, utilización y recursos usados. Son lecturas de metrics certificadas; no hay suma, media de ratios, mix, ahorro/ROI o costos calculados en frontend.

El Sankey representa exclusivamente `primary_visual` publicado: **DESTINATION→TRIP→RESOURCE**, con dimensión/anchos de la proyección. El frontend transforma magnitudes a coordenadas; no fabrica flows, residual como Trip, cobertura ni mezcla unidades. El oracle distingue ambos cortes: no suma dos capas como cobertura.

Destination/Resource resaltan conexiones sin navegar; Trip abre drawer. Los IDs gráficos se resuelven mediante el índice de entidades publicado; un label no se convierte en identidad ni se utiliza para buscar en otro Run. Existe representación accesible/lista de acciones equivalente. Vacío, una entidad y visual densa tienen checks focales.

## 6. D1 Detailed Analysis y Trip Drawer

Un único disclosure “Análisis detallado”, cerrado por default, carga datasets sólo al abrirlo. Tabs: **Plan, Demand, Resources, Alternatives, Exceptions, Evidence**.

| Tab | Lectura y comportamiento |
|---|---|
| Plan | Trip, Orders, origen/destino, recurso/source, load, capacity, utilization, cost. Search/filter/sort de la página actual y export del dataset completo certificado. |
| Demand | Order/prioridad/requested/assigned/Trips/Resources/coverage/status/reason; conserva splits y COVERED/PARTIALLY_COVERED/UNASSIGNED. |
| Resources | OWN y EXTERNAL conservan sus campos distintos: units/trips/capacity/distance/cost/utilization o services available/used/remaining/availability source. Capacidad de recursos no usados se recupera de hechos de elegibilidad ya publicados. |
| Alternatives | Sólo 0–3 alternativas publicadas: profile/policy/metrics/deltas/material differences; NOT_COMPUTED/BUDGET_LIMIT/NO_MATERIAL_ALTERNATIVE desde la evidencia correspondiente. Abrir/Compare no crea job ni ejecuta solver. |
| Exceptions | Categorías de negocio/factibilidad/policy/data y assumptions diferenciadas; fallo técnico presentado como error de carga, nunca como excepción de negocio. |
| Evidence | Context, policy, engine/version, constraints y fuentes certificadas; detalles técnicos/fingerprints bajo sección avanzada. |

Drawer Trip: ID, Orders, origen/destino, recurso/source, load/capacity/utilization/cost y razones/evidence determinísticas, más CTA contextual de IA. La unión agrega datos del Trip inmutable de la misma publicación; no reconstruye una decisión. Costos desconocidos permanecen NULL/“No informado”.

La paginación visible pide 25 filas; máximo de API 100. Search/filter/sort están expresamente rotulados como **página actual**, no se presentan como consulta global. El export no toma filas del DOM ni del filtro de vista. Formato/comparación decimal conserva centavos grandes sin conversión aritmética a `Number`.

## 7. D2 Dashboard, Day Gantt y Detailed Analysis

Mismo Hero shell/patrón: “Programación del plan aprobado”, cinco KPIs publicados: viajes programados, expected delivery compliance, margen medio, peak dispatch day y excepciones. **Expected Compliance no se sustituye por Strict ON_TIME**; el detalle conserva el conteo/definición estrictos donde corresponden.

Day Gantt usa **RESOURCE×DAY×TRIP** de la proyección backend. El renderer convierte fechas certificadas en coordenadas; no calcula dispatch/arrival/outbound/cycle/occupancy/available_again/margin/status. OWN conserva occupancy con end exclusivo; EXTERNAL muestra dispatch/arrival sin retorno ficticio. La escala incluye arrival/return fuera del horizonte y hace visible un viaje de un solo día. PRE_HORIZON/UNSCHEDULED/LATE y tiempos NULL no desaparecen para mejorar ratios.

Los viajes concurrentes del mismo recurso se distribuyen en subfilas de presentación por Trip dentro del grupo original. Es una decisión de layout: no asigna unidades, no crea matrícula/vehículo y no reemplaza lanes/witness del producer. La simultaneidad factible sigue siendo una certificación T9.

Tabs D2: **Schedule, Trips, Resources, Service, Exceptions, Evidence**. Service mantiene estados publicados ON_TIME/AT_RISK/LATE/PRE_HORIZON/UNSCHEDULED y ordena el margen conocido sin recalcularlo. Cada tab consume su dataset; Resources diferencia OWN/EXTERNAL.

El drawer incorpora Orders/load/costo heredado del **D1 exacto** fijado por `source_transport_plan` Run/FP, además de dispatch/arrival/due/margin/status/reasons D2. Una D1 posterior, incluso aprobada, no reemplaza los hechos del D2 histórico. E10 verifica esa secuencia con SQL/worker/API reales.

## 8. Selected Entity y control de races

Binding completo: `(run_id, result_fingerprint, entity_type, entity_id)`. Retrieval autorizado, lazy y acotado; no se envía el dataset completo al seleccionar Trip. El servicio valida publicación y origen exacto, y no busca el mismo ID en otro Case/Run/tenant.

AbortController más generación/binding impiden abrir un drawer antiguo tras cambiar de Run. Un turno con igual ID y contexto/selección diferentes devuelve conflicto; el replay original se resuelve antes de llamar al proveedor. Modo, pregunta y selección quedan asociados al intent mientras espera. Cambiar de modo/pregunta elimina una respuesta que ya no corresponda a ese formulario.

## 9. Dation IA / Decision Approval Copilot

Cuatro modos **EXPLAIN, EXPLORE, COMPARE, REVIEW**, con `decision_context_v1`. Contexto construido a partir de la base publicada, métricas/summary/review/policy/exceptions/assumptions y evidencia seleccionada autorizada; no desde CSV crudo, Case actual o state de frontend. COMPARE copia únicamente métricas/deltas/diferencias de alternativas ya publicadas.

El proveedor existente recibe hechos acotados y sólo puede seleccionar **fact IDs, reason IDs y alternative IDs** tipados. Campos libres/cifras/causas/alternativas desconocidas o respuesta malformada son rechazados. El backend construye el texto **FACT→REASON→BUSINESS IMPLICATION** con hechos y templates determinísticos. No se afirma causalidad por observar un costo menor; una razón necesita scope y prueba suficientes. Sin ella, no se inventa una explicación causal.

El Copilot no tiene herramientas de mutación, aprobación o solver. What-if que modifica constraints requiere nueva Simulation/Run determinística; describir diferencias entre alternativas ya publicadas no se confunde con una simulación nueva. Valores NULL no se completan ni se convierten en cero.

Provider failure/unconfigured, selección inválida, respuesta inventada o contexto fuera de presupuesto produce fallback determinístico declarado. Prompt máximo 24 KiB; si supera el límite, **no se envía** al proveedor y el recibo registra bytes/scope/counts/refs. Claims máximo 12 KiB: se omiten claims completos con refs/límite explícitos, sin cortar un reason o su calificador.

Approval awareness usa overlay backend actual: “recomendación actual” antes de aprobar, “decisión aprobada” después. No confunde generación de una recomendación con decisión empresarial. La respuesta no concede autorización.

### Provenance, replay e historial

Intent/hash incluyen Run/FP/context version/mode/selected entity/alternative refs/pregunta. Los recibos conservan contexto original, claims, provider/model/prompt version y source provenance. Replay precede al proveedor: no recrea contexto con hechos actuales. Se agrega overlay actual separado para aprobación/freshness; la UI identifica contexto histórico cuando perdió vigencia.

Historial lazy, paginado en 20 turnos, usando las tablas existentes de chat/interpretación. Leerlo no llama al proveedor ni regenera evidencia. Drawer/conversación conservan nombres accesibles, foco/Escape/retorno y el estado abierto/cerrado de disclosures nativos.

## 10. Approval Review y autorización humana

Review compacto con readiness/status, coverage/scheduling, hard constraints, exceptions y assumptions de la misma publicación. Acciones: revisar excepciones, consultar IA, verificar integridad/permisos y aprobar.

El permiso no se infiere del texto, Owner label, node state ni package. El GET de Review consulta el overlay backend `approval_allowed`/blockers; el POST conserva guards T8 y expected fingerprint. Integridad y autorización se verifican explícitamente, sin prefetch pesado en la carga inicial. SQL vuelve a comprobar freshness/ownership/upstream/read-set bajo locks. Un review obtenido antes de un cambio no autoriza una aprobación posterior inválida.

No se alteraron idempotencia, reglas de reapproval, ownership, invalidación downstream ni lineage. Approval overlay no cambia el hash ni los bytes del package histórico. E10 cubre aprobación humana, awareness del replay y rechazo de un review stale.

## 11. Export CSV y JSON completo

`Transport_Plan.csv` y `Day_Schedule.csv` salen de projections T7/T9. El dataset certificado es el **único driver de filas**. D1 reconoce el costo consolidado una vez por Trip; otra allocation conserva NULL. No se reparten/recalculan costos ni se agregan filas. Las columnas de display adicionales unen campos del Trip inmutable exacto, incluidas capacidad/utilization/cost model/reasons.

CSV conserva quoting, UTF-8 BOM y protección de fórmulas para texto; márgenes numéricos negativos siguen siendo números. Metadata de Run/FP aparece en columnas y headers. No se exporta el DOM ni el filtro local. NULL y cero real permanecen distintos.

JSON `complete_decision_export_v1` resuelve package y **todas** las referencias autorizadas propias; D2 incluye además package y todos los artifacts del D1 origen exacto. Sólo devuelve `complete=true` después de materializar/verificar todo. Artifact faltante/corrupto produce error explícito, y el cliente no descarga un archivo parcial llamado completo. No se rematerializa el resultado desde inputs actuales.

## 12. SQL, seguridad y migración

Migración nueva generada con Supabase CLI: `20261027190121_ultimate_copilot_consumers.sql`. Agrega sólo el checked RPC `public.platform_ultimate_copilot`; reutiliza chat_turns/messages/interpretation_sources y columnas de provenance T2. No agrega tabla de Branch/conversación, no modifica migraciones anteriores ni hace backfill/historical repair.

Función `SECURITY DEFINER SET search_path=pg_catalog`, nombres calificados, execute revocado a PUBLIC/anon/authenticated y concedido sólo a service_role; API/checked RPC validan miembro activo confirmado, tenant/DDA, Case y Run publicada. Advisory lock por turno para intent/replay; original receipts/sources no se reescriben. Viewer puede consultar historial autorizado en readonly, pero no crear turnos. Refs/paths y parent bindings proceden de artifacts autorizados, no de paths arbitrarios del cliente.

Se aplicó únicamente sobre PostgreSQL owned desechable del harness, después del catálogo completo hasta T9. E10/W10 ejercitaron API→SQL→Storage→worker reales. No se aplicó a Supabase remoto/producción. El ensayo integral fresh/upgrade/restore y las suites completas de seguridad/migración de T11 **no se presentan como ejecutados aquí**.

Supabase advisors: exit 0, mismos dos WARN del baseline, sin hallazgos nuevos: `public.profiles.tenant_read` (`auth_rls_initplan`) y `dation_private.workspace_id` (`function_search_path_mutable`). [Resultado](evidence/advisors.json), [comando/entorno owned](evidence/advisors-command.json). No se amplió alcance para reparar deuda ajena a T10.

## 13. Responsive, accesibilidad y estados

W10 real en **1440×900, 1024×768, 768×1024, 375×812 y 320×640**, ambos nodos. `body.scrollWidth` no supera viewport; tablas/charts usan scroll interno controlado. Hero/CTA/export/details/IA/review permanecen operables. Mismo Inter, surfaces, accent, borders y radio nativos; medidas publicadas en el JSON de W10, no supuestas por CSS.

Teclado real: alternativa de charts, tabs/arrow navigation, drawer/modal trapFocus, Escape y retorno al activador, historial/disclosures y launcher. Semántica/labels/selected states, `aria-busy`, errores explícitos y estados vacío/loading verificados. Foco 3 px, visible dentro de viewport y sin elemento que lo tape a 375 px. Zoom200% y reduced motion comprobados; no se agregó motion decorativo ni flashes rectangulares sobre cards redondeadas.

Contraste medido en 59 muestras renderizadas: mínimo de texto normal **10,5766:1**, mínimo de gráfico/texto grande **3,3572:1**, por encima de 4,5:1 y 3:1 respectivamente. [Mediciones y foco](evidence/w10/contrast-focus.json). No se afirma certificación universal WCAG a partir de esas muestras.

Stress acotado: Case Unicode de 120 caracteres y IDs Order/Resource de 128 aceptados por APIs reales; NULL/cero, costos decimales grandes, un Trip, listas vacías/no-match, error de retrieval y gráfico denso de 120 nodos. La prueba densa es **renderer-only**, no se presenta como un nuevo resultado de negocio certificado ni benchmark PERF11. Los fixtures de alternativas/costo desconocido provienen de outputs T7/T9, sin editar engines ni publicar toggles de demo en producto.

## 14. Performance y lazy loading

Carga inicial: package liviano (summary/metrics/review descriptivo) y primary visual. Ningún request inicial a Details, entity evidence, contexto/turnos IA, alternatives detail o verificación pesada de Review/artifacts. Details, entidades, IA, historial e integrity check se solicitan por acción del usuario; W10 registra requests y lo afirma, incluyendo espera de publicación.

Medidas del fixture W10 final (UTF-8 JSON canónico sin whitespace): D1 package **26.405 bytes**, D2 **22.476 bytes**. Son muestras medidas, no el benchmark de escala de T11. Los límites vigentes siguen siendo package512KiB, visual inline256KiB, chunks1MiB/100entidades, APIpage100, selected entity50KiB, prompt24KiB y claims12KiB; UIpage25 e historial20. Si una entidad/ref/contexto excede su frontera, se rechaza o se declara fallback, nunca se devuelve evidencia truncada como completa.

No se precomputan nuevos escenarios, no se ejecuta solver al abrir Alternatives/Compare y no se descarga full JSON hasta pedirlo. `abort`/generation evitan que respuestas viejas contaminen nueva selección.

## 15. Consistencia cruzada con Run real

E10 crea Runs mediante admission/SQL/worker/Storage reales y lee los callers de las superficies; no compara seis mocks derivados de un objeto fabricado. W10 agrega render real, seis tabs, drawer, descargas de UI, Copilot y Review sobre otro fixture real. Dentro de cada ejecución todos conservan su mismo Run/FP y hechos certificados.

| Ejecución | D1 Run / fingerprint | D2 Run / fingerprint | Resultado |
|---|---|---|---|
| E10 | `9c7323b8-428d-4339-bd26-77e1e653caff` / `cb6761054418ec0a5dce8a6ad0fecb1d2e521bee1d78eb5ee7028db789b44215` | `81621d2a-7086-4b01-ac9d-d66cb557cd27` / `2ad5271ab0f8b467eb57d30b28ff6b328f8135430a67988c53ff9f7c1986201b` | PASS |
| W10 | `5feef9f2-9725-4fd6-8a16-6b9343674cc9` / `ded835f75e666dab6298e2a6a0a24ca650903601f1831f63a40ca6f068e09cbe` | `8ca4cb05-ca36-40db-aa49-ba493b6f9430` / `227a7bf642ceaa2754050f429d190bc96a43b20a963ee3c8faf114af75d1f06e` | PASS |

Evidencia: [matriz API](evidence/e10/consistency.json), [matriz browser](evidence/w10/browser-consistency.json), [Runs/publicaciones W10](evidence/w10/fixture-runs.json). Se verifican valores, rows/allocations/costo una vez, tiempos/status, payload/provenance de IA/review y materialización de artifacts además del fingerprint. D2 conserva el parent A tras aprobar D1 B.

## 16. QA ejecutado

[Test ledger reproducible](test-ledger.json): comandos exactos desde `backend/`, variables limpiadas, runtimes, conteos, duración, logs y hashes. Python3.13.5, OR-Tools9.15.6755, Node24.19.0, Playwright1.63.0, Chromium151.0.7922.173, PostgreSQL17-alpine owned y SupabaseCLI2.122.0. Credenciales de Supabase/LLM/GCP remotos vacías en las shells de QA; ninguna API de producción usada como sandbox.

| Suite | PASS | Fail / Error / Skip | Duración | Evidencia |
|---|---:|---|---:|---|
| B-PY | 681 | 0 / 0 / 0 | 39,617 s | [log](evidence/b-py.log) |
| B-NODE | 153 | 0 / 0 / 0 | 0,278 s | [log](evidence/b-node.log) |
| U10 Python | 25 | 0 / 0 / 0 | 1,237 s | [log](evidence/u10-python.log) |
| U10 Node | 16 | 0 / 0 / 0 | 0,136 s | [log](evidence/u10-node.log) |
| E10 | 9 | 0 / 0 / 0 | 37,249 s | [log](evidence/e10.log) |
| W10 | 10 | 0 / 0 / 0 | 110,173 s | [log](evidence/w10.log) |
| B-FOCUS | 9 | 0 / 0 / 0 | 63,914 s | [log](evidence/b-focus.log) |

U10 está incluido en B-PY/B-NODE: no sumar conteos como tests únicos. Node usa `--experimental-test-isolation=none`, runner ya establecido para contar assertions reales en este entorno; el modo aislado por defecto reporta archivos y no sustituye esta evidencia. No se deshabilitaron tests ni se añadieron skips/exenciones.

E10 incluye permisos/tenant/Viewer, context/intent replay, approval actual/stale, full JSON faltante/corrupto y parent histórico. W10 incluye lazy loading, cinco viewports, teclado/foco, schema desconocido/recovery, race de entidad, zoom/reduced motion/labels largos, contraste, historial original, espera de publicación y modo/pregunta ligados durante respuesta.

IA se certificó con proveedor stub determinístico/adversario y fallback real sin proveedor configurado, no con un LLM live. Se probaron métricas/reasons/alternativas inventados, fake what-if, entidad de otra Run, contexto stale, error y respuesta malformada.

No se ejecutaron B-BROWSER/B-SQL/B-E2E completos como fase T11 ni PERF11/restore. La cobertura requerida para T10 es la tabla anterior más advisor/preservación focal; no se declara QA global de release.

## 17. R-cases aplicables

| Caso | Resultado T10 y evidencia/límite |
|---|---|
| R1 | PASS: CSV certificado reconoce costo consolidado una vez y mantiene allocations; U10/E10 y baseline assembler B-PY. |
| R2 | PASS: utilización ponderada ya certificada se muestra sin media local; U10 Node/fixtures y B-PY. |
| R3 | PASS: cortes distintos, dimensión publicada e índice de entidades sin usar labels; U10 Python/Node. |
| R4 | PASS: NULL distinto de cero en export/UI/context; fixture de costo desconocido y precisión decimal, U10. |
| R5 | PASS: sin causalidad desde costo observado; reason scope/facts verificados, fallback ante causa no probada, U10. |
| R6 | PASS: schema/header/binding desconocido o en conflicto falla seguro; U10/W10, guards legacy. |
| R7 | PASS en consumer: sólo alternativas publicadas, comparaciones/deltas y estados 0–3/budget sin solver; U10 y contratos/producer baseline incluidos en B-PY. No se afirma haber generado tres alternativas nuevas en E10. |
| R8 | PASS en consumer: binding/bytes/refs y export íntegro; corrupción/ausencia falla explícita E10. DAG/canonicalización de producers preservados en B-PY. |
| R9 | PASS: valores D2 exactos en visual/detalle/export/context; U10/E10/W10, sin fórmula frontend. |
| R10 | PASS: own end exclusivo, external sin retorno, un día y beyond-horizon; U10 Node y baseline T9 B-PY. |
| R11 | PASS: todos los IDs/status/NULL preservados; U10 y baseline D2 B-PY. |
| R12 | PASS: expected compliance y strict ON_TIME conservan definiciones distintas; lectura directa certificada, U10/B-PY. |
| R13 | PASS en presentación: concurrencia visible por Trip sin asignar unidades/placas ni cambiar recurso/fechas; U10 Node. El witness y factibilidad de dos unidades permanecen en T9/B-PY. |
| R14 | PASS: entidad mismo Run/FP, response tardía descartada, intent distinto409 y replay original; U10/E10/W10. |
| R15 | PASS: proveedor sólo selecciona refs permitidas, ataques/malformed/failure fallan a fallback sin nueva matemática; U10/E10. |
| R16 | PASS en frontera tocada: review separado de permisos, stale POST rechazado y replay con awareness actual; E10/B-FOCUS, guards T8 intactos. |
| R17 | PASS para budgets/lazy/paging/full JSON de T10: U10/E10/W10. El benchmark completo de escala PERF11 no fue ejecutado. |
| R18 | PASS para compatibilidad del consumer: espera publicación atómica sin prefetch y maneja retry/error sin estado parcial, W10. Fault matrix completa de crashes/leases de T8/T9 preservada; no se afirma repetirla aquí. |

## 18. Legacy compatibility y evidencia visual

Dashboards/readers v1, comparative service v1, export/chat/explain existentes, historia, deep links, filtros, shell y roles conservados. Las ramas Ultimate son explícitas; no se alimenta un reader v1 con package nuevo. B-PY/B-NODE/B-FOCUS cubren callers legacy y selección aprobada/Nueva corrida.

Comparación adicional reproducible contra copia separada **HEAD + overlay post-T9**, sin checkout/reset del repositorio. Mismos fixtures, estado, theme, reloj fijo, viewport y cursor fuera de filas hover. Los **10 pares legacy D1/D2 × cinco tamaños tienen 0 píxeles distintos y mismos estilos computados**. [Resultado](evidence/legacy-preservation/comparison.json), [harness](evidence/compare_legacy.py), capturas `post-t9-*`/`candidate-*` en el mismo directorio de evidencia.

Para las nuevas Runs, W10 levanta además API baseline desde la copia congelada, sobre la misma DB owned/Run: diez pares `d1|d2-{size}-before-t10.png` / `d1|d2-{size}.png`. La diferencia intencional es pasar de placeholder T9 a funcionalidad T10; Hero/tokens/controls siguen la familia aprobada. No se presenta igualdad de píxeles entre placeholder y nuevo dashboard. [Identidad del baseline API](evidence/baseline-api-source.json).

## 19. UI Preservation Gate

| Check | Estado | Evidencia |
|---|---|---|
| UI-P1 referencia actual | PASS | Inspección focal, capturas antes de modificar, baseline congelado y paths/tokens reales registrados. |
| UI-P2 integración nativa | PASS | Hero/toolbar/KPI/card/buttons/launcher/focus reutilizados; W10 real y comparación de estilos. |
| UI-P3 reuse/tokens | PASS | Renderers justificados por proyecciones nuevas; CSS acotado, sin framework/tokens/assets globales modificados. |
| UI-P4 visual/responsive | PASS | Pares comparables nuevos, 10 pares legacy idénticos, cinco viewports y no overflow de body. |
| UI-P5 accesibilidad/interacción | PASS | W10 teclado/foco/Escape/retorno/labels/contraste/zoom/reduced motion, lista accesible de charts y errores recuperables. |
| UI-P6 Skills trazables | PASS | Ledger con hashes, aplicación/evidencia, omisiones por precedencia y dependencias reales; sin decisiones funcionales delegadas a una Skill. |

## 20. Desviaciones y riesgos acotados

No hubo desviación semántica ni dato faltante que exigiera modificar producers. Capacidad de recursos no usados, estado de análisis y hechos heredados D1 se localizaron en evidencia ya publicada y se recuperan desde allí. No se añadieron fórmulas para completar campos.

Adaptaciones de ejecución: flag Node para assertions reales; copia congelada para comparar API baseline; captura espera decodificación de imágenes y cursor neutral; páginas independientes por viewport para evitar crash de Chromium durante capturas repetidas. La interrupción ambiental y los fallos transitorios del harness se corrigieron/revalidaron; los resultados finales no tienen fallos perdonados. No se conservaron como deuda de producto ni se eliminó cobertura para obtener PASS.

Search/filter/sort operan sobre página actual con scope visible; el dataset completo se obtiene por paginación/export, no se promete búsqueda global. Provider offline no prueba calidad de prosa de un modelo live; sí prueba los guards y el fallback que evitan inventar negocio. El JSON completo puede fallar si se pierde/corrompe cualquier artifact propio o upstream: es un error explícito deliberado, no un archivo incompleto aparentemente válido.

Los límites de payload/contexto están ejercitados; el estudio integral de volumen/performance, restore, matriz completa de seguridad y readiness de release pertenecen a T11/T12 y no reciben PASS por anticipado. No se afirma despliegue ni activación pública: flags/metadata de rollout conservados, ningún pipeline disparado por esta tarea.

## 21. Rollback y estado del entorno

Checkpoint post-T9 más [preimágenes](preservation.json) y manifiesto permiten revertir **sólo este delta** en una revisión posterior, conservando cambios anteriores. No ejecutar reset/clean ni borrar artifacts/historial. El nuevo montaje puede retirarse sin reensamblar Runs; los readers y exports históricos siguen disponibles. La función SQL aditiva puede quedar sin callers durante rollback de aplicación: no contiene migración de datos ni obliga a reescribir provenance ya guardada. Cualquier retirada futura debe preservar los recibos existentes.

Los contenedores owned de esta tarea terminaron detenidos/removidos; comprobación final de `docker ps --filter label=dation.qa.owner=codex-dation` sin contenedores activos. No se tocaron recursos ajenos. `git diff --check` exit0, HEAD/branch/índice conservados; manifest fuente verificado después de QA. No hubo conexión/escritura en producción ni cambios de infraestructura o configuración global.

## 22. Gate evaluation

| Gate | Estado en T10 | Fundamento y alcance |
|---|---|---|
| G-A alcance | PASS | Autorización exclusiva T10, delta28 sobre checkpoint, plan preservado; sin T11/push/deploy. |
| G-C contract | PASS | Dos schemas explícitos, bind Run/FP y entity; unknown seguro, ABI/producers sin cambios. |
| G-D datos | PASS, frontera T10 | Históricos inmutables, RPC aditivo ensayado en catálogo owned hasta T9, provenance original y export completo. Restore integral reservado a T11. |
| G-E engine | PASS, preservación | Engines/assemblers/matemáticas intactos; B-PY verde, consumers no deciden ni recalculan. |
| G-R result | PASS | Consistencia entre superficies con API/browser reales; NULL/costos/dates/refs correctos, R-cases aplicables. |
| G-L lineage | PASS, frontera T10 | Parent exacto aun con nueva aprobación, replay sin efectos y review stale rechazado; SQL T8/T9 intacto. |
| G-S security | PASS, frontera T10 | Tenant/Viewer/context/paths/refs y checked RPC negativos; ningún permiso desde texto/IA. Advisors sin nuevos hallazgos. |
| G-P performance | PASS, budgets T10 | Lazy medido, páginas/entidades/prompts acotados y fallos explícitos. PERF11 no ejecutado. |
| G-UI preservación/Skills | PASS | UI-P1–UI-P6 completos y evidencia browser/legacy comparable. |
| G-ENV entorno | PASS | Runtime recuperado, DB/API/worker/browser owned, todas las suites exigidas con tests reales y cero skips. |
| G-B deuda histórica | PASS, suites T10 | Ninguna exención, test deshabilitado, skip o regresión nueva en la cobertura exigida. |
| G-REL release | NO APLICA / NO AUTORIZADO | T11/T12 no ejecutados. Este GO no autoriza release ni certifica producción. |

No queda una STOP CONDITION abierta de T10. La autorización siguiente debe solicitarse por separado.

**GO — T10 completado. T11 puede ser solicitado.**
