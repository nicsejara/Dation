# T5 — Decision Graph + Readiness + Contextual Navigation

Fecha: 27/10/2026, America/Buenos_Aires. Los logs conservan UTC. Ejecución limitada a T5 según el [Master Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), F01–F23, §3.1, T5, §22 y §23; [autorización original](evidence/T5-user-request.txt) y [reanudación](evidence/T5-resume-request.txt). Baseline inmediato: [T4 aprobado](../t4/t4-execution-report.md).

El backend resuelve el graph Ultimate y entrega estados, freshness, fallos técnicos y acciones por permiso/capacidad. Map, Config, contexto, Home y Decision Center consumen esa proyección. D1 puede estar READY mientras su runtime permanece indisponible. D2 requiere el D1 aprobado vigente y no solicita un CSV adicional estándar. La fase no implementa ni ejecuta engines, admission, approval ni invalidación persistente nuevos.

## Baseline

- Branch `main`; HEAD inicial y último verificado: `ef997235a30251fbf7ae53690ed738092ee973d8`. No se hizo fetch, staging, commit, push ni deploy. `origin/main` se informa como referencia local, sin afirmar una comprobación remota nueva.
- T4 aprobado: B-PY 498, B-NODE 134, U4 25 incluidos en B-PY, S4 30 y W4 8. Se reutiliza ese baseline; no se reejecutaron T0–T4 ni Browser/E2E completos.
- Antes del primer trabajo T5 se copiaron **627 archivos pendientes, 32.266.454 bytes**, con hashes y patch tracked. Se verificaron las **147 entradas** del manifest T4. El árbol ya estaba modificado por las fases anteriores.
- Tras recuperar el entorno, esos 627 archivos de checkpoint y las 147 entradas T4 se verificaron de nuevo. La única extensión de un archivo pendiente previa al STOP era el registro del router en `backend/app/platform/routes.py`; además había exactamente siete archivos nuevos T5. No faltó ningún componente de implementación conocido.
- El diff completo T5 comprende **29 archivos de implementación, migración y tests: 15 nuevos y 14 modificados**. Se compara contra el checkpoint post-T4 y contra HEAD para archivos previamente limpios. Este reporte, ledgers y evidencia son documentación adicional.

Evidencia: [recovery verification](evidence/recovery-verification.json), [estado inicial](evidence/initial-state.json), [scope diff](scope-diff.json), [patch T5](evidence/t5-changes.patch), [preservación](preservation.json), [integridad](artifact-integrity.json). Los reportes/manifests previos permanecen intactos; las preimágenes necesarias para resolver sus hashes se preservan en la evidencia T5.

## Estado recuperado

El STOP anterior fue **STOP ENV**, por pérdida del executor. No se había aprobado la integración UI ni las suites S5/W5. La disponibilidad del servicio de entorno y la del executor se distinguieron: durante la caída el primero informó `starting`, pero el executor rechazó incluso la espera. No se atribuyó ese bloqueo a un contrato funcional ni se inventó un reporte guardado durante la indisponibilidad.

En la recuperación se comprobó `/workspace/Dation`, HEAD/branch/status, staging vacío, checkpoint y evidencia U5, antes de modificar. Se identificaron ocho archivos parciales, coincidentes con los cambios aplicados antes del STOP, y se preservaron sus bytes en `evidence/pre-stop/`. Python 3.13.5, Node 24.19.0, Docker 28.4.0, la imagen PostgreSQL 17, Chromium 151.0.7922.173 y ambos runners quedaron disponibles. No hubo reset, clean, checkout destructivo ni descarte de archivos.

## Work completed before STOP ENV

| Componente recuperado | Estado al reanudar |
|---|---|
| `definitions.py` | Registry tipado de dos Decisions y dependency closure; preservado |
| `requirements.py` | Requirements por contrato y read identities; preservado |
| `graph.py` | Resolver puro de ocho estados y dimensiones ortogonales; preservado |
| `ultimate_graph_routes.py` | Endpoints read/config-context/history; preservados |
| `decision_graph_service.py` | Orquestación inicial del snapshot y proyección; reutilizada y extendida para callers |
| Migración `20261027033128_ultimate_decision_graph.sql` | Snapshot SQL inicial y Definition exportada; todavía sin validación S5 |
| `test_ultimate_graph.py` | **23 escenarios U5 PASS**, log conservado |
| `platform/routes.py` | Registro del router T5 |

