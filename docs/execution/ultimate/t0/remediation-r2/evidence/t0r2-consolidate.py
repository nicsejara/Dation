"""Consolidate R2 only after all six complete gates pass on the frozen source."""
import hashlib,json,re,shutil,subprocess,os
from pathlib import Path
from datetime import datetime,timezone

R=Path('/workspace/Dation');W=Path('/workspace/work/dation-t0r2')
T=R/'docs/execution/ultimate/t0';O=T/'remediation-r2';E=O/'evidence'
EXPECTED={'B-PY':383,'B-NODE':128,'B-BROWSER':251,'B-SQL':46,'B-E2E':86,'B-FOCUS':9}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
freeze=json.loads((W/'final-source-freeze.json').read_text())
assert all(sha(R/p)==h for p,h in freeze['files'].items()),'Source changed after freeze'
initial=json.loads((W/'initial-state.json').read_text())
assert sha(R/'DATION_FINAL_MASTER_EXECUTION_PLAN.md')==initial['master_sha256']
assert sha(R/'docs/ultimate-mvp-implementation-master-plan.md')=='ff824a2fae9566cfb4e1f77ae81e8806d0b76d179b208660b29e9bd00e9ab6d6'
original_source_manifest=next(e for e in json.loads((T/'artifact-integrity.json').read_text())['files'] if e['path']=='docs/execution/ultimate/source-manifest.json')
assert sha(R/original_source_manifest['path'])==original_source_manifest['sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==freeze['head']
tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=R,text=True).split('\0'))-{''}
changed=set(subprocess.check_output(['git','diff','--name-only'],cwd=R,text=True).splitlines())
assert changed==set(freeze['files'])&tracked,('Unexpected tracked diff',changed^(set(freeze['files'])&tracked))
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=R,text=True).strip(),'Unexpected staging'
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=R,text=True).splitlines()
assert not [p for p in untracked if p not in freeze['files'] and not p.startswith('docs/execution/ultimate/t0/') and p not in ['DATION_FINAL_MASTER_EXECUTION_PLAN.md','docs/ultimate-mvp-implementation-master-plan.md','docs/execution/ultimate/source-manifest.json']], 'Unexpected untracked file'
records=[];passed_ids=set()
for name,count in EXPECTED.items():
 p=W/'revalidation'/(name+'.result.json');j=json.loads(p.read_text());log=W/'revalidation'/(name+'.log')
 assert j['status']=='PASS' and j['exit_code']==0 and j['tests']==count and j['failures_count']==0 and j['skipped']==0,(name,j)
 assert j['started_at']>=freeze['frozen_at'],(name,'pre-freeze result')
 assert sha(log)==j['log_sha256'],name
 shutil.copy2(p,E/p.name);shutil.copy2(log,E/log.name)
 j['original_log_path']=j['log_path'];j['log_path']=str((E/log.name).relative_to(R))
 j['failed_test_cases_unique']=0;j['passed_test_cases']=count
 records.append(j)
 if name!='B-NODE':
  passed_ids.update(re.findall(r'^test_[^\n]*? \(([^\n]+)\) \.\.\.',log.read_text(),re.M))
