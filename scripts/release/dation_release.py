#!/usr/bin/env python3
"""Dation Runtime V2: explicit prepare/promote/rollback. NEVER builds or changes billing."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

PROJECT='dation-runtime-v2-2026'
REGION='us-west1'
SERVICE='dation-core'
REGISTRY=f'{REGION}-docker.pkg.dev/{PROJECT}/dation-runtime/dation-core'
SHA_RE=re.compile(r'[0-9a-f]{40}\Z')
DIGEST_RE=re.compile(r'sha256:[a-f0-9]{64}\Z')
STATE=Path.home()/'.dation-releases-v2'

def require(ok, message):
    if not ok:
        raise RuntimeError('NO_GO: '+message)

def command(*args):
    process=subprocess.run(['gcloud',*args],capture_output=True,text=True)
    if process.returncode:
        raise RuntimeError('NO_GO: gcloud '+args[0]+' failed: '+process.stderr[-1000:])
    return process.stdout.strip()

def resource(kind,name):
    arguments=['run',kind,'describe',name,'--project='+PROJECT,'--region='+REGION,'--format=json']
    return json.loads(command(*arguments))

def service():
    return resource('services',SERVICE)

def revision(name):
    return resource('revisions',name)

def active(s):
    rows=[r for r in s.get('status',{}).get('traffic',[]) if r.get('percent')==100]
    require(len(rows)==1 and rows[0].get('revisionName'), 'expected one exact 100% traffic revision')
    return rows[0]['revisionName']

def template(s):
    return s.get('spec',{}).get('template',{})

def settings(s):
    t=template(s)
    annotations=t.get('metadata',{}).get('annotations',{})
    spec=t.get('spec',{})
    containers=spec.get('containers',[])
    require(len(containers)==1,'expected exactly one API container')
    keep={k:annotations.get(k) for k in (
         'autoscaling.knative.dev/minScale','autoscaling.knative.dev/maxScale',
         'run.googleapis.com/cpu-throttling')}
    require(keep['autoscaling.knative.dev/minScale'] in (None,'0'), 'min instances must remain zero')
    require(keep['autoscaling.knative.dev/maxScale'] in ('1','2'), 'max instances must be capped at two')
    return {'scaling':keep,'service_account':spec.get('serviceAccountName'),
            'env':containers[0].get('env',[]),
            'resources':containers[0].get('resources',{}),
            'concurrency':spec.get('containerConcurrency',None)}

def ready(r):
    return any(c.get('type')=='Ready' and str(c.get('status')).lower()=='true'
               for c in r.get('status',{}).get('conditions',[]))

def image_on_revision(r):
    containers=r.get('spec',{}).get('containers',[])
    require(len(containers)==1, 'revision does not contain exactly one container')
    return containers[0].get('image')

def state_file(sha):
    require(bool(SHA_RE.fullmatch(sha)),'SHA must be full lowercase 40 hexadecimal characters')
    return STATE/(sha+'.json')

def load(sha):
    path=state_file(sha)
    require(path.exists(),'release not prepared; run prepare first')
    result=json.loads(path.read_text())
    require(result.get('sha')==sha and result.get('project')==PROJECT and
            result.get('region')==REGION and result.get('service')==SERVICE,
            'release receipt identity mismatch')
    return result

def save(data):
    os.umask(0o077)
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=state_file(data['sha'])
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    tmp.replace(path)

def registry_image(sha):
    tag=REGISTRY+':'+sha
    digest=command('artifacts','docker','images','describe',tag,'--project='+PROJECT,
                   '--format=value(image_summary.digest)')
    require(bool(DIGEST_RE.fullmatch(digest)),'no verified digest for exact tagged release SHA')
    return REGISTRY+'@'+digest

def inspect(sha=None):
    s=service()
    current=active(s)
    result={'project':PROJECT,'service':SERVICE,'region':REGION,
            'active_revision':current,'traffic':s.get('status',{}).get('traffic',[]),
            'settings':settings(s)}
    if sha:
        path=state_file(sha)
        if path.exists():
            result['release']=load(sha)
    print(json.dumps(result,indent=2,ensure_ascii=False))

def assert_prepared(data):
    s=service()
    require(settings(s)==data['settings'],'service configuration changed unexpectedly')
    new=revision(data['new_revision'])
    require(ready(new),'candidate revision is not READY')
    require(image_on_revision(new)==data['image'],'revision image mismatch')
    require(data['old_revision']!=data['new_revision'],'old and new revisions are the same')
    return s

def resolve_new_revision(data):
    """Recover a revision after an interrupted deploy, but never redeploy blindly."""
    for _ in range(6):
        latest=service().get('status',{}).get('latestCreatedRevisionName')
        if latest and latest != data['old_revision']:
            candidate=revision(latest)
            if image_on_revision(candidate)==data['image'] and ready(candidate):
                return latest
            # Different image is not ours; never reassign another release.
            require(image_on_revision(candidate)==data['image'], 'another revision appeared; do not adopt it')
        time.sleep(2)
    raise RuntimeError('NO_GO: exact new revision is not ready; inspect and retry prepare')

def prepare(sha):
    path=state_file(sha)
    if path.exists():
        data=load(sha)
        if data.get('new_revision'):
            assert_prepared(data)
            print('ALREADY_PREPARED',data['new_revision'])
            return
        require(active(service())==data['old_revision'],'traffic changed during interrupted prepare')
        data['new_revision']=resolve_new_revision(data)
    else:
        s=service()
        old=active(s)
        initial=settings(s)
        image=registry_image(sha)
        data={'project':PROJECT,'region':REGION,'service':SERVICE,'sha':sha,
              'image':image,'settings':initial,'old_revision':old,
              'new_revision':None,'promoted':False}
        save(data) # durable before API mutation
        command('run','deploy',SERVICE,'--project='+PROJECT,'--region='+REGION,
                '--image='+image,'--no-traffic','--quiet')
        data['new_revision']=resolve_new_revision(data)
    save(data)
    revised=assert_prepared(data)
    require(active(revised)==data['old_revision'],'old traffic changed during prepare')
    print(json.dumps({'PREPARED':True,'sha':sha,'new_revision':data['new_revision'],
                      'old_revision':data['old_revision'],'image':data['image'],
                      'traffic_changed':False},indent=2))

def smoke(sha):
    data=load(sha)
    assert_prepared(data)
    print(json.dumps({'READY':True,'sha':sha,'revision':data['new_revision'],
                      'image':data['image'],
                      'http_smoke':'NOT_EXECUTED: untagged zero-traffic revision'},indent=2))

def promote(sha,confirm):
    require(confirm=='PROMOTE_100','explicit confirmation required')
    data=load(sha)
    s=assert_prepared(data)
    if active(s)==data['new_revision']:
        print('ALREADY_ACTIVE',data['new_revision'])
        return
    require(active(s)==data['old_revision'],'current traffic differs from saved rollback revision')
    command('run','services','update-traffic',SERVICE,'--project='+PROJECT,
            '--region='+REGION,'--to-revisions='+data['new_revision']+'=100','--quiet')
    require(active(service())==data['new_revision'],'activation not confirmed')
    data['promoted']=True
    save(data)
    print('ACTIVATED',data['new_revision'])

def rollback(sha,confirm):
    require(confirm=='ROLLBACK_100','explicit confirmation required')
    data=load(sha)
    s=service()
    require(settings(s)==data['settings'],'runtime configuration changed since prepare')
    if active(s)==data['old_revision']:
        print('ALREADY_ROLLED_BACK',data['old_revision'])
        return
    require(active(s)==data['new_revision'],'unexpected active revision: refuse rollback')
    prior=revision(data['old_revision'])
    require(ready(prior),'prior revision not READY')
    command('run','services','update-traffic',SERVICE,'--project='+PROJECT,
            '--region='+REGION,'--to-revisions='+data['old_revision']+'=100','--quiet')
    require(active(service())==data['old_revision'],'rollback not confirmed')
    data['promoted']=False
    save(data)
    print('ROLLED_BACK',data['old_revision'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    for name in ('status','prepare','smoke','promote','rollback'):
        command_parser=sub.add_parser(name)
        if name!='status':
            command_parser.add_argument('--sha',required=True)
        if name in ('promote','rollback'):
            command_parser.add_argument('--confirm',required=True)
    args=parser.parse_args()
    try:
        if args.action=='status':inspect()
        elif args.action=='prepare':prepare(args.sha)
        elif args.action=='smoke':smoke(args.sha)
        elif args.action=='promote':promote(args.sha,args.confirm)
        elif args.action=='rollback':rollback(args.sha,args.confirm)
    except (RuntimeError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(2)

if __name__=='__main__':
    main()
