# T1 — ABI Ultimate v1

Especificación ejecutable aditiva de `DATION_FINAL_MASTER_EXECUTION_PLAN.md` §3/§6–9/§18/§20/T1. No habilita engines, endpoints, almacenamiento ni migraciones. El JSON consumible se genera con `app.results.registry.contract_metadata()` en `backend/app/static/contracts/result-contracts-v1.json`; U1 comprueba su igualdad y sus referencias JSON Schema.

## Dominio y precisión

`LogisticsModelVersion`, `Demand`, `TransportResource`, `CasePolicy`, `NodePolicy` y `FrozenCaseContext` son DTOs nuevos e inmutables. El último representa un snapshot de admisión con read set explícito; no es el DTO de creación de un Case vacío de T3. Role no selecciona otro engine. DIRECT y las dimensiones activas son explícitos; maximum no reemplaza guaranteed. Un override tiene motivo y no puede relajar los hard guardrails. No hay compiler de contratos de archivos, graph resolver ni solver nuevo.

| Path / concepto | Regla v1 |
| --- | --- |
| Decimal wire | String decimal finito exacto; también se admite input entero lossless. Floats binarios se rechazan. La salida normaliza sin exponente, ceros redundantes ni `-0`. No se infiere tipo por un label. |
| Money `{amount,currency}` | Amount en unidades mayores; currency de tres letras mayúsculas. `CurrencyPolicy` del snapshot fija minor_units 0–6 y ROUND_HALF_UP. No se toma la moneda del workspace actual ni hay FX. |
| Escalado interno | Decimal → entero exacto; rechazar granularidad incompatible y overflow signed64. No redondear cargas para hacerlas caber. |
| Cargas | Pallets/units/kg: máximo 3 decimales; m³: máximo 6. Son precisiones máximas representables; un contrato de Model posterior puede exigir granularidad más estricta. Conteos de vehículos/servicios son enteros, distintos de cargas. |
| Distancia / tarifa | Distancia de dominio con escala 3; tarifa con hasta 6 decimales. Positiva la distancia; tarifa conocida cero es válida. |
| Allocation fraction / ratios | Fracción de asignación hasta 6 decimales; ratios certificados hasta 4, con numerador/denominador declarados en catálogo. Denominador cero → NULL. |
| Costo desconocido | Campo Money completo NULL. Un subtotal conocido no se presenta como total_cost; cost_completeness explícito. Escala/currency de alternatives y candidates se ligan al contexto. |
| Fechas / timestamps | Fechas de negocio ISO DATE. Auditoría con timezone; canonicalización temporal UTC. Horizon incluye ambas fechas de salida, no limita automáticamente arribo/retorno. |
| IDs | UUID para ownership/contexto/Run; IDs de negocio pseudonimizados y estables para entidades. No patente/chofer ni Branch entity. |

La representación decimal cierra la precisión pendiente de T1; no convierte ni reserializa ningún valor legacy. Las validaciones de ratios comprueban valores suministrados: no son productores alternativos de KPIs.

## Transit y costos puros

Única autoridad Ultimate: `app.domain.logistics.transit.TransitEstimator`, versión `DATION_TRANSIT_V1`, estándar 500 km/día. Outbound y ciclo OWN se redondean independientemente sobre distancia simple y doble. Arrival inclusivo y available_again exclusivo; EXTERNAL no tiene ciclo ni ocupación de retorno. Ningún helper legacy se importa/reemplaza para estas fórmulas.

`trip_cost` implementa únicamente precio: EXTERNAL PER_TRIP usa tarifa por servicio; PER_KM usa la base ONE_WAY/ROUND_TRIP; OWN usa costo operativo del ciclo DIRECT. No asigna recursos, no decide factibilidad ni produce total_cost del resultado. Tarifas desconocidas permanecen NULL.

## Identidades y compatibilidad

| Cohorte | Engine / version | Profile | Schema / version | Implementado / disponible |
| --- | --- | --- | --- | --- |
| Legacy D1 | logistics-assignment-engine / 1.0.0 | Ausente, preservado | assignment_v1 / 1 | Sí / sí en el registro de código actual |
| Legacy D2 | logistics-scheduling-engine / 1.0.0 | Ausente, preservado | scheduling_v1 / 1 | Sí / sí en el registro de código actual |
| Legacy Dispatch | logistics-dispatch-engine / 2.2.0 | Ausente, preservado | dispatch_v2 / 2 | Sí / sí en el registro de código actual |
| Ultimate D1 | transport_plan / 2.0.0 | transport_plan_v1 | transport_plan_v1 / 1 | **No / no** |
| Ultimate D2 | day_scheduling / 2.0.0 | day_scheduling_v1 | day_scheduling_v1 / 1 | **No / no** |

