"""T1 scoped suite runner. No database, browser, remote API or Docker operations."""
from datetime import datetime, timezone
from pathlib import Path
import glob,hashlib,json,os,re,subprocess,time

ROOT=Path('/workspace/Dation');BACKEND=ROOT/'backend';OUT=Path('/workspace/work/dation-t1')
env=os.environ.copy()
for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:
    env[key]=''
env['PYTHONDONTWRITEBYTECODE']='1'
commands={
 'U1':[str(ROOT/'.venv/bin/python'),'-B','-m','unittest','tests.test_ultimate_contracts','tests.test_ultimate_transit','-v'],
 'B-PY':[str(ROOT/'.venv/bin/python'),'-B','-m','unittest','discover','-s','tests','-v'],
 'B-NODE':['node','--test',*sorted(glob.glob('tests/test_*.js',root_dir=BACKEND)),*sorted(glob.glob('tests/test_*.mjs',root_dir=BACKEND))],
}
for name,command in commands.items():
    started=datetime.now(timezone.utc).isoformat();begin=time.monotonic()
    print(json.dumps({'suite':name,'state':'RUNNING','started_at':started}),flush=True)
    with (OUT/(name+'.log')).open('w') as log:
        result=subprocess.run(command,cwd=BACKEND,env=env,text=True,stdout=log,stderr=subprocess.STDOUT)
    text=(OUT/(name+'.log')).read_text()
    if name=='B-NODE':
        def counter(label):
            match=re.search(r'^(?:# |ℹ )'+label+r' (\d+)$',text,re.M)
            return int(match.group(1)) if match else None
        tests=counter('tests');failures=counter('fail');skips=counter('skipped');errors=0
    else:
        counts=re.findall(r'^Ran (\d+) tests? in ([\d.]+)s',text,re.M)
        tests=int(counts[-1][0]) if counts else 0
        failures=len(re.findall(r'^FAIL:',text,re.M));errors=len(re.findall(r'^ERROR:',text,re.M))
        skipped=re.search(r'^OK \(skipped=(\d+)\)',text,re.M)
        skips=int(skipped.group(1)) if skipped else len(re.findall(r'^test_.* \.\.\. skipped',text,re.M))
    status='PASS' if result.returncode==0 and tests and failures==0 and errors==0 and skips==0 else 'FAIL'
    record={'suite':name,'status':status,'tests':tests,'failures':failures,'errors':errors,'skips':skips,
        'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-begin,3),
        'cwd':str(BACKEND),'command':command,'exit_code':result.returncode,'production_credentials_cleared':True,
        'log_path':str(OUT/(name+'.log')),'log_sha256':hashlib.sha256((OUT/(name+'.log')).read_bytes()).hexdigest()}
    (OUT/(name+'.result.json')).write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if status!='PASS':raise SystemExit(1)
