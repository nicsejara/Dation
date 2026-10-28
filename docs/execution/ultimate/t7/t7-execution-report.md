# T7 — D1 Policy / Cost / Coverage + Result & Evidence Assembler

Fecha: 27/10/2026, America/Buenos_Aires. Los logs conservan timestamps UTC.

Se completó el perfil D1 de pruebas con policies, precios, cobertura priorizada, guardrails, métricas certificadas, alternativas materiales y assembly puro de `transport_plan_v1`. El resultado es un AssemblyBundle en memoria con package, bytes preparados y contexto IA enlazado. No se conectó admisión, publicación, worker, DB/Storage o consumidores productivos. T8 no fue ejecutado.

## Baseline T6

Fuentes: [autorización T7](evidence/T7-user-request.txt), [Master Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), T7, §8–§10, §13–§14, §22–§23 y fixtures B/C/F/G/N/O/R1–R8. Baseline inmediato: [T6 aprobado](../t6/t6-execution-report.md). Se inspeccionaron sólo Core/Evidence T6, contratos/helpers T1, `app/results/`, catálogos y tests afectados. No hubo nueva auditoría end-to-end ni repetición de T0–T6 como fases.

- Branch `main`; HEAD `ef997235a30251fbf7ae53690ed738092ee973d8`.
- Antes de modificar se verificaron las **33 entradas** del manifest T6, sin discrepancias, y staging vacío.
- El árbol ya estaba modificado por T0–T6. No hubo reset, clean, descarte de archivos, checkout, staging, commit, fetch, push o deploy.
- Python **3.13.5**, OR-Tools **9.15.6755**, Node **24.19.0**, dependencias ya disponibles. No se instalaron herramientas.

## Checkpoint

Se preservó un checkpoint equivalente mediante SHA256, copias exactas y patch tracked binario, sin escribir en `.git`, cuyo acceso está restringido a lectura por la política del entorno.

- **786 archivos**, **41.092.786 bytes** en `/workspace/work/dation-t7/post-t6/`.
- Hash del inventario: `ccd39855e9a82c9f44e0a70fe7d5ff368e0d959e85da8dc4e30ec7c3222a104c`.
- [Inventario post-T6](evidence/initial-state.json), [patch previo](evidence/post-t6-tracked.patch), [preservación](preservation.json).
- Al cierre, **782 archivos conservan sus bytes actuales**; cuatro módulos se extendieron intencionalmente y tienen preimágenes preservadas. Las 33 entradas T6 se resuelven contra el archivo actual o su preimagen, sin reescribir su manifest/reporte.
- [Scope diferencial](scope-diff.json), [patch T7](evidence/t7-changes.patch), [integridad](artifact-integrity.json). El diff de T7 se calcula contra este checkpoint, no contra todos los pendientes acumulados de HEAD.

## Skills

Se aplicó la Execution Skills Policy: arquitectura/contratos aprobados → comportamiento existente → Skill como apoyo. [Ledger](skills-ledger.json).

| Disponibilidad | Aplicación / decisión |
|---|---|
| `cloud-environment:cloud-environment-runtime` | Leída al reanudar; entorno running/connected con observaciones actuales, runners locales y credenciales productivas vacías en QA |
| Python / optimización / testing | Sin Skill dedicada disponible; se usaron contratos, OR-Tools existente, unittest, certificadores y oráculos independientes |
| UI / Supabase / Docker | N/A: no frontend, SQL, nuevas migraciones, contenedores o proyectos remotos |

No se instalaron Skills/herramientas, ejecutaron generadores o usaron subagentes. Ninguna recomendación amplió el alcance.

## Files created

Paths relativos al repositorio:

| Archivo | Entregable |
|---|---|
| `backend/app/engines/assignment/transport_policies.py` | Constraints y objetivos lexicográficos T7 sobre el modelo CP existente |
| `backend/app/engines/assignment/transport_policy_result.py` | Producer final D1, costos, métricas, reasons y alternativas |
| `backend/app/engines/assignment/transport_policy_validator.py` | Certificación independiente de precios, policy y comparaciones |
| `backend/app/results/assembler.py` | AssemblyBundle, manifests y bytes determinísticos, sin IO/publicación |
| `backend/app/results/projections.py` | Sankey, datasets, summaries, exceptions/assumptions y partición de evidencia |
| `backend/app/results/approval_review.py` | Review determinístico, separado de aprobación actual |
| `backend/app/results/export_rows.py` | Filas Trip–Order con reconocimiento de costo una sola vez |
| `backend/app/results/ai_context.py` | Base ligada al Core y binding posterior al package, sin LLM |
| `backend/app/results/validation.py` | Verificación cruzada de Core/proyecciones/bytes y reconstrucción de evidencia |
| `backend/tests/test_transport_plan_policies.py` | 20 tests U7 de engine/policy y oráculos |
| `backend/tests/test_transport_result_package.py` | 26 tests U7 de package/consistencia e integridad |
| `backend/tests/fixtures/ultimate/t7-fixtures.json` | Fixtures controladas B/C/N/F/G/O versionadas |

También se crean este reporte, ledgers y evidencia de ejecución.

## Files modified

| Archivo | Extensión acotada |
|---|---|
| `backend/app/engines/assignment/transport_model.py` | Hook interno de policy; T7 considera ofertas/unidades finitas completas bajo budgets. Camino estructural T6 por defecto preservado |
| `backend/app/engines/assignment/transport_plan.py` | Hook opcional de policy y presupuesto de kernel, sin cambiar el comportamiento T6 por defecto |
| `backend/app/engines/assignment/transport_contracts.py` | SearchTrace privado distingue `D1_POLICY_V1` del perfil estructural T6 |
| `backend/app/results/registry.py` | `resolve_test_policy` por identidad completa; disponibilidad pública sin cambios |

Total: **16 archivos fuente/fixtures/tests: 12 nuevos, 4 modificados**. No se modificaron contratos/catálogos T1, metadata estática, frontend, legacy engines, exports/comparative service legacy, SQL, infraestructura o configuración productiva.

## Policy hierarchy

Jerarquía implementada por solves secuenciales y restricciones de igualdad sobre cada optimum probado:

1. Constraints físicas T6 y hard guardrails de la Node Policy, que ya valida que no relaja los de Case.
2. Máxima cobertura factible HIGH → MEDIUM → LOW sobre la cantidad primaria, manteniendo todas las dimensiones físicas activas.
3. Primary Goal.
4. Preferencias inferiores y tie-break estable por orden de recursos/slots.

Soporta `MINIMIZE_COST`, `MAXIMIZE_SERVICE`, `MAXIMIZE_OWN_CAPACITY`, `MINIMIZE_TRIPS`, `BALANCED`, `CUSTOM`. El caller principal no acepta un goal arbitrario que sustituya la Node Policy congelada. Los goals alternativos son exploraciones internas declaradas, conservando inputs y hard guardrails.

`D1_POLICY_V1` hace explícitas las bases de evaluación: coverage sobre primary quantity; demanda crítica HIGH; source share sobre Trips, consistente con `resource_mix` T1; un denominador vacío es una condición vacua del bound, mientras la métrica conserva NULL. Goal de capacidad propia maximiza cantidad primaria asignada a OWN, separado de esa métrica de mix por Trips. Estos parámetros se conservan en el certificado de policy.

BALANCED usa pesos iguales de COST/TRIPS/SERVICE/OWN_CAPACITY cuando no existen preferencias explícitas; CUSTOM usa sus pesos T1. Los términos inferiores se normalizan a escala 10.000 contra bounds explícitos del modelo. Pesos, bounds, escala y resultados de cada etapa están en Evidence. No existe epsilon monetario ni combinación de prioridades con costo que pueda comprar una violación hard.

## Cost model

El producer usa la autoridad T1 `trip_cost`:

- EXTERNAL PER_TRIP: tarifa por servicio.
- EXTERNAL PER_KM: tarifa × distancia × ONE_WAY/ROUND_TRIP.
- OWN: tarifa operativa/km × distancia DIRECT de ida y vuelta a base.
- Currency/minor units/ROUND_HALF_UP del contexto; sin FX, fixed fees, ingresos o margen implícitos.

Los certificadores verifican precios independientemente desde facts de input y fórmulas explícitas. Costo requerido desconocido bloquea una policy económica mediante `POLICY_COST_REQUIRED`; no se reemplaza por cero. Goals no económicos pueden producir costo UNKNOWN/PARTIAL y total NULL. El costo conocido de una solución vacía por demanda vacía es cero; UNKNOWN o INFEASIBLE sin solución utilizable conserva costo NULL y no ofrece CSV de plan.

Oráculos literales: B OWN30km×2/km×2=**120**, elegido frente a externo300; C OWN480km=**1920**, elegido externo**800**; N PER_KM100km ONE_WAY=**100**, frente a150; ROUND_TRIP=200, elegido PER_TRIP**150**. Los oráculos no llaman al helper productivo.

## Priority

La cobertura prioritaria queda fijada antes de objetivos/preferencias económicos. G conserva **HIGH30 + MEDIUM10**, residual MEDIUM20, con capacidad40, independientemente del orden de filas. Un reason de protección de prioridad sólo se emite con la etapa HIGH probada y candidate set completo en el scope declarado, no por observar una etiqueta HIGH.

Las órdenes con primary quantity cero siguen sujetas a sus otras dimensiones y tienen una etapa secundaria de cobertura sin desplazar los optima primarios. No se suman pallets, kg, volumen y units como si fueran una sola cantidad.

## Coverage / gap

Se mantienen conservation, split vectorial exacto, non-split, garantizadas, cuotas y kernel T6. El engine conserva todas las órdenes, assigned/residual por dimensión, Trip/resource refs y estados COVERED/PARTIALLY_COVERED/UNASSIGNED.

F produce **assigned52 / residual18 / 2 Trips**, un resultado parcial válido con `CAPACITY_GAP` observado y policy feasible cuando los guardrails lo permiten. A conserva **70 / gap0 / 3 Trips / costo350**. MINIMIZE_COST no elige vacío para ahorrar cuando la demanda es servible dentro de los hard bounds.

Un hard guardrail imposible no se relaja: con prueba completa devuelve INFEASIBLE, `policy_feasible=false`, sin recomendación utilizable. Un solve o candidate set incompleto no se usa para certificar imposibilidad global. Mathematical/solver status, policy feasibility, hard constraints y full coverage permanecen campos distintos.

## Metrics

Engine/certificador producen total_cost/completeness, trip_count, requested/assigned/residual/coverage, weighted utilization, mix por Trips, resources_used y coverage_by_priority. El assembler copia estas métricas y las verifica; no mantiene otra versión que prevalezca sobre Core.

Weighted utilization = `sum(load de Trips usados) / sum(guaranteed capacity de Trips usados)`, sobre primary dimension. R2 verifica 4/12 = **0,3333**, distinto del promedio simple de 50% y30%=40%. Denominadores cero producen NULL. ResourceUsage incluye servicios available/used/remaining/availability, unidades propias, loads, distancias, utilization y costos.

## Solver status / budgets / determinism

Se preservan OPTIMAL, FEASIBLE, UNKNOWN e INFEASIBLE. OPTIMAL exige todas las etapas nativas OPTIMAL, candidate set completo y certificado con valores/bounds por etapa. El objective value/bound resumen corresponde al Primary Goal; el certificado conserva también coverage y tie-breaks. Un FEASIBLE no se promueve por apariencia a OPTIMAL.

T7 amplía la cantidad de slots frente al bound estructural T6 para considerar la oferta finita que también puede intervenir en guardrails de mix. Continúan los límites de órdenes/recursos/horizonte/slots/variables y los guards numéricos de T6; un corte declara scope incompleto y evita prueba global. Se mantiene la compatibilidad/consolidación conservadora aprobada en T6, sin habilitar mezclas nuevas.

