# T1 — Domain / Result Contracts + Registry + Transit

## Baseline utilizado

T1 ejecutado exclusivamente bajo la [autorización del usuario](evidence/T1-user-request.txt), posterior a **GO — T0 BASELINE ESTABILIZADO**. Referencia normativa: [Final Master Execution Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), decisiones F01–F23 y sección T1. No se realizó una nueva auditoría transversal.

- Branch: `main`. HEAD inicial y final: `ef997235a30251fbf7ae53690ed738092ee973d8`.
- Inicio registrado: 26/10/2026 09:24:10 America/Buenos_Aires. QA final: 10:14:52–10:15:15, misma zona. Los logs preservan UTC original.
- Baseline oficial: [T0](../t0/t0-execution-report.md), [T0-R](../t0/t0-remediation-report.md) y [T0-R2](../t0/t0-remediation-r2-report.md). T0-R2: Python 383, Node 128, Browser 251, SQL 46, E2E 86 y Focus 9, sin failures/errors/skips.
- El workspace ya contenía cambios pendientes de T0/R/R2. Se preservaron sus bytes; no se restauró, descartó ni staged ningún cambio. Los 248 artifacts del manifest R2 y el propio manifest conservan sus hashes.
- Master Plan SHA256: `c7543ffa1ef26c79d9142797863fc8ba83613f6cb426cf1621eb0c11b5a27823`; plan previo: `ff824a2fae9566cfb4e1f77ae81e8806d0b76d179b208660b29e9bd00e9ab6d6`.

El diff de T1 agrega contratos inactivos, metadata y tests. No hay commit, push, merge, release ni modificación de infraestructura. T2 no fue ejecutado.

## Skills utilizadas

Se aplicó la Execution Skills Policy. Única Skill pertinente utilizada: [cloud-environment:cloud-environment-runtime](evidence/cloud-runtime-skill.txt), origen `skill://plugin_connector_1p_c5b7d5df5d7081918f2c4be5a633ed5d/cloud-environment-runtime/SKILL.md`. Se leyó para readiness del entorno administrado y aislamiento de credenciales en procesos de QA; se verificó con Python/Node existentes. No se usaron sus workflows de Docker, VPN, red o deploy.

No existe una Skill dedicada Python/domain/testing disponible: unittest y los oracles son herramientas, no Skills. UX/UI: N/A, sin interfaz afectada. Supabase/Postgres: N/A, sin operación de base de datos; el handoff documental reproduce las decisiones ya aprobadas. Detalle, propósito y hash: [skills ledger](skills-ledger.json).

## Files Created

Los 17 archivos nuevos de implementación y tests, congelados antes del QA final:

| Archivo desde raíz | Propósito |
| --- | --- |
| `backend/app/domain/logistics/__init__.py` | Exports del dominio Ultimate nuevo |
| `backend/app/domain/logistics/base.py` | DTO base inmutable y Decimal wire exacto |
| `backend/app/domain/logistics/units.py` | Money, moneda, escala, dimensiones y conversiones exactas |
| `backend/app/domain/logistics/contracts.py` | Model, Demand, Resource, Case/NodePolicy y snapshot de admisión |
| `backend/app/domain/logistics/transit.py` | Autoridad única Transit Ultimate |
| `backend/app/domain/logistics/costs.py` | Reglas puras de precio por viaje |
| `backend/app/results/__init__.py` | Exports de contratos nuevos |
| `backend/app/results/contracts.py` | Core/Evidence/Package, delivery, Context, Review y request/response ABI |
| `backend/app/results/canonical.py` | Serialización y DAG de fingerprints |
| `backend/app/results/registry.py` | Resolución explícita de schemas e identidades/runtime y metadata |
| `backend/app/results/metrics.py` | Catálogo versionado de 23 métricas |
| `backend/app/results/reason_codes.py` | Catálogo de 24 reasons y validación de facts/claims |
| `backend/app/static/contracts/result-contracts-v1.json` | Metadata JSON/JSON Schema consumible, generada desde los DTOs |
| `backend/tests/ultimate_fixtures.py` | Fixtures hipotéticos literales; ningún producer nuevo |
| `backend/tests/test_ultimate_contracts.py` | 53 tests de contratos, compatibilidad y hashes |
| `backend/tests/test_ultimate_transit.py` | 8 tests de fronteras, calendario y ciclo |
| `backend/tests/fixtures/ultimate/fingerprint-vectors-v1.json` | Preimages y goldens determinísticos |

