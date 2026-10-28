from pathlib import Path
from collections import Counter
import hashlib,json,shutil,statistics,subprocess,re

r=Path('/workspace/Dation');w=Path('/workspace/work/dation-t11-r')
out=r/'docs/execution/ultimate/t11';ev=out/'evidence/remediation'
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=read(w/'source-under-test-opt6.json');original=read(out/'evidence/source-under-test.json')
expected={'backend/app/domain/logistics/base.py','backend/app/engines/assignment/transport_plan.py','backend/app/engines/assignment/transport_policy_result.py','backend/app/results/assembler.py','backend/app/results/contracts.py','backend/app/results/reason_codes.py','backend/app/results/validation.py'}
assert {k for k,v in source['files'].items() if v!=original['files'][k]}==expected
assert all(sha(r/k)==v['sha256'] for k,v in source['files'].items())
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip();assert head==source['head']
history=read(out/'dossier-manifest.json');assert all(sha(out/k)==v['sha256'] for k,v in history['files'].items())
baseline=read(w/'baseline-manifest.json')
allowed=expected|{'backend/tests/test_ultimate_performance.py'}
assert all(sha(r/k)==v['sha256'] for k,v in baseline['files'].items() if k not in allowed)
py=read(w/'b-py-coverage-final.json');e2e=read(w/'e2e-final/suite-report.json');coverage=read(w/'e2e-coverage-final.json')
assert py['passed_executions']==688 and py['active_unique_ids']==680 and not any(py[k] for k in ['failures','errors','skips'])
assert e2e['passed'] and e2e['tests']==12 and not any(e2e[k] for k in ['failures','errors','skipped'])
assert coverage['active']==116 and not coverage['missing']
assert read(w/'schemas-18-before.json')==read(w/'schemas-18-after.json')
samples=read(w/'performance-opt6/engine-assembler.json')['samples'];gold=read(w/'profile-before/golden-full-publication.json')
assert len(samples)==5 and all(s['d1_publication']==gold for s in samples)
assert all(s['d1_fixture_contract_seconds']+s['d1_engine_seconds']+s['d1_assembler_seconds']<=90 for s in samples)
jobs=[read(p) for p in sorted((w/'full-worker-opt6').glob('complete-cold-job-*.json'))]
assert len(jobs)==2 and (w/'full-worker-opt6.log').read_text().endswith('\nOK\n')
image='sha256:b26cfedb7e7a70927171801dd89b44429b568b719528328cc5b99e78cf781ddb'
for j in jobs:
 assert j['admission_to_observed_complete_seconds']<=90 and j['worker']['complete_execution_seconds']<=90
 assert j['image_id']==j['api_image_id']==image
 assert j['limits']=={'memory_bytes':1073741824,'nano_cpus':2000000000}
 assert int(j['worker']['memory.max'])==1073741824 and int(j['worker']['memory.peak'])<.9*1073741824
image_sources=read(w/'image-source-hashes.json');assert len(image_sources)==327
assert all(source['files'][k]['sha256']==v for k,v in image_sources.items())

for name in ['git-status-final.txt','image-runtime.json','image-source-hashes.json','final-performance-summary.json','b-py-coverage-final.json','e2e-coverage-final.json','consistency-t8-final.log','full-worker-opt6.log']:
 shutil.copyfile(w/name,ev/name)
for name in ['e2e-final','consistency-final','full-worker-opt6']:
 shutil.copytree(w/name,ev/name,dirs_exist_ok=True)
shutil.copyfile(w/'source-under-test-opt6.json',ev/'source-under-test.json')
shutil.copyfile(w/'finalize_remediation.py',ev/'finalize_remediation.py')
shutil.copyfile('/workspace/work/dation-t11/Dockerfile.certification',ev/'Dockerfile.local-qa')

