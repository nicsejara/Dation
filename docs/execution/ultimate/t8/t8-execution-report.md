# T8 — Run, Worker, Approval, Lineage y Result Publication

D1 Ultimate conectado al lifecycle durable y validado en sandbox owned.

Ejecución limitada a T8. T9 no se ejecutó. No hubo push, deploy, acceso a datos productivos ni cambios de infraestructura/configuración productiva.

## Baseline y checkpoint

Baseline inmediato: [T7 aprobado](../t7/t7-execution-report.md); hoja de ruta: [Master Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), T8 y §25.3. La [autorización](evidence/T8-user-request.txt) aprobó exclusivamente esta frontera. No se repitieron T0–T7 como fases ni se hizo otra auditoría general.

HEAD Git conservado: `ef997235a30251fbf7ae53690ed738092ee973d8`, branch `main`. El árbol ya tenía cambios de las fases previas. No se ejecutó reset, clean, checkout, descarte, staging, commit, merge o push.

El checkpoint post-T7 conserva **823 archivos / 42.112.762 bytes**, copias íntegras en `/workspace/work/dation-t8/post-t7`, inventario SHA256 y patch tracked. SHA256 del inventario: `059e581b35fa899254286ef75410730193211a0adc303f8854fed44d346a837d`. Las preimágenes de archivos extendidos y el inventario quedan en [evidence](evidence/initial-state.json). El [control de preservación](preservation.json) resuelve también los **46 registros** del manifiesto T7.

## Skills y entorno

Se aplicaron `supabase:supabase`, `supabase:supabase-postgres-best-practices` y `cloud-environment:cloud-environment-runtime`; fuentes y snapshots en [skills-ledger.json](skills-ledger.json). Se usaron sus instrucciones sobre grants/RLS, Storage privado, locks, versiones del CLI, credenciales y entorno owned. No se ejecutaron Skills de diseño ni agentes paralelos.

Python 3.13.5, OR-Tools 9.15.6755, Node 24.19.0; PostgreSQL 17 y PostgREST v14 reales en containers etiquetados T8/owned; API y standalone worker reales. Storage/Auth son fixtures privados de loopback. Las credenciales productivas estuvieron vacías durante QA. No se instalaron dependencias nuevas.

La migración se generó mediante `supabase migration new ultimate_result_publication` con CLI 2.122.0 y se cargó únicamente en bases efímeras owned. El harness utiliza la captura de schema de su fixture, sin repair ni replay sobre ninguna base existente. Advisors se ejecutó por `--db-url` apuntando exclusivamente a loopback: [resultado](evidence/advisors.json). Dos WARN preexistentes: `public.profiles.tenant_read` y `dation_private.workspace_id`; ninguno corresponde a objetos T8. No se amplió el alcance para cambiar esas definiciones históricas.

## Archivos

**16 archivos fuente/tests: 12 nuevos y 4 modificados.** Lista, hashes, preimágenes y diff: [scope-diff.json](scope-diff.json).

Nuevos: `result_package_service.py`, `result_artifact_service.py`, `ultimate_run_service.py`, routes `results.py`, migración `20261027140333_ultimate_result_publication.sql`, U8, S8, E8, L8 y sus fixtures/helpers owned. Extendidos: `routes/dispatch.py`, `dispatch_job_service.py`, tenant `repository.py` y `domain/logistics/graph.py`.

No se modificaron engines matemáticos T6/T7, assembler/projections/catálogos T7, schemas T1, CSS, frontend, assets, Docker productivo, Cloud Build/Run, Supabase remoto, secrets o triggers productivos. El ajuste del grafo utiliza el hash de Node Policy persistido al comparar una Run con overrides.

## Admission, intención y snapshots

`GET /api/platform/logistics-cases/{case_id}/run-context` entrega el contexto D1. `POST /api/runs?run_id=<UUID>` distingue `ultimate_run_request_v1` de requests legacy. Requiere intención explícita; D2 se rechaza y no tiene runtime nuevo.

El RPC checked vuelve a verificar membresía, DDA, Case, Owner/Admin, Data Owner elegible, Model/Pack publicados, policy/guardrails, definition hash, read set, locators y hash del contexto bajo locks. No acepta rutas o runtime seleccionados por el browser.