Entregables documentales nuevos bajo esta carpeta: este reporte, [especificación ABI](abi-specification.md), [test ledger](test-ledger.json), [command ledger](command-ledger.json), [skills ledger](skills-ledger.json), [estado final](final-workspace.json), [manifest de integridad](artifact-integrity.json) y `evidence/`. El manifest enumera cada archivo y hash; los logs intermedios también se conservan.

## Files Modified

**Ningún archivo preexistente fue modificado por T1.** Los 29 archivos tracked previamente modificados permanecen idénticos al inicio; los archivos nuevos y la migración pendientes de etapas anteriores también se conservan. La presencia de CSS, tests Browser/E2E y SQL en `git status` corresponde al baseline recibido, no a trabajo nuevo de T1.

`dispatch_job_service.py` no necesitó cambios: la modificación prevista era condicional. El nuevo resolver ya exige identidad persistida completa; la conexión al worker y la admisión Ultimate siguen en T8/T9, antes de habilitar nuevos runtimes. No se cambió registry, serializer, schema, helper de fecha, export ni engine legacy.

## Contracts implemented

Contratos nuevos aditivos y versionados, con validación estricta, extra fields rechazados, estructuras inmutables y revalidación de instancias:

- Dominio logístico: `LogisticsModelVersion`, `Demand`, `TransportResource`, `FrozenCaseContext`, `CasePolicy` y `NodePolicy`. DIRECT, role, dimensiones, horizon, source, garantía y disponibilidad son explícitos. Un override requiere motivo y conserva hard guardrails. El snapshot de admisión no reemplaza el Case vacío de T3.
- `EngineCoreResult`, `EngineEvidence`, `EngineOutput`, `DecisionResultPackageV1` y `ResultContractBundle`, con cuerpos especializados D1/D2. Binding de Run/workspace/context/core, métricas, policy, Trips y reasons del bundle suministrado se comprueban sin ensamblar ni producir resultados.
- `FingerprintSet`, `ResultArtifactReference`, `DetailDatasetDescriptor`, `MetricDescriptor`, `ReasonCodeDefinition`, `AlternativeDescriptor`, `ExceptionDescriptor` y `AssumptionDescriptor`.
- `DecisionContextV1`: EXPLAIN/EXPLORE/COMPARE/REVIEW; referencias seleccionadas, alternativas certificadas, provenance, context hash e intent hash v2. Sólo ABI: sin retrieval ni llamadas LLM.
- `ApprovalReview` determinístico separado de `ApprovalOverlay.approval_allowed`, autoridad actual exterior al package inmutable. Las respuestas ligan overlay y resultado al mismo Run/fingerprint.
- INLINE y REFERENCE versionados. Dataset vacío válido requiere row_count cero; missing/corrupt son errores explícitos y jamás `[]`. References ligadas a tenant, Run, core, schema y manifest; no URLs arbitrarias.
- DTOs de proyecciones Sankey/Gantt y de detalle/export: contratos de datos solamente. Sin chart, dashboard, renderer, assembler ni producer nuevo.
- ABI declarativa de siete rutas nuevas, todas `implemented: false`. Request discriminado con pinning/contexto; sin engine ni closure elegidos por el cliente. No se instaló ningún endpoint.

El handoff M1–M3/artifact metadata/FKs/grants de T2 queda en la [especificación ABI](abi-specification.md). Es documentación, sin migrations, tablas, backfill, SQL ni escritura remota.

## Registry changes

El registro nuevo distingue **schema known**, **runtime implemented** y **runtime available**. Resuelve por engine name/version, runtime profile y result schema/version persistidos; `node_id` no es autoridad para perfiles nuevos. Unknown/version mismatch/header conflict falla explícitamente, sin fallback a Dispatch.

