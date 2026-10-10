-- Disposable test fixture for the legacy tables missing from the migration baseline.
-- This is NOT a production baseline (F17 belongs to Phase 4).
do $$ begin
  if not exists(select 1 from pg_roles where rolname='anon') then create role anon; end if;
  if not exists(select 1 from pg_roles where rolname='authenticated') then create role authenticated; end if;
  if not exists(select 1 from pg_roles where rolname='service_role') then create role service_role bypassrls; end if;
end $$;
create table public.datasets (
  id uuid primary key default gen_random_uuid(), created_at timestamptz not null default now(),
  original_filename text, storage_bucket text, storage_path text, mime_type text,
  size_bytes bigint, sha256 text, status text default 'validated', row_count integer,
  column_count integer, error_message text
);
create table public.decision_runs (
  id uuid primary key default gen_random_uuid(), dataset_id uuid references public.datasets(id),
  created_at timestamptz not null default now(), started_at timestamptz, finished_at timestamptz,
  engine_name text, engine_version text, configuration_json jsonb, result_json jsonb,
  status text not null check (status in ('queued','running','completed','error')),
  duration_ms integer, error_message text
);
grant usage on schema public to anon,authenticated,service_role;
grant all on public.datasets,public.decision_runs to service_role;