harness_names=['backend/tests/test_ultimate_performance.py','backend/tests/e2e/test_ultimate_scale.py','backend/tests/e2e/ultimate_scale_worker.py','backend/tests/fixtures/ultimate/t11-r-scale-golden.json','backend/tests/e2e/test_ultimate_consistency.py','backend/tests/e2e/test_ultimate_d1_result.py','backend/tests/e2e/ultimate_certification_support.py','backend/tests/e2e/ultimate_certification_fixture.py','backend/tests/integration/test_ultimate_restore.py']
harness={}
for name in harness_names:
 target=ev/'harness'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/name,target);harness[name]={'bytes':target.stat().st_size,'sha256':sha(target)}
(ev/'harness-source-manifest.json').write_text(json.dumps(harness,indent=2)+'\n')
full_patch=subprocess.check_output(['git','diff','--binary','HEAD','--','backend/app'],cwd=r)
(ev/'application-candidate-vs-head.patch').write_bytes(full_patch)

preservation={'head':head,'original_dossier_files_verified':len(history['files']),'original_dossier_unchanged':True,'original_pending_non_remediation_files_unchanged':True,'source_files':len(source['files']),'changed_application_files':sorted(expected),'unchanged_other_source_files':len(source['files'])-len(expected),'image_backend_asset_files_verified':len(image_sources),'schemas_identical':18,'no_push':True,'no_deploy':True,'T12_executed':False}
(ev/'scope-preservation.json').write_text(json.dumps(preservation,indent=2)+'\n')

metrics=read(w/'final-performance-summary.json');profile=read(w/'profile-exclusive-comparison.json')
fmt=lambda x:f'{x:.3f}'
rows='\n'.join(f"| {v['stage']} | {v['before_seconds']:.3f} | {v['before_percent']:.1f}% | {v['after_seconds']:.3f} | {v['after_percent']:.1f}% |" for v in profile['stages'])
profile_text=f'''\nMedición diagnóstica antes/después: {profile['before_total']:.3f} → {profile['after_total']:.3f} s. Tiempos exclusivos, sin doble conteo; los porcentajes usan el subtotal motor+assembler de cada perfil. Los tiempos inclusivos/CPU/calls y stacks están en [los JSON](evidence/remediation/profile-after-6/profile.json). Los guards están incluidos; el snapshot de diagnóstico se identifica en el perfil y no altera la medición formal.

| Fase exclusiva | Antes s | Antes % | Después s | Después % |
|---|---:|---:|---:|---:|
{rows}

Los tres objetivos alternativos se exploran bajo los presupuestos originales; sus tiempos inclusivos por objetivo se registran en cada perfil y no se suman nuevamente a esta tabla. `complete_evidence_reassembly` corresponde al adapter de filas sin tipar del baseline; después el merge de las particiones ya tipadas aparece como `whole_evidence_merge`, con validación del proof completo preservada. No hubo pruning, hints, concurrencia, timeouts nuevos ni cambio de estado de alternativas para acelerar.
'''

probe_rows='\n'.join(f"| {i} | {s['d1_fixture_contract_seconds']:.3f} | {s['d1_engine_seconds']:.3f} | {s['d1_assembler_seconds']:.3f} | {s['d1_fixture_contract_seconds']+s['d1_engine_seconds']+s['d1_assembler_seconds']:.3f} | {s['d1_engine_cpu_seconds']+s['d1_assembler_cpu_seconds']:.3f} | {s['peak_rss_kib']} |" for i,s in enumerate(samples,1))
job_rows='\n'.join(f"| {i} | {j['admission_to_observed_complete_seconds']:.3f} | {j['worker']['complete_execution_seconds']:.3f} | {j['worker']['complete_execution_cpu_seconds']:.3f} | {int(j['worker']['memory.peak'])/1024**2:.2f} | {j['startup_seconds_before_admission']:.3f} |" for i,j in enumerate(jobs,1))
stage_rows=[]
for label in sorted({e['stage'] for j in jobs for e in j['worker']['events']}):
 vals=[sum(e['seconds'] for e in j['worker']['events'] if e['stage']==label) for j in jobs]
 stage_rows.append(f'| {label} | {vals[0]:.3f} | {vals[1]:.3f} |')
