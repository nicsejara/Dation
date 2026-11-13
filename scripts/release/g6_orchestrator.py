#!/usr/bin/env python3
"""G6 no-cloud orchestration. Only a verified eligible main can dispatch publication."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import time

from g6_common import (GitHub, POLICY, POLICY_FILE, REPO, ROOT, context, download_plan,
    outputs, require, validate_plan, write, REGISTRY, DIGEST_RE)

spec=importlib.util.spec_from_file_location('ux_scope',ROOT/'scripts/ci/autodeploy_eligibility.py')
scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)


def current(gh, plan):
    validate_plan(plan)
    require(gh.main() == plan['application_sha'], 'main advanced; obsolete release')
    gh.protected()
    gh.gate(plan['gate_run_id'], plan['application_sha'],plan['risk'])


def preflight(gh, event, env=os.environ):
    context('auto',env)
    upstream=event.get('workflow_run',{})
    require(upstream.get('event')=='push' and upstream.get('conclusion')=='success' and upstream.get('head_branch')=='main' and
        upstream.get('head_repository',{}).get('id')==POLICY['repository_id'], 'untrusted/non-green upstream event')
    sha=upstream.get('head_sha','')
    require(scope.SHA.fullmatch(sha) and sha==env.get('GITHUB_SHA'), 'event SHA differs from workflow controls')
    base={'repository_id':POLICY['repository_id'],'release_run_id':env['GITHUB_RUN_ID'],
        'release_id':'g6-'+env['GITHUB_RUN_ID'],'application_sha':sha,'gate_run_id':upstream['id'],
        'control_sha':env['GITHUB_SHA'],'policy_sha256':scope.policy_hash(),'created_at_utc':datetime.now(timezone.utc).isoformat()}
    if env.get('DATION_UX_AUTODEPLOY_ENABLED')!='true': return {**base,'status':'SKIPPED','reason':'kill switch absent or false'}
    require(env.get('DATION_UX_BOOTSTRAP_APPROVED')=='true', 'bootstrap has not been approved/verified')
    require(env.get('DATION_UX_POLICY_SHA256')==scope.policy_hash(), 'policy differs from approved bootstrap')
    require(gh.main()==sha,'main advanced before publication')
    gh.protected()
    prs=gh.pages('/commits/'+sha+'/pulls')
    matching=[p for p in prs if p.get('merged_at') and p.get('merge_commit_sha')==sha and p.get('base',{}).get('ref')=='main']
    require(len(matching)==1,'missing or ambiguous merged PR')
    # Pull-list records omit merged/merged_by on some API versions.
    pull=gh.api('/pulls/'+str(matching[0]['number']))
    classification=scope.eligible_commit(sha,pull,env.get('DATION_UX_BASELINE_SHA',''))
    gh.gate(upstream['id'],sha,classification['risk'])
    return {**base,**classification,'status':'ELIGIBLE'}


def title(plan): return 'Publish Dation ' + plan['application_sha'] + ' / ' + plan['release_id']


def correlated(gh, plan):
    runs=gh.pages('/actions/workflows/'+POLICY['publisher_workflow']+'/runs?event=workflow_dispatch','workflow_runs')
    matches=[r for r in runs if r.get('display_title')==title(plan)]
    require(len(matches)<=1,'ambiguous publication correlation; no second dispatch')
    for run in matches:
        require(run.get('head_sha')==plan['application_sha'] and run.get('head_branch')=='main' and
            run.get('repository',{}).get('id')==POLICY['repository_id'] and
            run.get('head_repository',{}).get('id')==POLICY['repository_id'], 'correlated publisher provenance mismatch')
    return matches[0] if matches else None


def claim(gh, plan, out):
    current(gh,plan)
    require(not gh.artifact(plan['release_run_id'],'g6-publish-claim-'+plan['release_run_id'],optional=True), 'dispatch already claimed; collect/recover instead')
    file=out/'publish-claim.json'
    require(not file.exists(),'local dispatch claim already exists')
    write(file,{'release_id':plan['release_id'],'application_sha':plan['application_sha'],
        'release_run_id':plan['release_run_id'],'request_id':plan['release_id'],'state':'DISPATCH_CLAIMED',
        'at':datetime.now(timezone.utc).isoformat()})


def dispatch_collect(gh, plan, out, allow_dispatch=True, timeout=1800):
    current(gh,plan)
    checkpoint=gh.artifact(plan['release_run_id'],'g6-publish-claim-'+plan['release_run_id'])['publish-claim.json']
    require(checkpoint.get('release_id')==plan['release_id'] and checkpoint.get('application_sha')==plan['application_sha'], 'dispatch claim identity differs')
    run=correlated(gh,plan)
    if run is None:
        require(allow_dispatch and str(os.environ['GITHUB_RUN_ID'])==plan['release_run_id'] and os.environ.get('GITHUB_RUN_ATTEMPT')=='1',
            'ambiguous interrupted dispatch; never submit again during recovery')
        marker=out/'dispatch.started'
        with marker.open('x') as stream: stream.write(plan['release_id'])
        gh.api('/actions/workflows/'+POLICY['publisher_workflow']+'/dispatches',method='POST',
            body={'ref':'main','inputs':{'application_sha':plan['application_sha'],'confirm_publish':True,'request_id':plan['release_id']}})
    deadline=time.monotonic()+timeout
    while True:
        require(time.monotonic()<deadline,'publisher not terminal; preserve immutable claim, recover existing run only')
        if run is None:
            time.sleep(5);run=correlated(gh,plan);continue
        run=gh.run(run['id'],POLICY['publisher_workflow'],plan['application_sha'],terminal=False)
        require(run.get('display_title')==title(plan) and run.get('event')=='workflow_dispatch', 'publisher request correlation differs')
        if run.get('status')=='completed': break
        require(gh.main()==plan['application_sha'],'main advanced while publisher ran; no deploy')
        time.sleep(20)
    require(run.get('conclusion')=='success','publisher failed; diagnose exact run, no retry/permission expansion')
    bundle=gh.artifact(run['id'],'gate-c-'+str(run['id']))
    receipt=bundle['GATE_C_RECEIPT.json']
    require(receipt.get('status')=='PASS' and receipt.get('sha')==plan['application_sha'] and
        receipt.get('request_id')==plan['release_id'] and receipt.get('workflow_sha')==plan['application_sha'] and
        receipt.get('run_id')==str(run['id']) and receipt.get('project')==POLICY['project'] and
        receipt.get('architecture')=='amd64' and receipt.get('dependencies_verified') is True and receipt.get('imports_verified') is True,
        'publisher receipt SHA/run/request/validation mismatch')
    image=receipt.get('image_digest','')
    require(image.startswith(REGISTRY+'@') and DIGEST_RE.fullmatch(image.split('@')[-1]), 'receipt lacks immutable digest')
    current(gh,plan)
    result={'release_id':plan['release_id'],'application_sha':plan['application_sha'],
        'publish_run_id':run['id'],'request_id':plan['release_id'],'image_digest':image,'publisher_receipt':receipt,'status':'PUBLISH_PASS'}
    write(out/'publication.json',result)
    return result


def restore(gh, run_id, out):
    plan=download_plan(gh,run_id)
    write(out/'plan.json',plan)
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('preflight','claim','publish','restore','collect','verify','ops-guard'))
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--source-run')
    args=parser.parse_args();os.umask(0o077);args.out.mkdir(parents=True,exist_ok=True)
    try:
        mode='auto' if os.environ.get('GITHUB_EVENT_NAME')=='workflow_run' else 'ops'
        context(mode)
        require(scope.git('rev-parse','HEAD')==os.environ['GITHUB_SHA'], 'checked-out controls differ from workflow SHA')
        gh=GitHub()
        if args.phase=='ops-guard':
            require(mode=='ops' and os.environ.get('DATION_UX_OPERATION') in ('preflight','recover','rollback'), 'invalid manual operation')
            operation=os.environ['DATION_UX_OPERATION']
            if operation in ('recover','rollback'):
                expected='RECOVER_SAME_RELEASE' if operation=='recover' else 'ROLLBACK_100'
                require(os.environ.get('DATION_CONFIRMATION')==expected,'explicit operation confirmation missing')
            require(os.environ.get('DATION_UX_BOOTSTRAP_APPROVED')=='true' and os.environ.get('DATION_UX_POLICY_SHA256')==scope.policy_hash(), 'bootstrap/policy not approved')
            require(gh.main()==os.environ['GITHUB_SHA'], 'stale ops controls');gh.protected()
            runs=gh.pages('/actions/workflows/'+POLICY['gate_workflow']+'/runs?event=push&head_sha='+os.environ['GITHUB_SHA'],'workflow_runs')
            require(runs, 'ops control commit has no CI')
            latest=max(runs,key=lambda r:int(r['id']))
            gh.run(latest['id'],POLICY['gate_workflow'],os.environ['GITHUB_SHA'])
            gate_jobs=gh.pages('/actions/runs/'+str(latest['id'])+'/jobs?filter=latest','jobs')
            require(any(j.get('name')=='required-gate' and j.get('conclusion')=='success' for j in gate_jobs), 'ops controls lack exact green gate')
        elif args.phase=='preflight':
            event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
            try: plan=preflight(gh,event)
            except RuntimeError as error:
                plan={'status':'SKIPPED','reason':str(error),'application_sha':event.get('workflow_run',{}).get('head_sha')}
            write(args.out/'plan.json',plan)
            write(args.out/'G6_RELEASE_RECEIPT.json',{'status':'SKIPPED' if plan['status']!='ELIGIBLE' else 'PLANNED','reason':plan.get('reason'),
                'APPLICATION_SHA':plan.get('application_sha'),'CI_PASS':plan['status']=='ELIGIBLE','PUBLISH_PASS':False,'TRAFFIC_CHANGED':False})
            outputs(eligible=str(plan['status']=='ELIGIBLE').lower(),application_sha=plan.get('application_sha',''))
            print(json.dumps(plan,indent=2))
        elif args.phase=='restore': restore(gh,args.source_run or os.environ['GITHUB_RUN_ID'],args.out)
        else:
            plan=validate_plan(json.loads((args.out/'plan.json').read_text()))
            if args.phase=='verify': current(gh,plan)
            elif args.phase=='claim': claim(gh,plan,args.out)
            else: dispatch_collect(gh,plan,args.out,allow_dispatch=args.phase=='publish')
    except Exception as error:
        message=str(error) if isinstance(error,RuntimeError) else type(error).__name__
        write(args.out/'G6_RELEASE_RECEIPT.json',{'status':'FAILED','reason':message,'TRAFFIC_CHANGED':False})
        print(message);raise SystemExit(1)

if __name__=='__main__': main()
