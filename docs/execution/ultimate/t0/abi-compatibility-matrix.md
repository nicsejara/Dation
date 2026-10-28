# T0 — ABI y compatibilidad del baseline

Baseline: `ef997235a30251fbf7ae53690ed738092ee973d8`, `main`; fuente de ejecución única: `DATION_FINAL_MASTER_EXECUTION_PLAN.md` aprobado, SHA256 `c7543ffa1ef26c79d9142797863fc8ba83613f6cb426cf1621eb0c11b5a27823`. Este documento registra interfaces existentes y límites ya aprobados. No implementa T1 ni reemplaza el Master Plan.

## Evidencia de API y runtimes

- [OpenAPI completo](evidence/openapi.json), [98 operaciones](evidence/api-inventory.json) y [runtime/paquetes](evidence/api-runtime-baseline.json).
- API local: 91 paths / 98 operaciones, idéntica estructuralmente a la captura de la auditoría anterior. GET productivo `/openapi.json`: 200 y contenido idéntico al baseline local. Esto no demuestra el SHA de la imagen ni del worker desplegado.
- GET `/health` productivo: 200. GET administrativo Cloud Run: 401; revisión/image/worker efectivos no certificados. No hubo cambios de infraestructura ni despliegue.
- [Golden sintético legacy](evidence/legacy-goldens.json): Trips D1/D2 idénticas al probe anterior al usar los mismos inputs, incluyendo costo970, salida6/11, llegada7/11 y ciclo2. [CSV observado](evidence/legacy-assignment.csv). Son hechos de legacy, no acceptance tests de Ultimate.

| Identidad | Engine name | Version | Result schema | Autoridad existente |
|---|---|---|---|---|
| `logistics_assignment` | `logistics-assignment-engine` | `1.0.0` | `assignment_v1` | `backend/app/engines/assignment/engine.py`; `dispatch_job_service.engine_identity` |
| `logistics_scheduling` | `logistics-scheduling-engine` | `1.0.0` | `scheduling_v1` | `backend/app/engines/scheduling/{engine,configured_engine}.py`; mismo dispatcher |
| Dispatch sin Decision Case | `logistics-dispatch-engine` | `2.2.0` | `dispatch_v2` | `backend/app/engines/dispatch/engine.py`; rama default del dispatcher |
| Módulo histórico simple | `logistics-simple-engine` | `0.2.0` | Contrato propio histórico | `backend/app/engines/logistics/engine.py`; no es el dispatcher durable actual |

## Matriz de preservación y adaptación futura ya prevista