for label,vals in [
 ('Other input contract/context + orchestration',[j['worker']['complete_execution_seconds']-sum(e['seconds'] for e in j['worker']['events']) for j in jobs]),
 ('Admission + queue + completion observation',[j['admission_to_observed_complete_seconds']-j['worker']['complete_execution_seconds'] for j in jobs])]:
 stage_rows.append(f'| {label} | {vals[0]:.3f} | {vals[1]:.3f} |')
performance=f'''## Before / After — formal PERF11 y job completo

Fixture exacto preservado: 500 Orders / 50 Resources / 31 días; `max_slots=128`, `max_variables=20000`, `deterministic_budget=5`, `kernel_budget=2`, seed 0. Candidate model limitado/honesto: 128 slots, 2816 variables declaradas, hasta 6735 constraints. Recommended FEASIBLE, cobertura parcial de 128 Trips; una alternativa material, tres objetivos explorados. Subproblemas nativos FEASIBLE/OPTIMAL, sin MODEL_INVALID.

| Muestra fría | Fixture/contract s | Motor s | Assembler s | Total s | CPU motor+assembler s | Peak RSS KiB |
|---|---:|---:|---:|---:|---:|---:|
{probe_rows}

Antes (n=3): p50 **98.007 s**, p95 nearest rank/máximo **100.113 s**. Después (n=5, sumando además fixture/contract): p50 **61.632 s**, p95 nearest rank/máximo **64.241 s**, mínimo **59.724 s**. Delta p50 **−36.374 s / −37.11%**; máximo baja **35.872 s / 35.83%**. Ninguna muestra se descartó. [Samples completos](evidence/remediation/performance-opt6/engine-assembler.json), [resumen](evidence/remediation/final-performance-summary.json).

El golden completo coincide en 5/5 muestras: package 343055 B, visual 45693 B, 83 artifacts / 43500169 B, máximo chunk 1047272 B / 100 filas. D2 conserva fingerprint `ffab2ab4189c27c643e11f80a0a8cb0cf6eef7fcd199735433b5d9091b7b0040`. Serializer de 1000 filas: 10 chunks / 770470 B, sin pérdida de filas. No se presenta ese stress como 1000 Trips reales del engine.

Las dos primeras Runs de procesos API+worker nuevos usan la imagen final real y CSVs/Model/Case/Pack creados por APIs en un sandbox owned. El reloj comienza ANTES del POST /api/runs y termina al observar COMPLETED; abarca admission, validación/carga de inputs, cola, motor, assembler, preparación, 83 uploads, recuperación/verificación de todos los objetos y finish. No hay negocio precalculado ni cache entre muestras. El arranque del servicio/health anterior a la admisión se registra separado; la envolvente de 90 s es de ejecución de la Run, no un SLO de aprovisionamiento del servicio.

| Primera Run fría | Admission→COMPLETED s | Worker completo s | Worker CPU s | Peak cgroup MiB | Startup previo s |
|---|---:|---:|---:|---:|---:|
{job_rows}

Job completo: p50 **87.486 s**, p95 nearest rank/máximo **88.174 s**; 2/2 PASS bajo **90 s**. Son las dos muestras predefinidas, sin repetir hasta obtener una favorable. Ensayos de versiones intermedias fallidos permanecen en el dossier. El test conserva timeout de observación 180 s sólo para registrar un exceso; el assert de aprobación sigue en 90 s.

| Etapa del worker/job | Run 1 s | Run 2 s |
|---|---:|---:|
{chr(10).join(stage_rows)}

Input/context loading y contract validation están incluidos en el reloj total, el evento de verificación y el residual de orquestación, además de los checks internos del motor. La normalización de uploads pertenece a la preparación del Pack, anterior a solicitar una Run; no se mueve ninguna etapa de ejecución fuera del reloj.

Worker real acotado: **2 CPU / 1 GiB**; pico **762765312 B (727.43 MiB)**, margen **28.96%**, sin OOM y por debajo del assert de 90% de su límite. Probe RSS final máximo **755756 KiB (~738.04 MiB)**; baseline máximo 723364 KiB (~706.41 MiB). No se declara una reducción de memoria comparando RSS y cgroup. [Imagen](evidence/remediation/image-runtime.json): Python **3.13.16**, OR-Tools **9.15.6755**, Pydantic **2.14.0**; B-PY/probe host Python **3.13.5**, runtime exterior **2 CPU / 8 GiB**. La prueba completa acotada complementa la probe host; no se extrapola su tiempo.

HTTP de escala mide por separado cinco lecturas reales de result/primary-visual/details-plan después de completar cada Run, incluidos bytes y p50/p95. No se usa esa lectura posterior para descontar trabajo de publicación. [Run 1](evidence/remediation/full-worker-opt6/complete-cold-job-1.json), [Run 2](evidence/remediation/full-worker-opt6/complete-cold-job-2.json).

'''

