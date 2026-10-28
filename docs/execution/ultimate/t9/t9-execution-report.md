# T9 — D2 Day Scheduling, Engine Evidence y Result Assembler

D2 implementado y validado sobre el lifecycle T8. Alcance exclusivo T9: no T10, UI final, Copilot real, push, deploy o producción.

## Baseline, alcance y checkpoint

Fuentes: [autorización T9](evidence/T9-user-request.txt), [Master Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), T9, §9/10, fixtures H–L y R9–R13; baseline inmediato: [T8 aprobado](../t8/t8-execution-report.md). Se inspeccionaron sólo contratos D1/D2, Transit, kernel T6, assembler compartido y la frontera admission/publication/lineage afectada. No hubo otra auditoría general ni repetición de T0–T8 como fases.

HEAD y branch conservados: `ef997235a30251fbf7ae53690ed738092ee973d8`, `main`. El árbol ya contenía cambios de fases aprobadas. No hubo reset, clean, descarte, checkout, staging, commit, merge o push.

Checkpoint post-T8: **864 archivos / 42.840.096 bytes**, copias en `/workspace/work/dation-t9/post-t8`, inventario SHA256 y patch tracked. SHA256 del inventario: `5fa1c33abf2ab52673f4dcca648f2217b502ac9011beea99071996cebbdbd28e`. Las **83 entradas** del manifiesto T8 se verificaron antes de modificar código; el [control final](preservation.json) las resuelve en archivos actuales o preimágenes conservadas. Los ocho archivos extendidos tienen copia previa en `evidence/post-t8/`.

## Skills y entorno

Se aplicaron las reglas pertinentes de `cloud-environment:cloud-environment-runtime`, `supabase:supabase` y `supabase:supabase-postgres-best-practices`, ya consultadas en esta conversación; snapshots y aplicación en [skills-ledger.json](skills-ledger.json). No hay una Skill específica Python/scheduling/optimization disponible. Contratos, kernel y oracles gobiernan el cálculo. No se usaron Skills UI ni subagentes.

Se volvió a comprobar disponibilidad del entorno, política de red y daemon local antes del harness. Python 3.13.5, OR-Tools 9.15.6755, Node 24.19.0, PostgreSQL 17 y PostgREST v14. No se instalaron dependencias. QA Python/API/SQL/worker corrió con credenciales productivas vacías; B-NODE es una suite offline de módulos/assertions sin llamadas a proveedores. Los procesos, DB, red, Auth y Storage de los escenarios fueron owned/aislados; Storage/Auth son fixtures privados, API/SQL/worker/engine reales.

La migración se creó con CLI Supabase 2.122.0 mediante `migration new ultimate_day_scheduling` y sólo se aplicó a bases efímeras owned. No se reparó migration history ni se reejecutó un baseline sobre una base existente. Advisors se ejecutó contra loopback sobre el schema final: [resultado](evidence/advisors.json). Conserva dos WARN previos (`public.profiles.tenant_read`, `dation_private.workspace_id`), sin findings nuevos T9.

## Archivos creados y modificados

**21 archivos fuente/tests: 13 nuevos y 8 modificados**, listados con hashes en [scope-diff.json](scope-diff.json).

Nuevos: `engines/scheduling/day_{contracts,metrics,scheduling,validator}.py`; `results/day_{assembler,projections,validation}.py`; `tests/day_fixtures.py`, `test_day_scheduling_core.py`, `test_day_result_package.py`, E9 y fixture owned; migración `20261027175943_ultimate_day_scheduling.sql`.

Extendidos: kernel compartido T6, `results/{assembler,ai_context,registry,validation}.py`, `routes/results.py`, `services/{ultimate_run_service,decision_graph_service}.py`. Se preservaron Scheduling/assignment/dispatch legacy, código matemático D1, T1 DTOs/catálogos/metadata pública, frontend/CSS/assets, dependencias y configuración productiva.

## Upstream D1 exacto

D2 consume un `ResultBinding(run_id, result_fingerprint)` aprobado/vigente. Config obtiene la aprobación vigente de manera no ambigua; el POST fija el binding mostrado. Nunca sustituye un binding solicitado por latest/completed/UI selection.

