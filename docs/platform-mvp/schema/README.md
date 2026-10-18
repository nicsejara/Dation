# Índice del esquema real

Fuente: [live-catalog.json](live-catalog.json), capturado en 2026-10-18T01:09:28.988781+00:00. PostgreSQL 17.6. Metadata y agregados; no datos de negocio.

Este índice facilita revisión; el JSON conserva definiciones exactas, orden de columnas, ACL y funciones completas. No es un instalador SQL.

## Tablas públicas

| Tabla | Columnas | Constraints | Índices adicionales | Triggers propios | RLS |
|---|---:|---:|---:|---:|---|
| `datasets` | 21 | 9 | 7 | 1 | Sí |
| `decision_approval_events` | 8 | 7 | 0 | 1 | Sí |
| `decision_case_reconciliations` | 5 | 2 | 0 | 0 | Sí |
| `decision_cases` | 12 | 6 | 4 | 1 | Sí |
| `decision_chat_turns` | 10 | 8 | 1 | 0 | Sí |
| `decision_comparative_analyses` | 22 | 9 | 1 | 1 | Sí |
| `decision_explanations` | 9 | 2 | 2 | 0 | Sí |
| `decision_interpretation_sources` | 6 | 8 | 0 | 1 | Sí |
| `decision_messages` | 9 | 4 | 3 | 0 | Sí |
| `decision_runs` | 26 | 15 | 12 | 6 | Sí |
| `dispatch_run_jobs` | 12 | 5 | 1 | 0 | Sí |
| `dispatch_worker_instances` | 4 | 2 | 1 | 0 | Sí |

### datasets

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
created_at timestamp with time zone DEFAULT now() NOT NULL
original_filename text NOT NULL
storage_bucket text DEFAULT 'dda-inputs'::text NOT NULL
storage_path text NOT NULL
mime_type text
size_bytes bigint
sha256 text
status text DEFAULT 'uploaded'::text NOT NULL
row_count integer
column_count integer
error_message text
dataset_type text DEFAULT 'logistics_legacy'::text NOT NULL
schema_version text
label text
is_default boolean DEFAULT false NOT NULL
parent_dataset_id uuid
profile_json jsonb
archived_at timestamp with time zone
is_sample boolean DEFAULT false NOT NULL
canonical_filename text
```

Constraints:
- `datasets_column_count_nonnegative`: `CHECK (column_count IS NULL OR column_count >= 0)`
- `datasets_dataset_type_check`: `CHECK (dataset_type = ANY (ARRAY['logistics_legacy'::text, 'orders'::text, 'fleet'::text]))`
- `datasets_parent_dataset_id_fkey`: `FOREIGN KEY (parent_dataset_id) REFERENCES datasets(id)`
- `datasets_pkey`: `PRIMARY KEY (id)`
- `datasets_row_count_nonnegative`: `CHECK (row_count IS NULL OR row_count >= 0)`
- `datasets_sha256_format`: `CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'::text)`
- `datasets_size_bytes_nonnegative`: `CHECK (size_bytes IS NULL OR size_bytes >= 0)`
- `datasets_status_valid`: `CHECK (status = ANY (ARRAY['uploaded'::text, 'processing'::text, 'processed'::text, 'error'::text]))`
- `datasets_storage_path_key`: `UNIQUE (storage_path)`

