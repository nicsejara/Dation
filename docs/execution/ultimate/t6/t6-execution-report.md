# T6 — D1 Transport Plan Core + Engine Evidence + Resource Feasibility

Fecha: 27/10/2026, America/Buenos_Aires. Timestamps de ejecución conservados en UTC.

Se implementó el núcleo D1 sobre DTOs Ultimate T1, con capacidades vectoriales, asignación y Trips conjuntos, oferta externa finita y reutilización OWN temporalmente certificada. Produce Core/Evidence tipados y una resolución completa por orden/recurso. El perfil es exclusivo de pruebas, sin admisión pública ni persistencia productiva.

## Baseline

Fuentes de ejecución: [solicitud T6](evidence/T6-user-request.txt), [Master Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), sección T6, F01/F04–F12/F17–F23, kernel §10, catálogo §13, pruebas/gates §22–§23 y fixtures §25. Baseline inmediato: [T5 aprobado](../t5/t5-execution-report.md). Se consultó T1 únicamente para su contrato de precisión y sus DTOs; no se repitió una auditoría end-to-end ni T0–T5.

- Branch `main`, HEAD `ef997235a30251fbf7ae53690ed738092ee973d8`.
- Las **172 entradas** del manifest T5 coincidieron antes de modificar y permanecen verificables al cierre.
- El árbol ya contenía trabajo pendiente T0–T5. Se preservaron sus archivos; no hubo reset, clean, descarte, checkout, staging, commit, fetch, push o deploy durante T6.
- Runtime usado: Python **3.13.5**, OR-Tools **9.15.6755**, Node **24.19.0**, dependencias ya instaladas. No se instalaron herramientas.

## Checkpoint post-T5

Se creó el equivalente autorizado de checkpoint mediante inventario SHA256, copias de bytes y patch tracked binario. `.git` tiene acceso de sólo lectura según la política de filesystem de este entorno; no se solicitó una escalación para modificarlo.

- **791 archivos**, **40.360.059 bytes** preservados en `/workspace/work/dation-t6/post-t5/`.
- Referencia de contenido post-T5: `411c7c2e49cbd7428aa5471e571b572dd39b4a7ab23a902fb8a1158f0ea0e95e`.
- [Inventario](evidence/initial-state.json), [patch previo](evidence/post-t5-tracked.patch), [preservación](preservation.json) y preimagen de `registry.py` incluida en la evidencia T6.
- Al cierre, **790 archivos del checkpoint conservan sus bytes actuales**; sólo `backend/app/results/registry.py` se extendió intencionalmente. Su preimagen permanece intacta. Los siete archivos nuevos T6 se identifican separadamente.

## Skills utilizadas

Se aplicó la Execution Skills Policy: arquitectura aprobada → comportamiento existente → Skill. [Ledger de Skills](skills-ledger.json).

| Skill / disponibilidad | Lectura y aplicación | Verificación |
|---|---|---|
| `cloud-environment:cloud-environment-runtime` | Leída al reanudar; estado del entorno, policy de red y runners. Tests locales sin credenciales productivas | Entorno `running/connected`, observaciones actuales; versiones, comandos y resultados preservados |
| Python / optimización / testing | No hay una Skill específica disponible en el catálogo o las guías locales | Se usan contratos T1, OR-Tools instalado, unittest, oráculos y certificador independiente |
| UI / Supabase / Docker | N/A para esta frontera | Sin frontend, consultas SQL, contenedores nuevos, migraciones o red productiva |

No se aplicaron Skills de diseño, generadores ni auditorías generales. No se usaron agentes adicionales.

## Files Created

Paths relativos a la raíz del repositorio:

| Archivo | Responsabilidad |
|---|---|
| `backend/app/engines/common/__init__.py` | Namespace de kernels puros compartidos |
| `backend/app/engines/common/day_resource_feasibility.py` | Existencia temporal de Trips fijos, cuotas y witness |
| `backend/app/engines/assignment/transport_contracts.py` | Input de snapshots/DTOs, opciones/budgets y resultado privado de prueba |
| `backend/app/engines/assignment/transport_model.py` | Candidatos y CP-SAT estructural acotados |
| `backend/app/engines/assignment/transport_plan.py` | Producer de Core/Evidence T1 y resoluciones |
| `backend/app/engines/assignment/transport_validator.py` | Certificación independiente, sin importar el solver/modelo ni su extracción |
| `backend/tests/test_transport_plan_core.py` | U6: 47 tests y oráculos independientes |