El presupuesto determinístico se reparte: recomendación primero, 70% del presupuesto de modelo cuando se exploran alternativas; 30% entre hasta tres exploraciones. El presupuesto de kernel se reparte entre verificación temporal y comparaciones locales, incluyendo la repetición independiente de esas pruebas. Sin alternativas, el modelo recomendado dispone del presupuesto de modelo completo. Se registran asignaciones, seed, versión de solver, hashes y límites. Hay un worker y límite defensivo de pared por solve.

Orden de IDs estable, fracciones/racionales y Decimal de T6 preservados. Mismos inputs/config/versión/seed dan recorridos reproducibles dentro de esos budgets; un cutoff de pared puede modificar calidad/status y debe permanecer explícito. No hay dependencia del orden de CSV.

## Reasons / independent certification

Se preservan reasons estructurales T6. Los nuevos claims positivos requieren prueba concreta:

- `SELECTED_PRIORITY_PROTECTION`: trace de cobertura prioritaria.
- `SELECTED_ONLY_FEASIBLE_RESOURCE`: conjunto completo de sustituciones factibles de esa Trip.
- `SELECTED_LOWEST_COST_FEASIBLE`: comparación de costos conocida y completa.
- `SELECTED_OWN_COST_ADVANTAGE`: alternativas externas comparables y más costosas.

El scope local de recursos mantiene las demás Trips fijas, revalida cuotas/tiempo con el kernel y declara candidates completos. Se limita a casos pequeños; si hay UNKNOWN, costo insuficiente o presupuesto no concluyente, se omite el claim. El certificador independiente revisa costos, guardrails y esas comparaciones; no confía sólo en el objetivo/status del solver. El assembler no emite reasons.

## Alternatives

Recomendación + **0–3 alternativas**, sobre los mismos inputs/Model/contexto y hard constraints. Se explora un set acotado/versionado de goals, con presupuesto reservado. Se excluye el mismo plan con otro label o reordenamiento de IDs; materialidad V1 requiere cambio real de allocations o resource assignments.

Cada alternativa conserva Core/Evidence completos, plan y evidencia de entidad recuperables, solver status, policy de exploración, metrics, fingerprints y deltas con units/null handling. No es otra Run aprobada ni una Branch. La recomendación no se modifica por abrir o ensamblar las comparaciones.

T1 mantiene el enum raíz `NOT_COMPUTED / COMPUTED_NONE / COMPUTED`. La metadata versionada `analysis-status` aclara `BUDGET_LIMIT / NOT_COMPUTED / NO_MATERIAL_ALTERNATIVE / COMPUTED`, scope y goals explorados. `COMPUTED_NONE` significa que no se encontró una alternativa material en ese análisis; no una demostración universal de que no existe ninguna.

## Result & Evidence Assembler

Boundary puro: `assemble(policy_result, frozen_context, versions) -> AssemblyBundle(package, artifacts, context)`. Recibe el resultado ya certificado; verifica schema/version, contexto y facts antes de preparar bytes.

Puede copiar, unir por IDs, ordenar/proyectar, construir templates/review/context/export y verificar consistencia. No lee DB/Storage, no llama al optimizador, no reemplaza asignaciones, no elige otra recomendación y no aprueba. `resolve_test_policy` y el assembler permanecen fuera de la admisión pública.

## transport_plan_v1

Package completo conforme a T1: root especializado, summary, metrics, Trips y demanda residual, seis datasets, SANKEY, alternativas, exceptions/assumptions, evidence, review, exports, IA base, manifest y fingerprints. Sin schema fallback a Dispatch.

Se preparan bytes JSON canónicos y refs determinísticas con workspace/Run/core fingerprint, schema/version, role/part, SHA256 y tamaño. Los artifacts contienen bindings ya conocidos al Core, sin el result fingerprint futuro.

## Sankey