| Frontera | ABI/comportamiento verificado hoy | Preservar / adaptación futura del plan |
|---|---|---|
| Decision Case | `decision_case_v2`, pair Orders/Fleet, input signature `orders_id:fleet_id`; Case requiere datasets al crearse | No confundir ese nombre de schema con la cohorte Ultimate `workflow_version=2`. Case vacío/Model/Pack nuevos se incorporan T2–T4, sin reinterpretar Cases actuales |
| Nodes / historia | IDs `logistics_assignment`, `logistics_scheduling`, `logistics_final_assignment`; current/latest/approved Run se proyectan por separado | Conservar IDs/URLs/historia. Nuevos graph states futuros no sustituyen silenciosamente estados legacy |
| Estados actuales | Case active/completed/archived; node available/running/review/approved/locked/needs_data/error/stale | Ocho estados target de §6 son otra proyección versionada. Error/freshness siguen explícitos |
| Run lifecycle SQL | CHECK efectivo: queued/running/completed/error | `FAILED` del output contract futuro necesita adapter explícito desde `error`; ningún rename global en T0 |
| Admission HTTP | POST `/api/runs`, query `run_id`; pair IDs, configuration/options, optional decision_case/source_run_id. D2 exige source_run_id | Preservar forma legacy, UUID idempotente, 202/Location/Retry-After y errores. Nuevos discriminadores/snapshots sólo en sus fases |
| Tipado actual | `RunRequest` valida configuración por node; `DecisionCaseRef` sólo acepta D1/D2 | No introducir DTOs nuevos en T0. [OpenAPI](evidence/openapi.json) conserva la definición completa de requests/responses |
| Roles públicos actuales | `team_routes.Responsibility` acepta `data_owner`/`decision_owner` en escrituras; algunos filtros de lectura conservan aliases `data_steward`/`approver` | No confundir aliases de lectura con enums válidos de escritura ni con Operating Role SHIPPER/PROVIDER. Los tests que envían roles antiguos reciben422; no ampliar la API por oportunidad para hacerlos pasar |
| Identidad de worker | Request persistido incluye engine_name/version/schema; worker compara contra `engine_identity(node)` actual | Registry persistido/dual-compatible de T1/T8 requerido antes de admitir nueva familia. No sustituir identidad de jobs antiguos |
| Replay | Hash de intención, lectura de job existente y replay antes de checks upstream mutables | Mismo Run/intención sin nuevo efecto/invalidation. Contexto nuevo no puede reinterpretar un request viejo |
| D1 legacy | `assignment_v1` no temporal; una fila de recurso puede generar múltiples abstract trips. Kg/loads/estimated_cost/scenarios.selected | La independencia de fechas es contrato legacy probado por B-PY. Capacidades/cupos/feasibilidad Ultimate se construyen como perfil nuevo T6–T7 |
| D1→D2 | Handoff `scheduling_input_v1`, source `scenarios.selected.trips`, Trip IDs y fingerprints | Preservar handoff antiguo; D2 nuevo consume exclusivamente nuevo D1 aprobado exacto con source fingerprint |
| D2 legacy | Conserva viajes de D1, calcula fechas/ciclos con su convención previa; handoff `final_assignment_input_v1` | No aplicar calendario inclusivo/Transit nuevo al helper viejo. D3 histórico sigue legible; no se crea Branch |
| Transit/costos | Probe externo480km cuesta970 con fixed10 y round distance; arribo un día después, cycle2 incluso externo | Hechos legacy preservados. Target:500km/día; arrival=dispatch+outbound−1; OWN cycle=ceil(2d/500); EXTERNAL cycleNULL. F04/F05/F08 ya aprobadas; no se implementan ahora |
| Money / null | Campos monetarios escalares legacy; exporters usan coalesce preservando0 frente aNULL | Target Money/context currency/unit/precision por path se formaliza T1. Unknown no se vuelve0 ni FX implícito |
| Result header | JSON legacy `schema_version`; payload escenarios/selected/handoff | Package futuro usa `result_schema`/`result_schema_version`; DB header coherente por cohorte. No publicar un package nuevo ficticio en T0 |
| CSV | `platform/exports.py::generate`: BOM UTF8, `;`, quoting, protección de fórmulas y columnas específicas por schema | Columnas/encoding legacy se preservan. Nuevo export usa rows certificados y granularidad propia T7/T9/T10 |
| Costo consolidado CSV | Assignment repite costo del viaje por fila Trip–Order en el export actual | Diferencia conocida respecto de target, no corregida retroactivamente. Nuevo CSV reconoce costo una vez por Trip y conserva residual en sus datasets |
| Unknown schema CSV | Rama default de `exports.generate` usa columnas Dispatch cuando schema es truthy desconocido | Riesgo ya previsto: registry exhaustivo para consumers nuevos, sin fallback falso. No modificar esta ruta legacy en T0 |
| IA context | `decision_context.build_decision_context` reconoce schemas viejos y legacy scenarios/baseline | `decision_context_v1` futuro requiere dispatcher explícito, sin reutilizar fallback para nuevos schemas |
| IA replay/evidence | `answer_question` usa SHA256 de la pregunta; comparative legacy puede completarse mediante `completed_evidence` | V2 agrega selección/mode/Run/fingerprint/context version; alternativas congeladas antes de publicación. No cambiar historial ni v1 en T0 |
| KPIs / visuals | Selectors legacy derivan algunos promedios/mix; distintas unidades/semántica a los nuevos contratos | Engine certifica metrics nuevas; assembler proyecta Sankey/Gantt; frontend sólo representa. No trasladar matemática a T10 |
| Approval | Guards SQL/backend, Run completed, contexto/upstream/Owner/permisos y actor real; eventos append-only | Review determinístico futuro no es permiso. LLM nunca aprueba; no reescribir actores/history ni restaurar approval por cache |
| Invalidation | `invalidate_run_lineage`/`reopen_on_run_admission` y locks preservan historia e invalidan camino afectado | L-A–L-F y read sets gobiernan perfil nuevo. Abrir/cancelar Config no invalida; replay no vuelve a invalidar |
| Tenancy | 19 tablas públicas con RLS; FKs/checked RPC/roles y schema privado; 17 policies | No sustituir membership por el ejemplo user_id de una Skill. Service key no autoriza operaciones fuera de fase |
| Storage | `dda-inputs` privado, límite10MiB, CSV/Excel MIME legacy; no JSON habilitado | Input snapshots/results JSON/JSONL necesitan la ampliación prevista al autorizar T4/T8. No cambiar bucket ni MIME ahora |
| Migrations | 31 archivos Git; baseline10/10 más23 upgrades actuales reproducen objetos de aplicación; history remoto sólo10 registros hasta5/10 | Catálogo aplicado no se deduce de history. No repair/replay. Reconciliación y diferencias de grants se registran como evidencia |
| Navegación / UI | Home→DDA→Case→Map→Config→Run→Dashboard; rerun D1→Config D1 / D2→Config D2; dirección visual existente | Preservar rutas, Hero/tokens/componentes y ownership. T0 ejecuta regresiones, no rediseño ni workflow de Skill UI |

## Registro documental de decisiones ABI de T0

Se ratifican las decisiones ya aprobadas de F01–F23 y §8 del Master Plan: headers por cohorte; adapter error→FAILED; Money por path sin moneda inferida del workspace actual; null≠0; calendario inclusivo sólo nuevo; `on_time_ratio` nuevo expresa cumplimiento esperado `(ON_TIME+AT_RISK)/total` con conteos separados; reason IDs estables; hash DAG sin autorreferencia; artifact manifest inmutable y overlay de permisos/aprobación fuera del hash. Esto es registro de la especificación vigente, sin DTOs, registry nuevo ni código implementado.

Las identidades existentes de la primera tabla quedan registradas con literales exactos. Las identidades/versiones de nuevos perfiles y su ABI concreta se codifican/revisan en T1 conforme al contrato aprobado; no se renombra ninguna identidad actual. Fechas, minor units, redondeos/bounds y canonicalización deben convertirse en contratos ejecutables T1; no se inventa una implementación T0 para resolverlos.

Las diferencias current→target de esta matriz están previstas por el plan. Los fallos de suites se evalúan aparte en el ledger/debt register y el reporte STOP/GO; no se justifican automáticamente por existir un target futuro.