tests='''Resultados finales:

| Gate reejecutado | Resultado |
|---|---|
| B-PY | **688 ejecuciones PASS**, 393.054 s, 0 failures/errors/skips; **680 IDs únicos** |
| PERF11 | Incluido en B-PY: seis métodos, cinco procesos fríos; payload/scale/bytes/budget PASS |
| Job completo de escala en imagen | **1 test / 2 escenarios fríos PASS**, 276.521 s totales incluidos setup/cleanup |
| CONSISTENCY11 | **4 PASS**, D1/D2 entre Dashboard, Details, CSV, JSON, IA, Review y Entity, incluidos negativos |
| E8 / T8 publicación | **8 PASS**, crashes/partial uploads/lost responses/lease/replay/history/Pack/permisos/integridad |
| U6/U7/U9 y serialización/contratos | **200 focales PASS** sobre la fuente final, más B-PY completo |
| Schema/correctness | **18 schemas idénticos**, 5/5 golden completo, vectores post-T10 PASS |

Los 12 rechecks CONSISTENCY11+E8 terminaron en 132.641 s, sin fallos/errors/skips. [Ledger](evidence/remediation/e2e-final/suite-report.json). El discovery actual E2E tiene **116 IDs**, todos cubiertos por 115 certificados previos, los rechecks afectados y el nuevo test de escala; cero missing/extra. No se cuentan aliases o rechecks como casos nuevos. [Coverage E2E](evidence/remediation/e2e-coverage-final.json).

Precisión del conteo B-PY: el discovery ya repetía ocho SchedulingEngineTests en T11; también están duplicados en la ejecución actual. Se conservaron, sin quitar cobertura ni reescribir tests ajenos. Los 688 son ejecuciones, 680 IDs únicos (baseline 687/679). Se verificó igualdad exacta entre IDs actuales descubiertos y ejecutados, con multiplicidades; cero missing/extra. [Coverage Python](evidence/remediation/b-py-coverage-final.json).

Comandos finales, desde backend/ y con variables Supabase/GCP/LLM productivas vacías:

```sh
python -B -m unittest discover -s tests -v
PYTHONPATH=tests/e2e python -B -m unittest test_ultimate_scale -v
python -B tests/e2e/run_suite.py --module test_ultimate_consistency --module test_ultimate_d1_result
```

Python host: `/workspace/Dation/.venv/bin/python`. Las variables de salida DATION_T11_* sólo ubican evidencias. Docker usa el socket local verificado; API y worker reciben credenciales sintéticas loopback del sandbox. El launcher observacional se monta read-only y no forma parte de la imagen de aplicación. No hace matemática ni cambia productores/validadores.

'''

