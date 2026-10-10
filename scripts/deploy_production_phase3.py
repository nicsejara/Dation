"""Publish Phase 3 after SQL readiness and exact-commit CI, preserving API settings."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROJECT, NUMBER, REGION, SERVICE = 'dation-510100', '469052310590', 'us-west1', 'dation-core'
WORKER = 'dation-core-worker'


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
    repository='dation-releases'
    probe=subprocess.run([cli,'artifacts','repositories','describe',repository,'--location='+REGION,
                          '--project='+PROJECT,'--format=value(name)'],env=environment,capture_output=True)
    if probe.returncode:
        cloud('artifacts','repositories','create',repository,'--repository-format=docker','--location='+REGION)
    image=f'{REGION}-docker.pkg.dev/{PROJECT}/{repository}/{SERVICE}:{sha}'
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