Se agregan este reporte, ledgers, patch diferencial, manifests y evidencia de QA como documentación de ejecución.

## Files Modified

Sólo `backend/app/results/registry.py`: agrega `resolve_test_core(identity)`, que exige la identidad completa `transport_plan / 2.0.0 / transport_plan_v1 / transport_plan_v1 / 1` y resuelve el producer local de pruebas.

Las entradas productivas `RUNTIMES`, sus capabilities, la metadata estática T1 y los resolvers de admisión existentes conservan su comportamiento. `require_available=True` sigue rechazando el runtime Ultimate. No se modifica ningún archivo de Assignment legacy, Dispatch, D2, frontend, schema, infraestructura o configuración productiva.

El [scope diff](scope-diff.json) identifica **8 archivos fuente/tests: 7 nuevos y 1 modificado**. El [patch T6](evidence/t6-changes.patch) está calculado contra post-T5, no atribuye a T6 todo el diff pendiente frente a HEAD.

## D1 Core Architecture

```text
TransportPlanInput (Model + FrozenCaseContext + Demand[] + Resource[])
 → candidatos acotados / CP-SAT estructural
 → Trips + allocations vectoriales exactas
 → day_resource_feasibility sobre Trips fijos
 → Core/Evidence T1 + resoluciones completas
 → certificador independiente
 → resultado local de prueba
```

El solver no lee CSV, tablas, archivos, callers legacy ni un workspace mutable. El input valida identidad/version/hash de Model contra contexto, dimensiones activas, currency, semantic read set D1, IDs únicos y disponibilidad conocida requerida. Los hashes de las interpretaciones consumidas vienen del snapshot T4; la futura admission T8 deberá enlazar/revalidar esos bytes y snapshots bajo su transacción, sin delegar esa responsabilidad al optimizador.

`TransportPlanComputation` envuelve `EngineOutput` T1 y agrega resoluciones completas, residual explícito por orden, ResourceUsage, certificado temporal y SearchTrace para el caller T7. No cambia el ABI T1 ni crea otra decisión Trip Planning.

## Candidate Generation

Orden estable por IDs, partición por origen/destino/distancia y firma de compatibilidad, con slots por recurso. Cada slot puede consolidar órdenes compatibles y usa una sola capacidad garantizada. El bound de slots considera demanda vectorial, cuota externa o unidades OWN/horizonte, y se corta por budgets explícitos.

- Hasta 100 órdenes, 40 recursos y 366 días inclusivos.
- Default 128 slots y 20.000 variables; máximos configurables de prueba 256 y 30.000.
- Un worker CP-SAT, seed explícito (default 0), presupuesto determinístico total repartido entre tres estratos de prioridad y límite de pared defensivo de 10 segundos por solve.
- Bounds numéricos antes de CP-SAT; denominadores/LCM de cobertura no pueden generar overflow. LCM fuera de presupuesto devuelve UNKNOWN con `RATIONAL_COVERAGE_INTEGER_BUDGET`.
- Truncamiento de candidatos se registra como `CANDIDATE_MODEL_BUDGET`; no se usa para certificar que el residual sea inevitable.

La partición por firma de cargo es conservadora: no enumera todas las mezclas potenciales de firmas que compartan compatibilidad parcial. `candidate_set_complete=false` declara esa frontera. No se generan todos los subconjuntos ni se afirma exhaustividad global.

## Capacity Model

Cada Trip satisface simultáneamente todas las dimensiones activas (`pallets`, `weight_kg`, `volume_m3`, `units`, según Model). Las variables transportan quanta vectoriales exactos, escalados según T1. La dimensión primaria se utiliza en métricas de reporting; no elimina constraints físicas secundarias.

Factibilidad siempre usa `guaranteed_capacity`. `maximum_capacity` permanece como hecho de input y no aporta espacio adicional. La capacidad física debe ser positiva; disponibilidad cero es válida. Costo o disponibilidad desconocidos no se reemplazan por cero, infinito o confirmación.

## Split / Non-Split

Para non-split, la variable es cero o toda la orden: un Trip completo o residual. `Model.split_permitted=false` prevalece aunque una fila permita split.