| Schema conocido | Runtime / version | Profile | Implementado / disponible |
| --- | --- | --- | --- |
| `assignment_v1` / 1 | `logistics-assignment-engine` / 1.0.0 | Ausente legacy | Sí / sí, en código existente |
| `scheduling_v1` / 1 | `logistics-scheduling-engine` / 1.0.0 | Ausente legacy | Sí / sí, en código existente |
| `dispatch_v2` / 2 | `logistics-dispatch-engine` / 2.2.0 | Ausente legacy | Sí / sí, en código existente |
| `transport_plan_v1` / 1 | `transport_plan` / 2.0.0 | `transport_plan_v1` | **No / no** |
| `day_scheduling_v1` / 1 | `day_scheduling` / 2.0.0 | `day_scheduling_v1` | **No / no** |

El lookup legacy conserva identidad y headers originales. El adapter puro `error` → `FAILED` no renombra el estado persistido. La disponibilidad de código no sustituye permisos, entitlements, Owner, freshness ni guards de admisión.

## Transit implementation

`TransitEstimator`, versión `DATION_TRANSIT_V1`, es la única autoridad Ultimate nueva: 500 km/día. Calcula con aritmética exacta `ceil(distance/500)` para outbound y, independientemente, `ceil(2*distance/500)` para ciclo OWN. EXTERNAL tiene cycle NULL. Arrival = dispatch + outbound − 1; OWN available_again = dispatch + cycle. No se duplica la fórmula en contratos/callers ni se modifica ningún helper legacy.

Fronteras verificadas: 120→1; 500→1; 501→2; 1000→2 outbound. OWN 480→outbound 1/cycle 2; OWN 501→cycle 3. Fechas inclusivas/exclusivas, cruce de mes/bisiesto, precisión decimal e independencia del contexto Decimal también pasan. Horizon limita las salidas, permite llegada/retorno posteriores.

`trip_cost` es un helper puro: EXTERNAL PER_TRIP/PER_KM con billing ONE_WAY/ROUND_TRIP; OWN operating cost de ciclo DIRECT. No decide asignación/factibilidad ni produce una métrica total_cost alternativa.

## Canonicalization / fingerprints

`DATION_CANONICAL_V1`: UTF-8, NFC, keys ordenadas, Decimal exacto sin exponente, fechas ISO y timestamps UTC. Rechaza floats, nonfinites, keys no string, colisiones NFC y valores no representables. Tipos se validan antes del hash; no se adivinan números a partir de strings genéricas. Domain separation incluye kind/version.

El DAG implementado es Input Context → input hash → Core → core fingerprint → artifact content SHA256 → Package/manifest → result fingerprint. No depende de un campo futuro contenido en sí mismo. Artifacts no contienen el result fingerprint futuro propio; pueden referenciar un upstream pasado.

Los hashes **matemáticos** excluyen Run/display/clock/actor actual y overlays. El result fingerprint es identidad **de publicación**: conserva Run, contexto histórico, fecha de publicación y manifest; excluye su autocampo. Permisos actuales, signed URLs y approval overlay van por fuera. Esta distinción preserva §8.4 del Master.

Goldens tipados y preimages quedan versionados. Dos procesos independientes con `PYTHONHASHSEED=1` y `2701` produjeron exactamente los mismos cuatro hashes: [evidencia](evidence/cross-process-vectors.json). Los tests verifican además cambios semánticos, invariancia de orden/Unicode, exclusiones y ausencia de ciclos. No se reserializó ningún resultado histórico.

## Reason Code catalog

24 IDs del contrato fuente, cada uno con stable ID, version, entity scope, producer único, facts requeridos tipados, claim strength y translation/message key. Un `ReasonEmission` sin facts suficientes, nulos o del tipo incorrecto es inválido. Las referencias a códigos del Core no son claims independientes: EngineOutput/bundle/package requieren la evidencia correspondiente.

Se comprueban witnesses locales y requisitos de certificados: OPTIMAL exige proof/bound; UNKNOWN no acredita infeasibilidad global, pero permite un witness local independiente válido. CAPACITY_GAP representa residual observado. No se genera ningún reason con IA ni se implementa el certificador matemático de T6–T9.

## Metric / Money / Unit contracts

23 MetricDescriptors versionados con schema/path, producer único, unidad, precisión, null semantics y referencias de numerador/denominador. Los DTOs verifican valores suministrados; no crean un segundo productor de KPIs.