Disponibilidad del registro no sustituye entitlements, permisos, Owner, freshness ni admisión de backend/SQL. Lookup nuevo exige identidad persistida completa; `node_id` no decide el runtime. Header nuevo `result_schema`/`result_schema_version`; header legacy `schema_version` original. Unknown/mismatch falla explícitamente, sin fallback a Dispatch. Adapter puro de lifecycle mapea `error` → `FAILED`; no cambia el enum persistido.

El dispatcher existente permanece intacto: la conexión de los nuevos producers al worker corresponde a T8/T9, antes de admitir nuevas Runs. Tampoco se modifica el fallback histórico de exporters/interpreter; los nuevos consumers deberán usar el registry exhaustivo en T8/T10. No hay resultados Ultimate publicados que atraviesen esas rutas en T1.

## Core, Evidence y Package

`EngineCoreResult` fija la selección matemática y `EngineEvidence` sus facts/certificados. `EngineOutput` exige binding de Run/workspace/context hash/core fingerprint y facts para cada reason referenciado por Trips/residual. Un `ReasonEmission` sin facts tipados suficientes es inválido. El catálogo contiene los 24 IDs mínimos del contrato fuente, con versión, scope, producer, requirements, claim strength y message key.

OPTIMAL exige un certificado y bound coincidente; FEASIBLE no puede presentarse como óptimo. UNKNOWN no acredita infeasibilidad global del Case. Sí admite un witness local independiente —por ejemplo una orden non-split mayor a guaranteed— con sus hechos completos. CAPACITY_GAP expresa residual observado, no inevitabilidad inferida.

`DecisionResultPackageV1` conserva las raíces especializadas: D1 transport_plan; D2 schedule + source_transport_plan. `ResultContractBundle` valida un Core/Evidence/Package ya suministrado, sin ensamblar ni producirlo. D2 timing no admite campos para editar allocations/routes/loads; el comparador puro verifica origen, fingerprint, Trip IDs y resource assignments. No comprueba aprobación SQL actual: eso sigue siendo autoridad del backend.

Review es un snapshot determinístico de los mismos facts y métricas. `approval_allowed` vive en `ApprovalOverlay`, fuera del package y sus hashes; las respuestas verifican el mismo Run/fingerprint. Las proyecciones SANKEY y DAY_GANTT son sólo DTOs: T1 no genera proyecciones ni dibuja gráficos.

| Productor futuro único | Datos | Consumers futuros |
| --- | --- | --- |
| transport_plan | Trips, residual, costos, cobertura/prioridad, utilización ponderada, mix por trips y reasons | Assembler D1 → Dashboard, Plan/Demand/Resources, CSV, Context, Review |
| day_scheduling | Fechas, ocupación, categorías disjuntas, compliance esperado y margen | Assembler D2 → Gantt, Schedule/Service/Resources, CSV, Context, Review |
| Assembler | Copia/joins/proyecciones/manifest/templates/review; comprueba, sin sustituir matemáticas | Mismo package para todos los consumers |
| Backend/SQL actual | Permiso/freshness/approval overlay | Acción formal de aprobación; nunca el LLM |

El catálogo tiene 23 descriptores de métricas con paths, unidades, precisión, null semantics y producer único. `on_time_ratio` nuevo usa ON_TIME + AT_RISK sobre todas las Trips, manteniendo los cinco conteos disjuntos. No se implementa un certificador de engine completo en T1; conservación/solver/certificación/publicación operacionales se entregan en T6–T9.

## Fingerprint DAG y serialización

`DATION_CANONICAL_V1`: UTF-8, NFC, keys ordenadas, sin whitespace de formato, sin floats/nonfinites, sin colisiones de keys NFC; fechas ISO y timestamps UTC. Validar DTO antes de proyectar/hash: una string genérica nunca se adivina como número. Se incluyen kind y canonical_version en los preimages semánticos.