Destination → Trip → Resource, exclusivamente primary reporting dimension. Cada corte transporta el mismo load: F tiene 52 en Destination→Trip y52 en Trip→Resource; sumar ambos daría104 y no se utiliza como cobertura.

IDs gráficos type-qualified opacos, sin colisiones con IDs de negocio. El artifact `sankey-entity-index` vincula nodos TRIP/RESOURCE con sus EntityRefs reales. Destination es una dimensión/filtro del Case en T1; su mapping conserva destination_id explícito sin inventar un EntityType nuevo ni usar el label como lookup. No hay Trip ficticia para residual, layout/frontend nuevo o mezcla de unidades.

## Detailed Analysis datasets

| Dataset ID | Datos certificados / descriptor |
|---|---|
| plan | Trip rows con allocations/precios, orden trip_id |
| demand | EntityEvidence por orden con requested/assigned/residual por dimensión, status, coverage y Trip/resource refs |
| resources | ResourceUsage tipado, costos y disponibilidad preservada |
| alternatives | Metadata de alternativas, plan/core fingerprint, status, metrics/deltas y refs del root |
| exceptions | Mismos objetos/facts/reason refs del package |
| evidence | EntityEvidence completo y referencias a constraints/reasons íntegros |

Cada descriptor declara row schema/version, columns/formats/units, primary key, stable order y refs/hash/cardinalidad. El envelope de delivery declara FULL, índices/cantidad de chunks y total_rows; no hay top-N silencioso. Alternatives/Exceptions usan el tipo EVIDENCE y filas EntityEvidence de la unión T1, distinguidos por dataset_id; no se altera un enum congelado para simular otra ABI.

## Evidence delivery

Filas/chunks hasta 100 entidades y 1MiB; package hasta512KiB y visual inline hasta256KiB conforme a T1. La evidencia pesada usa `PARTITIONED_ENGINE_EVIDENCE_V1`: filas EngineEvidence tipadas, mismo header y partitions explícitas, con reconstrucción íntegra y detección de IDs contradictorios. Los refs no anuncian una partición como el documento completo.

U7 reconstruye evidencia de más de1MiB sin truncación, y prueba 205 filas divididas en tres chunks. Falta/corrupción de un artifact produce error de integridad, no array vacío. Un único row indivisible que exceda el límite falla cerrado; no se afirma un benchmark productivo ni soporte ilimitado de Core/entidades.

## Exceptions / Assumptions

Se proyectan sólo desde reasons existentes y sus mismos facts. Gap se presenta como BUSINESS; restricciones de fecha/capacidad como FEASIBILITY y falta de compatibilidad como DATA. No se transforma un error técnico en excepción de negocio. Policy infeasible se expresa en feasibility/constraints/review, sin inventar un reason de catálogo para rellenar una excepción.

ASSUMED sigue ASSUMED. La proyección usa source DERIVED al describir el hecho operativo aportado: el DTO no autoriza inferir un actor confirmado ni distinguir DATION_DEFAULT de una entrada manual por observar un count. No se inventa provenance USER_CONFIRMED. Review/IA referencian los mismos objetos.

## Approval Review

Review determinístico de coverage FULL/PARTIAL/NONE/UNKNOWN, hard constraints, policy feasibility, solver outcome, exceptions y assumptions. Partial puede ser review-ready si satisface la policy. UNKNOWN o INFEASIBLE sin solución no lo son.

`decision_ready_for_review` no concede `approval_allowed`: no hay overlay mutable, permisos/freshness actuales o aprobación dentro del package/hash. Eso sigue para T8.

## Export rows

Filas preparadas para `Transport_Plan.csv`, una por Trip–Order allocation. Costo reconocido en la primera allocation ordenada de cada Trip; las demás tienen NULL. No se distribuye proporcionalmente ni se duplica. R1 verifica un Trip100 con dos filas **100 / NULL**, suma100.