Decimal wire finito exacto en string, con input entero lossless admitido; sin floats. Money en unidades mayores, currency explícita y política minor_units 0–6 / ROUND_HALF_UP fijada en el snapshot. Escalado exacto y overflow signed64 controlado. Cargas pallets/units/kg hasta 3 decimales; m³ 6; distancia 3; tarifa 6; allocation fraction 6; ratios 4. Un Model puede exigir granularidad más estricta. Conteos enteros seguros separados de cantidades.

`null != 0`; disponibilidad desconocida no es confirmada ni ilimitada; maximum no sustituye guaranteed; costo desconocido no se inventa cero. Sin FX ni defaults de moneda del workspace actual. Denominador cero → NULL. Las cinco categorías D2 son disjuntas; compliance esperado usa ON_TIME + AT_RISK sobre todas las Trips. No hay matemática de solver D1/D2 nueva.

## Tests executed

Candidate source congelado antes de los tres runners; sus 17 hashes siguen idénticos al terminar. Python 3.13.5, Node 24.19.0, Pydantic 2.14.0 y FastAPI 0.143.0 existentes; sin dependencias instaladas. Credenciales de Supabase/LLM/GCP anuladas en los procesos hijos. Sin DB, Docker, browser ni API remota.

| Suite | Estado T1 | Count ejecutado | Failures | Errors | Skips | Duración wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| U1 | PASS | 61 | 0 | 0 | 0 | 1.901 s |
| B-PY | PASS | 444 | 0 | 0 | 0 | 19.444 s |
| B-NODE | PASS | 128 | 0 | 0 | 0 | 1.768 s |
| B-BROWSER | NOT RUN | 0 | N/A | N/A | N/A | N/A |
| B-SQL | NOT RUN | 0 | N/A | N/A | N/A | N/A |
| B-E2E | NOT RUN | 0 | N/A | N/A | N/A | N/A |
| B-FOCUS | NOT RUN | 0 | N/A | N/A | N/A | N/A |

Los 61 tests U1 están incluidos en los 444 B-PY; no son 61 casos adicionales a ese total. B-PY retiene los **383 IDs previos completos**. B-NODE conserva exactamente sus 20 archivos/argv y 128 tests.

Browser/SQL/E2E/Focus conservan la evidencia aprobada de T0-R2 (251/46/86/9); **no se presentan como PASS nuevo de T1**. No se tocaron sus fronteras activas y el usuario excluyó repeticiones redundantes. No hubo suite requerida FAIL/BLOCKED al cierre.

Pruebas focales adicionales:

- [OpenAPI](evidence/api-preservation.json): igualdad exacta con T0, 91 paths/98 operaciones. Import sin startup, requests ni escrituras.
- [Hashes entre procesos](evidence/cross-process-vectors.json): iguales con ambos seeds.
- [Budgets](evidence/payload-budgets.json): fixtures hipotéticos D1 7,534 bytes/D2 6,737 bytes frente a package 524,288; visuales 361/336 frente a 262,144; contexto 4,263 bytes. Sin claim de performance de producción ni chunks reales. Se declaran chunk 1MiB/100 entidades, página 100 y selección 50KiB.
- [Preservación](evidence/legacy-preservation.json): 248 artifacts baseline, manifest, tracked changes y 17 archivos del candidate idénticos a sus snapshots.

La primera iteración U1 tuvo 56 tests con 1 FAIL y 1 ERROR por roundtrip/alias de los DTOs nuevos; se corrigieron sin desactivar tests ni cambiar legacy. Se conservan ese log, los reintentos y las ejecuciones anteriores al endurecimiento final de facts/witnesses/schema binding. El estado PASS es el de los logs finales y no oculta esos intentos.

Comandos exactos, tiempos y hashes en [test ledger](test-ledger.json) y [command ledger](command-ledger.json). Logs finales: [U1](evidence/U1.log), [B-PY](evidence/B-PY.log), [B-NODE](evidence/B-NODE.log). El runner reproducible y la verificación focal están preservados en `evidence/`.

## Legacy regression assessment

PASS dentro de las fronteras de T1: ningún archivo legacy modificado, los 383 tests Python retenidos, Node intacto y OpenAPI idéntico. `assignment_v1`, `scheduling_v1` y `dispatch_v2` conservan sus identidades, schemas, serializers, exports y date helpers. No hay backfill ni reinterpretación de Runs históricas.

