"""Apply progressive evidence once; reject partial installation, drift and missing prerequisites."""
import json
from pathlib import Path
import sys
from apply_production_queue import query

ROOT=Path(__file__).resolve().parents[1]
MIGRATION=ROOT/'supabase/migrations/20261013090000_progressive_comparative_analysis.sql'
MANIFEST=ROOT/'supabase/catalog/20261013090000_comparative.json'
CATALOG_SQL="""
SELECT jsonb_build_object(
 'functions',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',p.proname,
  'arguments',pg_get_function_identity_arguments(p.oid),'body',p.prosrc,'volatility',p.provolatile,
  'definer',p.prosecdef,'config',p.proconfig,
  'anon',has_function_privilege('anon',p.oid,'EXECUTE'),
  'authenticated',has_function_privilege('authenticated',p.oid,'EXECUTE'),
  'service_role',has_function_privilege('service_role',p.oid,'EXECUTE')) ORDER BY p.proname),'[]')
  FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'
  AND p.proname IN('protect_comparative_analysis','enqueue_comparative_analysis','claim_comparative_analysis','heartbeat_comparative_analysis','finish_comparative_analysis','validate_interpretation_source','read_decision_chat_turn_with_evidence','record_decision_chat_turn_with_evidence','record_decision_explanation_with_evidence','comparative_operational_snapshot','current_decision_explanation')),
 'tables',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.relname,'rls',c.relrowsecurity,
  'anon',has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE'),
  'authenticated',has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE'),
  'service_select',has_table_privilege('service_role',c.oid,'SELECT'),
  'service_insert',has_table_privilege('service_role',c.oid,'INSERT'),
  'service_update',has_table_privilege('service_role',c.oid,'UPDATE'),
  'service_delete',has_table_privilege('service_role',c.oid,'DELETE')) ORDER BY c.relname),'[]')
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
  AND c.relname IN('decision_comparative_analyses','decision_interpretation_sources')),
 'columns',(SELECT coalesce(jsonb_agg(jsonb_build_object('table',table_name,'column',column_name,'type',udt_name,
  'nullable',is_nullable,'default',column_default) ORDER BY table_name,ordinal_position),'[]')
  FROM information_schema.columns WHERE table_schema='public' AND
  table_name IN('decision_comparative_analyses','decision_interpretation_sources')),
 'constraints',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',conname,'definition',pg_get_constraintdef(oid)) ORDER BY conname),'[]')
  FROM pg_constraint WHERE conrelid IN(to_regclass('public.decision_comparative_analyses'),to_regclass('public.decision_interpretation_sources'))),
 'indexes',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',indexname,'definition',indexdef) ORDER BY indexname),'[]')
  FROM pg_indexes WHERE schemaname='public' AND tablename IN('decision_comparative_analyses','decision_interpretation_sources')),
 'triggers',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',tgname,'definition',pg_get_triggerdef(oid)) ORDER BY tgname),'[]')
  FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN(to_regclass('public.decision_comparative_analyses'),to_regclass('public.decision_interpretation_sources')))
) AS catalog;
"""



def main():
    from apply_production_observability import CATALOG_SQL as prerequisite_sql, MANIFEST as prerequisite_manifest
    if query(prerequisite_sql)[0]['catalog'] != json.loads(prerequisite_manifest.read_text()):
        raise RuntimeError('Phase 7 prerequisite catalog has drift. No changes applied.')
    expected=json.loads(MANIFEST.read_text())
    before=query(CATALOG_SQL)[0]['catalog']
    if any(before.values()):
        if before!=expected:raise RuntimeError('Comparative catalog is partial or has drift. No changes applied.')
    else:
        query(MIGRATION.read_text())
    if query(CATALOG_SQL)[0]['catalog']!=expected:
        raise RuntimeError('Comparative catalog verification failed. Do not deploy.')
    print('Progressive evidence verified: exact functions, tables, columns, constraints, indexes, triggers, RLS and privileges.')


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
