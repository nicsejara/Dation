"""Publish Phase 3 after SQL readiness and exact-commit CI, preserving API settings."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROJECT, NUMBER, REGION, SERVICE = 'dation-510100', '469052310590', 'us-west1', 'dation-core'
WORKER = 'dation-core-worker'


def run_request(method, path, environment, body=None):
    # Global One Platform routes keep the proxy-bound credential on its authorized host.
    token = environment.get('GCP_ACCESS_TOKEN')
    if not token:
        raise RuntimeError('Configure GCP_ACCESS_TOKEN securely for the Cloud Run API.')
    request = Request('https://run.googleapis.com/v1/' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method=method)
    try:
        with urlopen(request,timeout=30) as response:return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'Cloud Run {method} returned HTTP {exc.code}.') from None


def wait_ready(service, environment):
    name = service['metadata']['name']
    generation = int(service['metadata'].get('generation',0))
    path = f'projects/{PROJECT}/locations/{REGION}/services/{name}'
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        current = run_request('GET',path,environment)
        status = current.get('status',{})
        condition = next((c for c in status.get('conditions',[]) if c['type']=='Ready'),{})
        observed = int(status.get('observedGeneration',0))
        if observed >= generation and condition.get('status')=='True' and status.get('latestCreatedRevisionName')==status.get('latestReadyRevisionName'):
            print('Ready:',name,status['latestReadyRevisionName'],flush=True)
            return current
        if observed >= generation and condition.get('status')=='False':
            raise RuntimeError(f'Cloud Run {name} failed readiness: {condition.get("message", "unknown")[:600]}')
        time.sleep(2)
    raise RuntimeError(f'Cloud Run {name} did not become ready within ten minutes.')


def cloud_run(args, environment):
    action = args[2]
    if action=='describe':
        path=f'projects/{PROJECT}/locations/{REGION}/services/{args[3]}'
        return json.dumps(run_request('GET',path,environment))
    if action=='replace':
        body=json.loads(Path(args[3]).read_text())
        name=body['metadata']['name']
        parent=f'projects/{PROJECT}/locations/{REGION}/services'
        # A failed GET can mean more than absence; only a confirmed 404 permits create.
        try:
            current=run_request('GET',parent+'/'+name,environment)
        except RuntimeError as exc:
            if str(exc)!='Cloud Run GET returned HTTP 404.':raise
            current=None
        if current:
            body['metadata']['resourceVersion']=current['metadata']['resourceVersion']
            updated=run_request('PUT',parent+'/'+name,environment,body)
        else:
            updated=run_request('POST',parent,environment,body)
        return json.dumps(wait_ready(updated,environment))
    if action=='update':
        path=f'projects/{PROJECT}/locations/{REGION}/services/{args[3]}'
        current=run_request('GET',path,environment)
        body={key:current[key] for key in ['apiVersion','kind','spec']}
        body['metadata']={key:value for key,value in current['metadata'].items() if key in {'name','namespace','resourceVersion','labels','annotations'}}
        template_metadata=body['spec']['template'].get('metadata',{})
        body['spec']['template']['metadata']={key:value for key,value in template_metadata.items() if key in {'labels','annotations'}}
        container=body['spec']['template']['spec']['containers'][0]
        for flag in args[4:]:
            if flag.startswith('--image='):container['image']=flag.split('=',1)[1]
            elif flag.startswith('--update-labels='):
                key,value=flag.split('=',1)[1].split('=',1)
                body['metadata'].setdefault('labels',{})[key]=value
                body['spec']['template'].setdefault('metadata',{}).setdefault('labels',{})[key]=value
            elif flag.startswith('--update-env-vars='):
                key,value=flag.split('=',1)[1].split('=',1)
                container['env']=[e for e in container.get('env',[]) if e['name']!=key]+[{'name':key,'value':value}]
        body['spec']['traffic']=[{'latestRevision':True,'percent':100}]
        updated=run_request('PUT',path,environment,body)
        return json.dumps(wait_ready(updated,environment))
    raise RuntimeError('Unsupported Cloud Run operation: '+action)


def main():
    cli = shutil.which('gcloud') or '/workspace/.dation-cloud/google-cloud-sdk/bin/gcloud'
    if not Path(cli).exists():raise RuntimeError('Install the official Google Cloud CLI.')
    environment = dict(os.environ)
    if environment.get('GCP_ACCESS_TOKEN'):
        environment['CLOUDSDK_AUTH_ACCESS_TOKEN'] = environment['GCP_ACCESS_TOKEN']
    if environment.get('CLOUDSDK_CONFIG','').startswith('/run/codex-environment/'):
        environment['CLOUDSDK_CONFIG'] = '/workspace/.dation-cloud/gcloud-config'
    # Existing runtime secrets stay in Secret Manager and never become CLI values.
    def cloud(*args):
        if args[0]=='run':return cloud_run(args,environment)
        result=subprocess.run([cli,*args,'--project='+PROJECT,'--quiet'],env=environment,
                              check=True,stdout=subprocess.PIPE,text=True)
        return result.stdout.strip()

    if cloud('projects','describe',PROJECT,'--format=value(projectNumber)') != NUMBER:
        raise RuntimeError('The selected project does not own the production service.')
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise RuntimeError('Commit and validate the source before deploying.')
    checks=json.loads(subprocess.check_output(['gh','api',f'repos/nicsejara/Dation/commits/{sha}/check-runs'],text=True))['check_runs']
    if not any(c['name']=='tests' and c['conclusion']=='success' for c in checks):
        raise RuntimeError('Exact-commit GitHub CI must pass before publishing Phase 3.')
    key=environment.get('SUPABASE_SECRET_KEY')
    if not key:raise RuntimeError('Configure the existing Supabase data key securely to verify migration readiness.')
    request=Request('https://gijiinufjjurgfeehufj.supabase.co/rest/v1/',
        headers={'apikey':key,'Authorization':'Bearer '+key,'Accept':'application/openapi+json'})
    with urlopen(request,timeout=30) as response:paths=json.load(response).get('paths',{})
    required=['enqueue_dispatch_run','claim_dispatch_job','heartbeat_dispatch_job','finish_dispatch_job','cancel_dispatch_job','ack_case_reconciliation']
    if any('post' not in paths.get('/rpc/'+name,{}) for name in required):
        raise RuntimeError('Apply and verify the production queue migration before deploying.')
    current=json.loads(cloud('run','services','describe',SERVICE,'--region='+REGION,'--format=json'))
    previous=current['status']['latestReadyRevisionName']
    print('Rollback revision:',previous,flush=True)
    spec=current['spec']['template']['spec']
    source_env=spec['containers'][0].get('env',[])
    worker_env=[entry for entry in source_env if entry['name'] in {'SUPABASE_URL','SUPABASE_INPUT_BUCKET','SUPABASE_SECRET_KEY'}]
    if not any(e['name']=='SUPABASE_URL' and e.get('value')=='https://gijiinufjjurgfeehufj.supabase.co' for e in worker_env):
        raise RuntimeError('The production service must reference the expected Supabase project.')
    if not any(e['name']=='SUPABASE_SECRET_KEY' and 'valueFrom' in e for e in worker_env):
        raise RuntimeError('The worker requires the existing Supabase key as a Secret Manager reference.')
    repository='cloud-run-source-deploy'
    cloud('artifacts','repositories','describe',repository,'--location='+REGION,'--format=value(name)')
    image=f'{REGION}-docker.pkg.dev/{PROJECT}/{repository}/dation-phase3/{SERVICE}:{sha}'
    cloud('builds','submit',str(ROOT),'--tag='+image)
    worker={'apiVersion':'serving.knative.dev/v1','kind':'Service',
        'metadata':{'name':WORKER,'namespace':NUMBER,'labels':{'cloud.googleapis.com/location':REGION}},
        'spec':{'template':{'metadata':{'labels':{'dation-release':sha},'annotations':{
            'autoscaling.knative.dev/minScale':'1','autoscaling.knative.dev/maxScale':'2',
            'run.googleapis.com/cpu-throttling':'false','run.googleapis.com/execution-environment':'gen2'}},
            'spec':{'serviceAccountName':spec.get('serviceAccountName'), 'containerConcurrency':1,'timeoutSeconds':3600,
                    'containers':[{'image':image,'command':['python'],'args':['worker.py'],
                       'ports':[{'containerPort':8080}], 'env':worker_env,
                       'resources':{'limits':{'cpu':'1','memory':'2Gi'}}}]}}}}
    if not worker['spec']['template']['spec']['serviceAccountName']:
        del worker['spec']['template']['spec']['serviceAccountName']
    with tempfile.TemporaryDirectory(prefix='dation-deploy-') as temp:
        config=Path(temp)/'worker.json';config.write_text(json.dumps(worker));config.chmod(0o600)
        cloud('run','services','replace',str(config),'--region='+REGION)
    ready=json.loads(cloud('run','services','describe',WORKER,'--region='+REGION,'--format=json'))
    if not any(c['type']=='Ready' and c['status']=='True' for c in ready['status']['conditions']):
        raise RuntimeError('The worker is not ready. Keep the API on its current revision.')
    # Preserve the API's IAM, environment, secrets and scaling settings.
    cloud('run','services','update',SERVICE,'--region='+REGION,'--image='+image,
          '--update-labels=dation-release='+sha,'--update-env-vars=DATION_RELEASE_SHA='+sha)
    deployed=json.loads(cloud('run','services','describe',SERVICE,'--region='+REGION,'--format=json'))
    if not any(c['type']=='Ready' and c['status']=='True' for c in deployed['status']['conditions']):
        raise RuntimeError('The API revision is not ready; use the recorded rollback revision.')
    print(json.dumps({'release_sha':sha,'api_url':deployed['status']['url'],
        'api_revision':deployed['status']['latestReadyRevisionName'],
        'worker_revision':ready['status']['latestReadyRevisionName'],'rollback_revision':previous}))


if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError,subprocess.CalledProcessError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