El log [U5 pre-STOP](evidence/U5-first.log) y su SHA256 son verificables. Las Definitions, requirements, resolver y tests U5 no se reimplementaron. Los 23 casos volvieron a ejecutarse incluidos en B-PY, suite obligatoria; no se lanzó otra ejecución standalone U5 sólo por rutina.

## Work completed after recovery

1. Se registró y preservó el estado recuperado, sin reconstruir T5 desde cero.
2. Se validó el SQL/API en sandbox y se corrigió la referencia inicial a `error`: la columna real es `error_message`. Se completaron proyecciones de actores y conteos históricos sin alterar rows anteriores.
3. Se conectaron los callers Case/context/Home/Center al mismo servicio; se cubrió también Home attention para Cases fuera de los tres recientes.
4. Se integraron Map, selector, responsables nativos, Case Data, Config contextual e historial explícito, con disposición de scopes y protección frente a respuestas atrasadas.
5. Se agregaron S5, W5 y tests Node de la nueva navegación; se ajustó un test focal de creación T3 al nuevo destino Map.
6. Se ejecutaron las suites autorizadas y comparaciones visuales acotadas, conservando los intentos intermedios y la evidencia final por separado.

## Skills utilizadas

Se mantuvo la Execution Skills Policy: arquitectura → comportamiento existente → patrones de Dation → guía de Skill. El [ledger](skills-ledger.json) identifica fuente/SHA, lectura, aplicación, verificación y recomendaciones omitidas. Se reutilizaron las lecturas pertinentes ya realizadas en esta conversación; no se releyeron todas las Skills ni se abrió una nueva auditoría.

| Skill | Aplicación T5 | Evidencia |
|---|---|---|
| `design-system` | Hero/cards/buttons/selectors/estados nativos; CSS exclusivamente scoped | Comparación visual de primitivas y Map legacy |
| `emil-design-eng` | Foco/Escape/retorno, scopes, feedback y reduced motion; sin motion propio | W5, B-FOCUS y tabla Before/After/Why |
| `ui-ux-pro-max` | Guía focal de navegación, formularios, accesibilidad y responsive | W5, contraste, zoom y teclado |
| `break-ui` | Nombre de Case de 120 caracteres con Unicode, vacío/uno/múltiples, 320 px y zoom 200% | Fixtures W5; sin datos comerciales reales |
| `supabase:supabase` | RPC checked, grants explícitos y snapshot privado; documentación oficial de funciones | S5 y schema boundary; migración creada con CLI 2.122.0 |
| `supabase:supabase-postgres-best-practices` | Locks workspace → Case, lectura acotada, tenant/FKs y snapshots inmutables | S5 y catálogo/ACL/RLS |
| `cloud-environment:cloud-environment-runtime` | Verificación del executor/runners/Docker local y cleanup owned | Recovery/runtime/cleanup ledgers |

No se instalaron dependencias de aplicación ni se cambiaron framework, tokens, tipografía, paleta, assets o icon family. No se invocaron generadores, improve-animations, review-animations ni auditorías generales. La guía break-ui de detenerse antes de un fix no agregó otra aprobación: la autorización vigente cubre implementación y validación T5 completas.

## Files Created