Para split, el GCD de las cantidades escaladas define un quantum que conserva exactamente la misma proporción en cada dimensión activa. Si las precisiones hacen el vector indivisible, el engine no fracciona cada componente de manera independiente.

`allocation_fraction` es la representación T1 redondeada a seis decimales; los loads exactos conservan la fracción racional. Por ejemplo, 26/70 se representa `.371429`; el load sigue siendo exactamente 26, no 26.000030. El certificador deriva el racional desde los loads y verifica tanto proporcionalidad exacta como representación decimal. Una asignación positiva debe poder representarse como fracción positiva en ese ABI.

Se comprueba por orden/dimensión: `assigned + residual = requested`. Las órdenes sin asignación permanecen en las resoluciones e histórico del resultado local.

## External Finite Resources

`sum(trips abiertos)` de un recurso EXTERNAL no supera `services_available` en todo el horizonte, compartido entre lanes y días. No hay reset por lane/día ni slots ilimitados. El ciclo/retorno externo es NULL.

ResourceUsage conserva services available/used/remaining y `availability_source`. ASSUMED sigue ASSUMED y genera el reason T1 correspondiente; nunca se convierte a CONFIRMED. Cero servicios produce un resultado de negocio con gap, no una excepción técnica.

## Own Resource Feasibility

OWN limita concurrencia de ciclos con `units_available`. Las unidades no multiplican capacidad por Trip. El recurso debe atender desde su base declarada y una lane permitida. Los intervalos de ocupación se comparten entre todas las lanes del recurso.

El CP estructural usa intervalos opcionales y cumulative para excluir candidatos imposibles. Luego el kernel de Trips fijos verifica la existencia temporal por separado. El certificador comprueba el witness contra inputs originales, índices de unidades lógicas, tránsito T1 y ausencia de solapamientos; el fin de ocupación es exclusivo.

## Shared Feasibility Kernel

`day_resource_feasibility(trips, resources, horizon)` no importa D1/D2 ni decide cargas, recursos, goals económicos o calendario recomendado. Devuelve:

- FEASIBLE: witness por Trip con fechas y, para OWN, unidad lógica/retorno.
- INFEASIBLE: contradicción probada de cuota/ventana/disponibilidad o modelo temporal fijo exhaustivo.
- UNKNOWN: disponibilidad desconocida, límite de kernel o solve sin certificado suficiente.

T1 es la única autoridad: outbound `ceil(distance/500)`, OWN cycle `ceil(2*distance/500)`, arrival inclusiva y retorno exclusivo. El horizonte limita departure; arrival/return pueden quedar después de su fin si la due date lo permite.

Las fechas del witness se guardan como evidencia de existencia, no como `DaySchedule`, recomendación D2 ni resultado público. T9 podrá reutilizar el kernel para su propia política de scheduling. No hay dependencia D1 → D2.

Si el kernel contradice un candidato D1 con INFEASIBLE, el producer lanza `EngineCertificationError`. Si devuelve UNKNOWN, no expone los Trips como certificados: devuelve UNKNOWN sin solución utilizable. No repara silenciosamente un resultado inconsistido.

## Consolidation

Requiere misma ruta DIRECT, distancia, firma de cargo compatible con el recurso, todas las capacidades y una intersección válida de ventanas de dispatch. El Model no tiene un toggle adicional de consolidación en T1/T3: la regla conservadora usa su declaración de homogeneidad o grupos explícitos, sin inventar una nueva configuración de negocio.

No hay multi-stop, hubs, VRP, secuenciación de ruta, choferes, patentes o scheduling horario. Dos ventanas disjuntas no se consolidan aunque los loads entren físicamente.

## Core Result

Se produce `EngineCoreResult` especializado `transport_plan_v1`, junto con EngineEvidence y bindings de Run/context/core fingerprint T1.

- Trips: IDs estables, ruta/distancia, recurso/source, allocations, fracciones, loads, garantizadas, utilization, ready/due y referencias a reasons existentes.
- Demand: resolución completa en el wrapper, prioridad, requested/assigned/residual, cobertura, Trip refs y estado COVERED/PARTIALLY_COVERED/UNASSIGNED. Core conserva las filas residuales en `unassigned_demand` y el gap vectorial total.
- Resources: servicios/unidades, Trips, loads, distancias y utilization certificada en el wrapper y hechos de Evidence.

