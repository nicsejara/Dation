"""Capture app DDL (never rows) from the authorized Supabase project.

The snapshot is a fresh-install baseline, not an upgrade migration.
Requires SUPABASE_ACCESS_TOKEN; infrastructure schemas remain managed by Supabase.
"""
import json
from pathlib import Path
from apply_production_queue import query

ROOT = Path(__file__).resolve().parents[1]
SQL = """
select jsonb_build_object(
 'server_version_num',current_setting('server_version_num')::integer,
 'tables', (select jsonb_agg(jsonb_build_object(
   'name',c.relname,'qualified',format('%I.%I',n.nspname,c.relname),
   'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,
   'columns',(select jsonb_agg(format('%I %s%s%s',a.attname,
       format_type(a.atttypid,a.atttypmod),
       case when d.adbin is not null then ' DEFAULT '||pg_get_expr(d.adbin,d.adrelid) else '' end,
       case when a.attnotnull then ' NOT NULL' else '' end) order by a.attnum)
     from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
     where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped),
   'constraints',(select coalesce(jsonb_agg(jsonb_build_object('name',co.conname,'kind',co.contype,
     'definition',pg_get_constraintdef(co.oid,true)) order by co.conname),'[]'::jsonb)
     from pg_constraint co where co.conrelid=c.oid),
   'indexes',(select coalesce(jsonb_agg(pg_get_indexdef(i.indexrelid) order by i.indexrelid::regclass::text),'[]'::jsonb)
     from pg_index i where i.indrelid=c.oid and not exists(select 1 from pg_constraint co where co.conindid=i.indexrelid)),
   'triggers',(select coalesce(jsonb_agg(pg_get_triggerdef(t.oid,true) order by t.tgname),'[]'::jsonb)
     from pg_trigger t where t.tgrelid=c.oid and not t.tgisinternal),
   'grants',(select jsonb_agg(jsonb_build_object('role',case when x.grantee=0 then 'PUBLIC'
     else quote_ident(pg_get_userbyid(x.grantee)) end,'privilege',x.privilege_type,'grantable',x.is_grantable))
     from aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) x)
 ) order by c.relname) from pg_class c join pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and c.relkind='r'),
 'functions',(select jsonb_agg(jsonb_build_object('definition',pg_get_functiondef(p.oid),
   'signature',format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
   'grants',(select jsonb_agg(jsonb_build_object('role',case when x.grantee=0 then 'PUBLIC'
     else quote_ident(pg_get_userbyid(x.grantee)) end,'privilege',x.privilege_type,'grantable',x.is_grantable))
     from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) x)) order by p.proname)
   from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public'),
 'policies',(select coalesce(jsonb_agg(to_jsonb(p)),'[]'::jsonb) from pg_policies p where schemaname='public')
) as catalog;
"""


def render(catalog):
    if catalog['policies']:
        raise RuntimeError('Policy capture requires review before rendering this baseline.')
    lines = [
        '-- Production catalog capture: gijiinufjjurgfeehufj, 2026-10-10, Phase 3.',
        '-- No application data or credentials. FRESH INSTALL ONLY; see supabase/README.md.',
        '-- PostgreSQL 17+; infrastructure: public schema, anon/authenticated/service_role roles.',
        'BEGIN;',
    ]
    for table in catalog['tables']:
        lines.append('CREATE TABLE '+table['qualified']+' (\n  '+',\n  '.join(table['columns'])+'\n);')
    # All relations exist before any FK; referenced unique keys precede FKs.
    for foreign in (False, True):
        for table in catalog['tables']:
            for constraint in table['constraints']:
                if (constraint['kind']=='f') == foreign:
                    name='"'+constraint['name'].replace('"','""')+'"'
                    lines.append(f"ALTER TABLE {table['qualified']} ADD CONSTRAINT {name} {constraint['definition']};")
    for function in catalog['functions']:
        lines.append(function['definition'].rstrip()+';')
    for table in catalog['tables']:
        lines.extend(index+';' for index in table['indexes'])
        lines.extend(trigger+';' for trigger in table['triggers'])
        if table['rls']:
            lines.append('ALTER TABLE '+table['qualified']+' ENABLE ROW LEVEL SECURITY;')
        if table['force_rls']:
            lines.append('ALTER TABLE '+table['qualified']+' FORCE ROW LEVEL SECURITY;')
        lines.append('REVOKE ALL ON TABLE '+table['qualified']+' FROM PUBLIC, anon, authenticated, service_role;')
        for grant in table['grants']:
            lines.append(f"GRANT {grant['privilege']} ON TABLE {table['qualified']} TO {grant['role']}"
                         + (' WITH GRANT OPTION' if grant['grantable'] else '')+';')
    for function in catalog['functions']:
        lines.append('REVOKE ALL ON FUNCTION '+function['signature']+' FROM PUBLIC, anon, authenticated, service_role;')
        for grant in function['grants']:
            lines.append(f"GRANT {grant['privilege']} ON FUNCTION {function['signature']} TO {grant['role']}"
                         + (' WITH GRANT OPTION' if grant['grantable'] else '')+';')
    lines.extend(['COMMIT;', "NOTIFY pgrst, 'reload schema';",''])
    return '\n\n'.join(lines)


if __name__ == '__main__':
    catalog=query(SQL)[0]['catalog']
    if len(catalog['tables']) != 7 or len(catalog['functions']) != 13:
        raise RuntimeError('This is no longer the reviewed Phase 3 schema; create a new baseline version instead.')
    target=ROOT/'supabase/baseline'
    target.mkdir(exist_ok=True)
    (target/'20261010100000_public_schema.sql').write_text(render(catalog))
    (target/'20261010100000_catalog.json').write_text(json.dumps(catalog,indent=2,sort_keys=True)+'\n')
    print(f"Captured DDL: {len(catalog['tables'])} tables, {len(catalog['functions'])} functions; no rows.")
