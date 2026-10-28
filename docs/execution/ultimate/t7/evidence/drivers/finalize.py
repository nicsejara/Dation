"""Preserve T7 evidence and verify the post-T6 delta; never mutate git."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess
R=Path('/workspace/Dation');W=Path('/workspace/work/dation-t7');O=R/'docs/execution/ultimate/t7';E=O/'evidence';E.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
initial=read(W/'initial-state.json');candidate=read(W/'candidate.json')
assert len(candidate['files'])==16
assert git('rev-parse','HEAD').decode().strip()==initial['head']=='ef997235a30251fbf7ae53690ed738092ee973d8'
assert git('branch','--show-current').decode().strip()==initial['branch']=='main'
assert not git('diff','--cached','--name-only')
subprocess.run(['git','diff','--check'],cwd=R,check=True)
for n,v in candidate['files'].items():assert sha(R/n)==v['sha256'],n
same=[];changed=[]
for n,v in initial['files'].items():
 assert sha(W/'post-t6'/n)==v['sha256'],n
 assert (R/n).exists(),n
 if sha(R/n)==v['sha256']:same.append(n)
 else:
  assert n in candidate['files'],n
  changed.append(n);copy(W/'post-t6'/n,E/'post-t6'/n)
assert len(same)==782 and len(changed)==4
assert hashlib.sha256(json.dumps(initial['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==initial['checkpoint_sha256']
t6=R/'docs/execution/ultimate/t6/artifact-integrity.json'
assert sha(t6)==initial['T6_manifest_sha256']
resolved=[]
for entry in read(t6)['files']:
 name=entry['path'];p=E/'post-t6'/name if name in changed else R/name
 assert sha(p)==entry['sha256'],name
 resolved.append({'path':name,'resolved_from':str(p.relative_to(R)),'sha256_verified':True})
assert len(resolved)==33
results=[]
for name,expected in [('B-PY',614),('B-NODE',137),('U7',46)]:
 result=read(W/(name+'.result.json'))
 assert result['status']=='PASS' and result['tests']==expected
 assert result['failures']==result['errors']==result['skips']==result['exit_code']==0
 assert sha(W/(name+'.log'))==result['log_sha256']
 for suffix in ['.log','.result.json']:copy(W/(name+suffix),E/(name+suffix))
 result.update(log='evidence/'+name+'.log',raw_result='evidence/'+name+'.result.json');results.append(result)
python_log=(W/'B-PY.log').read_text().splitlines()
u6=[line for line in python_log if '(test_transport_plan_core.' in line and line.endswith(' ... ok')]
u7=[line for line in python_log if ('(test_transport_plan_policies.' in line or '(test_transport_result_package.' in line) and line.endswith(' ... ok')]
assert len(u6)==47 and len(u7)==46
for n in ['initial-state.json','candidate.json','T7-user-request.txt','post-t6-tracked.patch','t7-changes.patch','qa-final-batch.log']:copy(W/n,E/n)
for n in ['U7-policies-first.log','U7-package-first.log','U7-second.log','U7-third.log']:copy(W/n,E/'attempts'/n)
for p in (W/'drivers').glob('*.py'):copy(p,E/'drivers'/p.name)
skill=R/'docs/execution/ultimate/t6/evidence/skills/runtime-skill.txt';copy(skill,E/'skills/runtime-skill.txt')
write(O/'skills-ledger.json',{'phase':'T7','available_local_skills':[str(p.relative_to(R)) for p in sorted((R/'.agents/skills').glob('*/SKILL.md'))],
 'used':[{'name':'cloud-environment:cloud-environment-runtime','package':'c5/cloud-environment-runtime','read_this_phase':True,
 'source':'skill://plugin_connector_1p_c5b7d5df5d7081918f2c4be5a633ed5d/cloud-environment-runtime/SKILL.md',
 'snapshot':'evidence/skills/runtime-skill.txt','sha256':sha(skill),'applied':['current managed environment status','local runners','production-credential-cleared QA'],
 'verified':['running/connected with current observations','Python3.13.5 OR-Tools9.15.6755 Node24.19.0','three mandatory suites PASS']}],
 'not_available':['dedicated Python/domain skill','dedicated optimization skill','dedicated Python testing skill'],
 'not_applicable':[{'category':'design/UI','reason':'No frontend changes.'},{'category':'Supabase/Docker','reason':'No schema, SQL, remote project or new container used.'}],
 'tools_installed':False,'dependencies_installed':False,'subagents_used':False,'precedence':'Approved contracts and invariants before Skill guidance'})
created=[n for n,v in candidate['files'].items() if v['baseline']=='new T7 file'];modified=[n for n in candidate['files'] if n not in created]
assert len(created)==12 and len(modified)==4 and set(modified)==set(changed)
write(O/'scope-diff.json',{'phase':'T7','baseline_head':initial['head'],'comparison':'Immediate post-T6 checkpoint','source_files':16,
 'created':created,'modified':modified,'files':candidate['files'],'frontend_changes':False,'legacy_engine_changes':False,
 'SQL_or_infrastructure_changes':False,'public_admission_changes':False,'T8_executed':False})
write(O/'preservation.json',{'phase':'T7','baseline_inventory_files':786,'baseline_inventory_bytes':41092786,
 'checkpoint_kind':initial['checkpoint_kind'],'checkpoint_sha256':initial['checkpoint_sha256'],'copies_verified':786,
 'current_files_unchanged':782,'intentionally_extended':changed,'T6_manifest_unchanged':True,'T6_entries_verified':33,'T6_resolution':resolved,
 'legacy_assignment_scheduling_dispatch_exports_comparative_and_frontend_unchanged':True,
 'no_reset_clean_discard_checkout_staging_commit_or_history_change':True})
write(O/'test-ledger.json',{'phase':'T7','suites':results,'U6_included_in_B_PY':{'tests':47,'log_lines':u6},
 'U7_included_in_B_PY':{'tests':46,'policy_module_tests':20,'package_module_tests':26,'log_lines':u7},
 'oracles':[{'name':'B/C/N literal independent price rules','production_helper_used':False},{'name':'finite external placements with varied quantities/prices','cases':9,'production_objective_used':False}],
 'R1_R8':{key:'PASS' for key in ['R1','R2','R3','R4','R5','R6','R7','R8']},
 'intermediate_runs':[{'log':'evidence/attempts/U7-policies-first.log','tests':18},{'log':'evidence/attempts/U7-package-first.log','tests':23},{'log':'evidence/attempts/U7-second.log','tests':44},{'log':'evidence/attempts/U7-third.log','tests':45}],
 'not_run':[{'suite':'Browser/E2E/SQL full','reason':'No changed frontend/API/worker/DB/publication; scoped mandatory suites cover the affected boundary.'},{'suite':'T0-T6 as phases','reason':'Approved baseline; U6 still covered by mandatory B-PY.'},{'suite':'T8 and later','reason':'Explicitly unauthorized.'}],
 'frozen_candidate_verified':True,'zero_failures_errors_skips':True})
write(O/'command-ledger.json',{'phase':'T7','suites':[{k:r[k] for k in ['suite','cwd','command','started_at','finished_at','seconds','exit_code']} for r in results],
 'QA_driver':'evidence/drivers/qa.py','integrity_driver':'evidence/drivers/finalize.py',
 'production_credentials_cleared':['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN'],
 'runtime':{'python':'3.13.5','ortools':'9.15.6755','node':'24.19.0','cloud_observations_current':True,'cloud_connectivity':'connected','cloud_observed_phase':'running'},
 'git_diff_check':'PASS','local_checkpoint_commit':False,'no_push_deploy_or_production_access':True})
patterns=[re.compile(rb'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'),re.compile(rb'\bsbp_[A-Za-z0-9]{30,}'),re.compile(rb'\bsk-proj-[A-Za-z0-9_-]{30,}')]
findings=[str(p.relative_to(R)) for p in O.rglob('*') if p.is_file() and any(pattern.search(p.read_bytes()) for pattern in patterns)]
assert not findings,findings
manifest=O/'artifact-integrity.json';state=E/'final-state.json'
if not manifest.exists():write(manifest,{'phase':'T7','finalizing':True})
if not state.exists():write(state,{'phase':'T7','finalizing':True})
status=git('status','--porcelain=v1','-z','--untracked-files=all').decode();paths=[entry[3:] for entry in status.split('\0') if entry]
unexpected=[n for n in paths if n not in initial['files'] and n not in candidate['files'] and not n.startswith('docs/execution/ultimate/t7/')]
assert not unexpected,unexpected
write(state,{'phase':'T7','captured_at':datetime.now(timezone.utc).isoformat(),'HEAD':initial['head'],'branch':'main',
 'git_status_short_branch':git('status','--short','--branch','--untracked-files=all').decode(),'working_tree_clean':False,'staged_paths':[],
 'source_files':16,'created':12,'modified':4,'post_T6_current_unchanged':782,'post_T6_extended':changed,'T6_manifest_entries_resolved':33,
 'git_diff_check':'PASS','out_of_scope_paths_added':[],'credential_scan_findings':[],'T8_executed':False,
 'commit_created':False,'push_executed':False,'deploy_executed':False,'production_modified':False,
 'durable_runs_artifacts_packages_published':False,'public_capabilities_changed':False,'infrastructure_changed':False})
names=set(candidate['files'])|{str(p.relative_to(R)) for p in O.rglob('*') if p.is_file() and p!=manifest}
entries=[{'path':n,'bytes':(R/n).stat().st_size,'sha256':sha(R/n)} for n in sorted(names)]
write(manifest,{'phase':'T7','head':initial['head'],'captured_at':datetime.now(timezone.utc).isoformat(),'decision':'GO','excludes_self':True,'source_files':16,'files':entries})
for entry in entries:assert sha(R/entry['path'])==entry['sha256'],entry['path']
report=O/'t7-execution-report.md'
for target in re.findall(r'\]\(([^)]+)\)',report.read_text()):
 if '://' not in target and not target.startswith('#'):assert (report.parent/target.split('#')[0]).resolve().exists(),target
assert report.read_text().count('**GO — T7 completado. T8 puede ser solicitado.**')==1
print(json.dumps({'result':'PASS','HEAD':initial['head'],'branch':'main','source_files':16,'created':12,'modified':4,
 'checkpoint_copies_verified':786,'T6_entries_resolved':33,'manifest_entries':len(entries),
 'suites':{r['suite']:r['tests'] for r in results},'staged_paths':[],'T8_executed':False},ensure_ascii=False))