candidate_old=read(out/'release-candidate-status.json')
assert all(sha(r/k)==v for k,v in candidate_old['knowledge'].items())
frozen_source={**source,'status':'FROZEN_LOCAL_QA_CANDIDATE','application_image_id':image,'T12_executed':False,'push_executed':False,'deploy_executed':False}
(ev/'source-frozen.json').write_text(json.dumps(frozen_source,indent=2)+'\n')
candidate={'status':'FROZEN_LOCAL_WORKTREE_QA_CANDIDATE_NOT_DEPLOYED','phase':'T11-R','decision':'GO','head_checkpoint':head,'branch':'main','application_source_content_sha256':source['source_content_sha256'],'source_manifest':'evidence/remediation/source-frozen.json','image_local':image,'image_tag':'dation-certification:t11-r-under-test','image_backend_assets_matching_files':327,'working_tree_changes_not_yet_committed':True,'application_remediation_patch':'evidence/remediation/application-remediation-only.patch','harness_source_manifest':'evidence/remediation/harness-source-manifest.json','application_candidate_patch':'evidence/remediation/application-candidate-vs-head.patch','versions':candidate_old['versions'],'migrations':candidate_old['migrations'],'knowledge':candidate_old['knowledge'],'artifact_layout':candidate_old['artifact_layout'],'rollback_scope':'Previously tested dual-compatible backend/readers/worker. Close admissions and drain/recover jobs; retain DB/artifacts and use no destructive schema downgrade. No visual rollback assertion.','historical_status_preserved':'release-candidate-status.json','previous_rollback_backend_image':candidate_old['prepared_rollback_image_tested'],'rollback_scope_erratum':'Historical Dockerfile overlay did not replace served Config; backend/reader/worker compatibility remains the scope of existing restore proof. No visual rollback claim.','T12_authorized':False,'T12_executed':False,'push_executed':False,'deploy_executed':False,'production_modified':False}
(out/'release-candidate-status-t11-r.json').write_text(json.dumps(candidate,indent=2)+'\n')
gate=f'''## Gate evaluation

| Gate | Resultado | Evidencia / alcance |
|---|---|---|
| G-A alcance | PASS | Siete archivos de aplicación; sin auditoría nueva, features, UI, infraestructura o producción |
| G-C contrato | PASS | 18 schemas y bytes del package + 83 artifacts idénticos; validadores conservados |
| G-D datos | PASS preservado | SQL/restore/hashes/ACL anteriores, cero cambios de schema/migraciones/Storage protocol |
| G-E engine | PASS | U6/U7/U9/oracles e invariantes; solver/policies/Transit inalterados |
| G-R resultado | PASS | CONSISTENCY11/E8 reejecutados; R17 escala verificado con el job completo |
| G-L lineage | PASS | E8 historial/replay/Pack concurrente; fuentes y snapshots/approval sin cambios |
| G-S seguridad | PASS | Negativos de tenant/FP/Storage/integridad reejecutados; WARN históricos explícitos |
| G-P performance | PASS en entorno medido | 5/5 subtotales ≤64.241 s y 2/2 jobs completos ≤88.174 s; límite 90 s |
| G-UI preservación | PASS preservado | Frontend/CSS/assets/tokens idénticos a T11; ninguna Skill UI aplicada en T11-R |
| G-ENV QA | PASS | Python/Docker/SQL/API/worker reales disponibles; versiones y límites registrados |
| G-B suites | PASS | B-PY688/680 únicos; affected12+new1 y matriz previa no afectada con coverage completo |
| G-REL candidato local | PASS | Fuentes/imagen/versions/migrations y evidencia congeladas para revisión; **T12 no autorizado** |

La remediación cierra los cuatro failures originales: una expectativa inválida del harness y tres excesos reales de tiempo. No hay regresiones funcionales nuevas demostradas por los gates afectados. No se reabren T0–T10 ni la auditoría general.

## Release Candidate Manifest

Candidato **local de working tree**, HEAD checkpoint `{head}`, branch `main`. SHA256 del paquete de 380 fuentes **`{source['source_content_sha256']}`**. Imagen local API/worker **`{image}`**; 327 archivos backend/assets comparados por hash. Las fuentes T11/T11-R siguen pendientes de commit; HEAD por sí solo NO contiene estos fixes. [Manifest de candidato](release-candidate-status-t11-r.json), [fuentes](evidence/remediation/source-frozen.json), [scope](evidence/remediation/scope-preservation.json), [diff T11-R exclusivo](evidence/remediation/application-remediation-only.patch), [patch completo de aplicación contra HEAD](evidence/remediation/application-candidate-vs-head.patch) y [fuentes del harness](evidence/remediation/harness-source-manifest.json).

Los 311 archivos del dossier original permanecen byte a byte iguales. [Índice de remediación](T11-R-index.md) incorpora este resultado sin borrar el STOP histórico. El manifest nuevo enumera la evidencia de esta remediación. Ninguna imagen se publicó, no hubo commit/push/deploy, ni cambios de infraestructura, credenciales, triggers o configuración productiva. El pipeline de producción no se disparó desde esta tarea.

**GO — T11 completado. T12 puede ser solicitado.**
'''