docker_env=os.environ.copy()
for key in ['DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:
 docker_env.pop(key,None)
for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:
 docker_env[key]=''
docker_env['DOCKER_HOST']='unix:///var/run/docker.sock'
def docker_read(*args):
 return subprocess.check_output(['docker','--host=unix:///var/run/docker.sock',*args],env=docker_env,text=True).strip()
preserved=[]
for identifier in ['57d0569c15c9','89c072eaca56','e63696788ed3','ada4ae04845f']:
 item=json.loads(docker_read('inspect','--format','{{json .State}}',identifier))
 assert item['Status']=='exited',('Preexisting container changed',identifier,item['Status'])
 preserved.append({'id':identifier,'status':item['Status']})
containers=[json.loads(line) for line in docker_read('ps','-a','--format','{{json .}}').splitlines() if line]
assert not [item for item in containers if item['Names'].startswith('dation-t0r2-sql-')], 'R2 SQL container left behind'
networks=docker_read('network','ls','--format','{{.Name}}').splitlines()
write(E/'owned-cleanup.json',{'preexisting_containers_preserved':preserved,'r2_sql_containers_remaining':[],'docker_containers':[{'id':item['ID'],'name':item['Names'],'state':item['State']} for item in containers],'e2e_networks_remaining':[n for n in networks if n.startswith('dation-e2e-')],'remote_resources_changed':False})
raw=json.loads((W/'e2e/suite-report.json').read_text())
assert raw['passed'] and raw['tests']==86 and not raw['failures'] and not raw['errors'] and not raw['skipped']
shutil.copy2(W/'e2e/suite-report.json',E/'e2e-suite-report.json')
for source in (W/'e2e').rglob('*.json'):
 target=E/'e2e-reports'/source.relative_to(W/'e2e');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
for p in (W/'revalidation').glob('*.attempt*'):shutil.copy2(p,E/p.name)
for p in W.glob('*.log'):shutil.copy2(p,E/p.name)
for n in ['initial-state.json','final-source-freeze.json','r2-scope-diff.json','runtime.json','root-causes.json','focal-ledger.json','preservation-checks.json','r1-integrity-resolution.json','owned-sql-container.json']:
 shutil.copy2(W/n,E/n)
for source in [W/'focus',W/'browser-diagnostic']:
 shutil.copytree(source,E/source.name,dirs_exist_ok=True)
for source in ['/tmp/dation-t0r2-run-suite.py','/tmp/t0r2-final-batch.py','/tmp/t0r2-sql-suite.py','/tmp/t0r2-focus-probe.py','/tmp/t0r2-focus-stress.py','/tmp/t0r2-fixture-fault-probe.py','/tmp/t0r2-browser-diagnostic.py','/tmp/t0r2-consolidate.py']:
 shutil.copy2(source,E/Path(source).name)
now=datetime.now(timezone.utc).isoformat()
gates={
 'G-B':'PASS — six complete suites, zero failures/errors/skips; all original failing IDs covered.',
 'G-C':'PASS at T0 — no contract/DTO/engine/graph changes or new incompatibility.',
 'G-D':'PASS at T0 — authorized additive Home migration, owned fresh+upgrade, unchanged business rows and function ACL; no baseline/history repair.',
 'G-R':'PASS at T0 — existing result/consumer/exports and real engine regressions green; Ultimate packages remain future work.',
 'G-L':'PASS at T0 — current/historical approvals, upstream/downstream, races/retries/recovery and read purity covered by existing full suites.',
 'G-S':'PASS at T0 — Owner/Admin/nonowner/Viewer/tenant and RPC/ACL negatives; Home never grants approval.',
 'G-ENV':'PASS — all runners available, tests >0, local owned infrastructure, zero skips.',
 'G-A':'PASS — only R2 residual scope; T1 not executed, no remote writes or release actions.',
 'G-UI':'PASS — 32 before/after states, 24 pixel-identical normal-height captures, 12 focus/touch/zoom checks, full Browser green.'}
olddebt=json.loads((T/'debt-register.json').read_text())
original_ids={f['test_id'] for f in olddebt['failures']}
assert original_ids<=passed_ids,sorted(original_ids-passed_ids)
write(O/'test-identities.json',{'phase':'T0-R2','observed_non_node_test_ids':sorted(passed_ids),'original_failure_ids':sorted(original_ids),'original_failure_ids_all_covered':True,'test_method_preservation':freeze['existing_test_ids'],'new_module':'test_home_owner_attention','new_tests':3})
summary={'phase':'T0-R2','captured_at':now,'source_head':freeze['head'],'decision':'GO','report':'t0-remediation-r2-report.md','evidence':'remediation-r2/evidence','tests':records,'remaining_failed_test_ids':[],'new_unresolved_clusters':[],'gates':gates,'T1_executed':False,'production_applied':False,'original_R1_bytes':'remediation-r2/evidence/r1-baseline','original_R1_metadata_sha256':{n:initial['files']['docs/execution/ultimate/t0/'+n] for n in ['debt-register.json','debt-register.md','baseline-test-ledger.json','command-ledger.json']}}
summary.update({'product_modified':True,'r2_scope':'remediation-r2/evidence/r2-scope-diff.json','sql_migration':{'path':'supabase/migrations/20261026010000_home_decision_owner_attention.sql','object':'public.platform_home(uuid,uuid)','environment':'owned local sandbox only','production_applied':False,'rollback_reference':'remediation-r2/evidence/platform_home.pre-r2.rollback.sql'},'test_ids':'remediation-r2/test-identities.json','skills':'remediation-r2/evidence/skills-ledger.json'})
write(O/'qa-summary.json',summary)
for name in ['debt-register.json','baseline-test-ledger.json','command-ledger.json']:
 p=T/name;old=json.loads((E/'r1-baseline/docs/execution/ultimate/t0'/name).read_text());current=json.loads(p.read_text())
 assert {k:v for k,v in current.items() if k!='remediation_T0_R2'}==old,'Historical metadata changed: '+name
 current['remediation_T0_R2']=summary
 if name=='command-ledger.json':
  current['remediation_T0_R2']={**summary,'runtime':json.loads((W/'runtime.json').read_text()),'runner':'remediation-r2/evidence/dation-t0r2-run-suite.py','sql_runner':'remediation-r2/evidence/t0r2-sql-suite.py','batch':'remediation-r2/evidence/t0r2-final-batch.py','focal_attempts':'remediation-r2/evidence/focal-ledger.json','isolation':'exclusive flock /tmp/dation-t0r-suite.lock; no concurrent Docker bridge changes and Chromium','production_credentials_cleared':True}
 write(p,current)
oldmd=(E/'r1-baseline/docs/execution/ultimate/t0/debt-register.md').read_text()
addition='\n\n## T0-R2 — Targeted Baseline Remediation\n\n'+now+' — **GO** del baseline T0; T1 no ejecutado.\n\nLos blockers Home/Owner, fixture snapshot/teardown y foco de baja altura quedan resueltos, al igual que los cinco E2E residuales y las expectativas Browser pendientes documentadas en T0-R. Las seis suites completas pasan con cero failures/errors/skips: Python383, Node128, Browser251, SQL46, E2E86 y Focus9. Los tres tests nuevos son de Home SQL.\n\nNo se usa ninguna exención histórica para obtener verde. Las entradas T0/T0-R anteriores se conservan sin reinterpretar sus resultados históricos. La resolución actual y los IDs cubiertos están en [reporte R2](t0-remediation-r2-report.md), [QA](remediation-r2/qa-summary.json) e [identidades](remediation-r2/test-identities.json). Persisten como límites documentales las observaciones remotas previas; no se ejecutó ningún cambio productivo ni una nueva inspección remota.\n'
(T/'debt-register.md').write_bytes((E/'r1-baseline/docs/execution/ultimate/t0/debt-register.md').read_bytes()+addition.encode())
report=T/'t0-remediation-r2-report.md';text=report.read_text()
text=text.replace('Estado de trabajo: **validación completa en curso**. Este documento todavía no constituye una decisión GO/STOP final.','Estado final: **GO del baseline T0**. Captura final UTC: `'+now+'`. T1 no se ejecutó.')
rows='\n'.join('| '+j['suite']+' | PASS | '+str(j['tests'])+' | 0 | 0 | 0 | '+str(j['suite_reported_seconds'] or j['wall_seconds'])+'s | [log](remediation-r2/evidence/'+j['suite']+'.log) |' for j in records)
gate_rows='\n'.join('| '+key+' | '+value+' |' for key,value in gates.items())
replacement='Las seis suites se ejecutaron completas después del freeze de source, con los comandos exactos y entorno registrados en [QA](remediation-r2/qa-summary.json) y el command ledger.\n\n| Suite | Estado | Tests | Failures | Errors | Skips | Duración | Evidencia |\n| --- | --- | ---: | ---: | ---: | ---: | --- | --- |\n'+rows+'\n\nNode ejecutó los mismos 20 archivos y reporta 128 casos; no se confunde ese conteo con las 20 unidades por archivo del reporte T0. Browser conserva sus 251 tests. E2E pasó de 83 a 86 por los tres tests nuevos de Home. B-FOCUS repite intencionalmente cobertura de lineage y no sustituye las demás suites.\n\nB-SQL conserva el alcance del SQLSandbox histórico indicado por §22.1. La nueva migración se prueba además contra todas las migraciones vigentes en el sandbox E2E, incluyendo fresh y upgrade real.\n\nSe conservan todos los intentos fallidos: el primer Browser completo corrió 251 tests con 3 failures y 6 errors; los focales aislaron los residuales sin una nueva auditoría. Los dos timeouts intermitentes de Home/toolbar pasaron sin cambiar producto en su focal y en la suite completa final; no se les atribuye una causa no demostrada ni se les otorga una exención. Los cinco E2E originales tienen focal PASS y pasan también en la suite final de 86. [Causas](remediation-r2/evidence/root-causes.json), [focales](remediation-r2/evidence/focal-ledger.json), [primer Browser](remediation-r2/evidence/B-BROWSER.attempt1.log).\n\n| Gate | Resultado / alcance |\n| --- | --- |\n'+gate_rows+'\n\nLos PASS corresponden a T0 y su baseline vigente. No certifican entregables de fases Ultimate futuras ni autorizan release productivo.'
text=text.replace('Pendiente de consolidar las seis suites completas y reevaluar G-B, G-C, G-D, G-R, G-L, G-S, G-ENV, G-A y G-UI con sus resultados finales. Los focales no sustituyen este gate.',replacement)
text=text.replace('los resultados R2 se incorporarán en campos separados y evidencia propia.','los resultados R2 se incorporan en campos separados y evidencia propia.')
text+='\n\nLas 31 piezas de source/tests pendientes respecto de HEAD (incluidas las heredadas de T0-R) coinciden con el freeze. T0-R2 modificó 13 archivos respecto del estado inicial: una corrección CSS de baja altura, una migración nueva y soporte/tests relacionados. [Scope y diff](remediation-r2/evidence/r2-scope-diff.json), [freeze](remediation-r2/evidence/final-source-freeze.json), [preservación](remediation-r2/evidence/preservation-checks.json). No se modificaron migraciones existentes, skips ni valores de timeout.\n\nLos 84 registros del manifiesto histórico T0-R se resuelven a archivos intactos o a sus bytes exactos archivados. Los planes conservan sus hashes originales. [Resolución histórica](remediation-r2/evidence/r1-integrity-resolution.json); [integridad R2](remediation-r2/artifact-integrity.json).\n\n## FINAL DECISION\n\n**GO — T0 baseline estabilizado. T1 puede ser solicitado.**\n'
report.write_text(text)
state={'captured_at':now,'head':freeze['head'],'status_short_branch':subprocess.check_output(['git','status','--short','--branch'],cwd=R,text=True),'T1_executed':False,'commit_created':False,'push_executed':False,'production_applied':False}
write(O/'final-workspace.json',state)
historical=T/'remediation/artifact-integrity.json';resolved=[]
for entry in json.loads(historical.read_text())['files']:
 candidates=[R/entry['path'],E/'r1-baseline'/entry['path']]
 match=next((p for p in candidates if p.exists() and sha(p)==entry['sha256']),None)
 assert match,('Historical R1 bytes missing',entry['path'])
 resolved.append({'path':entry['path'],'resolved':str(match.relative_to(R)),'sha256':entry['sha256']})
write(E/'r1-integrity-resolution.json',{'manifest_sha256':sha(historical),'matched':len(resolved),'unresolved':[],'resolved':resolved})
paths=set([report,T/'debt-register.md',T/'debt-register.json',T/'baseline-test-ledger.json',T/'command-ledger.json',T/'artifact-integrity.json',T/'t0-remediation-report.md',T/'remediation/artifact-integrity.json',R/'DATION_FINAL_MASTER_EXECUTION_PLAN.md',R/'docs/ultimate-mvp-implementation-master-plan.md'])
paths.add(R/original_source_manifest['path'])
paths.update(R/p for p in freeze['files']);paths.update(p for p in O.rglob('*') if p.is_file() and p!=O/'artifact-integrity.json')
manifest={'phase':'T0-R2','captured_at':now,'decision':'GO','excludes_self':True,'historical_T0_and_R1_manifests_preserved':True,'files':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(paths)]}
write(O/'artifact-integrity.json',manifest)
assert all(sha(R/e['path'])==e['sha256'] for e in manifest['files'])
print(json.dumps({'decision':'GO','suites':{j['suite']:j['tests'] for j in records},'manifest_files':len(manifest['files']),'report':str(report),'T1_executed':False}))