El servicio verifica el package/manifest y bytes privados D1, lee su Core/evidencia/base de contexto certificados y usa los recursos del input D1 persistido. No recompone fechas desde CSV ni desde el Case actual. El job D2 conserva Core, evidencia, recursos, input summary y binding del origen como snapshot; el worker vuelve a compararlos con los artifacts publicados. `upstream_run_id`, input hash, package y `upstream_result_fingerprint` fijan la misma referencia.

SQL revalida tenant/Case, aprobación vigente, read set, Core fingerprint, recursos/modelo originales y binding solicitado bajo locks. La proyección canónica SQL del Core fuente se comparó con el hash T1 real. Un service-role con actor funcional válido tampoco puede admitir allocations falsificadas, otra disponibilidad o el flag defensivo de una fixture.

## Scheduling Core y kernel compartido

El Core lógico `DayScheduleCoreV1` usa el ABI T1 existente: `EngineCoreResult(result_schema='day_scheduling_v1', schedule=DaySchedule(...))`. No se creó otro contrato/store de resultados.

El input es versionado e inmutable. D2 conserva todos los Trip IDs, recursos/sources, route/distance, Order IDs, allocations/fractions y cargas D1. Sólo decide WHEN. Las referencias y los facts de detalle mantienen las asignaciones originales; no hay consolidación, split, routing, patentes, drivers, docks, turnos ni horas.

Se agregó una opción privada `select_earliest` al **mismo modelo temporal T6**. Su default preserva las certificaciones de existencia usadas por D1. D2 fija lexicográficamente el día más temprano certificado por Trip ID sobre ese modelo, con un solver de un thread, seed estable y presupuesto acotado. Slots internos colorean intervalos del grupo OWN; no son nuevos resources ni vehículos. No se afirma un óptimo de costo/servicio no demostrado: el resultado declara FEASIBLE y expone su regla de selección.

Un certifier separado verifica pertenencia al origen, ventanas, fechas Transit, margin, concurrencia, quotas externas, timeline, service order y métricas. Una contradicción real con Trips D1 certificados por T6 produce `UpstreamCertificationConflict` y falla cerrado. No se encontró ninguna en los handoffs reales. La prueba negativa explícita verifica el guard sin aprobar un origen imposible.

## Ventanas y Transit

`dispatch_window` T6 sigue siendo la autoridad de ventanas; `TransitEstimator` T1, la única autoridad de tránsito. No se copió una fórmula km/500 ni se usaron helpers legacy de horas/speed.

- Earliest respeta ready date D1 y comienzo de horizonte; el modelo compartido aplica disponibilidad/reutilización.
- Latest respeta fin de horizonte de **despacho** y el due date inclusivo con outbound certificado.
- El horizonte no corta arrival o retorno: el fixture J conserva dispatch 8/11 y arrival 10/11; OWN conserva también availability posterior.
- Si latest es anterior al comienzo, el diagnóstico defensivo es PRE_HORIZON, con tiempos NULL, no LATE ni una salida inventada.

## OWN y EXTERNAL

OWN respeta `units_available` del snapshot D1 mediante Cumulative y sus ciclos certificados. Ocupación: `[dispatch, available_again)`. Una unidad puede reutilizarse exactamente en el end exclusivo, nunca antes. El resource ID de grupo permanece intacto; un índice interno de slot sólo es evidencia.

EXTERNAL respeta la oferta de servicios de horizonte ya fijada por D1. Tiene dispatch/arrival y **cycle, busy_until, available_again NULL**; no se crea ni reserva retorno. ResourceTimeline/Gantt usan eventos de despacho externos, sin barra OWN ficticia.

## Status, margin y hard policy

Margin es la diferencia de días calendario due−arrival producida por el engine. `>0 ON_TIME`, `=0 AT_RISK`, `<0 LATE` son categorías distintas del contrato. PRE_HORIZON y UNSCHEDULED son categorías propias, con tiempos/margin NULL donde corresponde, y conservan su Trip en todos los denominadores.

