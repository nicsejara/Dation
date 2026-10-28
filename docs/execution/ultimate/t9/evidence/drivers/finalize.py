"""Preserve T8 evidence and prove the immediate post-T8 delta, without git writes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess
R=Path('/workspace/Dation');W=Path('/workspace/work/dation-t9');O=R/'docs/execution/ultimate/t9';E=O/'evidence'
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
assert len(candidate['files'])==21
for n,v in candidate['files'].items():assert sha(R/n)==v['sha256'],n
same=[];changed=[]
for n,v in initial['files'].items():
    assert sha(W/'post-t8'/n)==v['sha256'],n
    assert (R/n).is_file(),n
    if sha(R/n)==v['sha256']:same.append(n)
    else:
        assert n in candidate['files'],n
        changed.append(n)
assert len(initial['files'])==864
assert hashlib.sha256(json.dumps(initial['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==initial['checkpoint_sha256']
created=[];modified=[]
for n,v in candidate['files'].items():
    if v['baseline_sha256'] is None:created.append(n);continue
    modified.append(n)
    if n in initial['files']:copy(W/'post-t8'/n,E/'post-t8'/n)
    else:
        content=git('show','HEAD:'+n);p=E/'post-t8'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
    assert sha(E/'post-t8'/n)==v['baseline_sha256'],n
assert len(created)==13 and len(modified)==8
t7=R/'docs/execution/ultimate/t8/artifact-integrity.json';assert sha(t7)==initial['T8_manifest_sha256']
resolved=[]
for entry in read(t7)['files']:
    n=entry['path'];source=E/'post-t8'/n if n in modified else R/n;assert sha(source)==entry['sha256'],n
    resolved.append({'path':n,'resolved_from':str(source.relative_to(R)),'sha256_verified':True})
assert len(resolved)==83
results=[]
for name,expected in [('B-PY',656),('B-NODE',137),('U9',28),('E9',8),('S8',13),('E8',8),('L8',2),('D1-COMPAT',3),('LEGACY',1)]:
    result=read(W/(name+'.result.json'))
    assert result['status']=='PASS' and result['tests']==expected,(name,result)
    assert result['failures']==result['errors']==result['skips']==result['exit_code']==0
    assert sha(W/(name+'.log'))==result['log_sha256'],name
    for suffix in ['.log','.result.json']:copy(W/(name+suffix),E/(name+suffix))
    result.update(log='evidence/'+name+'.log',raw_result='evidence/'+name+'.result.json');results.append(result)
for name in ['initial-state.json','candidate.json','T9-user-request.txt','post-t8-tracked.patch','t9-changes.patch','qa-final-batch.log','d1-compat-vectors.json','advisors.json','advisors.stderr','advisors-command.json']:
    if (W/name).exists():copy(W/name,E/name)
for p in (W/'drivers').glob('*.py'):copy(p,E/'drivers'/p.name)
for p in (R/'docs/execution/ultimate/t8/evidence/skills').glob('*.txt'):copy(p,E/'skills'/p.name)
runtime=R/'docs/execution/ultimate/t8/evidence/skills/runtime-skill.txt';copy(runtime,E/'skills/runtime-skill.txt')
# Intermediate logs are evidence of diagnosed failures, never the PASS ledger.
patterns=[re.compile(rb'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'),re.compile(rb'\bsbp_[A-Za-z0-9]{30,}'),re.compile(rb'\bsk-proj-[A-Za-z0-9_-]{30,}')]
for p in W.glob('*.log'):
    if p.name in {r['suite']+'.log' for r in results}:continue
    data=p.read_bytes()
    for pattern in patterns:data=pattern.sub(b'[ephemeral fixture credential redacted]',data)
    dest=E/'attempts'/p.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
write(O/'skills-ledger.json',{'phase':'T9','subagents_used':False,'dependencies_installed':False,'used':[
    {'name':'supabase:supabase','package':'c0/supabase','snapshot':'evidence/skills/supabase-skill.txt','applied':['official Storage docs via MCP','CLI-generated migration','checked RPC/RLS/grants','owned Advisors']},
    {'name':'supabase:supabase-postgres-best-practices','package':'c0/supabase-postgres-best-practices','snapshot':'evidence/skills/postgres-skill.txt','applied':['consistent locks','least privilege','scoped indexes','lease fencing']},
    {'name':'cloud-environment:cloud-environment-runtime','package':'c5/cloud-environment-runtime','snapshot':'evidence/skills/runtime-skill.txt','applied':['current environment/network observations','owned Docker resources','loopback QA','production credentials cleared']}],
    'design_skills':'Not applicable; no frontend changes','precedence':'User T9 scope and current checked-actor architecture preserved; no production operations'})
write(O/'scope-diff.json',{'phase':'T9','baseline_head':initial['head'],'comparison':'Immediate post-T8 checkpoint','source_files':21,'created':created,'modified':modified,'files':candidate['files'],
    'frontend_changes':False,'D1_assignment_math_changes':False,'production_infrastructure_changes':False,'public_admissions_enabled':False,'T10_executed':False})
write(O/'preservation.json',{'phase':'T9','baseline_inventory_files':864,'baseline_inventory_bytes':sum(v['bytes'] for v in initial['files'].values()),'checkpoint_sha256':initial['checkpoint_sha256'],
    'checkpoint_kind':initial['checkpoint_kind'],'workspace_full_copies':'/workspace/work/dation-t9/post-t8','copies_verified':864,'current_files_unchanged':len(same),'intentionally_extended_from_inventory':changed,
    'preimages':{n:'evidence/post-t8/'+n for n in modified},'T8_manifest_unchanged':True,'T8_entries_verified':83,'T8_resolution':resolved,'D1_exact_byte_vectors_verified':3,'legacy_engines_frontend_and_T1_metadata_preserved':True,
    'no_reset_clean_discard_checkout_staging_commit_or_history_change':True})
py=(W/'B-PY.log').read_text().splitlines()
u6=[l for l in py if '(test_transport_plan_core.' in l and l.endswith(' ... ok')]
u7=[l for l in py if ('(test_transport_plan_policies.' in l or '(test_transport_result_package.' in l) and l.endswith(' ... ok')]
assert len(u6)==47 and len(u7)==46
write(O/'test-ledger.json',{'phase':'T9','suites':results,'U6_in_B_PY':{'tests':47,'log_lines':u6},'U7_in_B_PY':{'tests':46,'log_lines':u7},'lineage':{'E9':'PASS with real D1 and D2 producers/API/SQL/worker','D2_A_B_source':'D1 A exact Run/fingerprint; D1 preserved','D2_C_source':'D1 B exact Run/fingerprint after human approval','historical_upstream':'immutable','replay_after_new_path':'original Run, no repeated effects'},'fixtures_H_L':{'H':'PASS','I':'PASS','J':'PASS','K':'PASS defensive unit only; no fake E2E approval','L':'PASS'},'R9_R13':{n:'PASS' for n in ['R9','R10','R11','R12','R13']},
    'U8_in_B_PY':14,'U9_in_B_PY':28,'zero_failures_errors_skips':True,'current_sources_verified':True,'full_T0_T8_phase_reexecution':False,'T10_executed':False})
write(O/'command-ledger.json',{'phase':'T9','suites':[{k:r[k] for k in ['suite','cwd','command','started_at','finished_at','seconds','exit_code']} for r in results],
    'QA_driver':'evidence/drivers/qa.py','integrity_driver':'evidence/drivers/finalize.py','git_diff_check':'PASS','owned_advisors':'evidence/advisors-command.json',
    'credentials_cleared':['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN'],'git_write_push_deploy_or_production_access':False})
decision='GO — T9 completado. T10 puede ser solicitado.'
table='| Suite | Tests | Resultado | Fail/Error/Skip |\n|---|---:|---|---|\n'+'\n'.join('| '+r['suite']+' | '+str(r['tests'])+' | PASS | 0/0/0 |' for r in results)
gates='| Gate | Resultado | Evidencia |\n|---|---|---|\n'+'\n'.join('| '+name+' | PASS | '+proof+' |' for name,proof in [
 ('Baseline/alcance','864 copias; 83 entries T8 resueltas; sin T10/producción'),('Upstream exacto','E9: A/B→A, C→B; hashes, snapshots y actores históricos'),('Temporal/Transit','U9 H–L, kernel compartido, fechas DATE y OWN end exclusivo'),('Core/evidence/métricas','U9 R9–R13; sin pérdida de Trips; compliance y strict separados'),('Assembler/consumidores','Core/Gantt/details/CSV/context/review consistentes, hash DAG íntegro'),('Publication/fencing','E9 y S8/E8; protocolo único T8; sin publicación parcial'),('Regresiones','B-PY/B-NODE, L8, bytes D1 exactos y legacy real'),('STOP','Ninguna condición funcional abierta; negativos esperados fallan cerrado')])
report=(W/'t9-report-template.md').read_text().replace('{{DECISION}}',decision).replace('{{OUTCOME}}','D2 Day Scheduling implementado y validado en sandbox owned.').replace('{{QA_TABLE}}',table).replace('{{GATES}}',gates)
assert '{{' not in report
O.mkdir(parents=True,exist_ok=True);(O/'t9-execution-report.md').write_text(report)
status=git('status','--porcelain=v1','-z','--untracked-files=all').decode();paths=[x[3:] for x in status.split('\0') if x]
unexpected=[n for n in paths if n not in initial['files'] and n not in candidate['files'] and not n.startswith('docs/execution/ultimate/t9/')]
assert not unexpected,unexpected
write(E/'final-state.json',{'phase':'T9','captured_at':datetime.now(timezone.utc).isoformat(),'head':initial['head'],'branch':'main','git_status_short_branch':git('status','--short','--branch').decode(),
    'staged':[],'preexisting_changes_preserved':True,'source_files':21,'source_hashes_verified':True,'decision':decision,'T10_executed':False,'push_deploy_production_access':False})
findings=[str(p.relative_to(R)) for p in O.rglob('*') if p.is_file() and any(pattern.search(p.read_bytes()) for pattern in patterns)]
assert not findings,findings
manifest=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(O.rglob('*')) if p.is_file() and p.name!='artifact-integrity.json']
manifest.extend({'path':n,'bytes':(R/n).stat().st_size,'sha256':sha(R/n)} for n in sorted(candidate['files']))
write(O/'artifact-integrity.json',{'phase':'T9','head':initial['head'],'captured_at':datetime.now(timezone.utc).isoformat(),'decision':decision,'source_files':21,'excludes_self':True,'files':manifest})
print(json.dumps({'decision':decision,'source_files':21,'baseline_copies_verified':864,'T8_entries_verified':83,'evidence_entries':len(manifest),'staged':False,'T10_executed':False,'report':str(O/'t9-execution-report.md')}))
