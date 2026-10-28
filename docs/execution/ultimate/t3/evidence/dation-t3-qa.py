"""Frozen T3 candidate: required suites, plus scoped legacy consumers."""
from datetime import datetime,timezone
from pathlib import Path
import difflib,glob,hashlib,json,os,re,subprocess,time
ROOT=Path('/workspace/Dation');BACKEND=ROOT/'backend';OUT=Path('/workspace/work/dation-t3');BASE=OUT/'post-t2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
initial=json.loads((OUT/'initial-state.json').read_text())
pending=subprocess.check_output(['git','ls-files','--modified','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
candidate={};patch=[]
for name in sorted(set(pending)-{''}):
 if not name.startswith(('backend/','supabase/')):continue
 p=ROOT/name
 if name in initial['files']:
  old=(BASE/name).read_bytes()
 else:
  result=subprocess.run(['git','show','HEAD:'+name],cwd=ROOT,capture_output=True)
  old=result.stdout if result.returncode==0 else None
 if old==p.read_bytes():continue
 candidate[name]={'bytes':p.stat().st_size,'sha256':sha(p),'baseline_sha256':hashlib.sha256(old).hexdigest() if old is not None else None,'baseline':'post-T2 checkpoint' if name in initial['files'] else 'HEAD' if old is not None else 'new T3 file'}
 patch.extend(difflib.unified_diff((old or b'').decode().splitlines(True),p.read_text().splitlines(True),fromfile='post-T2/'+name,tofile='T3/'+name))
(OUT/'candidate.json').write_text(json.dumps({'phase':'T3','head':initial['head'],'frozen_at':datetime.now(timezone.utc).isoformat(),'files':candidate},indent=2)+'\n')
(OUT/'t3-changes.patch').write_text(''.join(patch))
env=os.environ.copy()
for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[key]=''
for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
env.update(PYTHONDONTWRITEBYTECODE='1',DATION_SQL_TEST_CONTAINER='dation-t3-20261026-ultimate',DATION_T3_BROWSER_ARTIFACTS=str(OUT/'browser'),DATION_E2E_ARTIFACTS=str(OUT/'legacy-api'))
PY=str(ROOT/'.venv/bin/python');BROWSER=str(BACKEND/'.browser-venv/bin/python')
commands={
 'B-PY':[PY,'-B','-m','unittest','discover','-s','tests','-v'],
 'B-NODE':['node','--test',*sorted(glob.glob('tests/test_*.js',root_dir=BACKEND)),*sorted(glob.glob('tests/test_*.mjs',root_dir=BACKEND))],
 'S3':[PY,'-B','-m','unittest','test_ultimate_case_models','-v'],
 'W3':[BROWSER,'-B','-m','unittest','test_ultimate_case_setup','-v'],
 'FOCAL-LEGACY-API':[PY,'-B','-m','unittest','test_decision_center.DecisionCenterTests.test_01_case_library_labels_pagination_identity_and_isolation','test_optimized_responsibilities.OptimizedResponsibilityTests.test_split_roles_reload_independent_node_assignments_and_actual_approval','test_optimized_responsibilities.OptimizedResponsibilityTests.test_archive_persists_reloads_and_preserves_case_history_and_assignments','-v'],
 'FOCAL-LEGACY-BROWSER':[BROWSER,'-B','-m','unittest','test_navigation.NavigationTests.test_new_decision_goes_to_empty_data_without_losing_existing_case','test_navigation.NavigationTests.test_approved_assignment_continues_directly_to_scheduling_configuration','test_navigation.NavigationTests.test_map_selector_switches_case_data_progress_url_and_restores_cancel_focus','-v'],
}
for name,command in commands.items():
 if os.environ.get('DATION_T3_SUITES') and name not in os.environ['DATION_T3_SUITES'].split(','):continue
 child=env.copy()
 if name=='S3':child['PYTHONPATH']='tests/integration'
 if name=='W3' or name=='FOCAL-LEGACY-BROWSER':child['PYTHONPATH']='tests/browser'
 if name=='FOCAL-LEGACY-API':child['PYTHONPATH']='tests/e2e'
 started=datetime.now(timezone.utc).isoformat();begin=time.monotonic();print(json.dumps({'suite':name,'state':'RUNNING','started_at':started}),flush=True)
 with (OUT/(name+'.log')).open('w') as log:result=subprocess.run(command,cwd=BACKEND,env=child,text=True,stdout=log,stderr=subprocess.STDOUT)
 data=(OUT/(name+'.log')).read_text()
 data=re.sub(r'(?im)^.*(?:cookie:|authorization:|apikey:).*$','    [ephemeral fixture auth headers redacted]',data)
 (OUT/(name+'.log')).write_text(data)
 if name=='B-NODE':
  def count(label):
   match=re.search(r'^(?:# |ℹ )'+label+r' (\d+)$',data,re.M);return int(match.group(1)) if match else 0
  tests=count('tests');failures=count('fail');skips=count('skipped');errors=0
 else:
  counts=re.findall(r'^Ran (\d+) tests? in ([\d.]+)s',data,re.M);tests=int(counts[-1][0]) if counts else 0
  failures=len(re.findall(r'^FAIL:',data,re.M));errors=len(re.findall(r'^ERROR:',data,re.M));skips=len(re.findall(r'^test_.* \.\.\. skipped',data,re.M))
 status='PASS' if result.returncode==0 and tests and failures==errors==skips==0 else 'FAIL'
 record=dict(suite=name,status=status,tests=tests,failures=failures,errors=errors,skips=skips,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),seconds=round(time.monotonic()-begin,3),cwd=str(BACKEND),command=command,exit_code=result.returncode,production_credentials_cleared=True,PYTHONPATH=child.get('PYTHONPATH'),log_sha256=sha(OUT/(name+'.log')))
 (OUT/(name+'.result.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
 if status!='PASS':raise SystemExit(1)
 changed=[name for name,value in candidate.items() if sha(ROOT/name)!=value['sha256']]
 if changed:raise RuntimeError('Candidate changed during QA: '+str(changed))
print(json.dumps({'candidate_files':len(candidate),'frozen_candidate_verified':True,'T4_executed':False}),flush=True)