No existe en T1 una policy certificada que habilite lateness; T9 no inventó una. El productor duro no programa tarde y el certifier rechaza una fila LATE no autorizada. R11 verifica la distinción contractual/metric de LATE y los diagnósticos defensivos; no se presenta como un perfil soft disponible.

Guardrails del Node Policy se contrastan con facts D1 inmutables. Si una policy local más exigente no se cumple, el review queda bloqueado sin reasignar Trips/recursos. UNKNOWN o presupuesto de selección no certificado produce error técnico, sin fabricar `NO_FEASIBLE_DISPATCH_DAY`, infeasibilidad ni un calendario vacío aprobable.

## Engine Evidence

Se emiten constraints/policy/solver evidence, entidades y reason emissions tipados ligados al Core/input hash. Los códigos T1 se emiten cuando existen los facts requeridos: dentro de ventana, earliest, protección de due, ready delay, ocupación OWN, cero margen, pre-horizon, falta de día factible, conflicto de capacidad demostrado y unscheduled.

La causa de ocupación requiere intervalos efectivamente bloqueantes. Un conflicto defensivo de capacidad usa intervalos obligatorios y units originales. No se infiere causalidad a partir del Gantt. Las entidades incluyen fechas seleccionadas/ventanas, slot lógico, resource/source, source Run/fingerprint y métricas auxiliares certificadas.

## Métricas certificadas

`DaySchedulingMetrics` mantiene scheduled/total/ratio, categorías disjuntas, expected delivery compliance, average margin, peak y exception count. Todos los Trips D1 integran el denominador; ninguna exclusión por status mejora un KPI.

La semántica T1 de `metrics.on_time_ratio` es **(ON_TIME + AT_RISK) / total_trips**. Strict ON_TIME se mantiene separado en facts producidos por el engine y copiados al summary/context: ratio y numerador/denominador propios. R12 verifica **6 ON_TIME + 2 AT_RISK → compliance 100%, strict ON_TIME 75%**.

El promedio usa sólo margins conocidos y publica su denominador. NULL no se convierte a cero. `peak_dispatch_day` se decide en backend por mayor cantidad y luego fecha más temprana. Las excepciones temporales se cuentan una vez por Trip; policy/hard-constraint readiness se informa por separado.

## Result Assembler y `day_scheduling_v1`

Se reutilizan `app/results/assemble`, `AssemblyBundle`, el mismo `ArtifactBuilder`, chunks, manifest, hash DAG y validadores. D2 tiene versión `RESULT_ASSEMBLER_D2_V1`. No hay otro publisher ni store.

El assembler copia Core/evidencia/contexto y no selecciona fechas, resuelve conflictos o cambia assignments. Validación independiente vuelve a comprobar consistencia; no repara resultados. Summary, métricas, visual, seis details, review, export y contexto quedan vinculados al mismo fingerprint con el upstream exacto incorporado al hash.

Los parámetros por default de D1 conservan su versión y bytes. La comparación aislada post-T8/current comprobó igualdad exacta de Core, package, artifacts y contexto en tres casos reales D1, incluido OWN y cobertura parcial: [vectores](evidence/d1-compat-vectors.json).

## Day Gantt y Detailed Analysis datasets

La proyección backend DAY_GANTT declara resource/source, Trip ID, dispatch/arrival/status y ocupación OWN completa. No trunca arrival/return al horizonte. Un viaje same-day conserva un item visible con dispatch=arrival. Para UNSCHEDULED/PRE_HORIZON no se fabrica una barra con fechas inexistentes; sus filas permanecen en Schedule/Trips/Service/Exceptions/Evidence y CSV.

| Dataset | Contenido certificado |
|---|---|
| Schedule | Todos los Trips, resource/source, ready, dispatch, arrival, due, margin/status y ciclo/availability |
| Trips | Facts D1 inmutables, Orders/allocations/fractions/cargas y timing D2, con referencia al origen |
| Resources | OWN units/ocupación y eventos; EXTERNAL sólo dispatch/arrival |
| Service | Todas las filas, ordenadas por menor margin conocido, Trip ID y NULL al final |
| Exceptions | Un diagnóstico temporal por Trip afectado, con reason facts |
| Evidence | Ventana, selección, constraints, disponibilidad/ocupación y bindings |