El comparador contractual D2 rechaza cambiar upstream Run/fingerprint, tenant/Case, Trips o recursos del D1 suministrado. No se modificó ningún mecanismo de aprobación, invalidación, lineage o historial existente. Los tests de races/SQL/publicación real corresponden a sus fases autorizadas posteriores, no quedan certificados por estos DTOs.

## Deviations from Master Plan

Sin cambios a F01–F23, stack, arquitectura ni alcance de fase. Se agregaron módulos auxiliares `base.py`, `units.py`, `costs.py`, `metrics.py` y fixtures para separar responsabilidades de los módulos equivalentes esperados; permanecen dentro de los paths previstos.

No se modificó el dispatcher por ser condicional y no existir producer/admisión Ultimate. La precisión Decimal, minor units y budgets se cerraron como parámetros versionados pendientes de T1, tal como permite el Master; no son nuevas decisiones de producto. No hay migración, endpoint activo ni implementación adelantada.

## Risks discovered

- Cerrados en T1: fallos iniciales de roundtrip/aliases, facts genéricos que perdían exactitud, binding entre schema y filas/referencias y posible inclusión de overlays mutables. Las validaciones y tests finales cubren sus negativos.
- Delimitación explícita: un DTO validado no prueba factibilidad del solver, igualdad matemática completa de proyecciones, existencia/integridad de bytes remotos ni permisos actuales. Certificadores/producer/assembler/publicación/retrieval siguen en T6–T10. Ambos runtimes nuevos permanecen no disponibles.
- El registry nuevo debe conectarse antes de admitir perfiles Ultimate en T8/T9; consumers/exporters nuevos deberán usar resolución exhaustiva. No se ampliaron los fallbacks históricos en T1.
- Las mediciones de payload son fixtures ABI pequeños; chunking, escala real, performance, restore y races se validarán en sus fases. No se les asigna PASS de producción ahora.

No existe STOP CONDITION sin resolver en el alcance T1. Estos límites no autorizan adelantar fases.

## STOP / GO gate evaluation

| Gate | Resultado T1 | Evidencia / alcance |
| --- | --- | --- |
| G-A | PASS | Sólo contratos/helpers/catalogs/tests/evidencia autorizados; sin auditoría transversal ni escritura remota |
| G-C | PASS | ABI aditiva, JSON metadata coincidente, unknown falla, reasons con facts y legacy preservado |
| G-B | PASS | 383 IDs retenidos + 61 nuevos; Node 128; cero failures/errors/skips |
| G-E | PASS, contractual | Transit/costos/policy y claims probados; ningún engine nuevo habilitado; no certifica T6/T9 |
| G-R | PASS, contractual | Binding Core/Evidence/Package, NULL y DAG determinístico; no certifica consumers/publicación futuros |
| G-L | PASS, contractual | Upstream D2 fijado; ningún Run/historial/invalidation existente cambiado; races quedan en T8/T11 |
| G-S | PASS, contractual | Refs tipadas y owner bindings; overlays fuera del package; sin cambios auth/DB/LLM; no certifica RLS futuro |
| G-P | PASS, contractual | Budgets versionados y fixtures medidos; no certifica chunker/latencia reales |
| G-ENV | PASS | Runners requeridos disponibles, >0 tests, sin skips; cero operaciones productivas |
| G-D | N/A | Ninguna DB/migration aplicada; sólo handoff documental para T2 |
| G-UI | N/A | Sin cambios de interfaz ni Skills UX/UI |
| G-REL | N/A | Sin commit/push/deploy ni release autorizado |

Se comprobaron las STOP CONDITIONS explícitas: no reinterpretación legacy, productor duplicado de métricas, fallback unknown→Dispatch, reason emitido sin facts, Transit duplicado, hashes no determinísticos, cambio F01–F23 o necesidad de migration T2.

Rollback T1: retirar únicamente los módulos/metadata/tests nuevos inactivos, conservando baseline y evidencia. No requiere rollback de DB ni de producción. El trabajo queda revisable y sin staging. Ver [estado final](final-workspace.json) e [integridad](artifact-integrity.json).

## FINAL T1 DECISION

**GO — T1 completado. T2 puede ser solicitado.**

T2 no se ejecutó. La ejecución termina con este reporte, sin commit, push ni despliegue.