1. Input context: snapshots/versions/read set/Policy/runtime/Transit/upstream. Excluye Case name, display metadata y texto de motivo de override. Ordena colecciones semánticas declaradas.
2. Core fingerprint: contexto matemático + hechos Core; excluye Run ID, decision label y execution clock.
3. Artifact: SHA256 de bytes exactos; puede incluir core fingerprint y upstream pasado, nunca el result_fingerprint de su package futuro ni permisos/signed URLs.
4. Package fingerprint: proyección inmutable con manifest, assembler/contract versions y Run. Excluye únicamente su propio campo; overlay/delivery se transportan por fuera. Conserva contexto histórico y fecha de publicación: **es identidad de publicación, no un hash matemático**.
5. Decision context hash incluye mode/selection/refs. Intent v2 agrega pregunta NFC/trim, Run/fingerprint/context version y evidence hashes. No modifica el hash legacy de preguntas.

`tests/fixtures/ultimate/fingerprint-vectors-v1.json` fija preimages canónicos sencillos y goldens tipados. Tests prueban cambio semántico, igualdad matemática entre Runs/display/clock diferentes, autocampo excluido y hashes iguales en procesos con seeds distintos. No hay artifacts ni llamadas a proveedores nuevos.

## INLINE / REFERENCE y API

Delivery v1 es discriminado por `mode`. INLINE exige row_count exacto y permite un dataset vacío válido. REFERENCE exige refs no vacías con owner Run/workspace/core, schema/version, hash y tamaño, presentes en el manifest. UNAVAILABLE y CORRUPT son errores explícitos de retrieval, nunca `[]`. No se aceptan URLs arbitrarias ni signed URLs dentro del package.

Presupuestos declarados: package 512KiB; visual inline 256KiB; chunk 1MiB/100 entidades; page 100 filas; selección 50KiB. El DTO controla los límites disponibles sin I/O; medición/chunking/retrieval real siguen en T7/T8/T11. Un descriptor no prueba bytes recuperables: el publisher/retriever futuro deberá verificar schema/hash/tamaño y binding.

La metadata congela siete rutas **no instaladas**: GET result/details/entities/artifacts/approval-review y POST decision-context/decision-assistant-v1, bajo `/api/runs/{run_id}/`. Todas declaran expected_result_fingerprint. `UltimateRunRequest` tiene discriminator/version/context pinning y source D1 para D2; no admite engine ni dependency closure del cliente. EXPLAIN/EXPLORE/COMPARE/REVIEW y selección están tipados; no hay retrieval seleccionado ni LLM nuevo.

## Handoff a T2 — especificación, no implementación

| Paquete previsto | Contrato a respetar al autorizar T2 |
| --- | --- |
| M1 | Models/Versions y contexto Case; catálogo privado release-only de Definitions. IDs/version/hash/payload canónico inmutables, PK/UNIQUE(workspace,id), FKs compuestas y RLS/grants mínimos. DTO LogisticsModelVersion y fingerprints son la entrada, no un editor arbitrario. |
| M2 | Pack estable + versiones/entries append-only. Manifest, slot, raw/canonical/contract hashes y normalizer version; FK de entrada al mismo tenant/Case/Pack. Pair Orders/Fleet y su dedup legacy se conservan. |
| M3 | Pinning de Run a contexto/model/pack/policies/registry/Transit/upstream; checks por cohorte, replay antes de efectos, locks workspace→Case y eventos append-only. No actualizar snapshots/actores/resultados viejos. |
| Artifact metadata | decision_result_artifacts con owner tenant/Run, kind/part/schema/version, SHA256/size/media, storage locator generado server-side, assembler/core fingerprint, lease/generation y publication state. Result fingerprint se vincula al publicar; FK compuesta diferible a Run y UNIQUE de binding. Lectura vía membership y manifest; ningún grant público por un hash. |
| Compatibilidad | Nullable/dual readers para legacy, ON DELETE RESTRICT en historia consumida. Fresh+upgrade+restore y negativos de tenant/RLS/permissions en sandbox owned. Prohibido repair/baseline replay o backfill implícito. |

No se redactó/aplicó ninguna migración, no se creó una tabla ni se invocó Supabase. El payload/hash de catálogo se define por los descriptores generados; su persistencia/checked RPCs se implementarán sólo bajo autorización de T2.