Con costo completo, la suma exportada coincide con total_cost; con costo incompleto se conserva NULL/completeness. Sin solución utilizable, CSV no disponible y rows=NULL. JSON describe el package completo sin referencia a un artifact futuro autorreferenciado.

## AI Context

Base `decision_context_v1` ligada al Core: Case, Model/version, horizonte, Case/Node Policy, Decision Definition, input summary, result summary, metrics, exceptions/assumptions, evidence, alternatives, review y entity refs. Sin CSV raw, proveedor LLM o texto inventado.

`DECISION_CONTEXT_BASE_V1` distingue el payload de storage preparado de la respuesta enlazada T1. Primero se hashea la base sin provenance del package futuro; después de completar el package, `bind_context` añade `{run_id,result_fingerprint}`, mode/selection y calcula context_hash. El contexto enlazado devuelve el DTO exacto `DecisionContextV1`; no se introduce un ciclo ni cambia su ABI.

## Fingerprints / manifests

Se aplica el DAG T1: input_context_hash → core_result_fingerprint → SHA de bytes de artifacts → result_fingerprint de package/manifest. Assembler/contract/runtime/Transit versions y refs quedan en su nivel correspondiente. El propio result_fingerprint se excluye únicamente de su proyección de hash.

IDs de artifacts derivados determinísticamente de Run/role/part/content; cada ref coincide con bytes exactos, tenant/Run/Core y manifest. Nada incorpora signed URLs, current permissions, approval overlays o el hash futuro del package dentro de artifacts. Los Core históricos no se reensamblan.

## Consistency validation

Antes de devolver AssemblyBundle se verifica Core/Evidence T1, conservación, costos, métricas, resoluciones, summaries, datasets, Sankey por corte, export por allocation/costo, review/IA y manifests/bytes. También se comprueba recuperación de Core/Evidence de alternativas.

Los tests negativos introducen deliberadamente costos duplicados, Sankey duplicado, summary inventado, Core cambiado y artifacts ausentes/corruptos. Assembly falla; no corrige el Core ni fabrica datos. Ningún candidato real de QA quedó en desacuerdo con sus certificadores. Esos negativos esperados no representan una STOP CONDITION abierta del producer.

## Tests

Comandos, timestamps, duración, exit code y SHA de logs: [test ledger](test-ledger.json), [command ledger](command-ledger.json), [candidate congelado](evidence/candidate.json).

| Suite | Tests | Duración | Resultado | Failures/errors/skips |
|---|---:|---:|---|---|
| B-PY | 614 | 35,915 s | PASS | 0/0/0 |
| B-NODE | 137 | 4,446 s | PASS | 0/0/0 |
| U7, dos módulos; también incluidos en B-PY | 46 | 6,204 s | PASS | 0/0/0 |

Los 47 tests U6 pasan incluidos en B-PY; A/D/E/M y kernel no se reejecutaron como una fase nueva. U7 agrega los oráculos B/C/N, F/G/O y **nueve combinaciones independientes** de packing/precios con cantidades diferentes, enumerando placements finitos sin helpers/objetivo del solver productivo.

R1–R8 PASS: costo consolidado una vez; weighted utilization; Sankey por corte; NULL≠0; reasons probados; safe-fail de schema/version; alternativas/estados; DAG/bytes/versiones. Se cubren Node override, goals, preferencias/bounds, guardrails imposibles, UNKNOWN, mutaciones del certificador, seis datasets, particiones, integridad, contexto y determinismo.

Se conservan logs intermedios: policies18, package23, suite44 y suite45; la evidencia final es46 sobre los16 hashes congelados. No se marcan cero tests/imports o skips como PASS. QA se ejecutó localmente con credenciales productivas vacías y loopback aprobado para TestClient.

No se repitieron Browser/E2E/SQL completos, dado que no se modifican frontend, DB, API, worker, approval o publicación. `git diff --check` PASS. No se instalaron dependencias ni se usó producción como sandbox.

## Legacy compatibility

