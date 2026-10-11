"""Apply Phase 7 once; exact catalog comparison rejects partial schemas and drift."""
import json
from pathlib import Path
import sys
from apply_production_queue import query

ROOT=Path(__file__).resolve().parents[1]
MIGRATION=ROOT/'supabase/migrations/20261010233000_operational_observability.sql'
MANIFEST=ROOT/'supabase/catalog/20261010233000_observability.json'
CATALOG_SQL="""
SELECT jsonb_build_object(
 'functions',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',p.proname,
  'arguments',pg_get_function_identity_arguments(p.oid),'body',p.prosrc,'volatility',p.provolatile,
  'definer',p.prosecdef,'config',p.proconfig,
  'anon',has_function_privilege('anon',p.oid,'EXECUTE'),
  'authenticated',has_function_privilege('authenticated',p.oid,'EXECUTE'),
  'service_role',has_function_privilege('service_role',p.oid,'EXECUTE')) ORDER BY p.proname),'[]')
  FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'
  AND p.proname IN('report_dispatch_worker','read_decision_chat_turn','record_decision_chat_turn','dispatch_operational_snapshot')),
 'tables',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.relname,'rls',c.relrowsecurity,
  'anon',has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE'),
  'authenticated',has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE'),
  'service_select',has_table_privilege('service_role',c.oid,'SELECT'),
  'service_insert',has_table_privilege('service_role',c.oid,'INSERT'),
  'service_update',has_table_privilege('service_role',c.oid,'UPDATE'),
  'service_delete',has_table_privilege('service_role',c.oid,'DELETE')) ORDER BY c.relname),'[]')
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
  AND c.relname IN('dispatch_worker_instances','decision_chat_turns')),
 'columns',(SELECT coalesce(jsonb_agg(jsonb_build_object('table',table_name,'column',column_name,'type',udt_name,
  'nullable',is_nullable,'default',column_default) ORDER BY table_name,ordinal_position),'[]')
  FROM information_schema.columns WHERE table_schema='public' AND
  (table_name IN('dispatch_worker_instances','decision_chat_turns') OR (table_name='decision_messages' AND column_name='turn_id'))),
 'constraints',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',conname,'definition',pg_get_constraintdef(oid)) ORDER BY conname),'[]')
  FROM pg_constraint WHERE conrelid IN(to_regclass('public.dispatch_worker_instances'),to_regclass('public.decision_chat_turns'))
  OR (conrelid=to_regclass('public.decision_messages') AND conname='decision_messages_turn_id_fkey')),
 'indexes',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',indexname,'definition',indexdef) ORDER BY indexname),'[]')
  FROM pg_indexes WHERE schemaname='public' AND (tablename IN('dispatch_worker_instances','decision_chat_turns')
  OR indexname IN('decision_messages_turn_role_idx','decision_messages_recent_idx','decision_runs_operational_idx')))
) AS catalog;
"""


def main():
    prerequisite=query("SELECT to_regprocedure('public.list_decision_cases(text,integer,integer,boolean)') IS NOT NULL AS phase5, "
                       "to_regclass('public.dispatch_run_jobs') IS NOT NULL AS jobs;")[0]
    if not all(prerequisite.values()):raise RuntimeError('Phase 5 prerequisites missing. No changes applied.')
    expected=json.loads(MANIFEST.read_text())
    before=query(CATALOG_SQL)[0]['catalog']
    if any(before.values()):
        if before!=expected:raise RuntimeError('Phase 7 catalog is partial or has drift. No changes applied.')
    else:
        query(MIGRATION.read_text())
    if query(CATALOG_SQL)[0]['catalog']!=expected:
        raise RuntimeError('Phase 7 exact catalog verification failed. Do not deploy.')
    query('BEGIN READ ONLY; SELECT dispatch_operational_snapshot() IS NOT NULL AS checked; COMMIT;')
    print('Phase 7 verified: exact functions, tables, columns, constraints, indexes, RLS and privileges. Read-only snapshot executed.')


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