| Archivo relativo al repositorio | Función |
|---|---|
| `backend/app/domain/logistics/definitions.py` | Definitions tipadas, versión/hash y closure acíclica |
| `backend/app/domain/logistics/requirements.py` | Inputs requeridos, compatibilidad y read identities |
| `backend/app/domain/logistics/graph.py` | Autoridad pura de estados/freshness/acciones |
| `backend/app/services/decision_graph_service.py` | Snapshot/proyección compartida, Config e historial |
| `backend/app/platform/ultimate_graph_routes.py` | APIs Graph/Config/history |
| `supabase/migrations/20261027033128_ultimate_decision_graph.sql` | Snapshot de Definition y readers SQL; sin tabla de estado mutable |
| `backend/app/static/js/dispatch/cases/ultimate-decision-map.mjs` | Composición del Map/Config/history sobre el DTO del servidor |
| `backend/app/static/js/dispatch/navigation/ultimate-graph.mjs` | Vocabulario visual y adaptación de targets; sin resolver JS |
| `backend/app/static/css/ultimate-graph.css` | Layout scoped y legibilidad del CTA |
| `backend/tests/test_ultimate_graph.py` | U5: 23 escenarios puros |
| `backend/tests/test_ultimate_graph_navigation.mjs` | Tres casos Node de permisos/targets/Run explícita |
| `backend/tests/integration/test_ultimate_graph.py` | S5: API/SQL, lifecycle controlado, permisos y readers |
| `backend/tests/browser/test_ultimate_navigation.py` | W5: Map/Center/Config, navegación, permisos y responsive |
| `backend/tests/e2e/ultimate_graph_fixture.py` | Fixture owned API/PostgREST/PostgreSQL, sin engine Ultimate |
| `backend/tests/e2e/ultimate_graph_state.py` | Metadata de lifecycle explícita para tests, no productor de resultados |

## Files Modified

| Archivo | Cambio T5 |
|---|---|
| `backend/app/platform/routes.py` | Router T5 |
| `backend/app/platform/ultimate_routes.py` | Contexto con graph desde el snapshot común |
| `backend/app/platform/decision_center.py` | Enrichment de Cases Ultimate e historial por cohorte |
| `backend/app/platform/home.py` | Proyección de Cases y atención mediante graph común |
| `backend/app/static/js/dispatch/cases/decision-map.mjs` | Extensión de Hero/card actuales; comportamiento legacy por defecto preservado |
| `backend/app/static/js/dispatch/cases/ultimate-case-setup.mjs` | Crear Case → Map y entrada al Map desde contexto |
| `backend/app/static/js/dispatch/upload/ultimate-case-data.mjs` | Volver al Map y compartir su proyección de navegación |
| `backend/app/static/js/dispatch/workspace.mjs` | Routing por cohorte, hydrate seguro y scopes separados |
| `backend/app/static/js/dispatch/navigation/case-flow.mjs` | Pasos Ultimate gobernados por actions del servidor |
| `backend/app/static/js/dispatch/traceability-controller.mjs` | Reconocer el Case Ultimate activo |
| `backend/app/static/js/dispatch/traceability-ui.mjs` | Selector nativo con metadata Ultimate; sin pair legacy ficticio |
| `backend/app/static/js/platform/dda-navigation.mjs` | Breadcrumb contextual hacia Map |
| `backend/app/static/js/platform/decision-center.mjs` | Labels/estados/targets de la proyección Ultimate |
| `backend/tests/browser/test_ultimate_case_setup.py` | Focal de creación: verificar Map y regresar al contexto |

Los CSS globales que Git muestra pendientes pertenecen al baseline previo. T5 no los modifica. Tampoco modifica engines, Result Architecture, approval writers, jobs, infraestructura o configuración productiva.

## Decision Definitions

Registry controlado por release: `ULTIMATE_DECISION_GRAPH_V1`, schema `decision_graph_definition_v1`, hash canónico, snapshots inmutables en la tabla privada T2. Cada Definition declara ID/version/question/implemented/applicability/dependencies/required approvals/inputs/read set/variables/constraints/objectives/outputs/evidence/downstream contract. Closure calculada y validada contra ciclos/dependencias desconocidas.

| ID técnico preservado | Label de producto | Dependencia |
|---|---|---|
| `logistics_assignment` | Transport Plan | Ninguna |
| `logistics_scheduling` | Day Scheduling | D1 aprobado vigente |

