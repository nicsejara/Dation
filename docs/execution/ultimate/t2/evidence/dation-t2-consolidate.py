"""Create T2 report ledgers and manifest; preserve T0/T1 metadata unchanged."""
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib,json,re,shutil,subprocess

ROOT=Path('/workspace/Dation');WORK=Path('/workspace/work/dation-t2');OUT=ROOT/'docs/execution/ultimate/t2';E=OUT/'evidence'
E.mkdir(parents=True,exist_ok=True)
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

for path in sorted(WORK.iterdir()):
    if path.is_file():shutil.copyfile(path,E/path.name)
for path in sorted((WORK/'sql').rglob('*')):
    if path.is_file():
        target=E/'sql'/path.relative_to(WORK/'sql');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
for name in ['dation-t2-qa.py','dation-t2-empty-case-smoke.py','dation-t2-close-evidence.py','dation-t2-consolidate.py']:
    shutil.copyfile(Path('/tmp')/name,E/name)
shutil.copyfile(WORK/'skills-ledger.json',OUT/'skills-ledger.json')
now=datetime.now(timezone.utc)
final=[]
for suite in ['B-PY','B-NODE','B-SQL','S2','FOCAL-API','FOCAL-EMPTY-API']:
    row=read(WORK/(suite+'.result.json'))
    assert row['status']=='PASS' and row['tests']>0 and row['failures']==row['errors']==row['skips']==0
    row['raw_result']='evidence/'+suite+'.result.json';row['log_path']='evidence/'+suite+'.log'
    row['log_sha256']=sha(E/(suite+'.log'));final.append(row)
notrun=[{'suite':s,'status':'NOT RUN','tests':0,'failures':None,'errors':None,'skips':None,'seconds':None,
         'baseline_T0_R2_tests':n,'reason':'Shared reader boundaries checked focally with SQL and real HTTP; no frontend changes'}
        for s,n in [('B-BROWSER',251),('B-E2E',86),('B-FOCUS',9)]]
write(OUT/'test-ledger.json',dict(phase='T2',captured_at=now.isoformat(),
    captured_at_America_Buenos_Aires=now.astimezone(ZoneInfo('America/Buenos_Aires')).isoformat(),
    final_suites=final,not_run=notrun,unique_Python_tests=456,unique_SQL_tests=72,S2_included_in_B_SQL=True,
    U1_tests_retained_in_B_PY=61,tests_removed_or_skipped=False,
    earlier_runs=[dict(log='evidence/readers.attempt1.log',status='PASS',tests=12,final_candidate=False),
                  dict(log='evidence/S2.attempt1.log',status='PASS',tests=24,final_candidate=False)]))
commands=[dict(kind='required_or_focal_final_suite',suite=row['suite'],argv=row['command'],cwd=row['cwd'],
               PYTHONPATH=row.get('PYTHONPATH'),exit_code=0,log=row['log_path'],result=row['raw_result']) for row in final]
commands += [
 dict(kind='checkpoint',script='evidence/initial-state.json',patch='evidence/post-t1-tracked.patch',no_commit=True),
 dict(kind='official_CLI_migration_creation',argv=['npx','--offline','--yes','supabase@2.122.0','migration','new','ultimate_foundation'],cwd=str(ROOT),exit_code=0),
 dict(kind='official_CLI_migration_creation',argv=['npx','--offline','--yes','supabase@2.122.0','migration','new','ultimate_result_artifacts'],cwd=str(ROOT),exit_code=0),
 dict(kind='suite_orchestration',argv=['python','-B','/tmp/dation-t2-qa.py'],cwd=str(ROOT),exit_code=0,script='evidence/dation-t2-qa.py',log='evidence/qa-batch.log'),
 dict(kind='focal_proof_and_cleanup',argv=['/workspace/Dation/.venv/bin/python','-B','/tmp/dation-t2-close-evidence.py'],cwd=str(ROOT),exit_code=0,script='evidence/dation-t2-close-evidence.py'),
 dict(kind='read_only_git',argv=['git','diff','--check'],cwd=str(ROOT),exit_code=0),
 dict(kind='read_only_git',argv=['git','status','--short','--branch'],cwd=str(ROOT)),
 dict(kind='read_only_git',argv=['git','rev-parse','HEAD'],cwd=str(ROOT))]
write(OUT/'command-ledger.json',dict(phase='T2',captured_at=now.isoformat(),commands=commands,
    scope='Exact final runner argv plus migration/checkpoint/evidence operations; not a transcript of every file read',
    credential_environment={'cleared_in_children':['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN'],
     'PYTHONDONTWRITEBYTECODE':'1','DATION_SQL_TEST_CONTAINER':'dation-t2-20261026-ultimate'},
    Docker_selector='explicit local socket; inherited endpoint/context/TLS selectors cleared',
    no_remote_database_operations=True,no_commit_push_deploy=True,T3_executed=False))

initial=read(WORK/'initial-state.json');freeze=read(WORK/'source-freeze.json');scope=read(WORK/'scope-diff.json')
assert all(sha(ROOT/n)==v['sha256'] for n,v in initial['files'].items())
assert all(sha(ROOT/n)==digest for n,digest in freeze['files'].items())
assert git('rev-parse','HEAD')==initial['head'] and not git('diff','--cached','--name-only')
check=subprocess.run(['git','diff','--check'],cwd=ROOT,text=True,capture_output=True);assert check.returncode==0
write(OUT/'final-workspace.json',dict(phase='T2',captured_at=now.isoformat(),branch=git('branch','--show-current'),
    head=git('rev-parse','HEAD'),cached_origin_main=git('rev-parse','refs/remotes/origin/main'),origin_is_cached_not_fresh_remote_query=True,
    git_status_short_branch=git('status','--short','--branch')+'\n',tree_clean=False,
    explanation='Approved post-T1 pending changes retained; T2 changes remain unstaged as requested',
    baseline_files_preserved=343,T2_modified_files=scope['files_modified'],T2_new_files=scope['files_created'],
    source_hashes_match_final_QA=True,staged_changes=[],git_diff_check_exit_code=check.returncode,
    commit_created=False,push=False,merge=False,deploy=False,production_database_changes=False,
    T3_executed=False,sandbox_cleanup=read(WORK/'sandbox-cleanup.json')))

paths=[ROOT/n for n in freeze['files']]+[p for p in OUT.rglob('*') if p.is_file() and p.name!='artifact-integrity.json']
write(OUT/'artifact-integrity.json',dict(phase='T2',captured_at=now.isoformat(),decision='GO',excludes_self=True,
    post_T1_manifest_path='docs/execution/ultimate/t1/artifact-integrity.json',
    post_T1_manifest_sha256=initial['T1_manifest_sha256'],
    files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(paths)]))
print(json.dumps(dict(manifest_files=len(paths),source_files=len(freeze['files']),baseline_preserved=343,
    HEAD=git('rev-parse','HEAD'),required_suites='PASS',T3_executed=False)))
