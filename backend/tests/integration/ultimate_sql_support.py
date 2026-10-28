"""Complete PostgreSQL 17 application catalog, exclusively in a labelled owned sandbox.

Unlike SQLSandbox's intentionally historical coverage, this applies the captured
baseline plus EVERY later migration. It never repairs history or contacts Supabase.
"""
from pathlib import Path
import json
import os
import subprocess
from uuid import uuid4

REPO = Path(__file__).resolve().parents[3]
BASELINE = REPO / 'supabase/baseline/20261010100000_public_schema.sql'
POST_T1_CUTOFF = '20261026010000'
CONTAINER = os.environ.get('DATION_SQL_TEST_CONTAINER')
DOCKER = ['docker', '--host=unix:///var/run/docker.sock']

AUTH = """
CREATE SCHEMA auth;
CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,email_confirmed_at timestamptz);
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
 SELECT (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid $$;
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;
"""

# Captured T0 Supabase administrative defaults; fixture only, never product DDL.
MANAGED_DEFAULTS = """
DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='supabase_admin') THEN
 CREATE ROLE supabase_admin NOLOGIN; END IF; END $$;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres,supabase_admin IN SCHEMA public
 GRANT ALL ON TABLES TO postgres,anon,authenticated,service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres,supabase_admin IN SCHEMA public
 GRANT ALL ON SEQUENCES TO postgres,anon,authenticated,service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres,supabase_admin IN SCHEMA public
 GRANT EXECUTE ON FUNCTIONS TO postgres,anon,authenticated,service_role;
"""
MANAGED_EXISTING_GRANTS = """
GRANT DELETE,TRUNCATE,REFERENCES,TRIGGER ON public.profiles,public.workspace_ddas,
 public.workspace_members,public.workspaces TO service_role;
GRANT REFERENCES,TRIGGER ON public.audit_events TO service_role;
"""

CATALOG_SQL = """
SELECT jsonb_build_object(
 'columns',(SELECT jsonb_agg(to_jsonb(x) ORDER BY table_schema,table_name,ordinal_position)
  FROM (SELECT table_schema,table_name,ordinal_position,column_name,data_type,udt_name,is_nullable,column_default
   FROM information_schema.columns WHERE table_schema IN('public','dation_private')) x),
 'constraints',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,table_name,name)
  FROM (SELECT n.nspname schema_name,t.relname table_name,c.conname name,c.contype,
    c.condeferrable,c.condeferred,pg_get_constraintdef(c.oid) definition
   FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
   WHERE n.nspname IN('public','dation_private')) x),
 'indexes',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schemaname,tablename,indexname)
  FROM (SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes
   WHERE schemaname IN('public','dation_private')) x),
 'policies',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schemaname,tablename,policyname)
  FROM (SELECT * FROM pg_policies WHERE schemaname IN('public','dation_private')) x),
 'relations',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,name)
  FROM (SELECT n.nspname schema_name,c.relname name,c.relkind,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text acl
   FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname IN('public','dation_private') AND c.relkind IN('r','p','v')) x),
 'functions',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,name,args)
  FROM (SELECT n.nspname schema_name,p.proname name,pg_get_function_identity_arguments(p.oid) args,
    p.prosecdef,p.proconfig,p.proacl::text acl,pg_get_functiondef(p.oid) definition
   FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname IN('public','dation_private') AND p.prokind='f') x),
 'triggers',(SELECT jsonb_agg(to_jsonb(x) ORDER BY schema_name,table_name,name)
  FROM (SELECT n.nspname schema_name,c.relname table_name,t.tgname name,t.tgenabled,pg_get_triggerdef(t.oid) definition
   FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE NOT t.tgisinternal AND n.nspname IN('public','dation_private')) x),
 'defaults',(SELECT jsonb_agg(to_jsonb(x) ORDER BY owner_name,schema_name,kind)
  FROM (SELECT pg_get_userbyid(d.defaclrole) owner_name,n.nspname schema_name,d.defaclobjtype kind,d.defaclacl::text acl
   FROM pg_default_acl d JOIN pg_namespace n ON n.oid=d.defaclnamespace
   WHERE n.nspname IN('public','dation_private')) x));
"""


class UltimateSQLSandbox:
    @classmethod
    def command(cls, sql, database=None, check=True):
        if not CONTAINER:
            raise RuntimeError('DATION_SQL_TEST_CONTAINER must name an owned T2 PostgreSQL 17 sandbox')
        env=os.environ.copy()
        for name in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):
            env.pop(name,None)
        result=subprocess.run([*DOCKER,'exec','-i',CONTAINER,'psql','-U','postgres',
            '-d',database or cls.database,'-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose'],
            input=sql,text=True,capture_output=True,env=env,timeout=60)
        if check and result.returncode:
            raise AssertionError(result.stderr)
        return result

    @classmethod
    def verify_owner(cls):
        result=subprocess.run([*DOCKER,'inspect','--format','{{index .Config.Labels "dation.qa.phase"}}',CONTAINER or ''],
                              capture_output=True,text=True,timeout=10)
        if result.returncode or result.stdout.strip()!='T2':
            raise RuntimeError('Refusing an unlabelled/non-owned SQL container')
        version=cls.command('SHOW server_version_num;',database='postgres').stdout.strip()
        if not 170000<=int(version)<180000:
            raise RuntimeError('Ultimate SQL suite requires PostgreSQL 17')

    @classmethod
    def create_database(cls, ultimate=True):
        name='dation_t2_'+uuid4().hex
        cls.command('CREATE DATABASE '+name+';',database='postgres')
        try:
            cls.command((Path(__file__).parent/'infrastructure.sql').read_text(),database=name)
            cls.command(AUTH+MANAGED_DEFAULTS,database=name)
            cls.command(BASELINE.read_text(),database=name)
            cls.migrate(name,ultimate=ultimate)
            cls.command(MANAGED_EXISTING_GRANTS,database=name)
        except BaseException:
            cls.drop_database(name)
            raise
        return name

    @classmethod
    def migrate(cls,database,ultimate=True,only_t2=False):
        for migration in sorted((REPO/'supabase/migrations').glob('*.sql')):
            version=migration.name[:14]
            if version<='20261010100000' or (not ultimate and version>POST_T1_CUTOFF):continue
            if only_t2 and version<=POST_T1_CUTOFF:continue
            cls.command(migration.read_text(),database=database)

    @classmethod
    def drop_database(cls,name):
        if not name.startswith('dation_t2_'):raise RuntimeError('Not an owned disposable database')
        cls.command('DROP DATABASE '+name+';',database='postgres')

    @classmethod
    def catalog(cls,database=None):
        return json.loads(cls.command(CATALOG_SQL,database=database).stdout)

    @classmethod
    def setUpClass(cls):
        cls.verify_owner()
        cls.database=cls.create_database()

    @classmethod
    def tearDownClass(cls):cls.drop_database(cls.database)
