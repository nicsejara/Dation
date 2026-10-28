"""Materialize T1 ledgers and preserve raw evidence. No production mutations."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import re
import shutil
import subprocess

ROOT=Path('/workspace/Dation')
WORK=Path('/workspace/work/dation-t1')
OUT=ROOT/'docs/execution/ultimate/t1'
EVIDENCE=OUT/'evidence'

def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

EVIDENCE.mkdir(parents=True,exist_ok=True)
for path in sorted(WORK.iterdir()):
    if path.is_file():
        # Keep the expanded focal proof produced by the final evidence script.
        target=EVIDENCE/('api-preservation.initial.json' if path.name=='api-preservation.json' else path.name)
        shutil.copyfile(path,target)
for name in ['dation-t1-qa.py','dation-t1-final-evidence.py','dation-t1-consolidate.py']:
    shutil.copyfile(Path('/tmp')/name,EVIDENCE/name)
shutil.copyfile(WORK/'skills-ledger.json',OUT/'skills-ledger.json')

now=datetime.now(timezone.utc)
final=[]
for name in ['U1','B-PY','B-NODE']:
    record=read(WORK/(name+'.result.json'))
    assert record['status']=='PASS' and record['exit_code']==0 and record['tests']>0
    assert record['failures']==record['errors']==record['skips']==0
    assert sha(EVIDENCE/(name+'.log'))==record['log_sha256']
    record['raw_result']='evidence/'+name+'.result.json'
    record['original_log_path']=record['log_path']
    record['log_path']='evidence/'+name+'.log'
    final.append(record)

not_run=[]
for name,count in [('B-BROWSER',251),('B-SQL',46),('B-E2E',86),('B-FOCUS',9)]:
    not_run.append({'suite':name,'status':'NOT RUN','tests':0,'failures':None,'errors':None,
                    'skips':None,'seconds':None,'baseline_T0_R2_tests':count,
                    'reason':'No active boundary changed; user explicitly excludes redundant broad suites'})
attempts=[]
for path in sorted(EVIDENCE.glob('U1.attempt*.log')):
    text=path.read_text()
    match=re.search(r'^Ran (\d+) tests in ([\d.]+)s',text,re.M)
    attempts.append({'log_path':str(path.relative_to(OUT)),'log_sha256':sha(path),
                     'tests':int(match.group(1)),'suite_reported_seconds':float(match.group(2)),
                     'failures':len(re.findall(r'^FAIL:',text,re.M)),
                     'errors':len(re.findall(r'^ERROR:',text,re.M)),
                     'status':'FAIL' if 'FAILED (' in text else 'PASS','final_candidate':False})
prior=[]
for path in sorted(EVIDENCE.glob('*.before-*.result.json')):
    record=read(path)
    record['raw_result']=str(path.relative_to(OUT))
    record['final_candidate']=False
    prior.append(record)
write(OUT/'test-ledger.json',{'phase':'T1','captured_at':now.isoformat(),
     'captured_at_America_Buenos_Aires':now.astimezone(ZoneInfo('America/Buenos_Aires')).isoformat(),
     'decision':'GO','required_suites':final,'other_baseline_suites':not_run,
     'U1_included_in_B_PY':True,'intermediate_U1_attempts':attempts,
     'prior_candidate_runs':prior,'failed_required_suites_at_close':0,
     'tests_removed_or_skipped':False})

commands=[{'kind':'required_final_suite','suite':row['suite'],'argv':row['command'],'cwd':row['cwd'],
           'exit_code':row['exit_code'],'result':row['raw_result'],'log':row['log_path']} for row in final]
commands += [
    {'kind':'suite_orchestration','argv':['/workspace/Dation/.venv/bin/python','-B','/tmp/dation-t1-qa.py'],
     'cwd':str(ROOT),'exit_code':0,'script':'evidence/dation-t1-qa.py','log':'evidence/qa-batch-final.log'},
    {'kind':'focal_preservation_and_budgets','argv':['/workspace/Dation/.venv/bin/python','-B','/tmp/dation-t1-final-evidence.py'],
     'cwd':str(ROOT),'exit_code':0,'script':'evidence/dation-t1-final-evidence.py',
     'results':['evidence/legacy-preservation.json','evidence/api-preservation.json','evidence/payload-budgets.json']},
    {'kind':'cross_process_determinism','argv':read(EVIDENCE/'cross-process-vectors.json')['command'],
     'cwd':str(ROOT/'backend'),'environment_overrides':[{'PYTHONHASHSEED':'1'},{'PYTHONHASHSEED':'2701'}],
     'exit_codes':[0,0],'result':'evidence/cross-process-vectors.json'},
    {'kind':'documentation_consolidation','argv':['python','/tmp/dation-t1-consolidate.py'],
     'cwd':str(ROOT),'script':'evidence/dation-t1-consolidate.py'},
    {'kind':'workspace_readonly','argv':['git','diff','--check'],'cwd':str(ROOT),'exit_code':0},
    {'kind':'workspace_readonly','argv':['git','status','--short','--branch'],'cwd':str(ROOT)},
    {'kind':'workspace_readonly','argv':['git','rev-parse','HEAD'],'cwd':str(ROOT)}]
write(OUT/'command-ledger.json',{'phase':'T1','captured_at':now.isoformat(),
     'scope':'Exact required runner argv and focal verification; no claim to be a transcript of every file read',
     'runtime':'evidence/runtime.json','commands':commands,
     'credential_environment':{'cleared_in_children':['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN',
             'LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN'],'PYTHONDONTWRITEBYTECODE':'1'},
     'network_database_browser_docker_operations':False,'new_dependencies_installed':False,
     'commit_push_deploy':False,'T2_executed':False})

initial=read(WORK/'initial-state.json')
freeze=read(WORK/'source-freeze.json')
status=git('status','--short','--branch')+'\n'
assert git('rev-parse','HEAD')==initial['head']
assert not git('diff','--cached','--name-only')
assert sorted(git('diff','--name-only').splitlines())==sorted(initial['existing_changed_paths'])
assert all(sha(ROOT/name)==digest for name,digest in freeze['files'].items())
assert all(sha(ROOT/name)==digest for name,digest in initial['preserve'].items())
check=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
assert check.returncode==0,(check.stdout,check.stderr)
write(OUT/'final-workspace.json',{'phase':'T1','captured_at':now.isoformat(),
     'captured_at_America_Buenos_Aires':now.astimezone(ZoneInfo('America/Buenos_Aires')).isoformat(),
     'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),
     'cached_origin_main':git('rev-parse','refs/remotes/origin/main'),
     'origin_ref_is_cached_not_a_new_remote_query':True,'git_status_short_branch':status,
     'tree_clean':False,'explanation':'Approved pending T0/R/R2 changes retained; T1 additive files untracked as authorized',
     'T1_preexisting_files_modified':[],'T1_source_artifact_test_files_created':list(freeze['files']),
     'preexisting_tracked_changes':initial['existing_changed_paths'],
     'staged_changes':[],'git_diff_check':{'exit_code':check.returncode,'stdout':check.stdout,'stderr':check.stderr},
     'baseline_artifacts_unchanged':248,'candidate_hashes_equal_final_QA':True,
     'commit_created':False,'push':False,'merge':False,'T2_executed':False,
     'migrations_created_in_T1':False,'database_operations':False,'infrastructure_changed':False,
     'deployment':False})

files=[ROOT/name for name in freeze['files']]
files += [path for path in OUT.rglob('*') if path.is_file() and path.name!='artifact-integrity.json']
write(OUT/'artifact-integrity.json',{'phase':'T1','captured_at':now.isoformat(),'decision':'GO',
     'excludes_self':True,'baseline_manifest_unchanged':True,
     'baseline_manifest_path':'docs/execution/ultimate/t0/remediation-r2/artifact-integrity.json',
     'baseline_manifest_sha256':initial['t0_r2_manifest_sha256'],
     'files':[{'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path)}
              for path in sorted(files)]})
print(json.dumps({'decision':'GO','source_files':len(freeze['files']),
                  'manifest_files':len(files),'head':git('rev-parse','HEAD'),
                  'baseline_preserved':248,'required_suites':[{'suite':r['suite'],'tests':r['tests'],'status':r['status']} for r in final]}))