`estimated_cost`, costos totales y de candidatos permanecen NULL; cost completeness UNKNOWN. Los facts tarifarios de input se conservan en evidencia, sin ejecutar política económica T7. `policy_feasible=NULL` evita certificar goals/guardrails que T6 todavía no implementa. Ningún Hero, Sankey, dashboard, package o assembler se produce en esta fase.

## Engine Evidence

Evidencia estructurada T1: constraints, entidades, candidate summaries y reason emissions con facts tipados. Incluye:

- Por par orden/recurso: scope estático explícito, ruta/source/compatibilidad, disponibilidad, ventanas, requested/guaranteed por dimensión y rechazos sustentados.
- Por Trip: capacidad garantizada y carga por dimensión, consolidación y witness temporal.
- Por recurso: cuota/uso y assumptions de oferta.
- Por orden: requested/assigned/residual por dimensión, prioridad y Trip refs.
- Search: statuses nativos, seed, versión de solver, hashes, slots/variables y límites.

Se emiten únicamente reasons T1 con prueba disponible: `GUARANTEED_CAPACITY_USED_FOR_FEASIBILITY`, `CONSOLIDATED_COMPATIBLE_DEMAND`, `NO_COMPATIBLE_RESOURCE`, `NON_SPLIT_EXCEEDS_GUARANTEED_CAPACITY`, `DATE_WINDOW_INCOMPATIBLE`, `RESOURCE_SERVICE_LIMIT_REACHED`, `ASSUMED_EXTERNAL_AVAILABILITY` y `CAPACITY_GAP` observado.

Los rechazos de un par no se presentan como una demostración de infeasibilidad global del plan. Un candidato no elegido y sin rechazo estático probado queda UNKNOWN, no automáticamente INFEASIBLE. No se fuerzan razones positivas ni se emiten `SELECTED_LOWEST_COST_FEASIBLE`, `SELECTED_ONLY_FEASIBLE_RESOURCE`, ventaja own o protección de prioridad sin su certificado completo.

## Independent Validator

`transport_validator.py` no importa el modelo CP, el generador, sus helpers de compatibilidad, extracción ni métricas. Relee inputs originales y valida:

- Conservación y proporcionalidad exacta en cada dimensión activa.
- Non-split, fracción decimal y referencias estables.
- Guaranteed capacity, total loads y ratios.
- Ruta, distancia, base, source y compatibilidad.
- Cuota externa en horizonte y preservación de assumptions.
- Unidades OWN, tránsito, ventanas y ausencia de solapamientos por unidad.
- Resoluciones completas, residual, ResourceUsage, métricas estructurales, entidades/reasons/candidate facts y fingerprints.

Un resultado inválido se rechaza con error técnico; no se redondea/reasigna para hacerlo pasar. Los tests adversarios re-enlazan incluso fingerprints válidos después de adulterar Core para alcanzar estos checks, además de cubrir fallos de envelope. Ningún candidato real producido en QA terminó en desacuerdo con el certificador; los rechazos deliberados de fixtures negativos son la cobertura esperada.

## Solver Status

Se conserva el status nativo CP-SAT por etapa en SearchTrace/Evidence. Un optimum del modelo estructural conservador no certifica un optimum de la política completa de Dation: Core entrega FEASIBLE con certificado de factibilidad, no OPTIMAL/global bound T7.

UNKNOWN sin incumbent utilizable no se transforma en INFEASIBLE ni en gap inevitable. Si una etapa posterior no prueba mejora pero existe un incumbent previo certificado, se conserva ese candidato FEASIBLE y el límite/status posterior. El kernel diferencia sus tres estados; su INFEASIBLE pertenece sólo al problema de Trips fijos. Los fallos de input/modelo/certificador son errores técnicos, no excepciones de negocio inventadas.

## Determinism

Ordenación estable de órdenes/recursos/grupos, IDs de Trip derivados de su contenido más ordinal de repetición, operaciones Decimal/racionales y CP-SAT de un worker con seed explícito. Se registran solver version, opciones, hash del modelo y hash de inputs estructurales. Los tres estratos HIGH/MEDIUM/LOW maximizan cobertura fraccional normalizada para construir el candidato estructural; no implementan la jerarquía económica/guardrails/alternatives T7.