### decision_approval_events

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
run_id uuid NOT NULL
case_id uuid NOT NULL
node_id text NOT NULL
action text NOT NULL
actor text NOT NULL
occurred_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL
replacement_run_id uuid
```

Constraints:
- `decision_approval_events_action_check`: `CHECK (action = ANY (ARRAY['approved'::text, 'superseded'::text]))`
- `decision_approval_events_actor_check`: `CHECK (actor = 'shared_workspace:dation'::text)`
- `decision_approval_events_case_id_fkey`: `FOREIGN KEY (case_id) REFERENCES decision_cases(id) ON DELETE RESTRICT`
- `decision_approval_events_pkey`: `PRIMARY KEY (id)`
- `decision_approval_events_replacement_run_id_fkey`: `FOREIGN KEY (replacement_run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT`
- `decision_approval_events_run_id_action_key`: `UNIQUE (run_id, action)`
- `decision_approval_events_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT`

### decision_case_reconciliations

```sql
case_id uuid NOT NULL
version bigint DEFAULT 1 NOT NULL
attempts integer DEFAULT 0 NOT NULL
available_at timestamp with time zone DEFAULT now() NOT NULL
updated_at timestamp with time zone DEFAULT now() NOT NULL
```

Constraints:
- `decision_case_reconciliations_case_id_fkey`: `FOREIGN KEY (case_id) REFERENCES decision_cases(id) ON DELETE CASCADE`
- `decision_case_reconciliations_pkey`: `PRIMARY KEY (case_id)`

### decision_cases

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
schema_version text DEFAULT 'decision_case_v1'::text NOT NULL
domain text DEFAULT 'logistics'::text NOT NULL
status text DEFAULT 'active'::text NOT NULL
orders_dataset_id uuid NOT NULL
fleet_dataset_id uuid NOT NULL
input_signature text NOT NULL
state_json jsonb DEFAULT '{}'::jsonb NOT NULL
created_at timestamp with time zone DEFAULT now() NOT NULL
updated_at timestamp with time zone DEFAULT now() NOT NULL
last_activity_at timestamp with time zone DEFAULT now() NOT NULL
archived_at timestamp with time zone
```

Constraints:
- `decision_cases_distinct_inputs_check`: `CHECK (orders_dataset_id <> fleet_dataset_id)`
- `decision_cases_domain_check`: `CHECK (domain = 'logistics'::text)`
- `decision_cases_fleet_dataset_id_fkey`: `FOREIGN KEY (fleet_dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `decision_cases_orders_dataset_id_fkey`: `FOREIGN KEY (orders_dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT`
- `decision_cases_pkey`: `PRIMARY KEY (id)`
- `decision_cases_status_check`: `CHECK (status = ANY (ARRAY['active'::text, 'completed'::text, 'archived'::text]))`

### decision_chat_turns

```sql
turn_id uuid NOT NULL
run_id uuid NOT NULL
question_hash text NOT NULL
created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL
provider text NOT NULL
model text NOT NULL
knowledge_version text NOT NULL
prompt_version text NOT NULL
usage_json jsonb DEFAULT '{}'::jsonb NOT NULL
request_id uuid
```

Constraints:
- `decision_chat_turns_knowledge_version_check`: `CHECK (length(knowledge_version) >= 1 AND length(knowledge_version) <= 150)`
- `decision_chat_turns_model_check`: `CHECK (length(model) >= 1 AND length(model) <= 150)`
- `decision_chat_turns_pkey`: `PRIMARY KEY (turn_id)`
- `decision_chat_turns_prompt_version_check`: `CHECK (length(prompt_version) >= 1 AND length(prompt_version) <= 150)`
- `decision_chat_turns_provider_check`: `CHECK (length(provider) >= 1 AND length(provider) <= 100)`
- `decision_chat_turns_question_hash_check`: `CHECK (question_hash ~ '^[0-9a-f]{64}$'::text)`
- `decision_chat_turns_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON DELETE CASCADE`
- `decision_chat_turns_usage_json_check`: `CHECK (jsonb_typeof(usage_json) = 'object'::text)`

### decision_comparative_analyses

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
base_run_id uuid NOT NULL
base_result_fingerprint text NOT NULL
source_mode text NOT NULL
status text NOT NULL
request_json jsonb NOT NULL
result_json jsonb
result_fingerprint text
progress_json jsonb DEFAULT '{"stage": "queued"}'::jsonb NOT NULL
error_message text
duration_ms bigint
created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL
started_at timestamp with time zone
finished_at timestamp with time zone
available_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL
deadline_at timestamp with time zone DEFAULT (clock_timestamp() + '00:30:00'::interval) NOT NULL
generation integer DEFAULT 1 NOT NULL
attempts integer DEFAULT 0 NOT NULL
max_attempts integer DEFAULT 3 NOT NULL
lease_token uuid
lease_expires_at timestamp with time zone
heartbeat_at timestamp with time zone
```

Constraints:
- `decision_comparative_analyses_base_run_id_fkey`: `FOREIGN KEY (base_run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT`
- `decision_comparative_analyses_base_run_id_id_key`: `UNIQUE (base_run_id, id)`
- `decision_comparative_analyses_base_run_id_key`: `UNIQUE (base_run_id)`
- `decision_comparative_analyses_check`: `CHECK (status = 'running'::text AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL OR status <> 'running'::text AND lease_token IS NULL AND lease_expires_at IS NULL)`
- `decision_comparative_analyses_check1`: `CHECK (status <> 'completed'::text OR jsonb_typeof(result_json) = 'object'::text AND result_fingerprint IS NOT NULL)`
- `decision_comparative_analyses_max_attempts_check`: `CHECK (max_attempts >= 1 AND max_attempts <= 5)`
- `decision_comparative_analyses_pkey`: `PRIMARY KEY (id)`
- `decision_comparative_analyses_source_mode_check`: `CHECK (source_mode = ANY (ARRAY['existing'::text, 'computed'::text]))`
- `decision_comparative_analyses_status_check`: `CHECK (status = ANY (ARRAY['queued'::text, 'running'::text, 'completed'::text, 'error'::text]))`

### decision_explanations

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
run_id uuid NOT NULL
created_at timestamp with time zone DEFAULT now() NOT NULL
provider text NOT NULL
model text NOT NULL
knowledge_version text NOT NULL
prompt_version text NOT NULL
response_json jsonb NOT NULL
usage_json jsonb DEFAULT '{}'::jsonb NOT NULL
```

Constraints:
- `decision_explanations_pkey`: `PRIMARY KEY (id)`
- `decision_explanations_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON UPDATE RESTRICT ON DELETE CASCADE`

### decision_interpretation_sources

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
run_id uuid NOT NULL
analysis_id uuid
explanation_id uuid
chat_turn_id uuid
created_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL
```

Constraints:
- `decision_interpretation_sources_chat_turn_id_fkey`: `FOREIGN KEY (chat_turn_id) REFERENCES decision_chat_turns(turn_id) ON DELETE RESTRICT`
- `decision_interpretation_sources_chat_turn_id_key`: `UNIQUE (chat_turn_id)`
- `decision_interpretation_sources_check`: `CHECK (((explanation_id IS NOT NULL)::integer + (chat_turn_id IS NOT NULL)::integer) = 1)`
- `decision_interpretation_sources_explanation_id_fkey`: `FOREIGN KEY (explanation_id) REFERENCES decision_explanations(id) ON DELETE RESTRICT`
- `decision_interpretation_sources_explanation_id_key`: `UNIQUE (explanation_id)`
- `decision_interpretation_sources_pkey`: `PRIMARY KEY (id)`
- `decision_interpretation_sources_run_id_analysis_id_fkey`: `FOREIGN KEY (run_id, analysis_id) REFERENCES decision_comparative_analyses(base_run_id, id) ON DELETE RESTRICT`
- `decision_interpretation_sources_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT`

### decision_messages

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
run_id uuid NOT NULL
created_at timestamp with time zone DEFAULT now() NOT NULL
role text NOT NULL
content text NOT NULL
provider text
model text
knowledge_version text
turn_id uuid
```

Constraints:
- `decision_messages_pkey`: `PRIMARY KEY (id)`
- `decision_messages_role_check`: `CHECK (role = ANY (ARRAY['user'::text, 'assistant'::text]))`
- `decision_messages_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON UPDATE RESTRICT ON DELETE CASCADE`
- `decision_messages_turn_id_fkey`: `FOREIGN KEY (turn_id) REFERENCES decision_chat_turns(turn_id) ON DELETE CASCADE`

### decision_runs

```sql
id uuid DEFAULT gen_random_uuid() NOT NULL
dataset_id uuid NOT NULL
created_at timestamp with time zone DEFAULT now() NOT NULL
started_at timestamp with time zone
finished_at timestamp with time zone
engine_name text NOT NULL
engine_version text NOT NULL
configuration_json jsonb DEFAULT '{}'::jsonb NOT NULL
status text DEFAULT 'queued'::text NOT NULL
result_json jsonb
error_message text
duration_ms bigint
schema_version text DEFAULT 'legacy_v0.2'::text NOT NULL
orders_dataset_id uuid
fleet_dataset_id uuid
input_fingerprint text
result_fingerprint text
summary_json jsonb
progress_json jsonb
decision_case_id uuid
node_id text
upstream_run_id uuid
approved_at timestamp with time zone
superseded_at timestamp with time zone
superseded_by_run_id uuid
approved_by text
```

Constraints:
- `decision_runs_approved_by_check`: `CHECK (approved_by IS NULL OR approved_by = 'shared_workspace:dation'::text AND approved_at IS NOT NULL)`
- `decision_runs_case_node_pair_check`: `CHECK (decision_case_id IS NULL AND node_id IS NULL OR decision_case_id IS NOT NULL AND node_id IS NOT NULL)`
- `decision_runs_completed_has_result`: `CHECK (status <> 'completed'::text OR result_json IS NOT NULL)`
- `decision_runs_dataset_id_fkey`: `FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON UPDATE RESTRICT ON DELETE RESTRICT`
- `decision_runs_decision_case_id_fkey`: `FOREIGN KEY (decision_case_id) REFERENCES decision_cases(id) ON DELETE RESTRICT`
- `decision_runs_duration_nonnegative`: `CHECK (duration_ms IS NULL OR duration_ms >= 0)`
- `decision_runs_error_has_message`: `CHECK (status <> 'error'::text OR error_message IS NOT NULL)`
- `decision_runs_fleet_dataset_id_fkey`: `FOREIGN KEY (fleet_dataset_id) REFERENCES datasets(id)`
- `decision_runs_node_id_check`: `CHECK (node_id IS NULL OR (node_id = ANY (ARRAY['logistics_assignment'::text, 'logistics_scheduling'::text, 'logistics_final_assignment'::text])))`
- `decision_runs_orders_dataset_id_fkey`: `FOREIGN KEY (orders_dataset_id) REFERENCES datasets(id)`
- `decision_runs_pkey`: `PRIMARY KEY (id)`
- `decision_runs_status_valid`: `CHECK (status = ANY (ARRAY['queued'::text, 'running'::text, 'completed'::text, 'error'::text]))`
- `decision_runs_superseded_by_run_id_fkey`: `FOREIGN KEY (superseded_by_run_id) REFERENCES decision_runs(id) ON DELETE SET NULL`
- `decision_runs_superseded_requires_approval_check`: `CHECK (superseded_at IS NULL OR approved_at IS NOT NULL)`
- `decision_runs_upstream_run_id_fkey`: `FOREIGN KEY (upstream_run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT`

### dispatch_run_jobs

```sql
run_id uuid NOT NULL
request_json jsonb NOT NULL
request_fingerprint text NOT NULL
state text DEFAULT 'queued'::text NOT NULL
attempts integer DEFAULT 0 NOT NULL
max_attempts integer DEFAULT 3 NOT NULL
lease_token uuid
lease_expires_at timestamp with time zone
heartbeat_at timestamp with time zone
available_at timestamp with time zone DEFAULT now() NOT NULL
deadline_at timestamp with time zone DEFAULT (now() + '00:30:00'::interval) NOT NULL
created_at timestamp with time zone DEFAULT now() NOT NULL
```

Constraints:
- `dispatch_job_lease_pair`: `CHECK (state = 'running'::text AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL OR state <> 'running'::text AND lease_token IS NULL AND lease_expires_at IS NULL)`
- `dispatch_run_jobs_max_attempts_check`: `CHECK (max_attempts >= 1 AND max_attempts <= 5)`
- `dispatch_run_jobs_pkey`: `PRIMARY KEY (run_id)`
- `dispatch_run_jobs_run_id_fkey`: `FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT`
- `dispatch_run_jobs_state_check`: `CHECK (state = ANY (ARRAY['queued'::text, 'running'::text, 'completed'::text, 'error'::text]))`

### dispatch_worker_instances

```sql
worker_id uuid NOT NULL
revision text NOT NULL
seen_at timestamp with time zone NOT NULL
ready boolean NOT NULL
```

Constraints:
- `dispatch_worker_instances_pkey`: `PRIMARY KEY (worker_id)`
- `dispatch_worker_instances_revision_check`: `CHECK (revision ~ '^[a-zA-Z0-9-]{1,100}$'::text)`

## Funciones públicas

Firmas exactas; cuerpos/grants en `catalog.functions`, seguridad/search_path en `catalog.function_security`.
- `public.ack_case_reconciliation(target_case_id uuid, observed_version bigint)`
- `public.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text)`
- `public.cancel_dispatch_job(target_run_id uuid)`
- `public.claim_comparative_analysis(worker_token uuid, lease_seconds integer)`
- `public.claim_dispatch_job(worker_token uuid, lease_seconds integer)`
- `public.comparative_operational_snapshot()`
- `public.current_decision_explanation(target_run_id uuid)`
- `public.decision_case_history(target_case_id uuid, target_node_id text, page_limit integer, page_offset integer)`
- `public.dispatch_operational_snapshot()`
- `public.enqueue_case_reconciliation()`
- `public.enqueue_comparative_analysis(target_base_id uuid, job_request jsonb, existing_result jsonb, retry_failed boolean)`
- `public.enqueue_dispatch_run(run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer)`
- `public.finish_comparative_analysis(target_analysis_id uuid, worker_token uuid, terminal_values jsonb)`
- `public.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb)`
- `public.heartbeat_comparative_analysis(target_analysis_id uuid, worker_token uuid, lease_seconds integer, progress jsonb)`
- `public.heartbeat_dispatch_job(target_run_id uuid, worker_token uuid, lease_seconds integer, progress jsonb)`
- `public.list_decision_cases(case_status text, page_limit integer, page_offset integer, summary_only boolean)`
- `public.maintain_dispatch_jobs()`
- `public.protect_comparative_analysis()`
- `public.protect_persistence_identity()`
- `public.read_decision_chat_turn(target_turn_id uuid, target_run_id uuid, intent_hash text)`
- `public.read_decision_chat_turn_with_evidence(target_turn_id uuid, target_run_id uuid, intent_hash text)`
- `public.record_decision_chat_turn(target_turn_id uuid, target_run_id uuid, intent_hash text, question_text text, answer_text text, metadata jsonb)`
- `public.record_decision_chat_turn_with_evidence(target_turn_id uuid, target_run_id uuid, intent_hash text, question_text text, answer_text text, metadata jsonb, evidence_analysis_id uuid)`
- `public.record_decision_explanation_with_evidence(explanation jsonb, evidence_analysis_id uuid)`
- `public.reject_approval_event_mutation()`
- `public.report_dispatch_worker(target_worker_id uuid, worker_revision text, is_ready boolean)`
- `public.request_case_reconciliation(target_case_id uuid)`
- `public.set_default_fleet(target_id uuid)`
- `public.validate_current_run_admission()`
- `public.validate_decision_run_history()`
- `public.validate_dispatch_run()`
- `public.validate_interpretation_source()`

## Esquemas administrados

Auth/Storage se describen en `catalog.managed_relations` (estructura, sin filas), `catalog.storage_policies`, `catalog.storage_buckets` y `catalog.storage_layout`. No se reconstruyen ni migran esos esquemas como parte del baseline público.

Comparación reconstruida: [catalog-comparison.json](catalog-comparison.json). Preflight: [lineage-preflight.json](lineage-preflight.json), [consulta exacta](lineage-preflight.sql). Metadata Auth: [auth-readiness.json](auth-readiness.json); HTTP/runtime: [runtime-readiness.json](runtime-readiness.json). Checksums de todos los JSON de esta carpeta: [SHA256SUMS](SHA256SUMS).

Para nueva captura usar una carpeta distinta:

```bash
python scripts/audit_platform_schema.py --output /tmp/dation-platform-schema-next
```