Se conserva el binding estructural T3 `ULTIMATE_FOUNDATION_V1`, mediante compatibilidad explícita con esta versión de Definition. El snapshot estructural anterior y las Model Versions ya publicadas no se reescriben ni rebindan. La respuesta distingue `binding_version`, `graph_version` y `definition_hash`; no busca una Definition arbitraria desde labels o cliente. No hay editor visual, Branch entity ni D3 universal. El graph productivo sólo contiene D1 y D2; COMING_SOON se prueba con una Definition controlada de test, sin publicar una funcionalidad futura.

## Graph Resolver

`resolve_case_graph(context, model, pack, run_history, responsibilities, runtime_capabilities)` es la autoridad pura de negocio. El servicio obtiene un snapshot SQL autorizado y entrega esa misma proyección a todos los callers. El frontend adapta nombres visuales y targets; no reconstruye dependencies, approvals, readiness, freshness, applicability o runtime.

El resolver recorre dependencies topológicamente; el orden del registry no decide habilitación. Una aprobación se considera vigente por su autoridad persistida, ausencia de supersession, resultado publicado y read set/contexto frescos. No se usa una Run histórica ni `created_at` para reemplazar una aprobación vigente. Múltiples candidatos activos sin autoridad inequívoca se exponen como fallo técnico y cierran acciones; no se elige uno por heurística.

Las lecturas no reparan `state_json`, mueven pointers, admiten Runs ni escriben approvals. La selección de una Run histórica es una referencia separada de la proyección actual.

## Node State Semantics

| Estado exacto | Semántica T5 |
|---|---|
| LOCKED | Falta upstream/aprobación requerida; D2 antes de D1 aprobado vigente |
| DATA_REQUIRED | Dependencies satisfechas pero faltan inputs publicados/compatibles o datos requeridos por su objetivo |
| READY | Requisitos de negocio/datos satisfechos; no afirma permiso ni runtime |
| IN_PROGRESS | Run vigente QUEUED/RUNNING con contexto fresco |
| COMPLETED | Resultado de Run vigente publicado y pendiente de aprobación |
| APPROVED | Resultado actual aprobado, publicado y fresco |
| COMING_SOON | Definition reconocida sin implementación; ningún CTA ejecutable |
| NOT_APPLICABLE | D2 cuando el D1 aprobado tiene cero Trips según su contrato; no se crea Run vacía |

Freshness, `technical_failure`, runtime y permisos/actions son campos separados. Un fallo técnico no se transforma en falta de datos. Viewer/archived/Owner pendiente no cambian artificialmente READY a LOCKED. Trip count desconocido no se convierte en cero ni en una Run vacía.

## Requirements / Read Sets

D1 requiere `transport_demand` y `transport_resources` publicados, con contrato recompilado desde su Model Version, normalizer compatible y records válidos. No alcanza con un candidato READY de upload. La validación de campos permanece en el descriptor T4. Disponibilidad desconocida o costo requerido por un objetivo económico aparecen como requirements; no se rellenan con infinito/cero/confirmado.

Read set D1: demanda, recursos, Model, horizonte, Case Policy y Node Policy. La identidad de un slot incluye canonical hash, contract hash y normalizer. Read set D2: el ID exacto del D1 aprobado vigente, horizonte y Node Policy. No consume todo el manifest sólo porque cambió una Pack Version.

D2 no vuelve a solicitar Demand/Resources ni otro CSV estándar: ready date, due date y distancia ya pertenecen al input D1. El fixture de enrichment irrelevante confirma que un slot fuera del read set no invalida D1/D2. No se agregó un uploader o dataset type de enrichment futuro.

## Freshness

Se comparan las referencias congeladas de la Run, Definition hash, binding de Model/contexto y upstream exacto con el snapshot actual. Un cambio de demanda/recursos consumidos deja la aprobación histórica intacta y cambia la proyección vigente a stale; D2 vuelve a LOCKED si D1 dejó de estar APPROVED actual.

Una nueva Pack Version con las mismas interpretaciones consumidas no invalida por su número o ID global. Enrichment irrelevante conserva las identidades de lectura. Aprobar una Run vieja o abrir su deep link no la vuelve current. El histórico conserva IDs, actors, timestamps, supersession y upstream.

