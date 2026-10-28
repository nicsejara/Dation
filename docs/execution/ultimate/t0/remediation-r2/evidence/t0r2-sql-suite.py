import fcntl,json,os,subprocess,time
from pathlib import Path
from uuid import uuid4
w=Path('/workspace/work/dation-t0r2');name='dation-t0r2-sql-'+uuid4().hex[:10]
env=os.environ.copy()
for key in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_ACCESS_TOKEN','LLM_API_KEY','LLM_BASE_URL','GCP_ACCESS_TOKEN']:env[key]=''
for key in ['DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
env['DOCKER_HOST']='unix:///var/run/docker.sock'
def docker(*args):
 r=subprocess.run(['docker','--host=unix:///var/run/docker.sock',*args],env=env,capture_output=True,text=True,timeout=60)
 if r.returncode:raise RuntimeError(r.stderr)
 return r.stdout.strip()
created=False
try:
 with open('/tmp/dation-t0r-suite.lock','a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  version=docker('info','--format','{{.ServerVersion}}')
  identifier=docker('run','-d','--name',name,'--label','dation.task=T0-R2','--network','none','-e','POSTGRES_HOST_AUTH_METHOD=trust','postgres:17-alpine');created=True
  for _ in range(150):
   ready=subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','postgres'],env=env,capture_output=True).returncode==0
   if ready:break
   time.sleep(.1)
  else:raise RuntimeError('Owned SQL PostgreSQL did not become ready')
  (w/'owned-sql-container.json').write_text(json.dumps({'name':name,'id':identifier,'docker_server':version,'network':'none','label':'dation.task=T0-R2','production_applied':False},indent=2)+'\n')
 r=subprocess.run(['/workspace/Dation/.venv/bin/python','-B','/tmp/dation-t0r2-run-suite.py','B-SQL','--sql-container',name],env=env)
finally:
 if created:
  with open('/tmp/dation-t0r-suite.lock','a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);docker('rm','-f','-v',name)
raise SystemExit(r.returncode)
