create table if not exists public.decision_cases (
    id uuid primary key default gen_random_uuid(),
    schema_version text not null default 'decision_case_v1',
    domain text not null default 'logistics',
    status text not null default 'active',
    orders_dataset_id uuid not null references public.datasets(id) on delete restrict,
    fleet_dataset_id uuid not null references public.datasets(id) on delete restrict,
    input_signature text not null,
    state_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_activity_at timestamptz not null default now(),
    archived_at timestamptz,
    constraint decision_cases_domain_check check (domain in ('logistics')),
    constraint decision_cases_status_check check (status in ('active','completed','archived')),
    constraint decision_cases_distinct_inputs_check check (orders_dataset_id <> fleet_dataset_id)
);

create index if not exists decision_cases_status_activity_idx
    on public.decision_cases (status, last_activity_at desc);
create index if not exists decision_cases_orders_idx
    on public.decision_cases (orders_dataset_id);
create index if not exists decision_cases_fleet_idx
    on public.decision_cases (fleet_dataset_id);
create index if not exists decision_cases_signature_idx
    on public.decision_cases (input_signature);

alter table public.decision_cases enable row level security;
revoke all on table public.decision_cases from anon, authenticated;
grant select, insert, update, delete on table public.decision_cases to service_role;

with normalized as (
    select
        coalesce(
            configuration_json #>> '{decision_case,case_id}',
            result_json #>> '{decision_case,case_id}'
        )::uuid as case_id,
        orders_dataset_id,
        fleet_dataset_id,
        created_at,
        coalesce(finished_at, created_at) as activity_at,
        coalesce(
            configuration_json #>> '{decision_case,node_id}',
            result_json #>> '{decision_case,node_id}'
        ) as node_id,
        id as run_id,
        coalesce(
            result_json #>> '{decision_case,status}',
            configuration_json #>> '{decision_case,status}'
        ) as decision_status,
        nullif(coalesce(
            result_json #>> '{decision_case,approved_at}',
            configuration_json #>> '{decision_case,approved_at}'
        ), '')::timestamptz as approved_at
    from public.decision_runs
    where orders_dataset_id is not null
      and fleet_dataset_id is not null
      and coalesce(
            configuration_json #>> '{decision_case,case_id}',
            result_json #>> '{decision_case,case_id}'
          ) is not null
), grouped as (
    select
        case_id,
        min(created_at) as created_at,
        max(activity_at) as last_activity_at,
        (array_agg(orders_dataset_id order by created_at desc))[1] as orders_dataset_id,
        (array_agg(fleet_dataset_id order by created_at desc))[1] as fleet_dataset_id
    from normalized
    group by case_id
), snapshots as (
    select
        g.*,
        (
            select n.run_id from normalized n
            where n.case_id = g.case_id and n.node_id = 'logistics_assignment'
            order by n.created_at desc limit 1
        ) as assignment_run_id,
        (
            select n.decision_status from normalized n
            where n.case_id = g.case_id and n.node_id = 'logistics_assignment'
            order by n.created_at desc limit 1
        ) as assignment_status,
        (
            select n.approved_at from normalized n
            where n.case_id = g.case_id and n.node_id = 'logistics_assignment'
            order by n.created_at desc limit 1
        ) as assignment_approved_at,
        (
            select n.run_id from normalized n
            where n.case_id = g.case_id and n.node_id = 'logistics_scheduling'
            order by n.created_at desc limit 1
        ) as scheduling_run_id,
        (
            select n.decision_status from normalized n
            where n.case_id = g.case_id and n.node_id = 'logistics_scheduling'
            order by n.created_at desc limit 1
        ) as scheduling_status,
        (
            select n.approved_at from normalized n
            where n.case_id = g.case_id and n.node_id = 'logistics_scheduling'
            order by n.created_at desc limit 1
        ) as scheduling_approved_at
    from grouped g
)
insert into public.decision_cases (
    id,
    schema_version,
    domain,
    status,
    orders_dataset_id,
    fleet_dataset_id,
    input_signature,
    state_json,
    created_at,
    updated_at,
    last_activity_at
)
select
    s.case_id,
    'decision_case_v1',
    'logistics',
    'active',
    s.orders_dataset_id,
    s.fleet_dataset_id,
    s.orders_dataset_id::text || ':' || s.fleet_dataset_id::text,
    jsonb_build_object(
        'schema_version', 'decision_case_v1',
        'id', s.case_id::text,
        'domain', 'logistics',
        'signature', s.orders_dataset_id::text || ':' || s.fleet_dataset_id::text,
        'created_at', s.created_at,
        'updated_at', s.last_activity_at,
        'inputs', jsonb_build_object(
            'orders_dataset_id', s.orders_dataset_id::text,
            'fleet_dataset_id', s.fleet_dataset_id::text
        ),
        'stale_predecessor', null,
        'nodes', jsonb_build_object(
            'logistics_assignment', jsonb_build_object(
                'status', case
                    when s.assignment_status = 'approved' then 'approved'
                    when s.assignment_run_id is not null then 'review'
                    else 'available'
                end,
                'run_id', s.assignment_run_id,
                'approved_at', s.assignment_approved_at,
                'error', null
            ),
            'logistics_scheduling', jsonb_build_object(
                'status', case
                    when s.scheduling_status = 'approved' then 'approved'
                    when s.scheduling_run_id is not null then 'review'
                    when s.assignment_status = 'approved' then 'available'
                    else 'locked'
                end,
                'run_id', s.scheduling_run_id,
                'approved_at', s.scheduling_approved_at,
                'error', null
            ),
            'logistics_final_assignment', jsonb_build_object(
                'status', case
                    when s.scheduling_status = 'approved' then 'available'
                    else 'locked'
                end,
                'run_id', null,
                'approved_at', null,
                'error', null
            )
        )
    ),
    s.created_at,
    s.last_activity_at,
    s.last_activity_at
from snapshots s
on conflict (id) do nothing;