S5 usa metadata controlada de lifecycle sobre SQL real. Para reemplazos se observan los triggers ya existentes del baseline; T5 no incorpora un nuevo writer ni la closure de invalidación persistente T8. Las publicaciones Pack T4 no borran Runs/approvals.

## SQL/API Snapshot

La migración T5 sólo agrega una fila versionada de Definition y dos funciones. No agrega tabla mutable de node state, columnas o triggers. El RPC SECURITY DEFINER fija `search_path=pg_catalog`, revoca ejecución pública y sólo admite service role. Revalida membership, tenant, DDA, Case, node y Run; usa locks workspace → Case para obtener el snapshot compatible con los writers existentes.

El reader devuelve contexto/Pack actual, entries y provenance acotadas, candidatos vigentes y metadata publicada/actores. El historial se pagina, separado del estado actual. `cohort` es una lectura interna autorizada para clasificar candidatos Home fuera de los tres recientes; no acepta Definitions ni estados del cliente. La proyección de resultado publicado usa metadata durable T2 y CORE READY, no un engine ni descarga de evidencia pesada.

Se conserva la inmutabilidad de Definitions/Model/Pack/Run pinning. El servicio compara JSON/hash de Definition en DB contra el registry de código y falla cerrado ante divergencia. [Schema boundary](evidence/schema-boundary.json): cinco filas legacy, Definitions anteriores, catálogo, ACL/RLS/defaults y funciones existentes permanecieron idénticos; flags foundation/Pack siguieron cerrados por defecto al aplicar la migración. Sólo se aplicó en sandbox owned.

Las rutas son GET `.../logistics-cases/{case_id}/graph`, `.../graph/config/{node_id}` y `.../graph/history/{node_id}`. Config reobtiene snapshot y verifica elegibilidad actual. Es contexto de configuración, no admission ni autorización para una escritura futura: T8 deberá revalidar bajo su transacción/locks antes de ejecutar.

## Runtime Availability

Los runtimes Ultimate T6/T9 siguen sin integrar. El servicio no anuncia ninguno disponible y `actions.execute.allowed=false`. La UI comunica esa capacidad y mantiene el botón de ejecución deshabilitado. No llama engines legacy como fallback.

Los fixtures SQL de lifecycle guardan metadata explícita marcada como fixture T5; no se presentan como outputs certificados de engine, ejecución matemática o publicación productiva. T5 no valida bytes de artifacts de resultado ni implementa el publisher/assembler T8; consume la autoridad de metadata prevista por T2.

## Decision Map UI

Se compone el Hero y renderer de cards del Map actual, estilos existentes, botones de workflow y selectores nativos de responsabilidad. El registry aporta preguntas/labels; las actions del DTO deciden targets y elegibilidad. La separación responsive, loading/error/empty, cards y shell mantienen el lenguaje vigente.

| Before | After | Why |
|---|---|---|
| El Case Ultimate se abría en setup y no tenía Map funcional | Crear/abrir Case → Map accesible incluso con Pack vacío | Representar DATA_REQUIRED sin exigir archivos para existir |
| Map legacy derivaba readiness y tenía una tercera decisión futura genérica | Map Ultimate muestra las dos Definitions y consume estados/actions backend | Evitar doble autoridad y D3 universal |
| Carga validada no habilitaba una lectura explícita de Graph | Case Data vuelve al Map y recupera su nueva proyección | Separar candidato, publicado y Decision READY |
| Responsables y controles ya aprobados en Map legacy | Se componen los mismos selectores, con cambio explícito por Admin | Conservar geometría, permisos y ausencia de autoasignación |
| Label largo comprimido por el ancho legacy del CTA | Ajuste scoped de ancho intrínseco, sin cambiar tokens | Mantener el CTA legible en una línea cuando hay espacio |
| Focus de atención genérico podía mostrarse como “siguiente” con todo aprobado | Se omite ese marcador sin autoridad específica de próxima acción | No presentar una decisión posterior inexistente |
| Respuestas atrasadas podían competir al abrir selector/historial | Versiones de request y scopes descartan respuestas anteriores | Preservar Case, selección y foco |