U6 verifica permutaciones de filas, inmutabilidad de inputs, fingerprints/evidence iguales y contextos Decimal distintos. Las garantías se fijan para mismos inputs, versión, seed y presupuestos; un corte defensivo de pared en un host saturado puede cambiar calidad/status y debe conservarse como tal, sin prometer igualdad de un optimum no certificado. No se afirma optimalidad económica ni equivalencia del criterio estructural con la policy completa de T7.

## Fixtures / Oracles

| Fixture / frontera | Aserción observada en U6 |
|---|---|
| A: 70 pallets, externos 26×2 y 30×1 | Assigned70, residual0, 3 Trips; costo final no evaluado T6 |
| D: 6+8 compatibles, un servicio | Un Trip14 |
| D: ventanas 2–3 y 6–8 | No consolidación; dos servicios cubren ambas, uno deja residual |
| E: non-split28, guarantee26/max30 | Residual28; al agregar guarantee30 sólo ese recurso sirve |
| F: 70 y externos26×2 | Assigned52, residual18, 2 Trips, business result válido |
| M: 28 pallets y28.000kg, garantías30/20.000 y30/26.000 | Ninguno sirve; variante24.000kg sólo B |
| Split vectorial de cuatro dimensiones | Misma fracción racional y conservación por dimensión |
| OWN: una unidad/ciclo480km | Ciclos de dos días sin overlap; tres unidades no multiplican capacidad non-split |
| Cero servicios/unidades; sin compatibles | Gap válido, sin servicios/unidades inventados |
| UNKNOWN/budgets | Sin falsa solución, global proof o inevitabilidad |

Oracle independiente de non-split: enumeración de placements sobre servicios finitos, **108 combinaciones pequeñas** de cantidades iguales/capacidades/cupos, sin llamar al objetivo ni helpers del solver. La igualdad de cantidades permite comparar su máxima cobertura cuantitativa con el criterio de cobertura fraccional T6 sin confundirlo con T7.

Oracle temporal independiente: enumeración day×unit y chequeo de intervalos en **cuatro configuraciones** de ventanas/unidades, sin CP-SAT ni TransitEstimator dentro del oracle (ciclo fixture literal dos días). Se agregan aserciones directas de múltiples dimensiones, conservación, due/horizon, assumptions y mutaciones de resultados.

## Tests

Resultados finales, sobre los mismos ocho hashes fuente congelados: [test ledger](test-ledger.json), [command ledger](command-ledger.json), [candidate](evidence/candidate.json).

| Suite | Tests | Duración | Resultado | Failures/errors/skips |
|---|---:|---:|---|---|
| B-PY | 568 | 31,591 s | PASS | 0/0/0 |
| B-NODE | 137 | 3,236 s | PASS | 0/0/0 |
| U6 standalone, también incluido en B-PY | 47 | 5,669 s | PASS | 0/0/0 |

Logs: [B-PY](evidence/B-PY.log), [B-NODE](evidence/B-NODE.log), [U6](evidence/U6.log). Las suites se ejecutaron con credenciales productivas vacías. La herramienta aprobó ejecución local con loopback para TestClient, sin acceso a proyectos remotos.

Los primeros 41 y 45 tests U6 se preservan como iteraciones anteriores. Una prueba inicial puntual detectó que el proto Python de OR-Tools 9.15 no expone `SerializeToString`; se usó su representación textual estable para el hash del modelo, sin tocar contratos de dominio. No se sustituyen esos intentos por la evidencia final.

No se repitieron Browser, E2E o SQL completos: no hay callers UI/worker/API modificados, migraciones o publicación durable. B-PY incluye regresiones de Assignment legacy y contratos/registry; B-NODE conserva los consumers actuales. `git diff --check` PASS e integridad final documentados.

## Legacy Compatibility

`assignment_v1`, `scheduling_v1`, `dispatch_v2`, sus goldens, archivos y callers conservan sus bytes post-T5. No se renombra un engine ni se elige runtime sólo por node_id. La única extensión del registry es una entrada explícita de resolución para tests por identidad completa, sin alterar admisión ni metadata estática.

