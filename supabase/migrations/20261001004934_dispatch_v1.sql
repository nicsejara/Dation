-- Additive migration. Apply manually in Supabase SQL Editor after backup/review.
begin;
alter table public.datasets
 add column if not exists dataset_type text not null default 'logistics_legacy' check (dataset_type in ('logistics_legacy','orders','fleet')),
 add column if not exists schema_version text,
 add column if not exists label text,
 add column if not exists is_default boolean not null default false,
 add column if not exists parent_dataset_id uuid references public.datasets(id),
 add column if not exists profile_json jsonb;
create unique index if not exists datasets_one_default_per_type on public.datasets(dataset_type) where is_default;
-- Legacy hash index is NON-unique. Enforce typed deduplication only for new contracts.
create unique index if not exists datasets_dispatch_hash_key on public.datasets(dataset_type,sha256)
 where dataset_type in ('orders','fleet') and sha256 is not null;
alter table public.decision_runs
 add column if not exists schema_version text not null default 'legacy_v0.2',
 add column if not exists orders_dataset_id uuid references public.datasets(id),
 add column if not exists fleet_dataset_id uuid references public.datasets(id),
 add column if not exists input_fingerprint text,
 add column if not exists result_fingerprint text,
 add column if not exists summary_json jsonb,
 add column if not exists progress_json jsonb;
create index if not exists decision_runs_orders_idx on public.decision_runs(orders_dataset_id);
create index if not exists decision_runs_fleet_idx on public.decision_runs(fleet_dataset_id);
create index if not exists datasets_parent_idx on public.datasets(parent_dataset_id) where parent_dataset_id is not null;
-- Serialize default changes in one transaction. Service role only; no definer escalation.
create or replace function public.set_default_fleet(target_id uuid) returns void
language plpgsql security invoker set search_path = public, pg_temp as $$
begin
 perform pg_advisory_xact_lock(701001);
 if not exists(select 1 from public.datasets where id=target_id and dataset_type='fleet') then
  raise exception 'La flota solicitada no existe';
 end if;
 update public.datasets set is_default=false where dataset_type='fleet' and is_default;
 update public.datasets set is_default=true where id=target_id;
end;
$$;
revoke all on function public.set_default_fleet(uuid) from public, anon, authenticated;
grant execute on function public.set_default_fleet(uuid) to service_role;
-- Consistency enforced in DB for all writers, without touching legacy records.
create or replace function public.validate_dispatch_run() returns trigger
language plpgsql security invoker set search_path = public, pg_temp as $$
begin
 if new.schema_version='dispatch_v1' then
  if new.orders_dataset_id is null or new.fleet_dataset_id is null or new.dataset_id<>new.orders_dataset_id then
   raise exception 'Una corrida dispatch requiere órdenes y flota';
  end if;
  if not exists(select 1 from public.datasets where id=new.orders_dataset_id and dataset_type='orders')
   or not exists(select 1 from public.datasets where id=new.fleet_dataset_id and dataset_type='fleet') then
   raise exception 'Tipos de datasets incorrectos';
  end if;
 end if;
 return new;
end;
$$;
drop trigger if exists decision_runs_dispatch_contract on public.decision_runs;
create trigger decision_runs_dispatch_contract before insert or update on public.decision_runs
 for each row execute function public.validate_dispatch_run();
commit;
-- Non-destructive rollback: deploy previous application, keep added columns/data.
-- Do not drop columns if dispatch runs exist. RLS policies are not modified.