La evidencia incluye referencias pre-STOP, stress con nombre máximo de 120 caracteres/Unicode, seis anchos hasta 320 px, zoom 200%, reduced motion, teclado, foco no tapado, Escape/retorno y touch. Los números finales de contraste y capturas están en el ledger. Se comprobó paridad de píxeles/estilos de primitivas a cinco anchos; el Map legacy también conserva píxeles exactos a 1440/390 frente a las capturas previas al STOP. No se agregó animación propia ni se modificaron tokens globales.

## Navigation

- Case nuevo → Map → DATA_REQUIRED → Case Data → publicación → Map READY → Config D1.
- D1 COMPLETED mantiene D2 LOCKED; D1 APPROVED actual habilita Config D2 con su upstream exacto y sin CSV adicional.
- Nueva corrida D1/D2 abre su Config contextual con el mismo Case; no pasa por Upload si el Pack sigue vigente. Config sólo consulta contexto; no crea una Run.
- History pagina Runs y abre Case/node/Run explícitos. El panel de metadata histórica no sustituye todavía al renderer de resultados futuro ni cambia el graph actual.
- Selector nativo muestra el Case abierto y permite cambiar a otros, con paginación y sin recrear Case/Pack. No aparece aviso redundante de nuevo Case para el primero/único.
- Back/Forward/reload/deep links mantienen los identificadores. Scopes abortan polling/requests anteriores. W5 verifica carreras entre Cases y apertura repetida de selector.
- Se prueba salida y retorno de documento y restauración por `pageshow.persisted`. El evento persistido se ejercita explícitamente; no se afirma que Chromium haya conservado realmente el documento en BFCache en todos los recorridos.

## Home / Decision Center Integration

Case/context, Map y Center reciben el mismo `graph` y acciones. Home enriquece los tres Cases recientes y, de forma acotada, los candidatos de atención Ultimate fuera de ese grupo. Un handoff obsoleto después de cambiar un input consumido se retira de la página de atención; no se infiere D2 READY desde un latest completed histórico.

La paginación/listado y los agregados históricos del portfolio existentes se preservan. T5 no implementa invalidación persistente global T8 ni recalcula todo el portfolio en cada GET. En atención, si el total de candidatos supera la página comprobada, `total_is_upper_bound` lo declara explícitamente; el total se corrige por los candidatos descartados de esa página. Las filas devueltas sí usan la proyección actual. No se abrió un rediseño de Home ni una nueva jerarquía de navegación.

Center representa labels/estados Ultimate y navega mediante sus targets. Los readers legacy siguen por su cohorte y conservan sus URLs/semántica; los bindings sintéticos T2 sin contexto T3 no se convierten en un workflow ejecutable.

## Legacy Compatibility

Se preservan navegación D1/D2 legacy, Orders/Fleet, Runs/approvals históricos, Home attention por Owner, Case archive, links directos, roles y polling disposal. No se convierte un Case viejo ni se modifica su pair. La prueba B-FOCUS conserva explícitamente la preferencia por una aprobación sobre una candidata posterior.

La asignación de responsables usa el RPC actual; no se concede ownership desde Operating Role, labels o frontend. Viewer/archived siguen readonly. La presencia de un Owner elegible y los permisos son dimensiones de acción separadas del estado de negocio. El test focal de creación T3 verifica el destino nuevo Map y luego vuelve al contexto guardado, preservando el Case sin CSV y su hash al recargar.

## Tests

Los resultados finales, comandos, timestamps, duración, exit code y hashes de logs se consolidan en [test ledger](test-ledger.json) y [command ledger](command-ledger.json). U5 está incluido en B-PY; el log pre-STOP permanece como evidencia independiente de recuperación.

| Suite | Tests | Resultado | Failures / errors / skips |
|---|---:|---|---|
| B-PY | 521 | PASS | 0 / 0 / 0 |
| U5, incluido en B-PY | 23 | PASS | 0 / 0 / 0 |
| B-NODE | 137 | PASS | 0 / 0 / 0 |
| S5 | 19 | PASS | 0 / 0 / 0 |
| W5, última ejecución | 10 | PASS | 0 / 0 / 0 |
| B-FOCUS | 9 | PASS | 0 / 0 / 0 |
| Focal creación Case sin CSV | 1 | PASS | 0 / 0 / 0 |

