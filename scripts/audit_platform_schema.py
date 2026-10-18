"""Read-only Platform MVP audit: database metadata and aggregate counts, never rows.

Run from the repository with SUPABASE_ACCESS_TOKEN injected securely:
    python scripts/audit_platform_schema.py --output docs/platform-mvp/schema

The fixed project and HTTPS credential route reuse the existing administration
client. This does not apply migrations or overwrite the historical SQL baseline.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from apply_production_queue import REF, query
from capture_public_schema import SQL as PUBLIC_CATALOG_SQL


EXTRA_SQL = """
jsonb_build_object(
 'views',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'schema',n.nspname,'name',c.relname,'kind',c.relkind,
   'definition',pg_get_viewdef(c.oid,true),'options',c.reloptions,
   'grants',(SELECT jsonb_agg(jsonb_build_object('role',CASE WHEN x.grantee=0 THEN 'PUBLIC'
     ELSE pg_get_userbyid(x.grantee) END,'privilege',x.privilege_type))
     FROM aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) x)
  ) ORDER BY n.nspname,c.relname),'[]'::jsonb)
   FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname IN('public','storage') AND c.relkind IN('v','m')),
 'sequences',(SELECT coalesce(jsonb_agg(to_jsonb(s) - 'last_value' ORDER BY sequencename),'[]'::jsonb)
   FROM pg_sequences s WHERE schemaname='public'),
 'function_security',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'signature',format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
   'security_definer',p.prosecdef,'config',p.proconfig,'volatility',p.provolatile)
   ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)),'[]'::jsonb)
   FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'),
 'managed_relations',(SELECT coalesce(jsonb_agg(jsonb_build_object(
   'schema',n.nspname,'name',c.relname,'kind',c.relkind,
   'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,
   'columns',(SELECT jsonb_agg(jsonb_build_object('name',a.attname,
     'type',format_type(a.atttypid,a.atttypmod),'not_null',a.attnotnull) ORDER BY a.attnum)
     FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped))
   ORDER BY n.nspname,c.relname),'[]'::jsonb)
   FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname IN('auth','storage') AND c.relkind IN('r','p')),
 'storage_policies',(SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY tablename,policyname),'[]'::jsonb)
   FROM pg_policies p WHERE schemaname='storage'),
 'storage_buckets',(SELECT coalesce(jsonb_agg(jsonb_build_object('id',id,'name',name,
   'public',public,'file_size_limit',file_size_limit,'allowed_mime_types',allowed_mime_types)
   ORDER BY id),'[]'::jsonb) FROM storage.buckets),
 'storage_layout',(SELECT coalesce(jsonb_agg(to_jsonb(s) ORDER BY bucket_id,path_parts),'[]'::jsonb)
   FROM (SELECT bucket_id,array_length(string_to_array(name,'/'),1) AS path_parts,
     count(*) AS objects,
     count(*) FILTER (WHERE name ~ '^[0-9a-fA-F-]{36}/') AS uuid_prefix_objects
     FROM storage.objects GROUP BY bucket_id,array_length(string_to_array(name,'/'),1)) s)
)
"""


def readonly(sql):
    return query("BEGIN READ ONLY; SET LOCAL statement_timeout='20s'; " + sql + "; COMMIT;")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # A single transaction yields a consistent catalog and storage metadata.
    catalog = readonly('WITH base AS (' + PUBLIC_CATALOG_SQL.strip().removesuffix(';')
                       + ') SELECT catalog || ' + EXTRA_SQL + ' AS catalog FROM base')[0]['catalog']
    # Identifiers originate in the catalog and are still quoted, never interpolated raw.
    counts = ','.join("'" + t['name'].replace("'", "''") + "',(SELECT count(*) FROM "
                      + t['qualified'] + ')' for t in catalog['tables'])
    totals = readonly('SELECT jsonb_build_object(' + counts + ') AS counts')[0]['counts']
    snapshot = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                'project_ref': REF, 'read_only': True,
                'scope': 'public DDL; managed auth/storage metadata; aggregate counts; no business rows',
                'catalog': catalog, 'aggregate_row_counts': totals}
    serialized = json.dumps(snapshot, indent=2, sort_keys=True) + '\n'
    if re.search(r'sb_secret_|sbp_|-----BEGIN .*PRIVATE KEY', serialized):
        raise RuntimeError('Sensitive material detected; refusing to save catalog.')
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / 'live-catalog.json'
    if target.exists():
        raise RuntimeError('Output already exists; select a new directory to preserve audit history.')
    target.write_text(serialized)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    (args.output / 'SHA256SUMS').write_text(digest + '  live-catalog.json\n')
    print(json.dumps({'read_only': True, 'tables': len(catalog['tables']),
                      'functions': len(catalog['functions']), 'views': len(catalog['views']),
                      'policies': len(catalog['policies']),
                      'storage_policies': len(catalog['storage_policies']),
                      'buckets': len(catalog['storage_buckets']), 'sha256': digest}))


if __name__ == '__main__':
    main()
