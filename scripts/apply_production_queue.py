"""Apply the reviewed additive Phase 3 migration through Supabase Management API.

Requires SUPABASE_ACCESS_TOKEN in the secure environment, never a chat argument.
Uses no data API service key for DDL. Existing historical migrations must be present.
"""
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

REF = 'gijiinufjjurgfeehufj'
ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / 'supabase/migrations/20261010100000_dispatch_durable_jobs.sql'


def query(sql):
    token = os.getenv('SUPABASE_ACCESS_TOKEN')
    if not token:
        raise RuntimeError('Configure SUPABASE_ACCESS_TOKEN securely; the Supabase data key cannot apply DDL.')
    request = Request(f'https://api.supabase.com/v1/projects/{REF}/database/query',
        data=json.dumps({'query':sql}).encode(),
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
    try:
        with urlopen(request,timeout=60) as response:
            return json.load(response)
    except HTTPError as exc:
        # Do not print response bodies: provider errors can contain query/data details.
        raise RuntimeError(f'Supabase administration returned HTTP {exc.code}.') from None


VERIFY = """
select
  to_regclass('public.dispatch_run_jobs') is not null as jobs,
  to_regclass('public.decision_case_reconciliations') is not null as outbox,
  (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname='public' and p.proname in
   ('enqueue_dispatch_run','maintain_dispatch_jobs','claim_dispatch_job','heartbeat_dispatch_job',
    'finish_dispatch_job','cancel_dispatch_job','ack_case_reconciliation','request_case_reconciliation')) = 8 as functions,
  (select count(*) from pg_trigger where not tgisinternal and tgname in
   ('decision_runs_reconcile_insert','decision_runs_reconcile_update')) = 2 as triggers,
  (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and c.relname in ('dispatch_run_jobs','decision_case_reconciliations')
   and c.relrowsecurity) = 2 as rls;
"""


def main():
    before = query(VERIFY)[0]
    if before['jobs'] or before['outbox']:
        if not all(before.values()):
            raise RuntimeError('An incomplete queue schema exists. Review it before applying the migration.')
        print('Production queue migration already present; schema checks passed.')
        return
    prerequisite = query("select to_regclass('public.decision_cases') is not null as cases, "
                         "to_regprocedure('public.approve_decision_run_version(uuid,uuid,text)') is not null as approval;")[0]
    if not all(prerequisite.values()):
        raise RuntimeError('The decision_case/history migrations must be applied first.')
    query(MIGRATION.read_text())
    if not all(query(VERIFY)[0].values()):
        raise RuntimeError('The migration returned but schema verification failed. Do not deploy the API.')
    print('Production queue migration applied atomically; tables, RPCs, triggers and RLS verified.')


if __name__ == '__main__':
    try:main()
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