La superficie final midió **43 elementos de texto**, contraste mínimo **5,429:1**, sin fallos ni overflow horizontal en los seis anchos. [Contraste](evidence/browser/contrast.json), [responsive](evidence/browser/responsive.json), [foco](evidence/browser/focus.json), [Map 1440 px](evidence/browser/map-1440.png), [Map 390 px](evidence/browser/map-390.png), [paridad legacy](evidence/legacy-map-parity/parity.json).

Los intentos intermedios se conservan como tales: import/cwd/PYTHONPATH del runner, falta de contexto `window` en el nuevo test Node, una corrida B-PY interrumpida por restricción de loopback, fixtures sin actor/mensaje exigidos, parámetro incorrecto de URL del test Center y el reader SQL inicial con nombre de columna incorrecto. No se convierten imports fallidos, cero casos o suites interrumpidas en PASS. Tampoco se relajaron constraints, permisos o assertions para acomodar fixtures.

La cobertura S5 incluye Case vacío/candidato/demanda parcial/Pack completo, runtime cerrado, lifecycle controlado, D1 aprobado para D2, tenant/Viewer/archived/Owner, autoridad histórica, respuesta de Config pura, actores/upstream/counts tras supersession, immutable Definitions y coherencia Home/Center/contexto. U5 cubre los ocho estados, ciclos, requirements exactos, read sets, cambios relevantes/irrelevantes y unknowns.

W5 cubre los recorridos UI completos, historial, nueva corrida, Case switch, Back/Forward/reload/deep links, permisos, selección nativa de Data Owner, carreras, Center, responsive/contraste/foco/zoom/touch. B-FOCUS verifica los consumers legacy afectados. No se ejecutaron Browser/E2E completos por rutina, ni suites de engines/assembler futuros. El último ajuste de etiqueta afecta sólo la vista Ultimate y W5: [reuse de QA](evidence/qa-reuse.json) documenta qué se repitió y qué consumidores conservaron sus bytes.

## Deviations

1. La reanudación no reinició T5. Se reutilizaron los ocho archivos parciales, el checkpoint y U5. El SQL se corrigió tras un fallo concreto S5; el servicio se extendió para los callers pendientes.
2. Se incorporó un módulo de composición Ultimate para evitar ejecutar la lógica de readiness legacy en la cohorte nueva. Reutiliza el renderer/patrones existentes; no introduce un segundo resolver frontend ni framework.
3. La compatibilidad entre el binding estructural T3 y la Definition T5 es explícita y versionada. No se reescribe la Model Version publicada ni se acepta “latest definition” arbitraria.
4. Los helpers de lifecycle son fixtures de metadata; no una implementación de D1/D2, Result Assembler o publisher. Los productores y la admission permanecen para fases posteriores.
5. La prueba de BFCache distingue retorno real de documento de la cobertura explícita del handler `pageshow.persisted`. No se presenta una simulación del evento como evidencia de uso efectivo del cache de Chrome.

## Risks

- **Release pendiente:** migración y capacidades sólo se probaron en entornos owned locales. No se accedió ni modificó producción; T11/T12 siguen pendientes.
- **Ejecución posterior:** Config es un shell/contexto y el runtime/admission permanecen cerrados. La selección histórica ofrece metadata; no se declara completo un renderer de resultados futuro.
- **Freshness proyectada:** T5 no escribe la invalidación global T8. Los agregados/filters históricos del portfolio se mantienen y la atención acotada declara cuándo su total es un límite superior. No se afirma consistencia global de counters nuevos de graph aún no implementados.
- **Historia ambigua:** múltiples candidatos activos sin autoridad inequívoca cierran acciones y muestran fallo técnico; no se resuelve por timestamp.
- **Bounded reads:** inputs/provenance vienen de T4, historial se pagina y el snapshot limita candidatos activos. No se afirma un benchmark de carga productiva ni una auditoría integral de performance.
- **Estado Git:** se conserva trabajo T0–T5 local sin staging/commit. El diff/manifest T5 permite revisarlo sin atribuirle todos los cambios pendientes.