body=(w/'report-notes.md').read_text()
body=body.replace('los 12 schemas JSON','los 18 schemas JSON completos, comparando también los contratos originales previos al refactor')
body=body.replace('688 tests activos, frente a 687 del baseline','688 ejecuciones, frente a 687 del baseline; IDs únicos y duplicados heredados se detallan abajo')
body=body.replace('## Changes',profile_text+'\n## Changes',1)
body=body.replace('## Tests / Re-executed gates',performance+'## Tests / Re-executed gates\n\n'+tests,1)
body=body.replace('se conservarán con la evidencia','se conservaron con la evidencia').replace('Conservar la pasada B-PY intermedia fallida','Se conservaron la pasada B-PY intermedia fallida').replace('se detallan abajo','se detallan en el ledger anterior').replace('- p95 empírico','- El margen temporal del peor job final es 1.826 s frente a90 s; la certificación aplica al fixture/runtime medidos, sin promesa de latencia bajo otras cargas.\n- p95 empírico')
body=body.split('## Gate evaluation')[0]+gate
body=body.replace('# T11-R — Targeted D1 performance remediation + Python failure closure','# T11-R — Targeted D1 performance remediation + Python failure closure\n\nFecha: 2026-10-28 UTC. Estado final: **GO**. Fuente: autorización T11-R, Master Plan y STOP T11 previos. [Autorización preservada](evidence/remediation/T11-R-user-request.txt).')
(out/'t11-remediation-report.md').write_text(body)
(out/'T11-R-index.md').write_text('''# T11 — Conclusión vigente de T11-R

La remediación autorizada concluyó **GO**. [Reporte completo](t11-remediation-report.md). **T12 no ejecutado ni autorizado; sin commit, push o deploy.**

- [Estado del candidato local](release-candidate-status-t11-r.json).
- [Manifest de fuentes](evidence/remediation/source-frozen.json).
- [Coverage Python](evidence/remediation/b-py-coverage-final.json) y [E2E](evidence/remediation/e2e-coverage-final.json).
- [Performance formal y completo](evidence/remediation/final-performance-summary.json).
- [Manifest de esta remediación](t11-remediation-manifest.json).

El [reporte original](t11-execution-report.md), [estado bloqueado original](release-candidate-status.json) y [manifest original](dossier-manifest.json) conservan el STOP histórico. Sus 311 hashes no cambian. La conclusión vigente se incorpora mediante este suplemento, sin presentar los fallos anteriores como PASS retroactivo.
''')
files=[p for p in ev.rglob('*') if p.is_file()]+[out/n for n in ['t11-remediation-report.md','T11-R-index.md','release-candidate-status-t11-r.json']]
manifest={'phase':'T11-R','decision':'GO','head_checkpoint':head,'frozen_source_sha256':source['source_content_sha256'],'historical_dossier_files_unchanged':311,'files':{str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)}}
(out/'t11-remediation-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'report':str(out/'t11-remediation-report.md'),'decision':'GO','remediation_files':len(files),'source_sha256':source['source_content_sha256'],'image':image},indent=2))
