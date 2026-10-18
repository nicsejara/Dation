# Fase 0 · Inventario completo de API y autorización actual

Baseline de código: `22f1187451429c8e98dfcb9874f89b974500cb35`. Inventario contrastado con AST y `main.app.openapi()` local: **42 operaciones explícitas** (19 `main.py`, 23 `app/routes/dispatch.py`). Importar y generar el esquema no llama al lifespan ni a Supabase/LLM. No se ejecutaron mutaciones para inventariar endpoints.

## Convenciones

- **B**: `require_upload_access` (`app/auth.py`), HTTP Basic, mismo usuario literal `dation` + contraseña de entorno para todas las personas. En `dispatch.py` se aplica al router entero. **P**: público a nivel aplicación, sujeto a infraestructura externa.
- **WS sí**: contiene, lee, modifica o deriva datos que una futura capa Platform debe autorizar por workspace. **Global**: diagnóstico/operación compartida, futuro acceso administrativo. **No**: recurso estático o validación local sin acceso a datos persistidos. No existe scope workspace implementado en ninguna fila.
- Tablas abreviadas: **D** `datasets`; **R** `decision_runs`; **C** `decision_cases`; **J** `dispatch_run_jobs`; **Q** `decision_case_reconciliations`; **W** `dispatch_worker_instances`; **A** `decision_comparative_analyses`; **E** `decision_explanations`; **M** `decision_messages`; **T** `decision_chat_turns`; **S** `decision_interpretation_sources`; **V** `decision_approval_events`. Son las 12 tablas contrastadas con [schema/live-catalog.json](schema/live-catalog.json). **ST**: Storage del dataset (`storage_bucket`/`storage_path`), acceso con secreto backend. Las RPC listadas son llamadas REST internas, no endpoints nuevos de FastAPI.
- **Mutación** significa persistencia de negocio o llamada externa con coste; telemetry de cada petición se excluye. Un POST puede ser de sólo lectura. Todas las rutas de objeto/lista usan el secreto backend y carecen de filtros de tenant; tipos/UUID/lineage no son autorización.
- Excepto respuestas HTML/texto/CSV indicadas, salidas son JSON construidas por funciones/dicts sin `response_model` tipado. Campos exactos de motores se preservan por sus contratos `schema_version`.

## `backend/main.py` · 19 operaciones

