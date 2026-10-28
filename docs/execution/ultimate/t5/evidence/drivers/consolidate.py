"""Preserve final T5 evidence and historical baselines, without git mutations."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess
R=Path('/workspace/Dation');W=Path('/workspace/work/dation-t5');O=R/'docs/execution/ultimate/t5';E=O/'evidence';E.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
initial=json.loads((W/'initial-state.json').read_text());candidate=json.loads((W/'candidate.json').read_text());recovery=json.loads((W/'recovery-verification.json').read_text())
assert len(candidate['files'])==29 and all(sha(R/n)==v['sha256'] for n,v in candidate['files'].items())
names=['B-PY','B-NODE','S5','W5','B-FOCUS','FOCAL-CASE-CREATE']
results=[json.loads((W/(n+'.result.json')).read_text()) for n in names]
assert [x['tests'] for x in results]==[521,137,19,10,9,1]
assert all(x['status']=='PASS' and x['failures']==x['errors']==x['skips']==x['exit_code']==0 for x in results)
for name,data in zip(names,results):
 assert sha(W/(name+'.log'))==data['log_sha256']
 for suffix in ['.log','.result.json']:copy(W/(name+suffix),E/(name+suffix))
for name in ['T5-user-request.txt','T5-resume-request.txt','initial-state.json','recovery-verification.json','post-t4-tracked.patch','candidate.json','candidate-before-completion-label.json','t5-changes.patch','U5-first.log','before-visual.log','cli-version.log','cli-migration-help.log','qa-final-batch.log','qa-final-w5.log','qa-reuse.json','schema-boundary.json','schema-boundary.log','visual-parity.log','legacy-map-parity.log','cleanup.json']:
 copy(W/name,E/name)
for folder in ['pre-stop','visual-before','visual-parity','legacy-map-parity','browser','setup-focal','drivers','skills']:
 if (W/folder).exists():shutil.copytree(W/folder,E/folder,dirs_exist_ok=True)
attempts=E/'attempts';attempts.mkdir(exist_ok=True)
for path in W.glob('*.log'):
 if path.name not in {n+'.log' for n in names} and path.name not in ['U5-first.log','before-visual.log','cli-version.log','cli-migration-help.log','qa-final-batch.log','qa-final-w5.log','schema-boundary.log','visual-parity.log','legacy-map-parity.log']:
  copy(path,attempts/path.name)
shutil.copytree(W/'attempts',attempts,dirs_exist_ok=True)
changed=[];same=[]
for name,old in initial['files'].items():
 assert sha(W/'post-t4'/name)==old['sha256'],name
 if sha(R/name)==old['sha256']:same.append(name)
 else:
  assert name in candidate['files'],name
  changed.append(name);copy(W/'post-t4'/name,E/'post-t4'/name)
assert len(changed)==9 and len(same)==618,(changed,len(same))
modified=[];created=[]
for name,value in candidate['files'].items():
 if value['baseline']=='new T5 file':created.append(name)
 else:
  modified.append(name)
  if value['baseline']=='HEAD':
   p=E/'post-t4'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show','HEAD:'+name],cwd=R));assert sha(p)==value['baseline_sha256']
assert len(created)==15 and len(modified)==14
resolved=[];manifest=R/'docs/execution/ultimate/t4/artifact-integrity.json';assert sha(manifest)==initial['T4_manifest_sha256']
for value in json.loads(manifest.read_text())['files']:
 name=value['path'];p=E/'post-t4'/name if name in changed else R/name
 assert sha(p)==value['sha256'],name
 resolved.append({'path':name,'sha256_verified':True,'resolved_from':str(p.relative_to(R))})
assert len(resolved)==147
pre_same=[];pre_extended=[]
for name,value in recovery['pre_stop_T5_files'].items():
 assert sha(E/'pre-stop'/name)==value['sha256']
 (pre_same if sha(R/name)==value['sha256'] else pre_extended).append(name)
assert len(pre_same)==6 and len(pre_extended)==2,(pre_same,pre_extended)
write(O/'preservation.json',{'phase':'T5','baseline_pending_files':627,'checkpoint_copies_verified':627,'unchanged_current_baseline_files':618,
 'intentionally_extended_baseline_files':changed,'historical_T4_manifest_unchanged':True,'historical_T4_entries_verified':147,'T4_resolution':resolved,
 'pre_STOP_inventory_verified':8,'pre_STOP_files_unchanged':pre_same,'pre_STOP_files_extended_after_recovery':pre_extended,
 'reason_for_extensions':{'backend/app/services/decision_graph_service.py':'Shared callers, actors/history count integration; existing resolver reused.',
 'supabase/migrations/20261027033128_ultimate_decision_graph.sql':'S5 found error_message column mismatch; completed read-only metadata/cohort/count projection.'}})
write(O/'scope-diff.json',{'phase':'T5','baseline_head':initial['head'],'comparison':'Immediate post-T4 checkpoint; HEAD only for previously clean files',
 'source_files':29,'created':created,'modified':modified,'files':candidate['files'],'no_global_tokens_assets_engine_or_infrastructure_changes':True})
for result in results:result.update(log='evidence/'+result['suite']+'.log',raw_result='evidence/'+result['suite']+'.result.json')
u5=[line for line in (W/'B-PY.log').read_text().splitlines() if '(test_ultimate_graph.' in line and line.endswith(' ... ok')];assert len(u5)==23
write(O/'test-ledger.json',{'phase':'T5','suites':results,'aliases':[{'suite':'U5','status':'PASS','tests':23,'included_in':'B-PY','module':'tests.test_ultimate_graph','log_lines':u5,'repeated_only_for_alias':False}],
 'pre_STOP_U5':{'tests':23,'status':'PASS','log':'evidence/U5-first.log','log_sha256':sha(W/'U5-first.log'),'core_source_and_tests_preserved':True},
 'additional_boundaries':[{'name':'schema-boundary','status':'PASS','evidence':'evidence/schema-boundary.json'},
 {'name':'native-primitives-parity','status':'PASS','widths':[1440,1280,1024,768,390],'evidence':'evidence/visual-parity/parity.json'},
 {'name':'legacy-Map-parity','status':'PASS','widths':[1440,390],'evidence':'evidence/legacy-map-parity/parity.json'},
 {'name':'responsive-focus-contrast','status':'PASS','widths':[1440,1280,1024,768,390,320],'zoom':'200%','evidence':['evidence/browser/responsive.json','evidence/browser/focus.json','evidence/browser/contrast.json']}],
 'not_run':[{'suite':'B-BROWSER full','reason':'User requests scoped W5/B-FOCUS and actual affected callers only.'},
 {'suite':'B-E2E full','reason':'S5 and W5 real API/SQL fixtures cover the modified boundary; no new engine.'},
 {'suite':'T0-T4 rerun','reason':'Approved baseline; only one changed Case-create browser focal executed.'},
 {'suite':'T6 and later','reason':'Explicitly unauthorized.'}],
 'qa_reuse':['evidence/qa-reuse.json'],'latest_label_fix_consumers_repeated':['W5'],'all_suites_match_final_affected_source_files':True})
skills=[]
descriptions={
 'design-system':('Native Hero, cards, controls, states and semantic tokens; no generator.','Primitive and legacy Map pixel/style parity.'),
 'emil-design-eng':('Focus/Escape/return, native selectors/dialog, scope disposal and reduced motion; no new animation.','W5/B-FOCUS and Before/After/Why report table.'),
 'ui-ux-pro-max':('Focused form/navigation/a11y guidance reused; no design system/palette generation.','W5 contrast, keyboard, touch and responsive.'),
 'break-ui':('Schema-backed 120-character Unicode Case name, empty/one/multiple Cases, 320px and zoom200.','W5 fixtures/screenshots only; no commercial data or product toggle.')}
for name,(action,proof) in descriptions.items():
 src=R/'.agents/skills'/name/'SKILL.md';copy(src,E/'skills'/name/'SKILL.md')
 skills.append({'name':name,'source':str(src.relative_to(R)),'sha256':sha(src),'read':True,'reading':'PRE-STOP T5 / same-conversation relevant guide reused on recovery; no full reread',
  'applied':action,'verified':proof,'source_snapshot':'evidence/skills/'+name+'/SKILL.md'})
for name,file,package,action in [
 ('supabase:supabase','supabase-skill.txt','c0/supabase','Checked private snapshot/RPC, service-role-only grant, tenant/actor checks; official function docs.'),
 ('supabase:supabase-postgres-best-practices','postgres-skill.txt','c0/supabase-postgres-best-practices','Ordered locks, private snapshots, bounded/paged reads and existing ACL/RLS preservation.'),
 ('cloud-environment:cloud-environment-runtime','runtime-skill.txt','c5/cloud-environment-runtime','Executor recovery check, local Docker/runners, credential-cleared QA, owned cleanup.')]:
 src=E/'skills'/file;assert src.exists()
 skills.append({'name':name,'package':package,'sha256':sha(src),'source_snapshot':'evidence/skills/'+file,'read':True,
  'reading':'PRE-STOP T5; runtime read again on recovery','applied':action,'verified':'S5, schema-boundary, version checks and cleanup.'})
for rel in ['design-system/references/token-architecture.md','design-system/references/states-and-variants.md','break-ui/CATALOG.md']:
 copy(R/'.agents/skills'/rel,E/'skills'/rel)
write(O/'skills-ledger.json',{'phase':'T5','skills':skills,
 'references':['design-system/references/token-architecture.md','design-system/references/states-and-variants.md','break-ui/CATALOG.md','runtime-docker-reference.txt','runtime-networking-reference.txt','Postgres same-conversation RLS/index guidance'],
 'omitted':[{'guidance':'Global redesign, palette/font/starter/framework or generated tokens','reason':'F01/F23 and user preservation constraint.'},
 {'guidance':'Motion audit / automatic review-animations','reason':'No new audit or animation authorized.'},
 {'guidance':'break-ui report-before-fixing approval pause','reason':'Explicit end-to-end T5 implementation authorization takes precedence.'},
 {'guidance':'Production SQL/Storage/deployment','reason':'Explicitly prohibited in T5.'}],
 'required_dependencies_missing':[],'application_dependencies_added':False,'UI_preservation_gate':'PASS'})
write(O/'command-ledger.json',{'phase':'T5','suites':[{k:r[k] for k in ['suite','cwd','command','PYTHONPATH','started_at','finished_at','seconds','exit_code']} for r in results],
 'PRE_STOP_U5_command':['/workspace/Dation/.venv/bin/python','-B','-m','unittest','tests.test_ultimate_graph','-v'],
 'PRE_STOP_U5_cwd':'/workspace/Dation/backend','PRE_STOP_U5_log':'evidence/U5-first.log','standalone_U5_after_recovery':False,
 'driver':'evidence/drivers/qa.py','additional_commands':[{'script':'evidence/drivers/schema-boundary.py','result':'PASS','log':'evidence/schema-boundary.log'},
 {'script':'evidence/drivers/visual-parity.py','result':'PASS','log':'evidence/visual-parity.log'},
 {'script':'evidence/drivers/legacy-map-parity.py','result':'PASS','log':'evidence/legacy-map-parity.log'},
 {'command':['git','diff','--check'],'result':'PASS'}],
 'production_credentials_cleared':['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN'],
 'no_remote_project_access_or_writes':True,'no_commit_push_or_deploy':True})
write(E/'runtime.json',{'date':'2026-10-27','client_timezone':'America/Buenos_Aires','log_timezone':'UTC','python':'3.13.5','node':'24.19.0','chromium':'151.0.7922.173',
 'postgres':'17.11','docker':'28.4.0','supabase_cli':'2.122.0','app_runner':'/workspace/Dation/.venv/bin/python','browser_runner':'/workspace/Dation/backend/.browser-venv/bin/python',
 'Docker':'Local Unix socket; inherited endpoint/context/TLS selectors cleared for owned fixtures only.',
 'QA_authorization':'Local loopback/Chromium/Docker execution approved by tool review; no external project used as sandbox.',
 'production_credentials_used':False,'new_application_dependencies':False})
print(json.dumps({'source_files':29,'created':15,'modified':14,'baseline_current_unchanged':len(same),'baseline_extended':len(changed),'pre_STOP_unchanged':len(pre_same),'pre_STOP_extended':len(pre_extended),'T4_entries_verified':147,'required_suites':'PASS','evidence':str(E)}))
