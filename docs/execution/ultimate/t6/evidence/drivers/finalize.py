"""Consolidate T6 evidence and certify scope/preservation without git writes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess

R=Path('/workspace/Dation');W=Path('/workspace/work/dation-t6')
O=R/'docs/execution/ultimate/t6';E=O/'evidence';E.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def git(*args):return subprocess.check_output(['git',*args],cwd=R)

initial=read(W/'initial-state.json');candidate=read(W/'candidate.json')
assert len(candidate['files'])==8
for n,v in candidate['files'].items():assert sha(R/n)==v['sha256'],n
assert git('rev-parse','HEAD').decode().strip()==initial['head']=='ef997235a30251fbf7ae53690ed738092ee973d8'
assert git('branch','--show-current').decode().strip()==initial['branch']=='main'
assert not git('diff','--cached','--name-only')
subprocess.run(['git','diff','--check'],cwd=R,check=True)
extended=[];same=[]
for n,v in initial['files'].items():
 assert sha(W/'post-t5'/n)==v['sha256'],n
 assert (R/n).exists(),n
 if sha(R/n)==v['sha256']:same.append(n)
 else:
  assert n in candidate['files'],n
  extended.append(n);copy(W/'post-t5'/n,E/'post-t5'/n)
assert len(same)==790 and extended==['backend/app/results/registry.py']
assert hashlib.sha256(json.dumps(initial['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==initial['checkpoint_sha256']
t5=R/'docs/execution/ultimate/t5/artifact-integrity.json'
assert sha(t5)==initial['T5_manifest_sha256']
for v in read(t5)['files']:assert sha(R/v['path'])==v['sha256'],v['path']
assert len(read(t5)['files'])==172
results=[]
for name,expected in [('B-PY',568),('B-NODE',137),('U6',47)]:
 result=read(W/(name+'.result.json'))
 assert result['status']=='PASS' and result['tests']==expected
 assert result['failures']==result['errors']==result['skips']==result['exit_code']==0
 assert sha(W/(name+'.log'))==result['log_sha256']
 for suffix in ['.log','.result.json']:copy(W/(name+suffix),E/(name+suffix))
 result.update(log='evidence/'+name+'.log',raw_result='evidence/'+name+'.result.json')
 results.append(result)
u6_lines=[l for l in (W/'B-PY.log').read_text().splitlines() if '(test_transport_plan_core.' in l and l.endswith(' ... ok')]
assert len(u6_lines)==47
for n in ['initial-state.json','candidate.json','T6-user-request.txt','post-t5-tracked.patch','t6-changes.patch','qa-final-batch.log']:
 copy(W/n,E/n)
for n in ['U6-first.log','U6-second.log']:copy(W/n,E/'attempts'/n)
for p in (W/'drivers').glob('*.py'):copy(p,E/'drivers'/p.name)
runtime_src=R/'docs/execution/ultimate/t5/evidence/skills/runtime-skill.txt'
copy(runtime_src,E/'skills/runtime-skill.txt')
local_skills=[str(p.relative_to(R)) for p in sorted((R/'.agents/skills').glob('*/SKILL.md'))]
write(O/'skills-ledger.json',{
 'phase':'T6','available_local_skill_paths':local_skills,
 'used':[{'name':'cloud-environment:cloud-environment-runtime','package':'c5/cloud-environment-runtime',
 'source':'skill://plugin_connector_1p_c5b7d5df5d7081918f2c4be5a633ed5d/cloud-environment-runtime/SKILL.md',
 'read_this_phase':True,'source_snapshot':'evidence/skills/runtime-skill.txt','sha256':sha(runtime_src),
 'applied':['environment status/current observations','runner availability','network policy inspection','local tests with production credentials cleared'],
 'verified':['connected/running','Python3.13.5 OR-Tools9.15.6755 Node24.19.0','B-PY/B-NODE/U6 PASS']}],
 'not_available':['dedicated Python skill','dedicated optimization skill','dedicated Python testing skill'],
 'not_applicable':[{'category':'UI/design','reason':'No frontend changes or design scope.'},{'category':'Supabase/SQL/Docker','reason':'No DB, migrations, containers or production connections used.'}],
 'new_tools_or_dependencies_installed':False,'subagents_used':False,'policy_precedence':'Approved architecture and invariants before Skill recommendations'})
write(O/'preservation.json',{
 'phase':'T6','baseline_pending_and_manifest_files':791,'checkpoint_bytes':40360059,
 'checkpoint_sha256':initial['checkpoint_sha256'],'checkpoint_kind':initial['checkpoint_kind'],
 'checkpoint_copies_verified':791,'current_baseline_files_unchanged':790,'intentionally_extended':extended,
 'registry_preimage':'evidence/post-t5/backend/app/results/registry.py',
 'T5_manifest_unchanged':True,'T5_manifest_entries_verified':172,
 'legacy_assignment_dispatch_scheduling_files_unchanged':True,
 'baseline_work_discarded':False,'git_history_changed':False})
created=[n for n,v in candidate['files'].items() if v['baseline']=='new T6 file']
modified=[n for n in candidate['files'] if n not in created]
write(O/'scope-diff.json',{'phase':'T6','baseline_head':initial['head'],'comparison':'Immediate post-T5 checkpoint',
 'source_files':8,'created':created,'modified':modified,'files':candidate['files'],
 'frontend_changes':False,'legacy_engine_changes':False,'database_changes':False,'production_changes':False,
 'public_capability_changes':False,'T7_executed':False})
write(O/'test-ledger.json',{'phase':'T6','suites':results,'U6_included_in_B_PY':{'tests':47,'lines':u6_lines},
 'independent_oracles':[{'name':'finite external non-split placements','cases':108,'solver_helpers_used':False,'scope':'equal whole-order quantities to compare structural fractional coverage'},
 {'name':'day/unit enumeration','cases':4,'CP_SAT_or_TransitEstimator_used_by_oracle':False}],
 'intermediate_tests':[{'tests':41,'log':'evidence/attempts/U6-first.log'},{'tests':45,'log':'evidence/attempts/U6-second.log'}],
 'not_run':[{'suite':'Browser/E2E/SQL complete','reason':'No frontend, DB, API, worker, admission or publication changes; mandatory suites and changed boundary covered.'},{'suite':'T0-T5 rerun','reason':'Approved immediate T5 baseline; standard B-PY/B-NODE required by T6 still executed.'},{'suite':'T7 and later','reason':'Not authorized.'}],
 'all_suites_match_frozen_candidate':True,'zero_failures_errors_skips':True})
write(O/'command-ledger.json',{'phase':'T6','suites':[{k:v[k] for k in ['suite','command','cwd','started_at','finished_at','seconds','exit_code']} for v in results],
 'QA_driver':'evidence/drivers/qa.py','integrity_driver':'evidence/drivers/finalize.py',
 'production_credentials_cleared':['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN'],
 'runtime':{'python':'3.13.5','ortools':'9.15.6755','node':'24.19.0','cloud_observations_current':True,'cloud_connectivity':'connected','cloud_observed_phase':'running','network_policy':'restricted/enforced','VPN_configured':False},
 'git_diff_check':'PASS','checkpoint_commit_created':False,'no_push_deploy_or_production_access':True})

scan_patterns=[re.compile(rb'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'),re.compile(rb'\bsbp_[A-Za-z0-9]{30,}'),re.compile(rb'\bsk-proj-[A-Za-z0-9_-]{30,}')]
findings=[str(p.relative_to(R)) for p in O.rglob('*') if p.is_file() and any(pattern.search(p.read_bytes()) for pattern in scan_patterns)]
assert not findings,findings
manifest_path=O/'artifact-integrity.json';state_path=E/'final-state.json'
if not manifest_path.exists():write(manifest_path,{'phase':'T6','finalizing':True})
if not state_path.exists():write(state_path,{'phase':'T6','finalizing':True})
status=git('status','--porcelain=v1','-z','--untracked-files=all').decode()
paths=[entry[3:] for entry in status.split('\0') if entry]
unknown=[p for p in paths if p not in initial['files'] and p not in candidate['files'] and not p.startswith('docs/execution/ultimate/t6/')]
assert not unknown,unknown
write(state_path,{'phase':'T6','captured_at':datetime.now(timezone.utc).isoformat(),
 'HEAD':initial['head'],'branch':'main','git_status_short_branch':git('status','--short','--branch','--untracked-files=all').decode(),
 'working_tree_clean':False,'staged_paths':[],'source_files':8,'created':7,'modified':1,
 'post_T5_current_unchanged':790,'post_T5_intentionally_extended':extended,'T5_manifest_entries_verified':172,
 'git_diff_check':'PASS','out_of_scope_paths_added':[],'secret_scan_findings':[],
 'T7_executed':False,'commit_created':False,'push_executed':False,'deploy_executed':False,
 'productive_runs_artifacts_packages_created':False,'infrastructure_changed':False})
all_files=set(candidate['files'])|{str(p.relative_to(R)) for p in O.rglob('*') if p.is_file() and p!=manifest_path}
entries=[{'path':n,'bytes':(R/n).stat().st_size,'sha256':sha(R/n)} for n in sorted(all_files)]
write(manifest_path,{'phase':'T6','head':initial['head'],'captured_at':datetime.now(timezone.utc).isoformat(),
 'decision':'GO','excludes_self':True,'source_files':8,'files':entries})
for v in entries:assert sha(R/v['path'])==v['sha256'],v['path']
report=O/'t6-execution-report.md'
for target in re.findall(r'\]\(([^)]+)\)',report.read_text()):
 if '://' not in target and not target.startswith('#'):
  assert (report.parent/target.split('#')[0]).resolve().exists(),target
assert report.read_text().count('**GO — T6 completado. T7 puede ser solicitado.**')==1
print(json.dumps({'result':'PASS','head':initial['head'],'source_files':8,'created':7,'modified':1,
 'checkpoint_files_verified':791,'T5_manifest_entries_verified':172,'manifest_entries':len(entries),
 'suites':{v['suite']:v['tests'] for v in results},'staged_paths':[],'T7_executed':False},ensure_ascii=False))
