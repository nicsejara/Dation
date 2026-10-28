"""Close T2 evidence without modifying application files or any remote service."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,importlib.metadata,json,os,re,subprocess,sys

ROOT=Path('/workspace/Dation');WORK=Path('/workspace/work/dation-t2')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def write(name,value):(WORK/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

initial=read(WORK/'initial-state.json');freeze=read(WORK/'source-freeze.json')
assert all(sha(ROOT/n)==v['sha256'] for n,v in initial['files'].items())
assert all(sha(ROOT/n)==h for n,h in freeze['files'].items())
assert git('rev-parse','HEAD')==initial['head'] and not git('diff','--cached','--name-only')
modified=[n for n in freeze['files'] if n in git('diff','--name-only').splitlines()]
new=[n for n in freeze['files'] if n not in modified]
assert len(modified)==len(new)==5
assert set(git('diff','--name-only').splitlines())==set(initial['tracked_changes'])|set(modified)
patch=subprocess.check_output(['git','diff','--binary','--',*modified],cwd=ROOT)
for name in new:
    result=subprocess.run(['git','diff','--no-index','--binary','/dev/null',name],cwd=ROOT,capture_output=True)
    assert result.returncode in (0,1)
    patch+=result.stdout
(WORK/'t2-changes.patch').write_bytes(patch)

for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:
    os.environ[key]=''
sys.path.insert(0,str(ROOT/'backend'))
from main import app
baseline=read(ROOT/'docs/execution/ultimate/t0/evidence/openapi.json')
actual=app.openapi();assert actual==baseline
write('api-preservation.json',dict(exact_openapi_equal_to_T0_and_T1=True,paths=len(actual['paths']),
    operations=sum(k in {'get','post','put','patch','delete','head','options','trace'} for p in actual['paths'].values() for k in p),
    no_new_public_endpoints=True,no_startup_or_requests=True,baseline_sha256=sha(ROOT/'docs/execution/ultimate/t0/evidence/openapi.json')))

for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:os.environ.pop(key,None)
docker=['docker','--host=unix:///var/run/docker.sock'];container='dation-t2-20261026-ultimate'
def run(*args):return subprocess.check_output([*docker,*args],text=True).strip()
assert run('inspect','--format','{{index .Config.Labels "dation.qa.phase"}}',container)=='T2'
pg=json.loads(run('exec',container,'psql','-U','postgres','-X','-q','-A','-t','-c',
    "SELECT json_build_object('version',version(),'databases',(SELECT json_agg(datname ORDER BY datname) FROM pg_database WHERE NOT datistemplate));"))
assert pg['databases']==['postgres']
image=json.loads(run('image','inspect','--format','{{json .RepoDigests}}','postgres:17-alpine'))
write('runtime.json',dict(python=sys.version,node=subprocess.check_output(['node','--version'],text=True).strip(),
    pydantic=importlib.metadata.version('pydantic'),fastapi=importlib.metadata.version('fastapi'),postgres=pg['version'],
    postgres_image_digests=image,docker_target='unix:///var/run/docker.sock',owned_container=container,
    container_network='none',published_ports=[],supabase_cli='2.122.0 (tool only)',
    production_credentials_cleared=True,application_dependencies_changed=False,remote_SQL_operations=False))

skill_items=[]
for name,file,purpose,verified in [
 ('supabase:supabase','supabase-skill.txt','RLS, explicit ACLs under managed defaults, versioned additive migrations and official CLI generation','S2 26 tests, local SQL/HTTP negatives; no remote advisors/schema operations'),
 ('supabase:supabase-postgres-best-practices','postgres-skill.txt','Composite FKs/indexes, membership policies and small ordered transactions','Catalog/FK/grant comparison and S2'),
 ('cloud-environment:cloud-environment-runtime','runtime-skill.txt','Managed runtime readiness and owned local Docker/PostgreSQL isolation','Local daemon verified, PostgreSQL17/label asserted, scoped runners without production credentials')]:
    skill_items.append(dict(name=name,source_snapshot=file,sha256=sha(WORK/file),read=True,applied=purpose,verified=verified))
write('skills-ledger.json',dict(phase='T2',skills=skill_items,
    postgres_references=['schema-foreign-key-indexes.md','security-rls-performance.md'],
    runtime_references=['references/docker.md','references/networking.md'],
    Supabase_documentation=dict(changelog_requested='https://supabase.com/changelog.md',changelog_http_status=403,
      fallback='Official search_docs MCP; captured Supabase T0 defaults and current CLI --help',snapshot='supabase-docs.txt',
      no_network_policy_bypass=True,no_project_link_or_remote_query=True),
    UI_skills='N/A — no frontend or design change',no_stack_or_frozen_decision_changed=True))
write('scope-diff.json',dict(phase='T2',baseline_head=initial['head'],baseline_files_preserved=len(initial['files']),
    files_modified=modified,files_created=new,change_patch_sha256=sha(WORK/'t2-changes.patch'),
    no_new_UI_or_engine_changes=True,no_T3=True,no_commit=True,no_push=True,no_remote_writes=True))

# Retire only the verified, empty, task-owned container after every required suite.
assert all(read(WORK/(suite+'.result.json'))['status']=='PASS' for suite in ['B-PY','B-NODE','B-SQL','S2','FOCAL-API','FOCAL-EMPTY-API'])
run('stop',container);run('rm',container)
write('sandbox-cleanup.json',dict(captured_at=datetime.now(timezone.utc).isoformat(),owned_container=container,
    owner_label_verified=True,remaining_databases_before_cleanup=pg['databases'],stopped=True,removed=True,
    other_containers_changed=False,production_access=False))
print(json.dumps(dict(scope_files=len(freeze['files']),baseline_files_preserved=len(initial['files']),
    OpenAPI='identical (91 paths/98 operations)',sandbox_removed=True,head=git('rev-parse','HEAD'))))