`assignment_v1`, `scheduling_v1`, `dispatch_v2`, exports/comparative service, schemas/goldens históricos y frontend conservan sus bytes post-T6. La extensión CP sólo se activa al pasar el hook T7; T6 por defecto sigue cubierto por U6. Registry conserva identidades y capacidades productivas; el producer T7 se resuelve explícitamente para tests.

## Deviations

1. Checkpoint por hash/copias/patch, sin commit, debido a `.git` read-only.
2. Metadata de Alternatives/Exceptions usa las variantes EntityEvidence ya previstas en T1, sin cambiar catálogos o unions públicas.
3. Base IA y particiones de evidencia son adapters de delivery explícitamente versionados. La respuesta IA conserva T1 y el material reconstruido conserva todos los facts; no se publican APIs falsas.
4. Provenance de assumptions no presente en el DTO no se inventa: source DERIVED para el hecho operativo ASSUMED.

## Risks

- **No release:** perfil público, admission, worker, persistencia/publicación y permisos/freshness actuales siguen pendientes de T8 y fases posteriores.
- **Budgets:** un candidato truncado o timeout puede ser FEASIBLE/UNKNOWN; no demuestra inevitabilidad de gap ni optimum global. Los límites son explícitos.
- **Delivery:** T8 debe usar los adapters declarados para reconstituir evidencia y enlazar base IA, verificar bytes/refs y conservar inmutabilidad. No puede leer sólo la primera partición como evidencia completa.
- **Row indivisible:** por encima de1MiB se rechaza el assembly; no se trunca ni se afirma soporte/benchmark ilimitado.
- **Consolidación:** conserva la compatibilidad conservadora T6; no habilita mezclas, industria-hardcodes o multi-stop nuevos.
- **Assumption provenance:** DERIVED no afirma un origen de usuario/default que no viene en el snapshot tipado.
- **Git:** trabajo T0–T7 local, sin staging/commit; el delta y las preimágenes permiten revisar T7 de forma aislada.

## Gate evaluation

| Gate | T7 | Evidencia / alcance |
|---|---|---|
| G-A | PASS | T7 exclusivo,16 archivos, sin auditoría nueva/T8/producción |
| G-C | PASS | DTOs/catálogos T1 preservados, adapters de delivery/versiones explícitos |
| G-D | N/A escritura | Sin DB/Storage, migraciones o Run lifecycle |
| G-E | PASS | Constraints/priority/goals/costos, certificador y oráculos independientes |
| G-R | PASS | Core, proyecciones, review, export, IA y bytes consistentes; R1–R8 |
| G-L | Preservado | Sin modificar approvals, upstream, invalidación o historia |
| G-S | Preservado / PASS local | Sin endpoints/permisos nuevos; refs exactas y credenciales productivas vacías |
| G-P | PASS acotado | Budgets, chunks/refs/manifest y fallos cerrados; sin benchmark productivo |
| G-UI / Skills | N/A frontend | Sin cambios visuales; Skill runtime pertinente y trazada |
| G-ENV | PASS | Runners reales,614/137/46 tests, cero skips |
| G-B | PASS en suites requeridas | B-PY/B-NODE verdes, U6 incluido, legacy intacto |
| G-REL | NOT RUN | Sin push, deploy, infraestructura o publicación; no autorizado |

STOP CONDITIONS evaluadas: MIN_COST no gana vacío; prioridad y guardrails no se relajan; assembler no decide ni inventa reasons; alternativas respetan constraints; Sankey no calcula cobertura ni suma ambas capas; CSV no duplica costos; NULL no se convierte en0; no se requiere frontend/IA/T8 para producir/verificar el bundle; Core/proyecciones coinciden y legacy permanece intacto.

No queda una STOP CONDITION abierta en T7. Verificación final: [preservación](preservation.json), [estado local](evidence/final-state.json) e [integridad](artifact-integrity.json).

## FINAL DECISION

**GO — T7 completado. T8 puede ser solicitado.**

T8 no fue ejecutado. Sin push, deploy, publicación durable o cambios de infraestructura/producción.
