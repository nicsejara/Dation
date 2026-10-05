alter table public.decision_runs
    add column decision_case_id uuid references public.decision_cases(id) on delete restrict,
    add column node_id text,
    add column upstream_run_id uuid references public.decision_runs(id) on delete restrict,
    add column approved_at timestamptz,
    add column superseded_at timestamptz,
    add column superseded_by_run_id uuid references public.decision_runs(id) on delete set null;

alter table public.decision_runs
    add constraint decision_runs_node_id_check
    check (node_id is null or node_id in (
        'logistics_assignment',
        'logistics_scheduling',
        'logistics_final_assignment'
    )),
    add constraint decision_runs_case_node_pair_check
    check (
        (decision_case_id is null and node_id is null)
        or (decision_case_id is not null and node_id is not null)
    ),
    add constraint decision_runs_superseded_requires_approval_check
    check (superseded_at is null or approved_at is not null);

update public.decision_runs
set
    decision_case_id = coalesce(
        nullif(configuration_json #>> '{decision_case,case_id}', ''),
        nullif(result_json #>> '{decision_case,case_id}', '')
    )::uuid,
    node_id = coalesce(
        nullif(configuration_json #>> '{decision_case,node_id}', ''),
        nullif(result_json #>> '{decision_case,node_id}', '')
    ),
    upstream_run_id = nullif(
        configuration_json ->> 'source_assignment_run_id',
        ''
    )::uuid,
    approved_at = case
        when coalesce(
            result_json #>> '{decision_case,status}',
            configuration_json #>> '{decision_case,status}'
        ) = 'approved'
        then nullif(coalesce(
            result_json #>> '{decision_case,approved_at}',
            configuration_json #>> '{decision_case,approved_at}'
        ), '')::timestamptz
        else null
    end
where coalesce(
    configuration_json #>> '{decision_case,case_id}',
    result_json #>> '{decision_case,case_id}'
) is not null;

create index decision_runs_case_node_created_idx
    on public.decision_runs(decision_case_id, node_id, created_at desc)
    where decision_case_id is not null;

create index decision_runs_upstream_idx
    on public.decision_runs(upstream_run_id)
    where upstream_run_id is not null;

create unique index decision_runs_one_current_approval_idx
    on public.decision_runs(decision_case_id, node_id)
    where decision_case_id is not null
      and approved_at is not null
      and superseded_at is null;

create or replace function public.validate_decision_run_history()
returns trigger
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
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
$$;

revoke all on function public.validate_decision_run_history() from public, anon, authenticated;
grant execute on function public.validate_decision_run_history() to service_role;

drop trigger if exists decision_runs_history_contract on public.decision_runs;
create trigger decision_runs_history_contract
before insert or update on public.decision_runs
for each row execute function public.validate_decision_run_history();

create or replace function public.approve_decision_run_version(
    target_run_id uuid,
    target_case_id uuid,
    target_node_id text
)
returns setof public.decision_runs
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
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
$$;

revoke all on function public.approve_decision_run_version(uuid, uuid, text) from public, anon, authenticated;
grant execute on function public.approve_decision_run_version(uuid, uuid, text) to service_role;

with node_ids(node_id) as (
    values
      ('logistics_assignment'::text),
      ('logistics_scheduling'::text),
      ('logistics_final_assignment'::text)
), stats as (
    select
        c.id as case_id,
        n.node_id,
        count(r.id)::int as run_count,
        (array_agg(r.id order by r.created_at desc) filter (where r.id is not null))[1] as latest_run_id,
        (array_agg(r.status order by r.created_at desc) filter (where r.id is not null))[1] as latest_execution_status,
        (array_agg(r.id order by r.approved_at desc) filter (
            where r.approved_at is not null and r.superseded_at is null
        ))[1] as approved_run_id,
        (array_agg(r.approved_at order by r.approved_at desc) filter (
            where r.approved_at is not null and r.superseded_at is null
        ))[1] as approved_at
    from public.decision_cases c
    cross join node_ids n
    left join public.decision_runs r
      on r.decision_case_id = c.id
     and r.node_id = n.node_id
    group by c.id, n.node_id
), node_snapshots as (
    select
        s.case_id,
        jsonb_object_agg(
            s.node_id,
            coalesce(c.state_json #> array['nodes', s.node_id], '{}'::jsonb)
            || jsonb_build_object(
                'run_id', coalesce(s.approved_run_id, s.latest_run_id),
                'latest_run_id', s.latest_run_id,
                'approved_run_id', s.approved_run_id,
                'run_count', s.run_count,
                'latest_execution_status', s.latest_execution_status,
                'approved_at', s.approved_at
            )
        ) as nodes
    from stats s
    join public.decision_cases c on c.id = s.case_id
    group by s.case_id
)
update public.decision_cases c
   set schema_version = 'decision_case_v2',
       state_json = jsonb_set(
           jsonb_set(
               c.state_json,
               '{schema_version}',
               to_jsonb('decision_case_v2'::text),
               true
           ),
           '{nodes}',
           n.nodes,
           true
       )
  from node_snapshots n
 where c.id = n.case_id;

notify pgrst, 'reload schema';