T10 podrá renderizar la proyección y los datasets. No se añadió renderer, dashboard final ni cálculo de fechas en JS.

## Approval Review, export y Decision Context

El review determinístico contiene scheduled ratio, expected compliance, counts de servicio, hard constraints, excepciones y review items. `decision_ready_for_review` sigue separado de `approval_allowed`; la autoridad actual y el POST continúan en T8 con integridad, Owner/Admin, Case y freshness bajo locks.

`Day_Schedule.csv` queda preparado como descriptor DAY_SCHEDULE/TRIP y dataset completo: **una fila por Trip D1**, también pre-horizon/unscheduled, con NULLs reales y source Run/fingerprint. No se crearon nuevas allocations. La conexión del export/render final corresponde a T10.

Se extendió la base privada de `decision_context_v1` para aceptar las métricas D2 ya previstas por T1. Incluye source Run/fingerprint, schedule/service summary, evidence, exceptions, assumptions/review y provenance del package. D2 no introduce supuestos nuevos; los ya aprobados en D1 se conservan en el origen exacto enlazado y pueden recuperarse por su binding. No se invocó LLM ni se conectó Copilot. La forma serializada D1 se preserva.

## Integración publication T8

La nueva migración extiende **el mismo RPC** `platform_ultimate_execution`: admission, replay, prepare, journal, artifact bindings, finish, read y approve. El worker usa identidad completa persistida, sin fallback por nodo. D2 atraviesa el mismo flujo PREPARED→hash/size verification→fenced atomic finish→READY/COMPLETED y las mismas APIs livianas/detail/entity/review de T8.

El flag nuevo `ultimate_scheduling_admissions_enabled` queda **false por default**; los fixtures owned lo habilitan junto con la admisión Ultimate. La metadata pública congelada T1 permanece sin cambios, como en T8. La capacidad D2 del worker se proyecta honestamente en el grafo del release owned (`D2 READY`, `runtime_available=true` cuando aplica), sin abrir la admisión pública de T12.

Admission D2 retira sólo Runs D2 previas. Conserva la D1 aprobada/actores. Admission de D1 nueva mantiene la invalidación T8 de su closure downstream. Un worker D2 puede terminar su snapshot histórico si el origen pierde vigencia durante la ejecución, pero ese resultado queda stale/no aprobable. Replay se resuelve antes de reinterpretar el contexto actual.

## Lineage E9

| Secuencia real | Resultado |
|---|---|
| D1 A aprobada → D2 A | Binding exacto A/FP-A, artifacts íntegros y aprobación humana D2 |
| D1 A sigue aprobada → D2 B | B usa A/FP-A; D1 A no cambia; sólo D2 A queda superseded |
| D1 B completada sin aprobación | Config/admission D2 bloqueada; no usa latest completed |
| D1 B aprobada → D2 C | C usa B/FP-B; A/B D2 conservan A/FP-A para siempre |
| Replay D2 A después del camino C | Devuelve la Run original sin nuevos efectos, snapshots o approvals |
| Cambio de upstream mientras D2 ejecuta | Finaliza como historia sobre A; no se aprueba como vigente |
| Requests concurrentes / crash / respuesta finish perdida | Una intención/Run, lease fencing y recuperación T8, sin modificar D1 |

También se probaron tenant/Viewer/wrong fingerprint y falsificación directa de assignments, disponibilidad y certificado de origen. Ninguna crea otra Run válida ni sustituye el upstream.

## Fixtures, oracles y QA

H/I/J/L usan outputs reales T7: externo 1150 km outbound3; OWN480/cycle2 y secuencias 2/4 o 2/4/6; dos unidades 2/2/4; despacho al último día con arrival posterior. K es el handoff defensivo indicado por el plan, marcado sólo para unit tests; E9 nunca fabrica aprobación de una D1 imposible y SQL rechaza ese flag.

El oracle de OWN enumera placements finitos sin reutilizar solver, objective o helper Transit productivos. R9–R13 comprueban fechas entre consumidores, exclusividad/retorno externo, status disjuntos, compliance vs strict y concurrencia≤2. Negativos rehashean Gantt alterado, corrompen timeline/context/version y verifican fallo cerrado sin reparación.