Persistencia fija Model/Pack Version, Case/Node Policy, definición/grafo, contract/normalizer, transit, runtime completo, hashes y datasets normalizados. El job guarda el input tipado, metadata de los snapshots y reloj de publicación. El worker verifica bytes normalizados contra su hash/tamaño y contra los records fijados; no sustituye inputs desde el Case/Pack actual.

Replay consulta la intención persistida **antes** de feature flags, owners, requisitos o caminos mutables nuevos. El mismo UUID/cuerpo/actor devuelve la Run original, incluso superseded. Un cuerpo distinto para ese UUID falla sin efectos. Submit concurrente crea una Run y un job; abrir/cancelar configuración no crea ni invalida Runs.

## Worker y registry

La cohorte Ultimate resuelve `engine_name + engine_version + runtime_profile + schema + schema_version` persistidos. Se conecta exactamente `transport_plan / 2.0.0 / transport_plan_v1 / 1` al producer T7 y al assembler T7. No existe fallback por `node_id` ni cambio matemático en el servicio.

`claim_dispatch_job_v2` anuncia capacidad dual. El claim anterior queda limitado a jobs legacy para que un worker viejo no capture Ultimate. El reader/worker nuevo conserva los perfiles legacy y usa el protocolo previo para ellos. Se mantiene heartbeat y la cola durable; los fallos transitorios conservan el job para recuperar al expirar su lease. La reconciliación reconoce sólo el rechazo explícito del cache Ultimate por el servicio legacy y no lo reintenta indefinidamente.

## Artifacts, Storage y preparación

El pipeline es `Pinned Input → producer D1 T7 → Core/Evidence → assembler T7 → AssemblyBundle`. T8 no construye projections ni corrige assignments.

Prepare reserva metadata PREPARED con tenant, Run, schema/version, hash, tamaño, assembler, Core fingerprint y generación/lease del productor. Paths generados exclusivamente por SQL: `<workspace>/runs/<run>/<kind>/<part>/<content-hash>.json`, en el bucket privado existente. Upload usa `upsert=false`; conflicto se reconcilia leyendo y verificando exactamente los mismos bytes. No se sobrescriben ni borran artifacts READY.

Un journal inmutable guarda la **preparación** y permite reanudarla; no es un segundo reader ni fuente del resultado publicado. Todas las lecturas usan `decision_runs.result_json` y sus bindings READY. Los índices de páginas/entidades se obtienen de los bytes ya ensamblados y se fijan en metadata inmutable, sin alterar el package. Se preservó la sintaxis de lookup `TYPE/id` de T2 y se extendió el guard al tipo `CASE` que T1/T7 ya contemplan.

## Validación y publicación atómica

El worker verifica hash/tamaño/JSON canónico de todos los objetos antes de finish. SQL comprueba identidad del Run, contexto/hash congelados, schema/runtime/transit/assembler, manifest, Core/Evidence/export/base-context requeridos y fingerprint canónico T1/T7. Los hash helpers SQL se compararon con outputs reales de T1/T7.

Finish bloquea y verifica lease vigente/token/deadline; publica en **una transacción** Run COMPLETED, package, manifest/hash, fingerprints, artifacts READY y job terminal. Los guards deferred T2 enlazan manifest/Run/metadata. Un manifest incorrecto deja el Run y todos sus artifacts sin publicación terminal parcial.

SQL no hace HTTP. El worker con lease aporta la atestación del manifest cuyos objetos acaba de verificar. Los objetos privados se escriben de forma inmutable; el hash/tamaño se vuelven a comprobar al consumirlos y antes de aprobar.

## Fencing y recuperación

Probados token ajeno, lease vencido, dos claimers concurrentes, adopción por una generación nueva, worker anterior tardío y finish duplicado. El worker sin lease no puede realizar una publicación nueva. Un retry de finish ya confirmado devuelve el recibo inmutable del mismo fingerprint, sin volver a publicar.

E8 cubre proceso muerto antes de upload, uploads parciales, respuesta prepare perdida, muerte después de subir y antes de finish, y respuesta finish perdida. El sucesor reutiliza metadata/bytes íntegros ya preparados. Si faltan bytes PREPARED, reejecuta **el mismo producer y assembler T7** sobre el input fijado; prepare exige igualdad exacta con el journal existente. No se reensambla ningún resultado COMPLETED durante retrieval. Un candidato diferente falla cerrado y no reemplaza el preparado.

No se agregó GC automático de huérfanos. Los PREPARED permanecen recuperables; no se elimina historia ni READY como estrategia de retry.