| Método y ruta | Handler / auth | Input | Output principal | Tablas / Storage / externo | WS | Mutación |
| --- | --- | --- | --- | --- | --- | --- |
| GET `/` | `root` · P | — | `{service,version,status}` 200 | Ninguno | No | No |
| GET `/health` | `health` · P | — | `{status:healthy}` 200 | Ninguno | No | No |
| GET `/ready` | `ready` · B | — | `{ready,database,alerts}`, 200/503 | RPC `dispatch_operational_snapshot` y `comparative_operational_snapshot`: J/W/Q/R/T/A | Global | No, RPC STABLE |
| GET `/api/system/operations` | `operations` · B | — | Snapshot con queue/workers/reconciliation/runs_24h/chat_24h/comparative_queue, alerts, freshness; 200/503 | Mismas RPC J/W/Q/R/T/A | Global | No |
| GET `/metrics` | `prometheus_metrics` · B | — | Texto Prometheus de proceso y gauges DB; 200/503 | Mismas RPC J/W/Q/R/T/A | Global | No |
| GET `/app` | `decision_workspace` · B | Query SPA manejada por cliente; handler sin parámetros de vista | HTML `app/templates/app.html` | Archivo local | No | No |
| GET `/upload` | `upload_compatibility` · B | — | Mismo HTML que `/app`, ruta de compatibilidad | Archivo local, no `upload.html` | No | No |
| GET `/api/system/supabase-check` | `supabase_check` · B | — | `{ok,database?,table?,http_status?,error?}` según probe | D, lectura limitada | Global | No |
| GET `/api/system/llm-status` | `llm_status` · B | — | Configured/provider/model/knowledge_version/knowledge_files/prompt_version | Config y Markdown local; no request al LLM | Global | No |
| GET `/api/workspace/summary` | `get_workspace_summary` · B | — | `{datasets,runs}` contadores exactos globales | D/R con `count=exact`, sin workspace | Sí | No |
| GET `/api/datasets` | `get_datasets` · B | `type?`, `limit=25` (1..100), `offset=0`, `q?`, `include_archived=false` | `{items:[dataset]}` | D; con tipo puede leer ST para perfil obsoleto (`persist=False`) | Sí | No |
| GET `/api/datasets/{dataset_id}/profile` | `dataset_profile` · B | Path string | Orders/Fleet: `{dataset,...profile_json}`; legacy: dataset resumido, validation, profile, preview | D por ID; ST sólo para perfil legacy | Sí | No |
| GET `/api/runs` | `get_runs` · B | `limit=40` (1..100), `dataset_id?` string | `{items:[run resumen]}` sin result_json | R, global o por dataset_id | Sí | No |
| POST `/api/datasets/upload` | `upload_logistics_dataset` · B | Multipart CSV, query `dataset_type?`; form `label?`, `parent_dataset_id?:UUID`, `is_sample=false`; ≤10MiB | `{duplicate,dataset/ existing_dataset,validation?,sha256?}` según camino | D y ST; tipo Orders/Fleet usa validadores nuevos; legacy usa validator logistics | Sí | **Sí**: objeto + fila o dedup; compensación DELETE objeto en error |
| POST `/api/runs/{dataset_id}` | `run_logistics_decision` · B | Path string, body opcional `DecisionRunConfig`; query `objective?` (`min_cost/min_trips` sólo fallback legacy), `run_id?:UUID` | Run completo terminado, 200; errores HTTP | D/R/ST + motor logistics local | Sí | **Sí**: INSERT/PATCH run, dataset status; ejecución síncrona en petición |
| GET `/api/runs/{run_id}` | `read_decision_run` · B | Path string | Fila completa R incluyendo config/result/lineage; 404 ausente | R por ID | Sí | No; no expira ni repara jobs |
| GET `/api/runs/{run_id}/interpretation` | `read_run_interpretation` · B | Path string; `limit=50` (1..100), `offset=0` | run_id, explanation, messages, pagination y referencias/currency de evidencia | RPC STABLE `current_decision_explanation`; E/M/S/A | Sí | No; POST RPC interno es lectura |
| POST `/api/runs/{run_id}/explain` | `explain_decision_run` · B | Path string, sin body | id, run_id, provider/model/versions, evidence_analysis_id, explanation, usage | R/A, Markdown local, LLM; RPC `record_decision_explanation_with_evidence` → E/S | Sí | **Sí**: llamada facturable + INSERT explicación/evidencia |
| POST `/api/runs/{run_id}/chat` | `chat_about_decision` · B | Path string; `DecisionQuestion`: question recortada (2..2000), `turn_id?:UUID` | turn_id, run_id, answer, provider/model/versions, usage, evidence_analysis_id | R/A/M; RPC `read_decision_chat_turn_with_evidence` (lectura); LLM; RPC `record_decision_chat_turn_with_evidence` → T/M/S | Sí | **Sí** en turno nuevo; replay válido lee sin nueva llamada LLM |

`GET /api/datasets` sin `type` usa `workspace_service.list_datasets(limit)`; **ignora offset/q/include_archived** en ese camino. Con `type` sólo acepta `orders`/`fleet`, aplica tipo, archivo/paginación/búsqueda y deriva perfil sin guardar. La subida sin `dataset_type` toma el circuito legacy y no usa label/parent/is_sample. Estos comportamientos forman parte del baseline, no se corrigen en Fase 0.

## `backend/app/routes/dispatch.py` · 23 operaciones

Todas heredan **B** de `APIRouter(dependencies=[Depends(require_upload_access)])`, incluidas plantillas, contratos y diagnóstico.

