-- Phase 3. Additive upgrade over decision_run_history_v2; no historical rewrites.
begin;

create table public.dispatch_run_jobs (
    run_id uuid primary key references public.decision_runs(id) on delete restrict,
    request_json jsonb not null,
    request_fingerprint text not null,
    state text not null default 'queued' check (state in ('queued','running','completed','error')),
    attempts integer not null default 0,
    max_attempts integer not null default 3 check (max_attempts between 1 and 5),
    lease_token uuid,
    lease_expires_at timestamptz,
    heartbeat_at timestamptz,
    available_at timestamptz not null default now(),
    deadline_at timestamptz not null default now() + interval '30 minutes',
    created_at timestamptz not null default now(),
    constraint dispatch_job_lease_pair check (
      (state = 'running' and lease_token is not null and lease_expires_at is not null)
      or (state <> 'running' and lease_token is null and lease_expires_at is null)
    )
);
create index dispatch_jobs_claim_idx on public.dispatch_run_jobs(available_at, created_at)
    where state in ('queued','running');

create table public.decision_case_reconciliations (
    case_id uuid primary key references public.decision_cases(id) on delete cascade,
    version bigint not null default 1,
    attempts integer not null default 0,
    available_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
alter table public.dispatch_run_jobs enable row level security;
alter table public.decision_case_reconciliations enable row level security;
revoke all on public.dispatch_run_jobs, public.decision_case_reconciliations from public, anon, authenticated;
grant select, insert, update, delete on public.dispatch_run_jobs, public.decision_case_reconciliations to service_role;

create function public.request_case_reconciliation(target_case_id uuid) returns void
language sql security invoker set search_path = public, pg_temp as $$
    insert into public.decision_case_reconciliations(case_id)
    values (target_case_id)
    on conflict (case_id) do update set version = decision_case_reconciliations.version + 1,
      available_at = now(), updated_at = now();
$$;

-- Persist the projection outbox in the SAME transaction as a changed run.
create function public.enqueue_case_reconciliation() returns trigger
language plpgsql security invoker set search_path = public, pg_temp as $$
begin
    if new.decision_case_id is not null then
        perform public.request_case_reconciliation(new.decision_case_id);
    end if;
    return new;
end;
$$;
create trigger decision_runs_reconcile_insert after insert on public.decision_runs
    for each row execute function public.enqueue_case_reconciliation();
create trigger decision_runs_reconcile_update after update of status, approved_at, superseded_at on public.decision_runs
    for each row execute function public.enqueue_case_reconciliation();

create function public.enqueue_dispatch_run(
    run_payload jsonb, job_request jsonb, intent_fingerprint text, queue_limit integer default 32
) returns setof public.decision_runs
language plpgsql security invoker set search_path = public, pg_temp as $$
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
$$;

-- Explicit worker maintenance; GET endpoints never expire or alter runs.
create function public.maintain_dispatch_jobs() returns integer
language plpgsql security invoker set search_path = public, pg_temp as $$
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
$$;

create function public.claim_dispatch_job(worker_token uuid, lease_seconds integer default 120)
returns setof public.dispatch_run_jobs
language plpgsql security invoker set search_path = public, pg_temp as $$
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
$$;

create function public.heartbeat_dispatch_job(
    target_run_id uuid, worker_token uuid, lease_seconds integer default 120, progress jsonb default null
) returns boolean
language plpgsql security invoker set search_path = public, pg_temp as $$
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
$$;

create function public.finish_dispatch_job(target_run_id uuid, worker_token uuid, terminal_values jsonb)
returns setof public.decision_runs
language plpgsql security invoker set search_path = public, pg_temp as $$
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
$$;

create function public.cancel_dispatch_job(target_run_id uuid) returns setof public.decision_runs
language plpgsql security invoker set search_path = public, pg_temp as $$
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
$$;

-- Acknowledge only the version observed: concurrent approvals cannot lose repair work.
create function public.ack_case_reconciliation(target_case_id uuid, observed_version bigint)
returns void language sql security invoker set search_path = public, pg_temp as $$
    delete from public.decision_case_reconciliations
    where case_id=target_case_id and version=observed_version;
$$;

revoke all on function public.request_case_reconciliation(uuid), public.enqueue_case_reconciliation(),
    public.enqueue_dispatch_run(jsonb,jsonb,text,integer), public.maintain_dispatch_jobs(),
    public.claim_dispatch_job(uuid,integer), public.heartbeat_dispatch_job(uuid,uuid,integer,jsonb),
    public.finish_dispatch_job(uuid,uuid,jsonb), public.cancel_dispatch_job(uuid),
    public.ack_case_reconciliation(uuid,bigint) from public, anon, authenticated;
grant execute on function public.request_case_reconciliation(uuid), public.enqueue_case_reconciliation(),
    public.enqueue_dispatch_run(jsonb,jsonb,text,integer), public.maintain_dispatch_jobs(),
    public.claim_dispatch_job(uuid,integer), public.heartbeat_dispatch_job(uuid,uuid,integer,jsonb),
    public.finish_dispatch_job(uuid,uuid,jsonb), public.cancel_dispatch_job(uuid),
    public.ack_case_reconciliation(uuid,bigint) to service_role;
notify pgrst, 'reload schema';
commit;