## Retrieval y performance

Rutas schema-aware, con `expected_result_fingerprint` obligatorio:

- `/api/runs/{id}/result`: package liviano, summary, metrics, visual descriptor/projection según T7 y refs. **Cero fetches de evidencia pesada**.
- `/details/{dataset}`: página acotada y total completo; sólo chunks que intersectan la página.
- `/entities/{type}/{id}`: lookup de evidencia por índice y binding exacto.
- `/artifacts/{id}`: sólo IDs del manifest de esa Run/tenant/fingerprint.
- `/approval-review`: review determinístico más overlay actual, después de verificar integridad.

Unknown schema, tenant/Run/fingerprint ajeno, locator arbitrario, objeto ausente/corrupto o dataset inconsistente fallan de forma explícita; no producen resultados vacíos o supuestos de negocio. Las lecturas históricas no consultan el Case actual para recomponer el package. El servicio de base de contexto IA puede enlazar la evidencia certificada a ese mismo fingerprint sin invocar LLM. No se conectó Copilot, dashboard final, Sankey renderer ni Detailed Analysis UI de T10.

## Review, aprobación y actores

El package conserva el review determinístico T7. El overlay agrega permisos vigentes, Owner elegible, Case archivado, freshness/read set y metadata READY. La lectura liviana indica `INTEGRITY_CHECK_REQUIRED`; el review verifica todos los bytes y vuelve a leer el overlay.

El POST de aprobación exige Case/nodo/Run/fingerprint exactos, verifica nuevamente los objetos y revalida autoridad y contexto bajo locks SQL. Un GET previo no otorga autorización duradera. Viewer no escribe; Operator requiere ser el Decision Owner; Admin respeta Owner elegible y freshness. No existe un Approver separado ni aprobación automática por IA.

La aprobación sólo agrega `approved_at/by/user_id` y evento; no modifica package, Core, evidence o fingerprints. Retries preservan el primer actor/fecha. Cambiar el Owner actual no reescribe al actor histórico. Cambiar/remover Owner entre GET y POST bloquea la aprobación cuando corresponde.

## Freshness, invalidación y lineage

La comparación usa las keys semánticas consumidas: hashes canónicos/contrato/normalizer de Demand/Resources, Model, horizonte y policies. **Pack Version por sí sola no invalida**. Re-publicar contenido equivalente conserva D1; metadata/enrichment D2-only no consumido tampoco cambia su matemática o aprobación.

Admission de nueva D1 retira los candidatos anteriores propios y downstream bajo locks. Un cambio consumido del Pack marca supersession y conserva la causa `invalidated_by_pack_version_id`/`INPUT_READ_SET_CHANGED`. El downstream pierde vigencia cuando pierde upstream aprobado. Permanecen Runs, packages, actors, approvals/eventos, evidence y referencias históricas. Una Run en ejecución puede terminar su snapshot histórico tras cambiar el Pack; queda stale y no aprobable.

Tras aprobación vigente, T5 proyecta D1 APPROVED y dependencia D2 satisfecha. **D2 runtime permanece no disponible**; no se produjo `day_scheduling_v1` con un engine nuevo.

| Escenario | Frontera ejercida y evidencia |
|---|---|
| L-A | Nueva intención D1 pendiente, contexto D1 correcto, mismo Case/Decision; sin entidad Branch ni Run duplicada (L8/E8 y B-FOCUS legacy). |
| L-B | Config D2 lee la D1 aprobada exacta, sin mutar aprobación/fingerprint upstream. D2 se representa sólo mediante metadata T5 controlada. |
| L-C | Abrir/abandonar es puro; admission D1 B retira D1 A y downstream, preservando fechas/actores y causas (S8/L8/E8). |
| L-D | Múltiples Runs no aprobadas, selección histórica y grafo actual independientes; historial y snapshots intactos (L8/B-FOCUS). |
| L-E | D2 A/B metadata conserva sourceD1 A y su fingerprint por referencia inmutable; después de publicar/aprobar D1 B, D2 C metadata referencia B (L8). No ejecución D2. |
| L-F | Replay viejo después de camino nuevo, Pack semánticamente equivalente/enrichment, input consumido, rename y Owner change; sin restaurar approvals o reescribir actors (S8/L8/E8). |

## QA y legacy