| Método y ruta | Handler / auth | Input | Output principal | Tablas / Storage / externo | WS | Mutación |
| --- | --- | --- | --- | --- | --- | --- |
| GET `/api/dispatch/status` | `status` · B | — | available, engine_version, checks, message | Probes D/R/J/Q, catálogo OpenAPI RPC y metadata del bucket ST; no invoca RPC de negocio | Global | No |
| GET `/api/dispatch/contracts` | `contracts` · B | — | `formats`, `file_rules` (CSV,10MiB,encoding/delimiters/fechas/decimal) | Contratos locales | No | No |
| GET `/api/decision-cases` | `list_decision_cases` · B | `status=active` (active/completed/archived), `limit=50` (1..100), `offset=0`, `summary=false` | `{cases:[{case,decision_case,orders,fleet}]}`; `summary` limita bundles SQL | RPC STABLE `list_decision_cases` por **POST**; C/D/R | Sí | No; proyección de estado en memoria |
| POST `/api/decision-cases` | `create_decision_case` · B | `DecisionCaseCreate`: id, orders_dataset_id, fleet_dataset_id UUID, state? | `{case}` | C/D | Sí | **Sí**: crea; si ya existe y trae state, actualiza snapshot |
| GET `/api/decision-cases/{case_id}` | `get_decision_case` · B | UUID | `{case,decision_case,orders,fleet}` | C/D y RPC `decision_case_history` → R | Sí | No; no guarda estado reconstruido |
| GET `/api/decision-cases/{case_id}/runs` | `get_decision_case_runs` · B | UUID; `node_id?` assignment/scheduling/final_assignment; `limit=50` (1..100), `offset=0` | case_id,node_id,total,limit,offset,summary,runs con decision_state/is_latest/is_current_approved | C y RPC `decision_case_history` → R | Sí | No |
| PATCH `/api/decision-cases/{case_id}` | `update_decision_case` · B | UUID; `DecisionCaseUpdate`: status? active/completed/archived, state?; al menos uno | `{case}` | C por ID | Sí | **Sí**: status/snapshot/timestamps/archived_at; no borrado |
| POST `/api/datasets/validate` | `validate_dataset` · B | Query requerida `dataset_type=orders/fleet`, multipart CSV ≤10MiB | Reporte sin records, incluye file.name/size_bytes/sha256 | Sólo bytes recibidos y validadores locales | No persistido; datos del usuario | No; CPU, sin guardar |
| POST `/api/datasets/load-sample` | `load_sample` · B | — | orders,fleet,orders_validation,fleet_validation,duplicate por tipo | CSV repo `sample_data/v3`; D/ST y RPC `set_default_fleet` | Sí | **Sí**: altas/dedup, is_sample y default Fleet global |
| PATCH `/api/datasets/{dataset_id}` | `update_dataset` · B | UUID; `LabelUpdate {label}`; limpia no vacío ≤120 | `{dataset}` | D por ID | Sí | **Sí**: etiqueta |
| GET `/api/datasets/{dataset_id}/download` | `download_dataset` · B | UUID, sólo dataset Orders/Fleet | CSV attachment con original_filename saneado | D y ST | Sí | No |
| POST `/api/runs/preflight` | `preflight` · B | `Inputs`: orders_dataset_id,fleet_dataset_id UUID; allow_third_party=true | Compatibilidad, decision_readiness, orders_profile,fleet_profile,ambos datasets | D/ST; validación y assignment_preflight | Sí | No; POST de lectura/cálculo local |
| POST `/api/runs/assignment-preview` | `assignment_preview` · B | `AssignmentPreviewRequest`: ambos UUID; filters máximo12; resource_mode own/mixed/outsourced | Preview de scope/recursos, datasets, valid/errors/anomalies | D/ST; scope/preflight local | Sí | No; no motor completo ni persistencia |
| POST `/api/runs` | `run` · B | `RunRequest` (detallado abajo); query `run_id?:UUID` | Run encolado/replay, **202**; `Location`, `Retry-After:2` | D/C/R/J; `enqueue_dispatch_run`; puede asegurar C antes de RPC | Sí | **Sí**: case opcional + run/job atómicos; replay no duplica |
| POST `/api/runs/{run_id}/cancel` | `cancel_run` · B | UUID | Run cancelado o ya terminal recuperable | RPC `cancel_dispatch_job` → J/R; triggers pueden Q | Sí | **Sí**: marca error/cancelled; no DELETE |
| POST `/api/runs/{run_id}/approve` | `approve_run` · B | UUID; `ApprovalRequest {case_id:UUID,node_id:assignment/scheduling}` | Run aprobado; `projection_pending:true` si falla proyección posterior | R/C/V; RPC `approve_decision_run_version`, triggers Q; luego `sync_case_history` C | Sí | **Sí**: aprobación/supersesión/eventos atómicos y proyección eventual |
| POST `/api/datasets/{dataset_id}/default` | `default` · B | UUID | `{ok:true}` | RPC `set_default_fleet` → D | Sí | **Sí**: limpia default Fleet global y establece target |
| POST `/api/datasets/{dataset_id}/archive` | `archive` · B | UUID | `{dataset}` | D por ID; requiere Orders/Fleet; bloquea Fleet default | Sí | **Sí**: archived_at; objeto retenido |
| POST `/api/datasets/{dataset_id}/unarchive` | `unarchive` · B | UUID | `{dataset}` | D por ID; requiere Orders/Fleet | Sí | **Sí**: archived_at=null |
| GET `/api/dispatch/templates/{kind}` | `template` · B | kind `orders` o `fleet`; otros404 | CSV attachment `orders.csv`/`fleet.csv` | Generación local `template_csv` | No | No |
| POST `/api/datasets/{dataset_id}/refresh-profile` | `refresh_dataset_profile` · B | UUID | `{dataset}` | D/ST; `_ensure_profile(persist=True)` | Sí | **Sí condicional**: actualiza perfil obsoleto/tamaños/label ausente; retorna sin cambio si no necesita o no puede perfilar |
| GET `/api/runs/{run_id}/comparative` | `comparative_state` · B | UUID; run Assignment completado | Artefacto o status available / completed con source_mode original | R/A por run/base_run_id | Sí | No |
| POST `/api/runs/{run_id}/comparative` | `comparative_generate` · B | UUID; `retry=false` | Artefacto público; 202 queued/running o200 disponible; Location/Retry-After | R/A; RPC `enqueue_comparative_analysis`; worker luego D/ST/A | Sí | **Sí condicional**: reutiliza o enqueue/retry; no cambia R selected/aprobación |