| Suite | Tests | Resultado | Fail/Error/Skip |
|---|---:|---|---|
| B-PY | 656 | PASS | 0/0/0 |
| B-NODE | 137 | PASS | 0/0/0 |
| U9 | 28 | PASS | 0/0/0 |
| E9 | 8 | PASS | 0/0/0 |
| S8 | 13 | PASS | 0/0/0 |
| E8 | 8 | PASS | 0/0/0 |
| L8 | 2 | PASS | 0/0/0 |
| D1-COMPAT | 3 | PASS | 0/0/0 |
| LEGACY | 1 | PASS | 0/0/0 |

Logs, comandos, tiempos y hashes: [test-ledger.json](test-ledger.json), [command-ledger.json](command-ledger.json), [candidate](evidence/candidate.json). B-PY incluye U6, U7, U8 y U9. Las regresiones S8/E8/L8 se ejecutaron por extender publication/lineage; LEGACY ejecutó la regresión existente de seis Runs con assignment/scheduling v1, approvals e historia. No se repitieron suites amplias no afectadas ni B-BROWSER/T10.

Los intentos intermedios no se contabilizan como PASS. Se corrigieron sintaxis/alias SQL, un fixture R12 que permitía split en D1 y la expectativa de metadata pública congelada. El modo Node por default reportaba sólo 23 archivos; no se aceptó como el gate de 137 casos. Con `--experimental-test-isolation=none` se ejecutaron y pasaron los **137 casos reales**, sin modificar tests frontend.

## Compatibilidad legacy, desviaciones y riesgos

- Legacy `scheduling_v1`, calendarios/helpers, assignment/dispatch, rutas, approvals y exports siguen vigentes. No se migraron/backfillearon resultados históricos a D2 v2.
- Se conservó el ABI T1 y su metadata pública inactiva; la disponibilidad del release owned y la factory privada identifican la implementación D2. No se abrió rollout público para satisfacer un test o una pantalla.
- No se introdujo una policy soft de lateness ni un enriquecimiento/CSV nuevo. El contrato conserva LATE como categoría distinta; el perfil disponible es duro. Las restricciones son las certificadas por T1/T6 y el snapshot D1.
- El kernel conserva sus límites T6 (Trips/resources/horizonte) y presupuestos. Si no certifica la selección, se persiste error técnico; no se declara infeasibilidad por timeout ni se modifica el origen.
- Storage/Auth se probaron mediante el contrato privado del fixture; no se certificó disponibilidad o política de un proveedor productivo. El rollout posterior debe validar su entorno sin reescribir packages históricos.
- Las dos advertencias de Advisors pertenecen al baseline preservado. No se ampliaron cambios fuera de T9 para corregirlas.

Rollback seguro: cerrar la admisión D2 nueva, conservar readers/worker duales y schemas/artifacts/history. No borrar Runs/approvals, modificar D1 o reensamblar resultados publicados.

## Gate evaluation

| Gate | Resultado | Evidencia |
|---|---|---|
| Baseline/alcance | PASS | 864 copias; 83 entries T8 resueltas; sin T10/producción |
| Upstream exacto | PASS | E9: A/B→A, C→B; hashes, snapshots y actores históricos |
| Temporal/Transit | PASS | U9 H–L, kernel compartido, fechas DATE y OWN end exclusivo |
| Core/evidence/métricas | PASS | U9 R9–R13; sin pérdida de Trips; compliance y strict separados |
| Assembler/consumidores | PASS | Core/Gantt/details/CSV/context/review consistentes, hash DAG íntegro |
| Publication/fencing | PASS | E9 y S8/E8; protocolo único T8; sin publicación parcial |
| Regresiones | PASS | B-PY/B-NODE, L8, bytes D1 exactos y legacy real |
| STOP | PASS | Ninguna condición funcional abierta; negativos esperados fallan cerrado |

Estado Git y alcance: [final-state.json](evidence/final-state.json). T10 no se ejecutó. No hubo push, deploy, operaciones productivas ni cambios de infraestructura.

GO — T9 completado. T10 puede ser solicitado.
