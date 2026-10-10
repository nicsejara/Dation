"""Install the additive Phase 5 read RPC after verifying prerequisites and drift."""
from pathlib import Path
import sys
from apply_production_queue import query

ROOT=Path(__file__).resolve().parents[1]
MIGRATION=ROOT/'supabase/migrations/20261010220000_case_list_performance.sql'
SIGNATURE='public.list_decision_cases(text,integer,integer,boolean)'


def main():
    prerequisite=query("SELECT to_regprocedure('public.decision_case_history(uuid,text,integer,integer)') IS NOT NULL AS history, "
                       "to_regclass('public.decision_approval_events') IS NOT NULL AS approvals, "
                       "to_regclass('public.decision_runs_history_page_idx') IS NOT NULL AS history_index;")[0]
    if not all(prerequisite.values()):raise RuntimeError('Phase 4 prerequisites are missing. No changes applied.')
    current=query(f"SELECT prosrc AS body, provolatile AS volatility, prosecdef AS definer FROM pg_proc WHERE oid=to_regprocedure('{SIGNATURE}');")
    expected=MIGRATION.read_text().split(' AS $$\n',1)[1].split('$$;',1)[0].strip()
    if current:
        if current[0]['body'].strip()!=expected or current[0]['volatility']!='s' or current[0]['definer']:
            raise RuntimeError('Phase 5 function drift. No changes applied.')
    else:
        query(MIGRATION.read_text())
        installed=query(f"SELECT prosrc AS body, provolatile AS volatility, prosecdef AS definer FROM pg_proc WHERE oid=to_regprocedure('{SIGNATURE}');")
        if not installed or installed[0]['body'].strip()!=expected or installed[0]['volatility']!='s' or installed[0]['definer']:
            raise RuntimeError('Phase 5 definition failed verification. Do not deploy the API.')
    verified=query(f"SELECT NOT has_function_privilege('anon','{SIGNATURE}','EXECUTE') AS anonymous_private, "
                   f"NOT has_function_privilege('authenticated','{SIGNATURE}','EXECUTE') AS authenticated_private, "
                   f"has_function_privilege('service_role','{SIGNATURE}','EXECUTE') AS service_access;")[0]
    if not all(verified.values()):raise RuntimeError('Phase 5 privileges failed verification. Do not deploy the API.')
    # Test execution under a read-only transaction without exporting application data.
    query("BEGIN READ ONLY; SELECT count(*) AS checked FROM public.list_decision_cases('active',1,0,true); COMMIT;")
    print('Phase 5 read RPC verified: exact body, bounded page, STABLE, invoker and private privileges.')


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