## Variantes dinámicas y contratos que no deben omitirse

### Admisión de corridas

`RunRequest` en `dispatch.py` requiere `orders_dataset_id` y `fleet_dataset_id` UUID. Acepta `configuration={}`, `options={}`, `decision_case?` y `source_run_id?`. La selección del motor se hace por **`decision_case.node_id`**, no por la URL:

| decision_case.node_id | Configuración/opciones validadas | Fuente requerida | Persistencia/resultado |
| --- | --- | --- | --- |
| `logistics_assignment` | `AssignmentConfig`, `AssignmentOptions` | — | Motor Assignment, `assignment_v1`, case/node en columnas y JSON |
| `logistics_scheduling` | `SchedulingConfig`, `SchedulingOptions` | `source_run_id` UUID de Assignment aprobada vigente | Motor Scheduling, `scheduling_v1`, upstream_run_id/handoff del mismo case/Data Pack |
| Ausente (sin case) | `DispatchConfig`, `DispatchOptions` | No requerida por el modelo | Circuito Dispatch legacy-compatible; también en cola durable |

`DecisionCaseRef` sólo permite Assignment/Scheduling; no D3. `RunRequest.canonical` valida modelos concretos aunque OpenAPI expone configuration/options como dict: revisar sólo OpenAPI pierde esta semántica. Los modelos viven en `app/models/assignment_config.py`, `scheduling_config.py`, `dispatch_config.py` y `decision_config.py`; conservar límites, dimensiones, objetivos y reglas vigentes durante la encapsulación.

`dispatch_job_service.enqueue` resuelve el mismo `run_id`+fingerprint antes de revalidar el upstream mutable. Distinta intención con mismo UUID devuelve409. Cola llena429 + Retry-After. La identidad del UUID no está asociada a un workspace/actor, por lo que replay/cancel deben quedar dentro del plan de autorización. Un error después de `ensure_case` puede dejar el caso creado aunque la admisión final falle; la transacción de enqueue cubre run+job, no la creación previa del caso.

### Datasets y casos

- `POST /api/datasets/upload?dataset_type=orders` y `...=fleet` validan contratos específicos, permiten parent Fleet y generan nombre canónico. Sin query se usa `logistics_legacy`, nombre Storage `input.csv`, dedup por hash global. Tipo inválido422.
- `GET /api/datasets?type=orders/fleet` devuelve biblioteca typed; sin tipo devuelve la lista legacy general (no sólo datasets legacy). Las dos ramas carecen de tenant.
- `POST /api/datasets/load-sample` **es mutante**, incluso cuando los bytes ya existen: marca sample y establece Fleet vigente; nunca usar como health probe.
- `DecisionCaseCreate/Update`, `DecisionCaseRef`, `ApprovalRequest`, `AssignmentPreviewRequest` prohíben campos extra. Los snapshots son dicts validados/canonicalizados por `decision_case_service._validate_state`; no son un contrato de permisos.
- Aprobación de Assignment y de Scheduling usa misma ruta. El backend comprueba case/node/schema, upstream vigente y la RPC fija `approved_by='shared_workspace:dation'`; emite eventos `approved`/`superseded` en V y un replay no genera un segundo evento. La función real está capturada en el catálogo de esta fase y coincide con `20261010190000_approval_clock_after_lock.sql`. No existe actor humano distinto ni parámetro de actor aceptado del cliente.
- `GET /api/decision-cases/{case_id}/runs?node_id=logistics_final_assignment` permite historial/placeholder de nodo; no habilita ejecutar D3.