T5 no anuncia runtime público nuevo: sus capabilities siguen cerradas. Ninguna Run Ultimate, approval, artifact o Result Package se creó en producción ni en DB como parte de T6.

## Deviations

1. Checkpoint equivalente por hash/copias/patch en lugar de commit local, por la política read-only de `.git`; expresamente previsto en la autorización.
2. El wrapper privado agrega residual y ResourceUsage completos porque Core T1 contiene las filas residuales y el agregado, sin cambiar el ABI de publicación.
3. Consolidación conservadora por firmas iguales: es segura pero no globalmente exhaustiva. Se declara y nunca se usa para razones de exclusividad/óptimo global.
4. Status FEASIBLE conservador para el candidato certificado, preservando los statuses nativos estructurales. La política/economía T7 y su certificación quedan pendientes.

## Risks

- **Perfil no admitido:** no es un release ni runtime productivo listo; T7/T8 deben completar policy y publicación antes de exponer ejecución.
- **Búsqueda acotada:** pueden existir planes mejores fuera del candidate set/budget. CAPACITY_GAP describe el resultado observado, sin inevitabilidad global.
- **Precisión:** la fracción wire de seis decimales es representacional; los loads/racionales y sus quanta conservan la autoridad. T7/D2 deben mantener esta frontera y no reconstruir loads multiplicando sólo la fracción redondeada.
- **Policy pendiente:** cobertura estructural normalizada no certifica goals monetarios, guardrails, preferencias, balances ni alternatives. `policy_feasible` y costos permanecen NULL.
- **Witness:** fechas internas certifican existencia, no una recomendación D2. T9 deberá respetar Trips y reutilizar el kernel sin reoptimizar cargas.
- **Escala:** límites y estados honestos están cubiertos; no se afirma benchmark productivo ni exhaustividad para grandes instancias.
- **Git:** el árbol conserva trabajo local T0–T6 sin staging/commit. El checkpoint/patch diferencial permite revisar T6 sin atribuirle cambios anteriores.

## Gate Evaluation

| Gate | Evaluación T6 | Evidencia / frontera |
|---|---|---|
| G-A — Alcance | PASS | T6 exclusivo, ocho archivos, sin auditoría transversal/T7/producción |
| G-C — Contract | PASS | DTOs/Core/Evidence T1 y precisión preservados, metadata estática sin cambios |
| G-D — Datos | N/A escritura | Sin schema, SQL, migraciones, DB o publicación |
| G-E — Engine | PASS estructural | Capacidades/conservación/source/tiempo, oráculos y certificador independientes |
| G-R — Result | PASS en Core/Evidence | Bindings y hechos estructurales; sin package/assembler/costos T7 |
| G-L — Lineage | Preservado | No admission/approval/history/upstream mutados |
| G-S — Security | Preservado | Sin nuevas rutas o permisos; credenciales productivas vacías en QA |
| G-P — Performance | PASS acotado | Budgets, numeric guards, candidate bounds y UNKNOWN honestos; sin benchmark productivo |
| G-UI — Skills/preservación | N/A frontend | Ningún archivo UI modificado; Skill runtime pertinente y trazada |
| G-ENV — Entorno | PASS | Runners/versiones disponibles y tres suites con casos positivos/sin skips |
| G-B — Regresiones | PASS en suites autorizadas | B-PY568 y B-NODE137 verdes; legacy intacto |
| G-REL — Release | NOT RUN | No push, deploy, flags o infraestructura; no solicitado |

Las STOP CONDITIONS se verificaron: no se separó Trip Planning, no hay servicios infinitos/capacidad maximum/unidades como multiplicador, ninguna dimensión ignorada, non-split y conservación certificados, ningún calendario D2 ni dependencia circular, reasons sustentados, status honestos y legacy intacto. No se implementó T7 para pasar invariantes T6. Los negativos del certificador rechazan las mutaciones deliberadas; no quedó un desacuerdo del producer real sin resolver.

Verificación final: [preservación](preservation.json), [estado Git](evidence/final-state.json), [integridad de artifacts](artifact-integrity.json). No se crearon contenedores o servicios nuevos; no hubo cleanup destructivo de recursos ajenos.

## FINAL DECISION

**GO — T6 completado. T7 puede ser solicitado.**

T7 no fue ejecutado. Sin push, deploy, publicación durable o modificaciones productivas.
