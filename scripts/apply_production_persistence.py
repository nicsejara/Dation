"""Apply only the reviewed additive Phase 4 migration, never the fresh baseline.

Existing explicit deployment authorization is required. Credentials come exclusively
from SUPABASE_ACCESS_TOKEN. Catalog drift aborts before any production mutation.
"""
import json
from pathlib import Path
import sys
from apply_production_queue import query
from capture_public_schema import SQL as CATALOG_SQL

ROOT=Path(__file__).resolve().parents[1]
MIGRATION=ROOT/'supabase/migrations/20261010183000_persistence_traceability.sql'
CLOCK_MIGRATION=ROOT/'supabase/migrations/20261010190000_approval_clock_after_lock.sql'
VERIFY="""
SELECT
 to_regclass('public.decision_approval_events') IS NOT NULL AS audit_table,
 to_regprocedure('public.decision_case_history(uuid,text,integer,integer)') IS NOT NULL AS history_rpc,
 EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='decision_runs' AND column_name='approved_by') AS actor,
 (SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname IN
  ('approval_events_immutable','datasets_persistence_identity','cases_persistence_identity',
   'runs_persistence_identity','decision_runs_current_admission'))=5 AS triggers,
 EXISTS(SELECT 1 FROM pg_class WHERE oid=to_regclass('public.decision_approval_events') AND relrowsecurity) AS rls,
 NOT has_function_privilege('anon','public.decision_case_history(uuid,text,integer,integer)','EXECUTE')
 AND NOT has_function_privilege('authenticated','public.decision_case_history(uuid,text,integer,integer)','EXECUTE') AS private;
"""


def normalize(value):
    if isinstance(value,dict):
        return {k:normalize(v) for k,v in value.items() if k!='server_version_num'}
    if isinstance(value,list):
        return sorted((normalize(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
    return value


def main():
    catalog=query(CATALOG_SQL)[0]['catalog']
    names={t['name'] for t in catalog['tables']}
    if 'decision_approval_events' in names:
        if not all(query(VERIFY)[0].values()):
            raise RuntimeError('Incomplete Phase 4 schema. Review before deploying.')
        ensure_approval_clock()
        print('Phase 4 already present; schema, approval clock and privileges verified.')
        return
    expected=json.loads((ROOT/'supabase/baseline/20261010100000_catalog.json').read_text())
    if normalize(catalog)!=normalize(expected):
        raise RuntimeError('Production DDL differs from the reviewed Phase 3 catalog. No changes applied.')
    query(MIGRATION.read_text())
    if not all(query(VERIFY)[0].values()):
        raise RuntimeError('Phase 4 verification failed. Do not deploy new application code.')
    ensure_approval_clock()
    print('Phase 4 transactional migrations applied; history RPC, immutable audit, actor, clock, triggers and private privileges verified.')


def approval_body(path):
    function=path.read_text().split('CREATE OR REPLACE FUNCTION public.approve_decision_run_version(',1)[1]
    return function.split('AS $$',1)[1].split('$$;',1)[0].strip()


def ensure_approval_clock():
    sql="SELECT prosrc AS body FROM pg_proc WHERE oid='public.approve_decision_run_version(uuid,uuid,text)'::regprocedure;"
    current=query(sql)[0]['body'].strip()
    expected=approval_body(CLOCK_MIGRATION)
    if current==expected:
        return
    if current!=approval_body(MIGRATION):
        raise RuntimeError('Approval function drift. No clock upgrade applied.')
    query(CLOCK_MIGRATION.read_text())
    if query(sql)[0]['body'].strip()!=expected:
        raise RuntimeError('Approval clock upgrade verification failed.')
    print('Approval clock migration applied; timestamp is recorded after the case lock.')


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