### IA y evidencia

- Interpretación adapta contexto por `schema_version` en `decision_context.build_decision_context`: scheduling, assignment/dispatch y legacy. No recalcula motores en el endpoint de chat.
- Chat nuevo: verifica turno → carga run/evidencia/historial → proveedor → persistencia atómica T/M/S. `turn_id` permite replay de la misma pregunta; UUID con intención/run distintos409. No aporta autorización de usuario.
- Explanation siempre puede generar nueva salida/coste; su RPC une E/S. `GET interpretation` sólo lee y permite paginar mensajes con evidencia referenciada.
- Comparativo sólo admite Assignment completada; puede reutilizar escenarios existentes o encolar referencias. `retry=true` sólo cambia semántica para artefacto fallido; UI/URL no es guard de pertenencia.

## Superficies implícitas y worker

| Método/ruta | Auth actual | Input/output | Acceso / mutación | Tratamiento posterior |
| --- | --- | --- | --- | --- |
| GET/HEAD `/openapi.json` | P, FastAPI default | Esquema con 42 operaciones y HTTPBasic | Código, sin DB | Decidir exposición de docs en producción; no confundir esquema con permisos. |
| GET/HEAD `/docs` | P | Swagger HTML | Sin DB | Mismo gate operativo. |
| GET/HEAD `/docs/oauth2-redirect` | P | Helper HTML de FastAPI | Sin DB | No implementa OAuth/login del producto. |
| GET/HEAD `/redoc` | P | ReDoc HTML | Sin DB | Mismo gate operativo. |
| GET/HEAD `/static/{path:path}` | P, `StaticFiles` | Assets; JS/MJS/CSS revalidan cache | Archivos locales, no mutación | Path variable del mount; no sirve objetos privados de Supabase. |
| Cualquier URL de `worker.py:health_handler` salvo coincidencias siguientes | Sin auth propia de app; depende IAM/ingress | JSON liveness200 | Sin DB desde handler | No es router FastAPI. Responde liveness incluso ruta no reconocida; mantener privado. |
| Worker GET `/ready` | Igual | `{ready:true/false}`,200/503 | Estado local mantenido por report DB | No es la ruta `/ready` del API. |
| Worker GET `/metrics` | Igual | Texto métricas proceso | Lectura memoria; no snapshot global desde handler | Revisar IAM/scrape antes de exponer. |

No hay rutas de plataforma/membresía ni WebSocket/SSE ni API DELETE de datasets/casos/corridas en el baseline. Export CSV/JSON de dashboards se construye en frontend usando datos ya recuperados; no hay endpoint `/api/export` adicional. Las llamadas del worker/RPC son superficie interna documentada en [00-architecture-audit.md](00-architecture-audit.md), no operaciones adicionales de FastAPI.

## Error y autorización: límites del baseline

`dispatch.py:guarded` traduce LookupError404, RunConflict409, QueueFull429, ValueError422, TimeoutError408 y errores HTTP externos502. Comparativo usa409/404/422/429 y503 de dependencia; IA tiene504 de timeout y502/503 del proveedor. Los validadores de entrada globales generan422 con detalle de campos. Un 404/409 por integridad no prueba rechazo de acceso entre tenants: hoy no existe ese control.

Para migrar sin atajos: cada operación WS sí necesita actor+membership+workspace resueltos en servidor, autorización del padre/objeto y de todas sus referencias, scopes en consultas/mutaciones y propagación validada a colas. Los caminos de lista, búsqueda, counts, duplicate, profile, download, replay, historial, aprobación, cancelación e IA deben probarse tanto como la creación. Las operaciones globales necesitan rol administrativo o infraestructura privada. El plan puede mantener rutas legacy, pero debe cubrirlas; no convertir Basic compartido en una puerta alternativa al nuevo control.