## Rollback

Conservar readers/routing por cohorte e IDs históricos. Cerrar la entrada nueva mediante el procedimiento de release autorizado, sin borrar Model/Pack/Run/Definition ni modificar aprobaciones. Las APIs de lectura y links históricos deben conservarse. No hacer down migration destructiva ni usar un engine legacy como compensación. No se ejecutó rollback o cambio de flags productivo en esta fase.

## Gate Evaluation

| Gate | Estado T5 | Evidencia / límite |
|---|---|---|
| G-A — Alcance | PASS | Recuperación demostrada, 29 archivos, sin auditoría general, producción o T6 |
| G-C — Contract | PASS | Definitions versionadas/hash-linked, ocho estados, requirements/read sets y U5/S5 |
| G-D — Datos | PASS | Migración aditiva local, snapshots previos y cinco rows legacy intactos, sin tabla mutable de node state |
| G-E — Engine | N/A nuevo engine | Sin implementación/ejecución Ultimate; runtimes/admission cerrados |
| G-R — Result | N/A nuevo package | Sólo lectura de metadata publicada; sin assembler, métricas nuevas o certificación ficticia |
| G-L — Lineage | PASS en T5 | Approval current, freshness proyectada, Run histórica explícita y upstream exacto; sin closure persistente T8 |
| G-S — Security | PASS en sandbox | Tenant/member/DDA/node/Run, grants/RLS, Viewer/Owner/archived y lectura sin efectos |
| G-P — Performance | PASS en alcance acotado | Historial/picker paginados, lectura de evidencia pesada evitada, concurrencia/enrichment acotados; no benchmark productivo |
| G-UI — Preservación / Skills | PASS | Renderer/selectores nativos, paridad exacta legacy/primitivas, W5/B-FOCUS, contraste/foco/zoom/touch |
| G-ENV — Entorno | PASS tras recuperación | Runners disponibles, suites con casos positivos/sin skips, fixtures owned y cleanup |
| G-B — Baseline | Preservado | Sin nuevas regresiones observadas en suites exigidas/focales; reportes T0–T4 no reescritos |
| G-REL — Release | NOT RUN | No autorizado; sin commit, push, deploy, migración o flags productivos |

Condiciones STOP de T5 evaluadas sobre el candidato final:

| Condición | Resultado |
|---|---|
| Frontend/backend difieren o UI infiere graph | No observado; DTO común, rendering y targets del servidor |
| D2 READY sin D1 aprobado actual | Rechazado; COMPLETED y aprobación stale/histórica mantienen LOCKED |
| D2 exige CSV adicional estándar | No; required inputs D2 vacíos y upstream exacto |
| Historical latest sustituye approved current | No; approval/lineage gobiernan, `created_at` sólo ordena history para mostrar |
| Enrichment irrelevante invalida D1 | No; identidad limitada al read set probado |
| Case cambia al recuperar Config o nueva corrida fuerza Upload | No observado en W5/Node/B-FOCUS |
| Future node ejecutable o runtime inexistente disponible | No; graph productivo de dos nodos y execute=false |
| Back/Forward pierde Case/Run o respuestas anteriores ganan | No observado; W5 incluye scopes, races y selector repetido |
| Legacy navigation se rompe | No observado; B-FOCUS, Node y paridad de Map exacta |
| T5 requiere implementar D1/T6 para funcionar | No; fixtures explícitas de lifecycle, sin solver nuevo |

No queda una STOP CONDITION abierta en el alcance T5. El bloqueo anterior de entorno se resolvió y su trabajo se preservó. La [verificación final](evidence/final-state.json) y [artifact manifest](artifact-integrity.json) registran el estado revisable. [Cleanup](evidence/cleanup.json): sin contenedores owned T5 pendientes, sin detener recursos ajenos o el daemon.

## FINAL DECISION

**GO — T5 completado. T6 puede ser solicitado.**

T6 no fue ejecutado. El trabajo queda local, sin staging, commit, push, deploy ni cambios productivos.
