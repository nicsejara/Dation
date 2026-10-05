with run_activity as (
    select
        coalesce(
            configuration_json #>> '{decision_case,case_id}',
            result_json #>> '{decision_case,case_id}'
        )::uuid as case_id,
        max(
            greatest(
                coalesce(finished_at, created_at),
                nullif(coalesce(
                    result_json #>> '{decision_case,approved_at}',
                    configuration_json #>> '{decision_case,approved_at}'
                ), '')::timestamptz
            )
        ) as last_activity_at
    from public.decision_runs
    where coalesce(
        configuration_json #>> '{decision_case,case_id}',
        result_json #>> '{decision_case,case_id}'
    ) is not null
    group by 1
)
update public.decision_cases c
set
    last_activity_at = greatest(c.last_activity_at, a.last_activity_at),
    updated_at = greatest(c.updated_at, a.last_activity_at),
    state_json = jsonb_set(
        c.state_json,
        '{updated_at}',
        to_jsonb(greatest(c.updated_at, a.last_activity_at)),
        true
    )
from run_activity a
where c.id = a.case_id;

comment on table public.decision_cases is
    'Persistent Decision Case container bound to an immutable Orders + Fleet Data Pack snapshot.';
comment on column public.decision_cases.state_json is
    'Current Decision Map snapshot. Decision Run history remains stored separately in decision_runs.';
comment on column public.decision_cases.input_signature is
    'Orders dataset UUID + colon + Fleet dataset UUID used to verify Data Pack identity.';

notify pgrst, 'reload schema';
