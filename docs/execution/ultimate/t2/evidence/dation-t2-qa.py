"""Required T2 suites and three API boundary checks, all owned/local."""
from datetime import datetime,timezone
from pathlib import Path
import glob,hashlib,json,os,re,subprocess,time

ROOT=Path('/workspace/Dation');BACKEND=ROOT/'backend';OUT=Path('/workspace/work/dation-t2')
env=os.environ.copy()
for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:
    env[key]=''
for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:
    env.pop(key,None)
env.update(PYTHONDONTWRITEBYTECODE='1',DATION_SQL_TEST_CONTAINER='dation-t2-20261026-ultimate',
    DATION_T2_EVIDENCE=str(OUT/'sql'),DATION_E2E_ARTIFACTS=str(OUT/'api-smoke'))
PY=str(ROOT/'.venv/bin/python')
commands={
 'B-PY':[PY,'-B','-m','unittest','discover','-s','tests','-v'],
 'B-NODE':['node','--test',*sorted(glob.glob('tests/test_*.js',root_dir=BACKEND)),*sorted(glob.glob('tests/test_*.mjs',root_dir=BACKEND))],
 'B-SQL':[PY,'-B','-m','unittest','discover','-s','tests/integration','-p','test_*.py','-v'],
 'S2':[PY,'-B','-m','unittest','test_ultimate_schema','-v'],
 'FOCAL-API':[PY,'-B','-m','unittest',
  'test_decision_center.DecisionCenterTests.test_01_case_library_labels_pagination_identity_and_isolation',
  'test_data_hub.DataHubTests.test_02_detail_preview_filters_and_derived_packs_preserve_case_history',
  'test_home_owner_attention.HomeOwnerAttentionTests.test_fresh_schema_owner_nonowner_viewer_and_tenant_boundaries','-v'],
}
for name,command in commands.items():
    child=env.copy()
    if name=='S2':child['PYTHONPATH']='tests/integration'
    if name=='FOCAL-API':child['PYTHONPATH']='tests/e2e'
    started=datetime.now(timezone.utc).isoformat();begin=time.monotonic()
    print(json.dumps({'suite':name,'state':'RUNNING','started_at':started}),flush=True)
    with (OUT/(name+'.log')).open('w') as log:
        result=subprocess.run(command,cwd=BACKEND,env=child,text=True,stdout=log,stderr=subprocess.STDOUT)
    data=(OUT/(name+'.log')).read_text()
    if name=='B-NODE':
        def count(label):
            match=re.search(r'^(?:# |ℹ )'+label+r' (\d+)$',data,re.M)
            return int(match.group(1)) if match else 0
        tests=count('tests');failures=count('fail');skips=count('skipped');errors=0
    else:
        counts=re.findall(r'^Ran (\d+) tests? in ([\d.]+)s',data,re.M)
        tests=int(counts[-1][0]) if counts else 0
        failures=len(re.findall(r'^FAIL:',data,re.M));errors=len(re.findall(r'^ERROR:',data,re.M))
        skipped=re.search(r'^OK \(skipped=(\d+)\)',data,re.M)
        skips=int(skipped.group(1)) if skipped else len(re.findall(r'^test_.* \.\.\. skipped',data,re.M))
    status='PASS' if result.returncode==0 and tests and failures==errors==skips==0 else 'FAIL'
    record=dict(suite=name,status=status,tests=tests,failures=failures,errors=errors,skips=skips,
        started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),seconds=round(time.monotonic()-begin,3),
        cwd=str(BACKEND),command=command,exit_code=result.returncode,production_credentials_cleared=True,
        container=child['DATION_SQL_TEST_CONTAINER'] if name in {'B-SQL','S2'} else None,
        PYTHONPATH=child.get('PYTHONPATH'),log_path=str(OUT/(name+'.log')),
        log_sha256=hashlib.sha256((OUT/(name+'.log')).read_bytes()).hexdigest())
    (OUT/(name+'.result.json')).write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if status!='PASS':raise SystemExit(1)
