"""Owned PostgreSQL/PostgREST, Storage fixture, API and worker processes."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from auth_fixture import generate, token as user_token, USER_A, USER_B, VIEWER, DISABLED

import httpx

ROOT=Path(__file__).resolve().parents[2]
REPO=ROOT.parent
POSTGREST='postgrest/postgrest:v14.0@sha256:f8176256ad55a794a61ee6d76d00121635fac4d63bb3d51594e5ed6790f91c72'
PASSWORD='dispatch-e2e-private'


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


def jwt(secret,role):
    def b64(value):return base64.urlsafe_b64encode(value).rstrip(b'=')
    data=b'.'.join([b64(json.dumps({'alg':'HS256','typ':'JWT'}).encode()),
        b64(json.dumps({'role':role,'exp':int(time.time())+3600}).encode())])
    return (data+b'.'+b64(hmac.new(secret.encode(),data,hashlib.sha256).digest())).decode()


def wait_for(predicate,description,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.1)
    raise AssertionError('Timed out: '+description)


class Sandbox:
    def __init__(self, *, migration_hook=None):
        self.migration_hook=migration_hook

    def __enter__(self):
        self.identifier='dation-e2e-'+uuid4().hex[:12]
        self.database='dation_e2e'
        self.temp=tempfile.TemporaryDirectory(prefix=self.identifier+'-')
        self.directory=Path(self.temp.name)
        self.storage=self.directory/'storage';self.storage.mkdir()
        self.containers=[];self.processes=[];self.logs=[];self.worker=None;self.api=None
        try:
            self.start()
            return self
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def docker(self,*args):
        result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=120)
        if result.returncode:raise RuntimeError(result.stderr[-3000:])
        return result.stdout.strip()

    def sql(self,sql):
        result=subprocess.run(['docker','exec','-i',self.pg,'psql','-U','postgres','-d',self.database,
            '-X','-A','-t','-v','ON_ERROR_STOP=1'],input=sql,text=True,capture_output=True,timeout=30)
        if result.returncode:raise AssertionError(result.stderr)
        return result.stdout.strip()

    def start(self):
        self.network=self.identifier+'-net';self.docker('network','create',self.network)
        self.pg=self.identifier+'-pg'
        self.containers.append(self.pg)
        self.docker('run','-d','--name',self.pg,'--network',self.network,'--network-alias','postgres',
            '-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_DB='+self.database,'postgres:17-alpine')
        def pg_ready():
            result=subprocess.run(['docker','exec',self.pg,'pg_isready','-h','127.0.0.1','-U','postgres'],capture_output=True)
            return result.returncode==0
        wait_for(pg_ready,'final PostgreSQL TCP server')
        self.sql((ROOT/'tests/integration/infrastructure.sql').read_text())
        self.sql("CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,email_confirmed_at timestamptz); CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid $$; GRANT USAGE ON SCHEMA auth TO authenticated; GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;")
        self.sql((REPO/'supabase/baseline/20261010100000_public_schema.sql').read_text())
        for migration in sorted((REPO/'supabase/migrations').glob('*.sql')):
            if migration.name[:14]>'20261010100000':
                if self.migration_hook:self.migration_hook(self,migration.name)
                self.sql(migration.read_text())
        self.sql("UPDATE dation_private.platform_release SET admissions_open=true,workflow_gates_enabled=true;")
        for uid in (USER_A,USER_B,VIEWER,DISABLED):
            self.sql(f"INSERT INTO auth.users VALUES('{uid}','user-{uid[-1]}@example.test',now());")
        self.sql(f"INSERT INTO dation_private.legacy_owners(email,workspace_id) VALUES('user-1@example.test','00000000-0000-4000-8000-00000000da71'); SELECT platform_identity('{USER_A}'); SELECT platform_identity('{USER_B}');")
        self.workspace_a='00000000-0000-4000-8000-00000000da71'
        self.workspace_b=json.loads(self.sql(f"SELECT platform_create_workspace('{USER_B}','Workspace B','AR','UTC','ARS');"))['workspace_id']
        self.sql(f"INSERT INTO workspace_members(workspace_id,user_id,access_role,status) VALUES('{self.workspace_a}','{VIEWER}','viewer','active'),('{self.workspace_a}','{DISABLED}','operator','disabled');")
        # Engine/evidence scenarios start with eligible synthetic operators.
        # Ownership gate and role tests explicitly reset this fixture state.
        for wid,uid in ((self.workspace_a,USER_A),(self.workspace_b,USER_B)):
            self.sql(f"SELECT platform_set_member_responsibilities('{wid}','{uid}','{uid}',(SELECT updated_at FROM workspace_members WHERE workspace_id='{wid}' AND user_id='{uid}'),ARRAY['data_steward','decision_owner','approver']);")
        self.sql("CREATE ROLE dation_e2e_authenticator LOGIN NOINHERIT; GRANT anon,authenticated,service_role TO dation_e2e_authenticator;")
        secret=secrets.token_urlsafe(48)
        fixture_url='http://127.0.0.1:'+str(port())
        self.auth_key=generate(self.directory,fixture_url)
        public=json.loads((self.directory/'auth-fixture-jwks.json').read_text())
        public['keys'].append({'kty':'oct','alg':'HS256','k':base64.urlsafe_b64encode(secret.encode()).rstrip(b'=').decode()})
        self.token=jwt(secret,'service_role');self.anon_token=jwt(secret,'anon')
        self.rest_container=self.identifier+'-rest'
        self.containers.append(self.rest_container)
        self.docker('run','-d','--name',self.rest_container,'--network',self.network,
            '-p','127.0.0.1::3000','-e','PGRST_DB_URI=postgres://dation_e2e_authenticator@postgres:5432/'+self.database,
            '-e','PGRST_DB_ANON_ROLE=anon','-e','PGRST_JWT_SECRET='+json.dumps(public),POSTGREST)
        binding=self.docker('port',self.rest_container,'3000/tcp')
        self.rest_url='http://'+binding
        self.env={**os.environ,'SUPABASE_URL':fixture_url,
            'SUPABASE_SECRET_KEY':self.token,'SUPABASE_INPUT_BUCKET':'dda-inputs',
            'DATION_ACCESS_PASSWORD':PASSWORD,'LLM_API_KEY':'','LLM_BASE_URL':'','GCP_ACCESS_TOKEN':'',
            'SUPABASE_ACCESS_TOKEN':'','NO_PROXY':'127.0.0.1,localhost',
            'DATION_E2E_AUTH':str(self.directory),'DATION_E2E_STORAGE':str(self.storage),'DATION_E2E_REST':self.rest_url,'DATION_MAX_QUEUED_RUNS':'32'}
        self.user_tokens={uid:user_token(self.auth_key,self.env['SUPABASE_URL'],uid) for uid in (USER_A,USER_B,VIEWER,DISABLED)}
        self.http=httpx.Client(trust_env=False,timeout=30)
        wait_for(lambda:self.reachable(self.rest_url+'/',{'Authorization':'Bearer '+self.token}), 'authorized PostgREST catalog')
        self.start_process('storage',['-m','uvicorn','storage_gateway:app','--host','127.0.0.1',
            '--port',self.env['SUPABASE_URL'].rsplit(':',1)[1]],cwd=ROOT/'tests/e2e')
        wait_for(lambda:self.reachable(self.env['SUPABASE_URL']+'/rest/v1/',{'Authorization':'Bearer '+self.token}), 'Storage/REST gateway')
        self.api_port=port();self.api_url='http://127.0.0.1:'+str(self.api_port)
        self.api_client=httpx.Client(base_url=self.api_url,headers={'Authorization':'Bearer '+self.user_tokens[USER_A]},trust_env=False,timeout=30)
        self.db=httpx.Client(base_url=self.env['SUPABASE_URL']+'/rest/v1/',headers={
            'Authorization':'Bearer '+self.token,'apikey':self.token},trust_env=False,timeout=30)
        self.start_api()

    def reachable(self,url,headers=None):
        try:return self.http.get(url,headers=headers,timeout=1).status_code==200
        except httpx.HTTPError:return False

    def start_process(self,name,args,cwd=ROOT,env=None):
        logfile=(self.directory/(name+'-'+str(len(self.processes))+'.log')).open('w+')
        self.logs.append(logfile)
        process=subprocess.Popen([sys.executable,*args],cwd=cwd,env=env or self.env,stdout=logfile,stderr=subprocess.STDOUT)
        self.processes.append(process)
        return process

    def start_api(self):
        self.api=self.start_process('api',['-m','uvicorn','main:app','--host','127.0.0.1','--port',str(self.api_port)])
        wait_for(lambda:self.api.poll() is None and self.reachable(self.api_url+'/health'),'application API')

    def start_worker(self):
        if self.worker and self.worker.poll() is None:raise RuntimeError('Owned worker already running')
        self.worker_port=port()
        self.worker=self.start_process('worker',['worker.py'],env={**self.env,'PORT':str(self.worker_port)})
        wait_for(lambda:self.worker.poll() is None and self.reachable('http://127.0.0.1:'+str(self.worker_port)+'/'),'worker health')

    def stop(self,process,kill=False):
        if process and process.poll() is None:
            process.kill() if kill else process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)

    def diagnostics(self,label):
        artifact=os.getenv('DATION_E2E_ARTIFACTS')
        for log in self.logs:
            path=Path(log.name)
            print(path.name+'\n'+path.read_text()[-6000:],file=sys.stderr)
            if artifact:
                destination=Path(artifact)/label
                destination.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,destination/path.name)

    def __exit__(self,exc_type,exc,tb):
        for process in reversed(self.processes):self.stop(process)
        for name in reversed(self.containers):
            subprocess.run(['docker','rm','-f','-v',name],capture_output=True,timeout=30)
        if hasattr(self,'network'):subprocess.run(['docker','network','rm',self.network],capture_output=True,timeout=30)
        for name in ('http','api_client','db'):
            if hasattr(self,name):getattr(self,name).close()
        if exc_type:
            # Only synthetic loopback records live here; inherited secrets were cleared.
            self.diagnostics('startup-failure')
        for log in self.logs:log.close()
        self.temp.cleanup()
