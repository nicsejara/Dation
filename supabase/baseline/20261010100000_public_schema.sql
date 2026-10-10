-- Production catalog capture: gijiinufjjurgfeehufj, 2026-10-10, Phase 3.

-- No application data or credentials. FRESH INSTALL ONLY; see supabase/README.md.

-- PostgreSQL 17+; infrastructure: public schema, anon/authenticated/service_role roles.

BEGIN;

CREATE TABLE public.datasets (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  original_filename text NOT NULL,
  storage_bucket text DEFAULT 'dda-inputs'::text NOT NULL,
  storage_path text NOT NULL,
  mime_type text,
  size_bytes bigint,
  sha256 text,
  status text DEFAULT 'uploaded'::text NOT NULL,
  row_count integer,
  column_count integer,
  error_message text,
  dataset_type text DEFAULT 'logistics_legacy'::text NOT NULL,
  schema_version text,
  label text,
  is_default boolean DEFAULT false NOT NULL,
  parent_dataset_id uuid,
  profile_json jsonb,
  archived_at timestamp with time zone,
  is_sample boolean DEFAULT false NOT NULL,
  canonical_filename text
);

CREATE TABLE public.decision_case_reconciliations (
  case_id uuid NOT NULL,
  version bigint DEFAULT 1 NOT NULL,
  attempts integer DEFAULT 0 NOT NULL,
  available_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.decision_cases (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  schema_version text DEFAULT 'decision_case_v1'::text NOT NULL,
  domain text DEFAULT 'logistics'::text NOT NULL,
  status text DEFAULT 'active'::text NOT NULL,
  orders_dataset_id uuid NOT NULL,
  fleet_dataset_id uuid NOT NULL,
  input_signature text NOT NULL,
  state_json jsonb DEFAULT '{}'::jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  last_activity_at timestamp with time zone DEFAULT now() NOT NULL,
  archived_at timestamp with time zone
);

CREATE TABLE public.decision_explanations (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  run_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  provider text NOT NULL,
  model text NOT NULL,
  knowledge_version text NOT NULL,
  prompt_version text NOT NULL,
  response_json jsonb NOT NULL,
  usage_json jsonb DEFAULT '{}'::jsonb NOT NULL
);

CREATE TABLE public.decision_messages (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  run_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  provider text,
  model text,
  knowledge_version text
);

CREATE TABLE public.decision_runs (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  dataset_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  started_at timestamp with time zone,
  finished_at timestamp with time zone,
  engine_name text NOT NULL,
  engine_version text NOT NULL,
  configuration_json jsonb DEFAULT '{}'::jsonb NOT NULL,
  status text DEFAULT 'queued'::text NOT NULL,
  result_json jsonb,
  error_message text,
  duration_ms bigint,
  schema_version text DEFAULT 'legacy_v0.2'::text NOT NULL,
  orders_dataset_id uuid,
  fleet_dataset_id uuid,
  input_fingerprint text,
  result_fingerprint text,
  summary_json jsonb,
  progress_json jsonb,
  decision_case_id uuid,
  node_id text,
  upstream_run_id uuid,
  approved_at timestamp with time zone,
  superseded_at timestamp with time zone,
  superseded_by_run_id uuid
);

CREATE TABLE public.dispatch_run_jobs (
  run_id uuid NOT NULL,
  request_json jsonb NOT NULL,
  request_fingerprint text NOT NULL,
  state text DEFAULT 'queued'::text NOT NULL,
  attempts integer DEFAULT 0 NOT NULL,
  max_attempts integer DEFAULT 3 NOT NULL,
  lease_token uuid,
  lease_expires_at timestamp with time zone,
  heartbeat_at timestamp with time zone,
  available_at timestamp with time zone DEFAULT now() NOT NULL,
  deadline_at timestamp with time zone DEFAULT (now() + '00:30:00'::interval) NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_column_count_nonnegative" CHECK (column_count IS NULL OR column_count >= 0);

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_dataset_type_check" CHECK (dataset_type = ANY (ARRAY['logistics_legacy'::text, 'orders'::text, 'fleet'::text]));

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_pkey" PRIMARY KEY (id);

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_row_count_nonnegative" CHECK (row_count IS NULL OR row_count >= 0);

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_sha256_format" CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'::text);

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_size_bytes_nonnegative" CHECK (size_bytes IS NULL OR size_bytes >= 0);

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_status_valid" CHECK (status = ANY (ARRAY['uploaded'::text, 'processing'::text, 'processed'::text, 'error'::text]));

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_storage_path_key" UNIQUE (storage_path);

ALTER TABLE public.decision_case_reconciliations ADD CONSTRAINT "decision_case_reconciliations_pkey" PRIMARY KEY (case_id);

ALTER TABLE public.decision_cases ADD CONSTRAINT "decision_cases_distinct_inputs_check" CHECK (orders_dataset_id <> fleet_dataset_id);

ALTER TABLE public.decision_cases ADD CONSTRAINT "decision_cases_domain_check" CHECK (domain = 'logistics'::text);

ALTER TABLE public.decision_cases ADD CONSTRAINT "decision_cases_pkey" PRIMARY KEY (id);

ALTER TABLE public.decision_cases ADD CONSTRAINT "decision_cases_status_check" CHECK (status = ANY (ARRAY['active'::text, 'completed'::text, 'archived'::text]));

ALTER TABLE public.decision_explanations ADD CONSTRAINT "decision_explanations_pkey" PRIMARY KEY (id);

ALTER TABLE public.decision_messages ADD CONSTRAINT "decision_messages_pkey" PRIMARY KEY (id);

ALTER TABLE public.decision_messages ADD CONSTRAINT "decision_messages_role_check" CHECK (role = ANY (ARRAY['user'::text, 'assistant'::text]));

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_case_node_pair_check" CHECK (decision_case_id IS NULL AND node_id IS NULL OR decision_case_id IS NOT NULL AND node_id IS NOT NULL);

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_completed_has_result" CHECK (status <> 'completed'::text OR result_json IS NOT NULL);

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_duration_nonnegative" CHECK (duration_ms IS NULL OR duration_ms >= 0);

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_error_has_message" CHECK (status <> 'error'::text OR error_message IS NOT NULL);

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_node_id_check" CHECK (node_id IS NULL OR (node_id = ANY (ARRAY['logistics_assignment'::text, 'logistics_scheduling'::text, 'logistics_final_assignment'::text])));

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_pkey" PRIMARY KEY (id);

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_status_valid" CHECK (status = ANY (ARRAY['queued'::text, 'running'::text, 'completed'::text, 'error'::text]));

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_superseded_requires_approval_check" CHECK (superseded_at IS NULL OR approved_at IS NOT NULL);

ALTER TABLE public.dispatch_run_jobs ADD CONSTRAINT "dispatch_job_lease_pair" CHECK (state = 'running'::text AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL OR state <> 'running'::text AND lease_token IS NULL AND lease_expires_at IS NULL);

ALTER TABLE public.dispatch_run_jobs ADD CONSTRAINT "dispatch_run_jobs_max_attempts_check" CHECK (max_attempts >= 1 AND max_attempts <= 5);

ALTER TABLE public.dispatch_run_jobs ADD CONSTRAINT "dispatch_run_jobs_pkey" PRIMARY KEY (run_id);

ALTER TABLE public.dispatch_run_jobs ADD CONSTRAINT "dispatch_run_jobs_state_check" CHECK (state = ANY (ARRAY['queued'::text, 'running'::text, 'completed'::text, 'error'::text]));

ALTER TABLE public.datasets ADD CONSTRAINT "datasets_parent_dataset_id_fkey" FOREIGN KEY (parent_dataset_id) REFERENCES datasets(id);

ALTER TABLE public.decision_case_reconciliations ADD CONSTRAINT "decision_case_reconciliations_case_id_fkey" FOREIGN KEY (case_id) REFERENCES decision_cases(id) ON DELETE CASCADE;

ALTER TABLE public.decision_cases ADD CONSTRAINT "decision_cases_fleet_dataset_id_fkey" FOREIGN KEY (fleet_dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT;

ALTER TABLE public.decision_cases ADD CONSTRAINT "decision_cases_orders_dataset_id_fkey" FOREIGN KEY (orders_dataset_id) REFERENCES datasets(id) ON DELETE RESTRICT;

ALTER TABLE public.decision_explanations ADD CONSTRAINT "decision_explanations_run_id_fkey" FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON UPDATE RESTRICT ON DELETE CASCADE;

ALTER TABLE public.decision_messages ADD CONSTRAINT "decision_messages_run_id_fkey" FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON UPDATE RESTRICT ON DELETE CASCADE;

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_dataset_id_fkey" FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON UPDATE RESTRICT ON DELETE RESTRICT;

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_decision_case_id_fkey" FOREIGN KEY (decision_case_id) REFERENCES decision_cases(id) ON DELETE RESTRICT;

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_fleet_dataset_id_fkey" FOREIGN KEY (fleet_dataset_id) REFERENCES datasets(id);

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_orders_dataset_id_fkey" FOREIGN KEY (orders_dataset_id) REFERENCES datasets(id);

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_superseded_by_run_id_fkey" FOREIGN KEY (superseded_by_run_id) REFERENCES decision_runs(id) ON DELETE SET NULL;

ALTER TABLE public.decision_runs ADD CONSTRAINT "decision_runs_upstream_run_id_fkey" FOREIGN KEY (upstream_run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT;

ALTER TABLE public.dispatch_run_jobs ADD CONSTRAINT "dispatch_run_jobs_run_id_fkey" FOREIGN KEY (run_id) REFERENCES decision_runs(id) ON DELETE RESTRICT;

CREATE OR REPLACE FUNCTION public.ack_case_reconciliation(target_case_id uuid, observed_version bigint)
 RETURNS void
 LANGUAGE sql
 SET search_path TO 'public', 'pg_temp'
AS $function$
    delete from public.decision_case_reconciliations
    where case_id=target_case_id and version=observed_version;
$function$;

CREATE OR REPLACE FUNCTION public.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    target public.decision_runs%rowtype;
    approval_time timestamptz;
    source public.decision_runs%rowtype;
begin
    select * into target
      from public.decision_runs
     where id = target_run_id
     for update;

    if not found
       or target.status <> 'completed'
       or target.decision_case_id is distinct from target_case_id
       or target.node_id is distinct from target_node_id then
        raise exception 'La corrida no puede aprobarse para ese Decision Case';
    end if;

    if target.upstream_run_id is not null then
        select * into source
          from public.decision_runs
         where id = target.upstream_run_id;

        if not found
           or source.decision_case_id is distinct from target_case_id
           or source.approved_at is null
           or source.superseded_at is not null then
            raise exception 'La corrida upstream ya no es la decisión aprobada vigente';
        end if;
    end if;

    approval_time := coalesce(
        target.approved_at,
        nullif(target.result_json #>> '{decision_case,approved_at}', '')::timestamptz,
        now()
    );

    update public.decision_runs
       set superseded_at = approval_time,
           superseded_by_run_id = target_run_id
     where decision_case_id = target_case_id
       and node_id = target_node_id
       and id <> target_run_id
       and approved_at is not null
       and superseded_at is null;

    update public.decision_runs
       set approved_at = approval_time,
           superseded_at = null,
           superseded_by_run_id = null,
           configuration_json = jsonb_set(
               coalesce(configuration_json, '{}'::jsonb),
               '{decision_case}',
               coalesce(configuration_json -> 'decision_case', '{}'::jsonb)
                 || jsonb_build_object(
                     'case_id', target_case_id::text,
                     'node_id', target_node_id,
                     'status', 'approved',
                     'approved_at', approval_time
                 ),
               true
           ),
           result_json = jsonb_set(
               coalesce(result_json, '{}'::jsonb),
               '{decision_case}',
               coalesce(result_json -> 'decision_case', '{}'::jsonb)
                 || jsonb_build_object(
                     'case_id', target_case_id::text,
                     'node_id', target_node_id,
                     'status', 'approved',
                     'approved_at', approval_time
                 ),
               true
           )
     where id = target_run_id;

    return query
    select * from public.decision_runs where id = target_run_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.cancel_dispatch_job(target_run_id uuid)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
    perform 1 from public.dispatch_run_jobs where run_id=target_run_id for update;
    if not found then return; end if;
    update public.dispatch_run_jobs set state='error', lease_token=null, lease_expires_at=null
    where run_id=target_run_id and state in ('queued','running');
    if found then
        update public.decision_runs set status='error',finished_at=now(),
          error_message='La ejecución fue cancelada.',
          progress_json=jsonb_build_object('stage','cancelled')
        where id=target_run_id and status in ('queued','running');
    end if;
    return query select * from public.decision_runs where id=target_run_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.claim_dispatch_job(worker_token uuid, lease_seconds integer DEFAULT 120)
 RETURNS SETOF dispatch_run_jobs
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
declare target public.dispatch_run_jobs%rowtype;
begin
    perform public.maintain_dispatch_jobs();
    select * into target from public.dispatch_run_jobs
    where ((state='queued' and available_at <= now()) or (state='running' and lease_expires_at <= now()))
      and attempts < max_attempts and deadline_at > now()
    order by available_at, created_at for update skip locked limit 1;
    if not found then return; end if;
    update public.dispatch_run_jobs set state='running', attempts=attempts+1,
        lease_token=worker_token, heartbeat_at=now(),
        lease_expires_at=least(deadline_at,now()+make_interval(secs=>greatest(30,least(lease_seconds,300))))
    where run_id=target.run_id;
    update public.decision_runs set status='running', started_at=coalesce(started_at,now()),
        progress_json=jsonb_build_object('stage','validating','attempt',target.attempts+1), error_message=null
    where id=target.run_id and status in ('queued','running');
    return query select * from public.dispatch_run_jobs where run_id=target.run_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.enqueue_case_reconciliation()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
    if new.decision_case_id is not null then
        perform public.request_case_reconciliation(new.decision_case_id);
    end if;
    return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.enqueue_dispatch_run(run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer DEFAULT 32)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    existing_job public.dispatch_run_jobs%rowtype;
    target_id uuid := (run_payload ->> 'id')::uuid;
begin
    -- Serialize admission, but never calculation. Replays do not consume capacity.
    perform pg_advisory_xact_lock(701003);
    select * into existing_job from public.dispatch_run_jobs where run_id = target_id;
    if found then
        if existing_job.request_fingerprint is distinct from intent_fingerprint then
            raise exception using errcode = '22023', message = 'run_id ya pertenece a otra intención';
        end if;
        return query select * from public.decision_runs where id = target_id;
        return;
    end if;
    if exists(select 1 from public.decision_runs where id = target_id) then
        raise exception using errcode = '22023', message = 'run_id ya existe';
    end if;
    if (select count(*) from public.dispatch_run_jobs where state in ('queued','running'))
       >= greatest(1, least(queue_limit, 256)) then
        raise exception using errcode = '53300', message = 'La cola de ejecución está llena';
    end if;
    insert into public.decision_runs(
        id, dataset_id, orders_dataset_id, fleet_dataset_id, schema_version,
        engine_name, engine_version, configuration_json, decision_case_id, node_id,
        upstream_run_id, status, progress_json
    ) values (
        target_id, (run_payload ->> 'dataset_id')::uuid,
        (run_payload ->> 'orders_dataset_id')::uuid, (run_payload ->> 'fleet_dataset_id')::uuid,
        run_payload ->> 'schema_version', run_payload ->> 'engine_name', run_payload ->> 'engine_version',
        run_payload -> 'configuration_json', (run_payload ->> 'decision_case_id')::uuid,
        run_payload ->> 'node_id', (run_payload ->> 'upstream_run_id')::uuid,
        'queued', jsonb_build_object('stage','queued')
    );
    insert into public.dispatch_run_jobs(run_id, request_json, request_fingerprint)
    values (target_id, job_request, intent_fingerprint);
    return query select * from public.decision_runs where id = target_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb)
 RETURNS SETOF decision_runs
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
declare target public.dispatch_run_jobs%rowtype; outcome text := terminal_values ->> 'status';
begin
    if outcome not in ('completed','error') then raise exception 'Estado terminal inválido'; end if;
    select * into target from public.dispatch_run_jobs where run_id=target_run_id for update;
    if not found or target.state <> 'running' or target.lease_token is distinct from worker_token
       or target.lease_expires_at <= now() or target.deadline_at <= now() then return; end if;
    if outcome='completed' and (terminal_values -> 'result_json' is null
       or jsonb_typeof(terminal_values -> 'result_json') <> 'object') then
        raise exception 'Falta el resultado completado';
    end if;
    update public.decision_runs set status=outcome, finished_at=now(),
        duration_ms=(terminal_values ->> 'duration_ms')::integer,
        result_json=terminal_values -> 'result_json',
        result_fingerprint=terminal_values ->> 'result_fingerprint',
        input_fingerprint=coalesce(terminal_values ->> 'input_fingerprint',input_fingerprint),
        summary_json=terminal_values -> 'summary_json',
        progress_json=coalesce(terminal_values -> 'progress_json',jsonb_build_object('stage',outcome)),
        error_message=terminal_values ->> 'error_message'
    where id=target_run_id and status='running';
    if not found then return; end if;
    update public.dispatch_run_jobs set state=outcome, lease_token=null, lease_expires_at=null
    where run_id=target_run_id;
    return query select * from public.decision_runs where id=target_run_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.heartbeat_dispatch_job(target_run_id uuid, worker_token uuid, lease_seconds integer DEFAULT 120, progress jsonb DEFAULT NULL::jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
    update public.dispatch_run_jobs set heartbeat_at=now(),
        lease_expires_at=least(deadline_at,now()+make_interval(secs=>greatest(30,least(lease_seconds,300))))
    where run_id=target_run_id and state='running' and lease_token=worker_token
      and lease_expires_at > now() and deadline_at > now();
    if not found then return false; end if;
    if progress is not null then
        update public.decision_runs set progress_json=progress
        where id=target_run_id and status='running';
    end if;
    return true;
end;
$function$;

CREATE OR REPLACE FUNCTION public.maintain_dispatch_jobs()
 RETURNS integer
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
declare changed integer;
begin
    with expired as (
        update public.dispatch_run_jobs set state='error', lease_token=null, lease_expires_at=null
        where state in ('queued','running') and (
            deadline_at <= now()
            or (state='running' and lease_expires_at <= now() and attempts >= max_attempts)
        ) returning run_id
    )
    update public.decision_runs set status='error', finished_at=now(),
        error_message='La ejecución agotó su plazo o sus intentos de recuperación.',
        progress_json=jsonb_build_object('stage','error','reason','recovery_exhausted')
    where id in (select run_id from expired) and status in ('queued','running');
    get diagnostics changed = row_count;
    return changed;
end;
$function$;

CREATE OR REPLACE FUNCTION public.request_case_reconciliation(target_case_id uuid)
 RETURNS void
 LANGUAGE sql
 SET search_path TO 'public', 'pg_temp'
AS $function$
    insert into public.decision_case_reconciliations(case_id)
    values (target_case_id)
    on conflict (case_id) do update set version = decision_case_reconciliations.version + 1,
      available_at = now(), updated_at = now();
$function$;

CREATE OR REPLACE FUNCTION public.set_default_fleet(target_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
 perform pg_advisory_xact_lock(701001);
 if not exists(select 1 from public.datasets where id=target_id and dataset_type='fleet') then
  raise exception 'La flota solicitada no existe';
 end if;
 update public.datasets set is_default=false where dataset_type='fleet' and is_default;
 update public.datasets set is_default=true where id=target_id;
end;
$function$;

CREATE OR REPLACE FUNCTION public.validate_decision_run_history()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
declare
    case_orders uuid;
    case_fleet uuid;
    source_case uuid;
    source_node text;
    source_approved_at timestamptz;
    expected_source_node text;
begin
    if tg_op = 'UPDATE' then
        if new.decision_case_id is distinct from old.decision_case_id
           or new.node_id is distinct from old.node_id
           or new.upstream_run_id is distinct from old.upstream_run_id then
            raise exception 'La identidad y el lineage de una Decision Run son inmutables';
        end if;
    end if;

    if new.decision_case_id is null then
        if new.node_id is not null or new.upstream_run_id is not null then
            raise exception 'Una corrida sin Decision Case no puede declarar nodo o dependencia';
        end if;
        return new;
    end if;

    select orders_dataset_id, fleet_dataset_id
      into case_orders, case_fleet
      from public.decision_cases
     where id = new.decision_case_id;

    if not found then
        raise exception 'El Decision Case de la corrida no existe';
    end if;

    if new.orders_dataset_id is distinct from case_orders
       or new.fleet_dataset_id is distinct from case_fleet then
        raise exception 'La Decision Run usa un Data Pack distinto al Decision Case';
    end if;

    expected_source_node := case new.node_id
        when 'logistics_assignment' then null
        when 'logistics_scheduling' then 'logistics_assignment'
        when 'logistics_final_assignment' then 'logistics_scheduling'
        else null
    end;

    if expected_source_node is null then
        if new.upstream_run_id is not null then
            raise exception 'Assignment no admite una corrida upstream';
        end if;
    else
        if new.upstream_run_id is null then
            raise exception 'La decisión requiere una corrida upstream aprobada';
        end if;

        select decision_case_id, node_id, approved_at
          into source_case, source_node, source_approved_at
          from public.decision_runs
         where id = new.upstream_run_id;

        if not found
           or source_case is distinct from new.decision_case_id
           or source_node is distinct from expected_source_node
           or source_approved_at is null then
            raise exception 'El lineage de la Decision Run no corresponde al Decision Case';
        end if;
    end if;

    if new.approved_at is not null and new.status <> 'completed' then
        raise exception 'Sólo una corrida completada puede aprobarse';
    end if;

    return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.validate_dispatch_run()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
  if new.schema_version in ('dispatch_v1', 'dispatch_v2') then
    if new.orders_dataset_id is null
       or new.fleet_dataset_id is null
       or new.dataset_id <> new.orders_dataset_id then
      raise exception 'Una corrida dispatch requiere órdenes y flota';
    end if;

    if not exists (
      select 1
      from public.datasets
      where id = new.orders_dataset_id
        and dataset_type = 'orders'
    )
    or not exists (
      select 1
      from public.datasets
      where id = new.fleet_dataset_id
        and dataset_type = 'fleet'
    ) then
      raise exception 'Tipos de datasets incorrectos';
    end if;

    if new.status = 'completed'
       and new.result_json is not null
       and coalesce(new.result_json ->> 'schema_version', '') <> new.schema_version then
      raise exception 'La versión del resultado no coincide con la corrida';
    end if;
  end if;

  return new;
end;
$function$;

CREATE INDEX datasets_created_at_idx ON public.datasets USING btree (created_at DESC);

CREATE INDEX datasets_dispatch_active_idx ON public.datasets USING btree (dataset_type, created_at DESC) WHERE ((archived_at IS NULL) AND (dataset_type = ANY (ARRAY['orders'::text, 'fleet'::text])));

CREATE UNIQUE INDEX datasets_dispatch_hash_key ON public.datasets USING btree (dataset_type, sha256) WHERE ((dataset_type = ANY (ARRAY['orders'::text, 'fleet'::text])) AND (sha256 IS NOT NULL));

CREATE UNIQUE INDEX datasets_one_default_per_type ON public.datasets USING btree (dataset_type) WHERE is_default;

CREATE INDEX datasets_parent_idx ON public.datasets USING btree (parent_dataset_id) WHERE (parent_dataset_id IS NOT NULL);

CREATE INDEX datasets_sha256_idx ON public.datasets USING btree (sha256) WHERE (sha256 IS NOT NULL);

CREATE INDEX datasets_status_idx ON public.datasets USING btree (status);

ALTER TABLE public.datasets ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.datasets FROM PUBLIC, anon, authenticated, service_role;

GRANT INSERT ON TABLE public.datasets TO postgres;

GRANT SELECT ON TABLE public.datasets TO postgres;

GRANT UPDATE ON TABLE public.datasets TO postgres;

GRANT DELETE ON TABLE public.datasets TO postgres;

GRANT TRUNCATE ON TABLE public.datasets TO postgres;

GRANT REFERENCES ON TABLE public.datasets TO postgres;

GRANT TRIGGER ON TABLE public.datasets TO postgres;

GRANT MAINTAIN ON TABLE public.datasets TO postgres;

GRANT INSERT ON TABLE public.datasets TO service_role;

GRANT SELECT ON TABLE public.datasets TO service_role;

GRANT UPDATE ON TABLE public.datasets TO service_role;

GRANT DELETE ON TABLE public.datasets TO service_role;

ALTER TABLE public.decision_case_reconciliations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.decision_case_reconciliations FROM PUBLIC, anon, authenticated, service_role;

GRANT INSERT ON TABLE public.decision_case_reconciliations TO postgres;

GRANT SELECT ON TABLE public.decision_case_reconciliations TO postgres;

GRANT UPDATE ON TABLE public.decision_case_reconciliations TO postgres;

GRANT DELETE ON TABLE public.decision_case_reconciliations TO postgres;

GRANT TRUNCATE ON TABLE public.decision_case_reconciliations TO postgres;

GRANT REFERENCES ON TABLE public.decision_case_reconciliations TO postgres;

GRANT TRIGGER ON TABLE public.decision_case_reconciliations TO postgres;

GRANT MAINTAIN ON TABLE public.decision_case_reconciliations TO postgres;

GRANT INSERT ON TABLE public.decision_case_reconciliations TO service_role;

GRANT SELECT ON TABLE public.decision_case_reconciliations TO service_role;

GRANT UPDATE ON TABLE public.decision_case_reconciliations TO service_role;

GRANT DELETE ON TABLE public.decision_case_reconciliations TO service_role;

GRANT TRUNCATE ON TABLE public.decision_case_reconciliations TO service_role;

GRANT REFERENCES ON TABLE public.decision_case_reconciliations TO service_role;

GRANT TRIGGER ON TABLE public.decision_case_reconciliations TO service_role;

GRANT MAINTAIN ON TABLE public.decision_case_reconciliations TO service_role;

CREATE INDEX decision_cases_fleet_idx ON public.decision_cases USING btree (fleet_dataset_id);

CREATE INDEX decision_cases_orders_idx ON public.decision_cases USING btree (orders_dataset_id);

CREATE INDEX decision_cases_signature_idx ON public.decision_cases USING btree (input_signature);

CREATE INDEX decision_cases_status_activity_idx ON public.decision_cases USING btree (status, last_activity_at DESC);

ALTER TABLE public.decision_cases ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.decision_cases FROM PUBLIC, anon, authenticated, service_role;

GRANT INSERT ON TABLE public.decision_cases TO postgres;

GRANT SELECT ON TABLE public.decision_cases TO postgres;

GRANT UPDATE ON TABLE public.decision_cases TO postgres;

GRANT DELETE ON TABLE public.decision_cases TO postgres;

GRANT TRUNCATE ON TABLE public.decision_cases TO postgres;

GRANT REFERENCES ON TABLE public.decision_cases TO postgres;

GRANT TRIGGER ON TABLE public.decision_cases TO postgres;

GRANT MAINTAIN ON TABLE public.decision_cases TO postgres;

GRANT INSERT ON TABLE public.decision_cases TO service_role;

GRANT SELECT ON TABLE public.decision_cases TO service_role;

GRANT UPDATE ON TABLE public.decision_cases TO service_role;

GRANT DELETE ON TABLE public.decision_cases TO service_role;

GRANT TRUNCATE ON TABLE public.decision_cases TO service_role;

GRANT REFERENCES ON TABLE public.decision_cases TO service_role;

GRANT TRIGGER ON TABLE public.decision_cases TO service_role;

GRANT MAINTAIN ON TABLE public.decision_cases TO service_role;

CREATE INDEX decision_explanations_created_at_idx ON public.decision_explanations USING btree (created_at DESC);

CREATE INDEX decision_explanations_run_id_idx ON public.decision_explanations USING btree (run_id);

ALTER TABLE public.decision_explanations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.decision_explanations FROM PUBLIC, anon, authenticated, service_role;

GRANT INSERT ON TABLE public.decision_explanations TO postgres;

GRANT SELECT ON TABLE public.decision_explanations TO postgres;

GRANT UPDATE ON TABLE public.decision_explanations TO postgres;

GRANT DELETE ON TABLE public.decision_explanations TO postgres;

GRANT TRUNCATE ON TABLE public.decision_explanations TO postgres;

GRANT REFERENCES ON TABLE public.decision_explanations TO postgres;

GRANT TRIGGER ON TABLE public.decision_explanations TO postgres;

GRANT MAINTAIN ON TABLE public.decision_explanations TO postgres;

GRANT INSERT ON TABLE public.decision_explanations TO service_role;

GRANT SELECT ON TABLE public.decision_explanations TO service_role;

GRANT UPDATE ON TABLE public.decision_explanations TO service_role;

GRANT DELETE ON TABLE public.decision_explanations TO service_role;

GRANT TRUNCATE ON TABLE public.decision_explanations TO service_role;

GRANT REFERENCES ON TABLE public.decision_explanations TO service_role;

GRANT TRIGGER ON TABLE public.decision_explanations TO service_role;

GRANT MAINTAIN ON TABLE public.decision_explanations TO service_role;

CREATE INDEX decision_messages_run_id_created_at_idx ON public.decision_messages USING btree (run_id, created_at);

ALTER TABLE public.decision_messages ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.decision_messages FROM PUBLIC, anon, authenticated, service_role;

GRANT INSERT ON TABLE public.decision_messages TO postgres;

GRANT SELECT ON TABLE public.decision_messages TO postgres;

GRANT UPDATE ON TABLE public.decision_messages TO postgres;

GRANT DELETE ON TABLE public.decision_messages TO postgres;

GRANT TRUNCATE ON TABLE public.decision_messages TO postgres;

GRANT REFERENCES ON TABLE public.decision_messages TO postgres;

GRANT TRIGGER ON TABLE public.decision_messages TO postgres;

GRANT MAINTAIN ON TABLE public.decision_messages TO postgres;

GRANT INSERT ON TABLE public.decision_messages TO service_role;

GRANT SELECT ON TABLE public.decision_messages TO service_role;

GRANT UPDATE ON TABLE public.decision_messages TO service_role;

GRANT DELETE ON TABLE public.decision_messages TO service_role;

GRANT TRUNCATE ON TABLE public.decision_messages TO service_role;

GRANT REFERENCES ON TABLE public.decision_messages TO service_role;

GRANT TRIGGER ON TABLE public.decision_messages TO service_role;

GRANT MAINTAIN ON TABLE public.decision_messages TO service_role;

CREATE INDEX decision_runs_case_node_created_idx ON public.decision_runs USING btree (decision_case_id, node_id, created_at DESC) WHERE (decision_case_id IS NOT NULL);

CREATE INDEX decision_runs_created_at_idx ON public.decision_runs USING btree (created_at DESC);

CREATE INDEX decision_runs_dataset_id_idx ON public.decision_runs USING btree (dataset_id);

CREATE INDEX decision_runs_fleet_idx ON public.decision_runs USING btree (fleet_dataset_id);

CREATE UNIQUE INDEX decision_runs_one_current_approval_idx ON public.decision_runs USING btree (decision_case_id, node_id) WHERE ((decision_case_id IS NOT NULL) AND (approved_at IS NOT NULL) AND (superseded_at IS NULL));

CREATE INDEX decision_runs_orders_idx ON public.decision_runs USING btree (orders_dataset_id);

CREATE INDEX decision_runs_schema_created_idx ON public.decision_runs USING btree (schema_version, created_at DESC);

CREATE INDEX decision_runs_status_idx ON public.decision_runs USING btree (status);

CREATE INDEX decision_runs_upstream_idx ON public.decision_runs USING btree (upstream_run_id) WHERE (upstream_run_id IS NOT NULL);

CREATE TRIGGER decision_runs_dispatch_contract BEFORE INSERT OR UPDATE ON decision_runs FOR EACH ROW EXECUTE FUNCTION validate_dispatch_run();

CREATE TRIGGER decision_runs_history_contract BEFORE INSERT OR UPDATE ON decision_runs FOR EACH ROW EXECUTE FUNCTION validate_decision_run_history();

CREATE TRIGGER decision_runs_reconcile_insert AFTER INSERT ON decision_runs FOR EACH ROW EXECUTE FUNCTION enqueue_case_reconciliation();

CREATE TRIGGER decision_runs_reconcile_update AFTER UPDATE OF status, approved_at, superseded_at ON decision_runs FOR EACH ROW EXECUTE FUNCTION enqueue_case_reconciliation();

ALTER TABLE public.decision_runs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.decision_runs FROM PUBLIC, anon, authenticated, service_role;

GRANT INSERT ON TABLE public.decision_runs TO postgres;

GRANT SELECT ON TABLE public.decision_runs TO postgres;

GRANT UPDATE ON TABLE public.decision_runs TO postgres;

GRANT DELETE ON TABLE public.decision_runs TO postgres;

GRANT TRUNCATE ON TABLE public.decision_runs TO postgres;

GRANT REFERENCES ON TABLE public.decision_runs TO postgres;

GRANT TRIGGER ON TABLE public.decision_runs TO postgres;

GRANT MAINTAIN ON TABLE public.decision_runs TO postgres;

GRANT INSERT ON TABLE public.decision_runs TO service_role;

GRANT SELECT ON TABLE public.decision_runs TO service_role;

GRANT UPDATE ON TABLE public.decision_runs TO service_role;

GRANT DELETE ON TABLE public.decision_runs TO service_role;

CREATE INDEX dispatch_jobs_claim_idx ON public.dispatch_run_jobs USING btree (available_at, created_at) WHERE (state = ANY (ARRAY['queued'::text, 'running'::text]));

ALTER TABLE public.dispatch_run_jobs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.dispatch_run_jobs FROM PUBLIC, anon, authenticated, service_role;

GRANT INSERT ON TABLE public.dispatch_run_jobs TO postgres;

GRANT SELECT ON TABLE public.dispatch_run_jobs TO postgres;

GRANT UPDATE ON TABLE public.dispatch_run_jobs TO postgres;

GRANT DELETE ON TABLE public.dispatch_run_jobs TO postgres;

GRANT TRUNCATE ON TABLE public.dispatch_run_jobs TO postgres;

GRANT REFERENCES ON TABLE public.dispatch_run_jobs TO postgres;

GRANT TRIGGER ON TABLE public.dispatch_run_jobs TO postgres;

GRANT MAINTAIN ON TABLE public.dispatch_run_jobs TO postgres;

GRANT INSERT ON TABLE public.dispatch_run_jobs TO service_role;

GRANT SELECT ON TABLE public.dispatch_run_jobs TO service_role;

GRANT UPDATE ON TABLE public.dispatch_run_jobs TO service_role;

GRANT DELETE ON TABLE public.dispatch_run_jobs TO service_role;

GRANT TRUNCATE ON TABLE public.dispatch_run_jobs TO service_role;

GRANT REFERENCES ON TABLE public.dispatch_run_jobs TO service_role;

GRANT TRIGGER ON TABLE public.dispatch_run_jobs TO service_role;

GRANT MAINTAIN ON TABLE public.dispatch_run_jobs TO service_role;

REVOKE ALL ON FUNCTION public.ack_case_reconciliation(target_case_id uuid, observed_version bigint) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.ack_case_reconciliation(target_case_id uuid, observed_version bigint) TO postgres;

GRANT EXECUTE ON FUNCTION public.ack_case_reconciliation(target_case_id uuid, observed_version bigint) TO service_role;

REVOKE ALL ON FUNCTION public.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text) TO postgres;

GRANT EXECUTE ON FUNCTION public.approve_decision_run_version(target_run_id uuid, target_case_id uuid, target_node_id text) TO service_role;

REVOKE ALL ON FUNCTION public.cancel_dispatch_job(target_run_id uuid) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.cancel_dispatch_job(target_run_id uuid) TO postgres;

GRANT EXECUTE ON FUNCTION public.cancel_dispatch_job(target_run_id uuid) TO service_role;

REVOKE ALL ON FUNCTION public.claim_dispatch_job(worker_token uuid, lease_seconds integer) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.claim_dispatch_job(worker_token uuid, lease_seconds integer) TO postgres;

GRANT EXECUTE ON FUNCTION public.claim_dispatch_job(worker_token uuid, lease_seconds integer) TO service_role;

REVOKE ALL ON FUNCTION public.enqueue_case_reconciliation() FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.enqueue_case_reconciliation() TO postgres;

GRANT EXECUTE ON FUNCTION public.enqueue_case_reconciliation() TO service_role;

REVOKE ALL ON FUNCTION public.enqueue_dispatch_run(run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.enqueue_dispatch_run(run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer) TO postgres;

GRANT EXECUTE ON FUNCTION public.enqueue_dispatch_run(run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer) TO service_role;

REVOKE ALL ON FUNCTION public.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb) TO postgres;

GRANT EXECUTE ON FUNCTION public.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb) TO service_role;

REVOKE ALL ON FUNCTION public.heartbeat_dispatch_job(target_run_id uuid, worker_token uuid, lease_seconds integer, progress jsonb) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.heartbeat_dispatch_job(target_run_id uuid, worker_token uuid, lease_seconds integer, progress jsonb) TO postgres;

GRANT EXECUTE ON FUNCTION public.heartbeat_dispatch_job(target_run_id uuid, worker_token uuid, lease_seconds integer, progress jsonb) TO service_role;

REVOKE ALL ON FUNCTION public.maintain_dispatch_jobs() FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.maintain_dispatch_jobs() TO postgres;

GRANT EXECUTE ON FUNCTION public.maintain_dispatch_jobs() TO service_role;

REVOKE ALL ON FUNCTION public.request_case_reconciliation(target_case_id uuid) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.request_case_reconciliation(target_case_id uuid) TO postgres;

GRANT EXECUTE ON FUNCTION public.request_case_reconciliation(target_case_id uuid) TO service_role;

REVOKE ALL ON FUNCTION public.set_default_fleet(target_id uuid) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.set_default_fleet(target_id uuid) TO postgres;

GRANT EXECUTE ON FUNCTION public.set_default_fleet(target_id uuid) TO service_role;

REVOKE ALL ON FUNCTION public.validate_decision_run_history() FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.validate_decision_run_history() TO postgres;

GRANT EXECUTE ON FUNCTION public.validate_decision_run_history() TO service_role;

REVOKE ALL ON FUNCTION public.validate_dispatch_run() FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.validate_dispatch_run() TO postgres;

GRANT EXECUTE ON FUNCTION public.validate_dispatch_run() TO service_role;

COMMIT;

NOTIFY pgrst, 'reload schema';

