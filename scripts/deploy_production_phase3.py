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
sys.path.insert(0, str(ROOT/'backend'))
from app.cloud_identity import PROJECT, PROJECT_NUMBER as NUMBER, REGION, SERVICE
WORKER = 'dation-core-worker'


def run_request(method, path, environment, body=None):
    if method != "GET":
        raise RuntimeError("Historical deployment writes disabled; use zero_idle_release.py.")
    if path not in {f'projects/{PROJECT}/locations/{REGION}/services/{name}' for name in (SERVICE,WORKER)}:
        raise RuntimeError('Historical diagnostics cannot target another project or region.')
    # Read-only historical diagnostics.
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
    # Historical helpers remain for regression coverage; this entry never deploys.
    from zero_idle_release import main as safe_main
    safe_main()


if __name__=='__main__':main()
