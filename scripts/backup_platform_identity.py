"""Capture an access-restricted business backup and prove restoration locally.

Reads production only. Never logs business rows, file contents, credentials or
Auth password data. The local restore uses an owned disposable PostgreSQL server.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
from urllib.request import Request,urlopen
from apply_production_queue import query,ROOT

TABLES=['datasets','decision_cases','decision_runs','dispatch_run_jobs','decision_case_reconciliations',
 'decision_approval_events','decision_comparative_analyses','decision_explanations','decision_messages',
 'decision_chat_turns','decision_interpretation_sources','dispatch_worker_instances']
ADDED={'workspace_id','approved_by_user_id','actor_user_id'}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def rows_sql(tables=TABLES):
 return "SELECT jsonb_build_object("+','.join("'%s',(SELECT coalesce(jsonb_agg(to_jsonb(r)),'[]') FROM public.%s r)"%(t,t) for t in tables)+") AS tables;"
def summaries(tables,strip=False):
 return {t:{'rows':len(rows),'sha256':digest(sorted([{k:v for k,v in row.items() if not strip or k not in ADDED} for row in rows],key=lambda r:canonical(r)))} for t,rows in tables.items()}
def save(path,value):
 path.write_text(json.dumps(value,indent=2,ensure_ascii=False));path.chmod(0o600)
def run(args,**options):
 result=subprocess.run(args,capture_output=True,text=True,**options)
 if result.returncode:raise RuntimeError('Owned restore command failed: '+result.stderr[-1800:])
 return result.stdout

def capture(directory):
 directory.mkdir(mode=0o700,parents=True,exist_ok=False)
 tables=query(rows_sql())[0]['tables'];save(directory/'rows.json',tables)
 metadata={'tables':summaries(tables),'files':[],'read_only_production':True}
 objects=directory/'objects';objects.mkdir(mode=0o700)
 for row in tables['datasets']:
  from urllib.parse import quote
  key=row['storage_bucket']+'/'+row['storage_path'];local=objects/(row['id']+'.csv')
  request=Request(os.environ['SUPABASE_URL']+'/storage/v1/object/authenticated/'+quote(key,safe='/'),headers={
   'apikey':os.environ['SUPABASE_SECRET_KEY'],'Authorization':'Bearer '+os.environ['SUPABASE_SECRET_KEY']})
  with urlopen(request,timeout=30) as response:data=response.read()
  sha=hashlib.sha256(data).hexdigest()
  if row.get('sha256') and sha!=row['sha256']:raise RuntimeError('Storage integrity mismatch; release blocked.')
  local.write_bytes(data);local.chmod(0o600);metadata['files'].append({'id':row['id'],'sha256':sha,'bytes':len(data)})
 save(directory/'manifest.json',metadata)
 return tables,metadata

def restore(directory,tables,metadata):
 name='dation-restore-'+uuid4().hex[:12]
 run(['docker','run','-d','--name',name,'-e','POSTGRES_HOST_AUTH_METHOD=trust','postgres:17-alpine'])
 def sql(source):return run(['docker','exec','-i',name,'psql','-U','postgres','-X','-q','-A','-t','-v','ON_ERROR_STOP=1'],input=source)
 try:
  for _ in range(150):
   if subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','postgres'],capture_output=True).returncode==0:break
   time.sleep(.1)
  sql((ROOT/'backend/tests/integration/infrastructure.sql').read_text())
  sql("CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,email_confirmed_at timestamptz); CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid $$;")
  sql((ROOT/'supabase/baseline/20261010100000_public_schema.sql').read_text())
  migrations=sorted((ROOT/'supabase/migrations').glob('*.sql'))
  for migration in migrations:
   if '20261010100000'<migration.name[:14]<'20261018090000':sql(migration.read_text())
  # Restore historical rows in one transaction: defer FK checks, suppress only
  # admission/identity USER triggers locally, then re-enable and validate at commit.
  restore_sql="BEGIN; DO $$ DECLARE r record; BEGIN FOR r IN SELECT conrelid::regclass rel,conname FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace LOOP EXECUTE format('ALTER TABLE %s ALTER CONSTRAINT %I DEFERRABLE INITIALLY DEFERRED',r.rel,r.conname); END LOOP; END; $$;"
  for table in TABLES:restore_sql+=f'ALTER TABLE public.{table} DISABLE TRIGGER USER;'
  for table,rows in tables.items():
   if rows:
    literal=json.dumps(rows,ensure_ascii=False).replace("'","''")
    restore_sql+=f"INSERT INTO public.{table} SELECT * FROM jsonb_populate_recordset(NULL::public.{table},'{literal}'::jsonb);"
  restore_sql+='SET CONSTRAINTS ALL IMMEDIATE;'
  for table in TABLES:restore_sql+=f'ALTER TABLE public.{table} ENABLE TRIGGER USER;'
  sql(restore_sql+'COMMIT;')
  before=json.loads(sql(rows_sql()))
  if summaries(before)!=metadata['tables']:raise RuntimeError('Restore differs from the captured backup.')
  for migration in migrations:
   if migration.name[:14]>='20261018090000':sql(migration.read_text())
  after=json.loads(sql(rows_sql()))
  if summaries(after,strip=True)!=metadata['tables']:raise RuntimeError('Migration changed existing business evidence.')
  if sql("SELECT bool_and(convalidated) FROM pg_constraint WHERE connamespace='public'::regnamespace;").strip()!='t':raise RuntimeError('Unvalidated constraints after restore.')
  metadata['restore_verified']=True;metadata['migrated_existing_evidence_unchanged']=True
  metadata['migration_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in migrations if p.name[:14]>='20261018090000'}
  save(directory/'manifest.json',metadata)
 finally:subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 tables,metadata=capture(args.output);restore(args.output,tables,metadata)
 print(json.dumps({'backup_path':str(args.output),'tables':len(tables),'rows':sum(len(v) for v in tables.values()),'objects':len(metadata['files']),'restore_verified':True,'existing_evidence_unchanged':True}))
if __name__=='__main__':main()