| Suite | Tests | Resultado | Fail/Error/Skip |
|---|---:|---|---|
| B-PY | 628 | PASS | 0/0/0 |
| B-NODE | 137 | PASS | 0/0/0 |
| B-FOCUS | 9 | PASS | 0/0/0 |
| U8 | 14 | PASS | 0/0/0 |
| S8 | 13 | PASS | 0/0/0 |
| E8 | 8 | PASS | 0/0/0 |
| L8 | 2 | PASS | 0/0/0 |
| R8 | 1 | PASS | 0/0/0 |

Comandos, tiempos, counts, hashes, logs y source candidate: [test-ledger.json](test-ledger.json), [command-ledger.json](command-ledger.json) y [evidence](evidence/candidate.json). No se considera PASS una suite sin tests, con skips o cuyo entorno no arrancó. Los intentos intermedios y su corrección se conservan separados.

B-PY incluye los 47 tests U6 y 46 U7, además de U8 y las regresiones de worker/admission legacy. B-NODE y B-FOCUS preservan navegación, selección aprobada y lineage anterior. R8 ejecutó además la regresión legacy existente con seis Runs reales, assignment/scheduling legacy, approvals y conservación de evidencia sobre el esquema T8 owned; no implementó D2 Ultimate. Legacy `assignment_v1`, `scheduling_v1`, `dispatch_v2`, exports y Case flows conservan sus engines/schemas/readers. No hubo backfill de ResultPackage sobre Runs legacy.

## Desviaciones y riesgos

- Se agregó L8 focal para cubrir las referencias D2 A/B→A y C→B sin adelantar T9. Sus filas D2 son metadata de fixture identificada, no outputs certificados ni un runtime simulado como disponible.
- Los RPCs siguen el patrón checked existente: sólo service-role puede ejecutarlos; validan actor/membresía/Owner y lease expresamente. No se añadió un `auth.uid()` de usuario al JWT de servicio, que no representa al actor final. Los grants a PUBLIC/anon/authenticated se revocaron expresamente.
- Hubo fallos de fixture y disponibilidad local durante desarrollo: guard de índice, respuesta middleware de Storage, startup de PostgREST/API y boot UI bajo contención. La evidencia final distingue esos intentos de las suites completas sobre los bytes congelados. No se ocultaron como skips ni PASS.
- Los paquetes pendientes se recuperan por igualdad exacta. Si una reejecución limitada por presupuesto produce otro candidato, se conserva el original y se falla cerrado; no se modificó T7 para forzar igualdad. Los resultados completos nunca se recalculan.
- La prueba de Storage cubre contrato privado/upsert/hash usando fixture local; no certifica la disponibilidad de un proveedor productivo. No se ejecutó un smoke de producción ni se abrió la admisión pública.
- Las advertencias de Advisors son de objetos previos preservados. No se convirtieron en cambios fuera de T8. El fetch directo del changelog Supabase fue bloqueado por la política de red; se consultó documentación oficial mediante MCP sin eludirla.

## Rollback y gates

Rollback seguro: cerrar `ultimate_admissions_enabled`, conservar readers/workers duales y drenar/cancelar con el protocolo existente. Retener schema, Runs, artifacts, journals y eventos. No DELETE, repair, restauración de approvals o backfill. El flag público queda **false por defecto**; sólo los fixtures owned lo habilitan para T8.

| Gate | Resultado | Evidencia |
|---|---|---|
| Baseline/alcance | PASS | 823 copias y 46 entries T7 verificadas; math y frontend preservados |
| Admission/replay | PASS | U8/S8/E8/L8; una intención/Run; contexto fijado |
| Publication/fencing | PASS | S8/E8; sin estados parciales; lease y manifest exactos |
| Retrieval/security | PASS | U8/S8/E8; bytes, tenant/Run/fingerprint y páginas acotadas |
| Approval/read set | PASS | S8/E8; Owner vigente, contexto e integridad; actores históricos |
| Lineage/legacy | PASS | L8, R8, B-FOCUS y regresiones B-PY/B-NODE |
| STOP conditions | PASS | Ninguna condición funcional abierta; intentos fallidos diagnosticados y suites finales completas |
| T9/producción | PASS | No ejecutados; flag público cerrado; sin push/deploy |

T9 no se ejecutó ni se autoriza por esta entrega. Estado Git/alcance final: [final-state.json](evidence/final-state.json).

GO — T8 completado. T9 puede ser solicitado.
