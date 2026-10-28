"""Preserve T3 evidence and historical checkpoints without staging or committing."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path('/workspace/Dation');WORK=Path('/workspace/work/dation-t3');OUT=ROOT/'docs/execution/ultimate/t3';E=OUT/'evidence';E.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
initial=json.loads((WORK/'initial-state.json').read_text());candidate=json.loads((WORK/'candidate.json').read_text())
assert all(sha(ROOT/n)==r['sha256'] for n,r in candidate['files'].items())
names=['B-PY','B-NODE','S3','W3','FOCAL-LEGACY-API','FOCAL-LEGACY-BROWSER']
results=[json.loads((WORK/(n+'.result.json')).read_text()) for n in names]
assert all(r['status']=='PASS' and r['tests']>0 and r['failures']==r['errors']==r['skips']==0 for r in results)
for n in names:
 for ext in ['.log','.result.json']:copy(WORK/(n+ext),E/(n+ext))
for n in ['T3-user-request.txt','initial-state.json','post-t2-tracked.patch','candidate.json','candidate-before-w3-harness-update.json','candidate-before-dirty-fix.json','t3-changes.patch','qa-reuse.json','qa-reuse-dirty-fix.json','qa-batch.log','qa-final-browser-legacy.log','qa-final-dirty.log','qa-final-w3.log','schema-boundary.json','ui-skill-form-guidance.txt','cleanup.json']:
 copy(WORK/n,E/n)
for folder in ['attempts','visual-before','visual-parity','dda-parity','browser']:
 shutil.copytree(WORK/folder,E/folder,dirs_exist_ok=True)
for n in ['dation-t3-qa.py','dation-t3-schema-evidence.py','dation-t3-visual-parity.py','dation-t3-dda-parity.py','dation-t3-dda-parity-browser.py']:
 copy(Path('/tmp')/n,E/n)
unchanged=[];changed=[]
for name,old in initial['files'].items():
 assert sha(WORK/'post-t2'/name)==old['sha256'],name
 if sha(ROOT/name)==old['sha256']:unchanged.append(name)
 else:
  assert name in candidate['files'],name
  copy(WORK/'post-t2'/name,E/'post-t2'/name);changed.append(name)
assert changed==['backend/app/platform/home.py'],changed
t2=ROOT/'docs/execution/ultimate/t2/artifact-integrity.json';manifest=json.loads(t2.read_text());t2_resolution=[]
for entry in manifest['files']:
 name=entry['path'];path=E/'post-t2'/name if name in changed else ROOT/name
 assert sha(path)==entry['sha256'],name
 t2_resolution.append({'path':name,'matches_historical_hash':True,'resolved_from':str(path.relative_to(ROOT))})
write(OUT/'preservation.json',{'phase':'T3','baseline_pending_files':len(initial['files']),'checkpoint_copies_verified':len(initial['files']),'unchanged_current_files':len(unchanged),'intentionally_extended_files':changed,'historical_T2_manifest_unchanged':sha(t2)==initial['T2_manifest_sha256'],'historical_T2_entries_verified':len(t2_resolution),'T2_resolution':t2_resolution,'old_reports_migrations_contracts_tests_preserved':True,'candidate_verified':True,'source_files':len(candidate['files'])})
write(OUT/'scope-diff.json',{'phase':'T3','baseline':initial['head'],'files':candidate['files'],'created':[n for n,r in candidate['files'].items() if r['baseline']=='new T3 file'],'modified':[n for n,r in candidate['files'].items() if r['baseline']!='new T3 file'],'no_infrastructure_or_global_design_token_changes':True})
for r in results:r.update(log='evidence/'+r['suite']+'.log',raw_result='evidence/'+r['suite']+'.result.json')
u3_lines=[line for line in (WORK/'B-PY.log').read_text().splitlines() if '(test_ultimate_case_models.' in line and line.endswith(' ... ok')];assert len(u3_lines)==17
write(OUT/'test-ledger.json',{'phase':'T3','suites':results,'aliases':[{'suite':'U3','status':'PASS','tests':17,'included_in':'B-PY','module':'tests.test_ultimate_case_models','log_lines':u3_lines,'repeated_only_for_alias':False}],'additional_boundaries':[{'name':'schema-boundary','status':'PASS','evidence':'evidence/schema-boundary.json'},{'name':'native-visual-parity','status':'PASS','viewports':[1440,1280,1024,768,390],'evidence':'evidence/visual-parity/parity.json'},{'name':'actual-DDA-Hero','status':'PASS','geometry_styles_unchanged':True,'mobile_corner_changed_pixels':4,'evidence':'evidence/dda-parity/parity.json'}],'not_run':[{'suite':'B-BROWSER full','reason':'W3 plus three affected legacy navigation tests'},{'suite':'B-E2E full','reason':'Three affected legacy API/approval/archive tests'},{'suite':'B-SQL historical full','reason':'S3 full-catalog RPC suite plus additive migration/ACL/legacy-row focal'}],'inherited_baseline':{'T2':'docs/execution/ultimate/t2/t2-execution-report.md','B-PY':456,'B-NODE':128,'B-SQL':72,'S2':26},'qa_reuse':['evidence/qa-reuse.json','evidence/qa-reuse-dirty-fix.json'],'all_suites_match_final_affected_source_files':True,'latest_dirty_fix_consumers_repeated':['B-NODE','W3']})
skills=[]
applied={
 'design-system':('Reused existing native semantic/component tokens, controls and states; no generator or token rewrite.','Native gallery pixel/computed-style parity at five widths; scoped stylesheet.'),
 'emil-design-eng':('Immediate functional feedback, native dialog focus/Escape/return, keyboard and reduced motion. No added animation.','W3 01/02/06/08, Before/After table in report.'),
 'ui-ux-pro-max':('Focused forms search: linked focusable error summary, inline aria-describedby errors and blur validation.','W3 02; exact-percent Node test; evidence/ui-skill-form-guidance.txt.'),
 'break-ui':('Schema-backed 120-character names, 1000-character descriptions, Unicode, empty/one/multiple results, 320px and zoom200%. Fixtures only.','W3 04/07 responsive screenshots; no production toggle.')}
for name,(action,verified) in applied.items():
 src=ROOT/'.agents/skills'/name/'SKILL.md';copy(src,E/'skills'/name/'SKILL.md')
 skills.append({'name':name,'source':str(src.relative_to(ROOT)),'sha256':sha(src),'read':True,'applied':action,'verified':verified,'source_snapshot':'evidence/skills/'+name+'/SKILL.md'})
for name,snapshot,action,verified in [
 ('supabase:supabase','supabase-skill.txt','Additive CLI-generated migration, checked SECURITY DEFINER RPC, tenant/actor authority and default-closed flag.','S3 25; real API negatives; schema-boundary ACL/RLS check.'),
 ('supabase:supabase-postgres-best-practices','postgres-skill.txt','Workspace→Case ordered locks, CAS, composite FKs and immutable version snapshots.','S3 concurrent publication/admission-edit race and metadata/history preservation.'),
 ('cloud-environment:cloud-environment-runtime','runtime-skill.txt','Owned local PostgreSQL/PostgREST/Chromium harness; credential-cleared runners and local socket.','Label/version assertions and cleanup evidence; no remote project access.')]:
 src=ROOT/'docs/execution/ultimate/t2/evidence'/snapshot;copy(src,E/'skills'/snapshot)
 skills.append({'name':name,'source_snapshot':'evidence/skills/'+snapshot,'sha256':sha(src),'read':True,'reused_from_same_conversation_T2':True,'applied':action,'verified':verified})
write(OUT/'skills-ledger.json',{'phase':'T3','skills':skills,'references':['design-system/references/token-architecture.md','design-system/references/states-and-variants.md','break-ui/CATALOG.md','postgres/schema-foreign-key-indexes.md','postgres/security-rls-performance.md','runtime/references/docker.md','runtime/references/networking.md'],'omitted':[{'guidance':'new palettes/fonts/design system/starters/React/Framer examples','reason':'User requires existing native Dation stack/tokens/typography and no global redesign.'},{'guidance':'break-ui report-before-fixing stop / first-response-only variants','reason':'Explicit T3 end-to-end implementation and specific scoped task take precedence; no new approval step or product toggle.'},{'guidance':'general motion/brand audits or automatic review-animations','reason':'Outside authorized T3; review-animations disable-model-invocation respected.'}],'no_added_dependencies':True,'UI_preservation_gate':'PASS'})
write(OUT/'command-ledger.json',{'phase':'T3','suites':[{k:r[k] for k in ['suite','cwd','command','PYTHONPATH','started_at','finished_at','seconds','exit_code']} for r in results],'additional_commands':[{'command':['/workspace/Dation/.venv/bin/python','-B','/tmp/dation-t3-schema-evidence.py'],'evidence':'evidence/attempts/schema-boundary.log'},{'command':['/workspace/Dation/backend/.browser-venv/bin/python','-B','/tmp/dation-t3-visual-parity.py'],'evidence':'evidence/attempts/visual-parity.log'},{'command':['/workspace/Dation/.venv/bin/python','-B','/tmp/dation-t3-dda-parity.py'],'evidence':'evidence/attempts/dda-parity-final.log'}],'U3_alias':'Executed within B-PY; 17 module cases verified in ledger.','production_credentials_cleared':True,'no_remote_writes':True})
write(E/'runtime.json',{'date':'2026-10-26','client_timezone':'America/Buenos_Aires','python':'3.13.5','node':'24.19.0','chromium':'151.0.7922.173','postgres':'17.11','supabase_cli':'2.122.0','application_python':'/workspace/Dation/.venv/bin/python','browser_python':'/workspace/Dation/backend/.browser-venv/bin/python','optional_pixel_analysis':'System Python with existing Pillow; not an app/test runner fallback.','docker_socket':'unix:///var/run/docker.sock','SQL_container':'dation-t3-20261026-ultimate','SQL_labels':{'dation.qa.phase':'T3','dation.qa.owner':'codex-dation'},'production_credentials_used':False,'application_dependencies_added':False})
print(json.dumps({'T3_source_files':len(candidate['files']),'created':16,'modified':8,'baseline_unchanged':len(unchanged),'baseline_extended':changed,'T2_entries_verified':len(t2_resolution),'required_suites':'PASS','evidence_dir':str(E)},ensure_ascii=False))
