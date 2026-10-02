-- Additive migration for Dispatch v2 integrity. No historical rows are rewritten.
begin;

create or replace function public.validate_dispatch_run()
returns trigger
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
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
$$;

revoke all on function public.validate_dispatch_run() from public, anon, authenticated;
grant execute on function public.validate_dispatch_run() to service_role;

create index if not exists decision_runs_schema_created_idx
  on public.decision_runs(schema_version, created_at desc);

commit;
