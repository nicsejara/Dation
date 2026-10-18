"""Controlled Phase 2/3 cutover through existing Supabase administration access.

Run --freeze only once the PR's full gates pass. Capture/restore a FRESH backup,
then --apply. Auth admissions remain closed until GitHub Cloud Build confirms
both new worker and API revisions; --activate checks the backup and migration hashes.
No emails are sent by this tool and no historical business record is deleted.
"""
import argparse,hashlib,json,re
from pathlib import Path
from urllib.request import Request,urlopen
import os
from apply_production_queue import query,ROOT,REF
from backup_platform_identity import TABLES,summaries,rows_sql,save

MIGRATIONS=[ROOT/'supabase/migrations/20261018090000_platform_identity_tenancy.sql',ROOT/'supabase/migrations/20261018100000_platform_profile.sql']
TENANT=[t for t in TABLES if t!='dispatch_worker_instances']

def checked_backup(directory):
 manifest=json.loads((directory/'manifest.json').read_text())
 if not manifest.get('restore_verified') or not manifest.get('migrated_existing_evidence_unchanged'):
  raise RuntimeError('A verified restore of the current migration is required.')
 if any(manifest['migration_sha256'].get(p.name)!=hashlib.sha256(p.read_bytes()).hexdigest() for p in MIGRATIONS):
  raise RuntimeError('Migrations changed after restore verification.')
 if summaries(json.loads((directory/'rows.json').read_text()))!=manifest['tables']:
  raise RuntimeError('Backup rows do not match the verified manifest.')
 return manifest

def freeze(directory):
 directory.mkdir(mode=0o700,parents=True,exist_ok=False)
 privileges=query("SELECT table_name,privilege_type FROM information_schema.role_table_grants WHERE table_schema='public' AND grantee='service_role' ORDER BY table_name,privilege_type;")
 save(directory/'service-grants.json',privileges)
 sql='BEGIN; LOCK TABLE '+','.join('public.'+t for t in TENANT)+' IN ACCESS EXCLUSIVE MODE;'
 sql+="DO $$ BEGIN IF EXISTS(SELECT 1 FROM dispatch_run_jobs WHERE state IN('queued','running')) OR EXISTS(SELECT 1 FROM decision_comparative_analyses WHERE status IN('queued','running')) OR EXISTS(SELECT 1 FROM decision_case_reconciliations) THEN RAISE EXCEPTION 'Drain all jobs and reconciliation before freezing'; END IF; END; $$;"
 sql+='REVOKE INSERT,UPDATE,DELETE ON '+','.join('public.'+t for t in TENANT)+' FROM service_role; COMMIT;'
 query(sql)
 print('Existing business writes frozen; no active jobs or reconciliation remained. Worker health reporting stays available.')

def apply(directory,email):
 manifest=checked_backup(directory)
 existing=query("SELECT to_regclass('public.workspaces') IS NOT NULL AS migrated;")[0]['migrated']
 if existing:raise RuntimeError('Identity schema already exists; do not reapply. Verify the current cutover state.')
 before=query(rows_sql())[0]['tables']
 if {t:v for t,v in summaries(before).items() if t in TENANT}!={t:v for t,v in manifest['tables'].items() if t in TENANT}:raise RuntimeError('Production changed after backup. Capture/restore a fresh backup.')
 if not re.fullmatch(r'[^\s@\x00-\x1f]+@[^\s@\x00-\x1f]+\.[^\s@\x00-\x1f]+',email):raise RuntimeError('Provide the authorized legacy administrator email.')
 # Apply both reviewed migrations and the email binding in ONE outer transaction.
 chunks=[]
 for migration in MIGRATIONS:
  text=migration.read_text();text=re.sub(r'^BEGIN;\s*','',text,flags=re.M);text=re.sub(r'^COMMIT;\s*','',text,flags=re.M);chunks.append(text)
 escaped=email.strip().lower().replace("'","''")
 sql='BEGIN;'+''.join(chunks)+f"INSERT INTO dation_private.legacy_owners(email,workspace_id) VALUES('{escaped}','00000000-0000-4000-8000-00000000da71'); COMMIT;"
 query(sql)
 after=query(rows_sql())[0]['tables']
 if {t:v for t,v in summaries(after,strip=True).items() if t in TENANT}!={t:v for t,v in manifest['tables'].items() if t in TENANT}:raise RuntimeError('Business evidence differs. Keep admissions closed and investigate.')
 print('Both migrations applied atomically. Legacy ownership bound; existing evidence unchanged; new Auth admissions CLOSED.')

def auth_config():
 origin='https://dation-core-469052310590.us-west1.run.app'
 body={'site_url':origin+'/app','uri_allow_list':','.join([origin+'/auth/callback',origin+'/auth/callback/recovery']),
       'password_min_length':10,'jwt_exp':900}
 request=Request(f'https://api.supabase.com/v1/projects/{REF}/config/auth',method='PATCH',
  headers={'Authorization':'Bearer '+os.environ['SUPABASE_ACCESS_TOKEN'],'Content-Type':'application/json'},data=json.dumps(body).encode())
 with urlopen(request,timeout=30) as response:result=json.load(response)
 if any(result.get(key)!=value for key,value in body.items()):raise RuntimeError('Auth redirect configuration was not confirmed.')
 print('Production HTTPS callbacks and password/session policy configured. No email sent; delivery must be checked during user registration.')

def activate(directory,grants_directory):
 checked_backup(directory)
 grants=json.loads((grants_directory/'service-grants.json').read_text())
 sql='BEGIN;'
 for grant in grants:
  t,privilege=grant['table_name'],grant['privilege_type']
  if t in TENANT and privilege in {'SELECT','INSERT','UPDATE','DELETE','REFERENCES','TRIGGER','TRUNCATE'}:
   sql+=f'GRANT {privilege} ON public.{t} TO service_role;'
 sql+='UPDATE dation_private.platform_release SET admissions_open=true WHERE singleton; COMMIT;'
 query(sql)
 print('Service table privileges restored to their captured values; Auth admissions OPEN. Rollback to a non-tenant API is now forbidden.')

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','apply','auth-config','activate']);p.add_argument('--backup',type=Path);p.add_argument('--grants',type=Path);p.add_argument('--legacy-owner');args=p.parse_args()
 if args.action=='freeze':freeze(args.grants)
 elif args.action=='apply':apply(args.backup,args.legacy_owner or '')
 elif args.action=='auth-config':auth_config()
 else:activate(args.backup,args.grants)
if __name__=='__main__':main()
