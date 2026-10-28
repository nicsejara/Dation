"""Preserve T8 evidence and prove the immediate post-T7 delta, without git writes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess
R=Path('/workspace/Dation');W=Path('/workspace/work/dation-t8');O=R/'docs/execution/ultimate/t8';E=O/'evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
initial=read(W/'initial-state.json');candidate=read(W/'candidate.json')
assert git('rev-parse','HEAD').decode().strip()==initial['head']=='ef997235a30251fbf7ae53690ed738092ee973d8'
assert git('branch','--show-current').decode().strip()==initial['branch']=='main'
assert not git('diff','--cached','--name-only')
subprocess.run(['git','diff','--check'],cwd=R,check=True)
assert len(candidate['files'])==16
for n,v in candidate['files'].items():assert sha(R/n)==v['sha256'],n
same=[];changed=[]
for n,v in initial['files'].items():
    assert sha(W/'post-t7'/n)==v['sha256'],n
    assert (R/n).is_file(),n
    if sha(R/n)==v['sha256']:same.append(n)
    else:
        assert n in candidate['files'],n
        changed.append(n)
assert len(initial['files'])==823
assert hashlib.sha256(json.dumps(initial['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==initial['checkpoint_sha256']
created=[];modified=[]
for n,v in candidate['files'].items():
    if v['baseline_sha256'] is None:created.append(n);continue
    modified.append(n)
    if n in initial['files']:copy(W/'post-t7'/n,E/'post-t7'/n)
    else:
        content=git('show','HEAD:'+n);p=E/'post-t7'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
    assert sha(E/'post-t7'/n)==v['baseline_sha256'],n
assert len(created)==12 and len(modified)==4
t7=R/'docs/execution/ultimate/t7/artifact-integrity.json';assert sha(t7)==initial['T7_manifest_sha256']
resolved=[]
for entry in read(t7)['files']:
    n=entry['path'];assert sha(R/n)==entry['sha256'],n
    resolved.append({'path':n,'resolved_from':n,'sha256_verified':True})
assert len(resolved)==46
results=[]
for name,expected in [('B-PY',628),('B-NODE',137),('B-FOCUS',9),('U8',14),('S8',13),('E8',8),('L8',2),('R8',1)]:
    result=read(W/(name+'.result.json'))
    assert result['status']=='PASS' and result['tests']==expected,(name,result)
    assert result['failures']==result['errors']==result['skips']==result['exit_code']==0
    assert sha(W/(name+'.log'))==result['log_sha256'],name
    for suffix in ['.log','.result.json']:copy(W/(name+suffix),E/(name+suffix))
    result.update(log='evidence/'+name+'.log',raw_result='evidence/'+name+'.result.json');results.append(result)
for name in ['initial-state.json','candidate.json','T8-user-request.txt','post-t7-tracked.patch','t8-changes.patch','qa-final-batch.log','qa-boundary-final.log','qa-boundary-final2.log','qa-legacy-transition.log','advisors.json','advisors.stderr','advisors-command.json']:
    if (W/name).exists():copy(W/name,E/name)
for p in (W/'drivers').glob('*.py'):copy(p,E/'drivers'/p.name)
for p in (W/'skills').glob('*.txt'):copy(p,E/'skills'/p.name)
runtime=R/'docs/execution/ultimate/t7/evidence/skills/runtime-skill.txt';copy(runtime,E/'skills/runtime-skill.txt')
# Intermediate logs are evidence of diagnosed failures, never the PASS ledger.
patterns=[re.compile(rb'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'),re.compile(rb'\bsbp_[A-Za-z0-9]{30,}'),re.compile(rb'\bsk-proj-[A-Za-z0-9_-]{30,}')]
for p in W.glob('*.log'):
    if p.name in {r['suite']+'.log' for r in results}:continue
    data=p.read_bytes()
    for pattern in patterns:data=pattern.sub(b'[ephemeral fixture credential redacted]',data)
    dest=E/'attempts'/p.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
write(O/'skills-ledger.json',{'phase':'T8','subagents_used':False,'dependencies_installed':False,'used':[
    {'name':'supabase:supabase','package':'c0/supabase','snapshot':'evidence/skills/supabase-skill.txt','applied':['official Storage docs via MCP','CLI-generated migration','checked RPC/RLS/grants','owned Advisors']},
    {'name':'supabase:supabase-postgres-best-practices','package':'c0/supabase-postgres-best-practices','snapshot':'evidence/skills/postgres-skill.txt','applied':['consistent locks','least privilege','scoped indexes','lease fencing']},
    {'name':'cloud-environment:cloud-environment-runtime','package':'c5/cloud-environment-runtime','snapshot':'evidence/skills/runtime-skill.txt','applied':['current environment/network observations','owned Docker resources','loopback QA','production credentials cleared']}],
    'design_skills':'Not applicable; no frontend changes','precedence':'User T8 scope and current checked-actor architecture preserved; no production operations'})
write(O/'scope-diff.json',{'phase':'T8','baseline_head':initial['head'],'comparison':'Immediate post-T7 checkpoint','source_files':16,'created':created,'modified':modified,'files':candidate['files'],
    'frontend_changes':False,'T7_math_or_assembler_changes':False,'production_infrastructure_changes':False,'public_admissions_enabled':False,'T9_executed':False})
write(O/'preservation.json',{'phase':'T8','baseline_inventory_files':823,'baseline_inventory_bytes':sum(v['bytes'] for v in initial['files'].values()),'checkpoint_sha256':initial['checkpoint_sha256'],
    'checkpoint_kind':initial['checkpoint_kind'],'workspace_full_copies':'/workspace/work/dation-t8/post-t7','copies_verified':823,'current_files_unchanged':len(same),'intentionally_extended_from_inventory':changed,
    'preimages':{n:'evidence/post-t7/'+n for n in modified},'T7_manifest_unchanged':True,'T7_entries_verified':46,'T7_resolution':resolved,'T7_math_assembler_catalogs_legacy_engines_and_frontend_preserved':True,
    'no_reset_clean_discard_checkout_staging_commit_or_history_change':True})
py=(W/'B-PY.log').read_text().splitlines()
u6=[l for l in py if '(test_transport_plan_core.' in l and l.endswith(' ... ok')]
u7=[l for l in py if ('(test_transport_plan_policies.' in l or '(test_transport_result_package.' in l) and l.endswith(' ... ok')]
assert len(u6)==47 and len(u7)==46
write(O/'test-ledger.json',{'phase':'T8','suites':results,'U6_in_B_PY':{'tests':47,'log_lines':u6},'U7_in_B_PY':{'tests':46,'log_lines':u7},'lineage':{n:'PASS in relevant T8 boundary; D2 metadata only' for n in ['L-A','L-B','L-C','L-D','L-E','L-F']},
    'zero_failures_errors_skips':True,'current_sources_verified':True,'full_T0_T7_phase_reexecution':False,'T9_executed':False})
write(O/'command-ledger.json',{'phase':'T8','suites':[{k:r[k] for k in ['suite','cwd','command','started_at','finished_at','seconds','exit_code']} for r in results],
    'QA_driver':'evidence/drivers/qa.py','integrity_driver':'evidence/drivers/finalize.py','git_diff_check':'PASS','owned_advisors':'evidence/advisors-command.json',
    'credentials_cleared':['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN'],'git_write_push_deploy_or_production_access':False})
decision='GO — T8 completado. T9 puede ser solicitado.'
table='| Suite | Tests | Resultado | Fail/Error/Skip |\n|---|---:|---|---|\n'+'\n'.join('| '+r['suite']+' | '+str(r['tests'])+' | PASS | 0/0/0 |' for r in results)
gates='| Gate | Resultado | Evidencia |\n|---|---|---|\n'+'\n'.join('| '+name+' | PASS | '+proof+' |' for name,proof in [
    ('Baseline/alcance','823 copias y 46 entries T7 verificadas; math y frontend preservados'),('Admission/replay','U8/S8/E8/L8; una intención/Run; contexto fijado'),('Publication/fencing','S8/E8; sin estados parciales; lease y manifest exactos'),('Retrieval/security','U8/S8/E8; bytes, tenant/Run/fingerprint y páginas acotadas'),('Approval/read set','S8/E8; Owner vigente, contexto e integridad; actores históricos'),('Lineage/legacy','L8, R8, B-FOCUS y regresiones B-PY/B-NODE'),('STOP conditions','Ninguna condición funcional abierta; intentos fallidos diagnosticados y suites finales completas'),('T9/producción','No ejecutados; flag público cerrado; sin push/deploy')])
report=(W/'t8-report-template.md').read_text().replace('{{DECISION}}',decision).replace('{{OUTCOME}}','D1 Ultimate conectado al lifecycle durable y validado en sandbox owned.').replace('{{QA_TABLE}}',table).replace('{{GATES}}',gates)
assert '{{' not in report
O.mkdir(parents=True,exist_ok=True);(O/'t8-execution-report.md').write_text(report)
status=git('status','--porcelain=v1','-z','--untracked-files=all').decode();paths=[x[3:] for x in status.split('\0') if x]
unexpected=[n for n in paths if n not in initial['files'] and n not in candidate['files'] and not n.startswith('docs/execution/ultimate/t8/')]
assert not unexpected,unexpected
write(E/'final-state.json',{'phase':'T8','captured_at':datetime.now(timezone.utc).isoformat(),'head':initial['head'],'branch':'main','git_status_short_branch':git('status','--short','--branch').decode(),
    'staged':[],'preexisting_changes_preserved':True,'source_files':16,'source_hashes_verified':True,'decision':decision,'T9_executed':False,'push_deploy_production_access':False})
findings=[str(p.relative_to(R)) for p in O.rglob('*') if p.is_file() and any(pattern.search(p.read_bytes()) for pattern in patterns)]
assert not findings,findings
manifest=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='artifact-integrity.json']
manifest.extend({'path':n,'bytes':(R/n).stat().st_size,'sha256':sha(R/n)} for n in sorted(candidate['files']))
write(O/'artifact-integrity.json',{'phase':'T8','head':initial['head'],'captured_at':datetime.now(timezone.utc).isoformat(),'decision':decision,'source_files':16,'excludes_self':True,'files':manifest})
print(json.dumps({'decision':decision,'source_files':16,'baseline_copies_verified':823,'T7_entries_verified':46,'evidence_entries':len(manifest),'staged':False,'T9_executed':False,'report':str(O/'t8-execution-report.md')}))
