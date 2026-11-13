#!/usr/bin/env python3
"""Actions release backend for the existing manual helper identity.

Only PATCH an existing service with CAS. Checkpoints are uploaded before writes.
No builds, Jobs, data/auth requests, IAM writes or home-directory release state.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from g6_common import (CloudRun, GitHub, POLICY, RESOURCE, REGISTRY, ROOT, SHA_RE,
    DIGEST_RE, NoRedirect, context, download_plan, fingerprint, require, validate_plan, write)
from g6_orchestrator import current

OUTPUT_ONLY = {'name','uid','generation','observedGeneration','createTime','updateTime','deleteTime','expireTime',
    'creator','lastModifier','reconciling','conditions','terminalCondition','latestReadyRevision','latestCreatedRevision',
    'trafficStatuses','uri','urls','satisfiesPzs','etag'}
REVISION_OUTPUT = OUTPUT_ONLY | {'service','logUri','creator','lastModifier','observedGeneration'}


def canonical(name):
    if isinstance(name,str) and name.startswith(POLICY['service']+'-') and '/' not in name:
        return RESOURCE+'/revisions/'+name
    if isinstance(name,str) and name.startswith('projects/'+POLICY['project_number']+'/'):
        return 'projects/'+POLICY['project']+name[len('projects/'+POLICY['project_number']):]
    return name


def revision_id(name):
    name=canonical(name)
    if isinstance(name,str) and name.startswith(POLICY['service']+'-') and '/' not in name:
        name=RESOURCE+'/revisions/'+name
    prefix=RESOURCE+'/revisions/'
    require(isinstance(name,str) and name.startswith(prefix) and name[len(prefix):].startswith(POLICY['service']+'-'), 'revision is outside this service')
    return name[len(prefix):]


def immutable(image):
    require(isinstance(image,str) and image.startswith(REGISTRY+'@') and DIGEST_RE.fullmatch(image.split('@')[-1]), 'image is not a Runtime V2 digest')
    return image


def container(template):
    values=template.get('containers',[])
    require(len(values)==1,'sidecars or missing API container')
    return values[0]


def release_sha(template):
    env=container(template).get('env',[])
    values=[e.get('value') for e in env if e.get('name')=='DATION_RELEASE_SHA']
    require(len(values)==1 and SHA_RE.fullmatch(values[0] or ''),'missing exact deployed application SHA')
    return values[0]


def check_template(template):
    require(template.get('serviceAccount')=='dation-runtime@'+POLICY['project']+'.iam.gserviceaccount.com','runtime identity differs')
    scale=template.get('scaling',{})
    require(scale.get('minInstanceCount',0)==0 and scale.get('maxInstanceCount') in (1,2),'revision must remain min0 max<=2')
    c=container(template);limits=c.get('resources',{})
    require(limits.get('cpuIdle',True) and not limits.get('startupCpuBoost',False),'continuous/startup CPU forbidden')
    require(limits.get('limits')=={'cpu':'1','memory':'512Mi'} and 1<=template.get('maxInstanceRequestConcurrency',0)<=8 and template.get('timeout')=='300s','unexpected API capacity')
    env=c.get('env',[]);require(len(env)==len({e['name'] for e in env}),'duplicate env names')
    plain={e['name']:e.get('value') for e in env if 'value' in e}
    require(plain.get('DATION_CLOUD_EXECUTION_ENABLED')=='false' and plain.get('DATION_EXECUTION_MODE')=='jobs','cloud execution must remain disabled')
    require(plain.get('DATION_CLOUD_PROJECT')==POLICY['project'] and plain.get('DATION_CLOUD_PROJECT_NUMBER')==POLICY['project_number'] and plain.get('DATION_CLOUD_REGION')==POLICY['region'],'runtime project identity differs')
    approved_plain=set(json.loads((ROOT/'infra/zero-idle/release.json').read_text())['environment']) | {'DATION_RELEASE_SHA','PORT'}
    require(all(e['name'] in approved_plain for e in env if 'value' in e), 'unreviewed literal env may contain secrets; no public snapshot')
    for entry in env:
        name=entry['name']
        require(not name.startswith('DATION_TEST_') and name!='DATION_DISPATCH_FAKE_URL','test transport forbidden')
        if any(word in name for word in ('SECRET','TOKEN','PASSWORD','KEY')):
            ref=entry.get('valueSource',{}).get('secretKeyRef',{})
            require('value' not in entry and ref.get('secret') and str(ref.get('version','')).isdigit() and int(ref['version'])>=1,'literal/unpinned secret must not enter a public receipt')
    release_sha(template)
    immutable(c.get('image'))
    require(c.get('command')==['sh','-c'] and c.get('args')==['exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"'],'only the existing API process is permitted')


def template_settings(template):
    check_template(template)
    value=copy.deepcopy(template);value.pop('revision',None)
    c=container(value);c.pop('image',None)
    for item in c['env']:
        if item['name']=='DATION_RELEASE_SHA':item['value']='<release-sha>'
    # JSON maps have stable hashes; env order is also preserved during patch.
    return value


def settings(service):
    require(canonical(service.get('name'))==RESOURCE,'service belongs to another project')
    check_template(service['template'])
    scale=service.get('scaling',{})
    require(scale.get('scalingMode') in (None,'SCALING_MODE_UNSPECIFIED','AUTOMATIC') and scale.get('manualInstanceCount',0)==0,'manual resident scaling forbidden')
    require(not service.get('buildConfig') and not service.get('multiRegionSettings'),'source builds or multiple regions forbidden')
    require(scale.get('minInstanceCount',0)==0 and scale.get('maxInstanceCount') in (1,2),'service scaling is not capped at zero idle')
    require(not service.get('invokerIamDisabled',False),'existing IAM invocation checks must remain enabled')
    result={k:copy.deepcopy(v) for k,v in service.items() if k not in OUTPUT_ONLY | {'traffic','template'}}
    result['template']=template_settings(service['template'])
    return result


def iam_settings(policy):
    value=copy.deepcopy(policy);value.pop('etag',None)
    value['bindings']=sorted([{**b,'members':sorted(b.get('members',[]))} for b in value.get('bindings',[])],key=lambda b:json.dumps(b,sort_keys=True))
    return value


def active(service):
    rows=[r for r in service.get('trafficStatuses',[]) if r.get('percent',0)>0]
    require(len(rows)==1 and rows[0].get('percent')==100 and rows[0].get('revision'),'exact single 100% active revision required')
    return RESOURCE+'/revisions/'+revision_id(rows[0]['revision'])


def ready(revision):
    return any(c.get('type')=='Ready' and c.get('state')=='CONDITION_SUCCEEDED' for c in revision.get('conditions',[]))


def health(url):
    parsed=urllib.parse.urlsplit(url)
    require(parsed.scheme=='https' and parsed.hostname and parsed.hostname.endswith('.run.app') and parsed.path in ('','/') and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,'untrusted smoke origin')
    req=urllib.request.Request(url.rstrip('/')+'/health',headers={'User-Agent':'Dation-G6-health'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=60) as response:
            body=json.loads(response.read(65536));require(response.status==200 and body=={'status':'healthy'},'health response differs')
    except (urllib.error.URLError,ValueError) as error:
        raise RuntimeError('NO_GO: revision-specific health failed: '+type(error).__name__) from None
    return {'status':200,'body':{'status':'healthy'},'url':url.rstrip('/')+'/health'}


def targets(revision, tag=None, candidate=None):
    result=[{'type':'TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION','revision':revision_id(revision),'percent':100}]
    if tag:result.append({'type':'TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION','revision':revision_id(candidate),'percent':0,'tag':tag})
    return result


class Release:
    def __init__(self, gh, cloud, plan, publication, out, recovering=False):
        self.gh=gh;self.cloud=cloud;self.plan=validate_plan(plan);self.pub=publication;self.out=Path(out);self.recovering=recovering
        require(publication.get('release_id')==plan['release_id'] and publication.get('application_sha')==plan['application_sha'] and publication.get('status')=='PUBLISH_PASS','publication checkpoint mismatch')
        self.image=immutable(publication['image_digest'])
        self.new=RESOURCE+'/revisions/'+POLICY['service']+'-g6-'+plan['release_run_id']+'-'+plan['application_sha'][:8]
        self.tag='ux-'+plan['release_run_id']+'-'+plan['application_sha'][:8]
    def read(self,name):
        result=json.loads((self.out/name).read_text())
        require(result.get('release_id')==self.plan['release_id'] and result.get('application_sha')==self.plan['application_sha'],'checkpoint identity mismatch')
        return result
    def save(self,name,value):
        result={'release_id':self.plan['release_id'],'application_sha':self.plan['application_sha'],**value}
        write(self.out/name,result);return result
    def guard(self):current(self.gh,self.plan)
    def verify_revision(self,name,image,expected_settings):
        require(canonical(name).startswith(RESOURCE+'/revisions/'),'wrong revision resource')
        revision=self.cloud.api(canonical(name))
        require(canonical(revision.get('name'))==canonical(name) and ready(revision),'exact revision not READY')
        require(container(revision).get('image')==image,'revision digest differs')
        if canonical(name)==self.new: require(release_sha(revision)==self.plan['application_sha'],'candidate release marker differs')
        # Revision output metadata is not configuration. Compare every template field.
        shaped={k:copy.deepcopy(revision[k]) for k in expected_settings if k in revision}
        shaped['containers']=copy.deepcopy(revision.get('containers',[]))
        require(template_settings(shaped)==expected_settings,'revision settings drift')
        return revision
    def snapshot(self):
        self.guard();self.cloud.registry(self.plan['application_sha'],self.image)
        service=self.cloud.api();config=settings(service)
        require(not service.get('reconciling') and service.get('etag') and service.get('generation'),'service is not stable/CAS-capable')
        require(service.get('uri')==POLICY['service_url'],'service URI differs from approved application URL')
        old=active(service)
        require(old!=self.new and not any(t.get('tag') for t in service.get('trafficStatuses',[])),'initial tagged/mixed release needs review')
        old_state=self.cloud.api(old)
        old_revision=self.verify_revision(old,immutable(container(old_state)['image']),config['template'])
        latest=canonical(service.get('latestCreatedRevision'))
        if latest!=old:
            # An inactive prior G6 revision is acceptable only with immutable source proof.
            import re
            match=re.fullmatch(POLICY['service']+r'-g6-([0-9]+)-[a-f0-9]{8}',revision_id(latest))
            require(match, 'unowned prepared revision exists')
            prior_plan=download_plan(self.gh,match.group(1))
            bundle=self.gh.artifact(match.group(1),'g6-release-'+match.group(1))
            proof=bundle['G6_RELEASE_RECEIPT.json']
            require(proof.get('release_id')==prior_plan['release_id'] and proof.get('READY_REVISION')==latest and proof.get('ROLLBACK_REVISION')==old and proof.get('settings_fingerprint')==fingerprint(config) and proof.get('status') in ('ACTIVATED','FAILED_ROLLED_BACK','FAILED_PREPARED_CLEANED','ROLLED_BACK'),'inactive revision has no verified G6 history')
        deployed_sha=self.cloud.application_sha(container(old_revision)['image'])
        # Actual live release, not just the bootstrap anchor, must have an eligible runtime delta.
        from g6_orchestrator import scope
        scope.git('merge-base','--is-ancestor',deployed_sha,self.plan['application_sha'])
        cumulative=[p for p in scope.changed(deployed_sha,self.plan['application_sha']) if scope.image_path(p)]
        require(cumulative and all(scope.allowed_runtime(p) for p in cumulative),'live deployed baseline would introduce non-UX runtime changes')
        scope.validate_client_changes(deployed_sha,self.plan['application_sha'],cumulative)
        return self.save('snapshot.json',{'service':service,'settings':config,'settings_fingerprint':fingerprint(config),
            'iam_fingerprint':fingerprint(iam_settings(self.cloud.iam())),'old_revision':old,'old_image':container(old_revision)['image'],
            'old_application_sha':deployed_sha,'old_environment_sha':release_sha(old_revision),'new_revision':self.new,'image':self.image,'tag':self.tag,'url':service['uri']})
    def check_live(self,snapshot,expected_active=None,etag=None):
        service=self.cloud.api()
        require(fingerprint(settings(service))==snapshot['settings_fingerprint'],'runtime/service configuration drift')
        require(fingerprint(iam_settings(self.cloud.iam()))==snapshot['iam_fingerprint'],'service IAM drift')
        if expected_active: require(active(service)==expected_active,'traffic ownership lost')
        if etag: require(service.get('etag')==etag,'concurrent service update (CAS drift)')
        return service
    def settle(self, expected_active, timeout=600, generation=None, latest=None):
        deadline=time.monotonic()+timeout
        while True:
            service=self.cloud.api()
            observed = int(service.get('generation',0))
            if generation is not None: require(observed<=generation,'another generation appeared during reconcile')
            reached = (generation is None or observed==generation) and (latest is None or canonical(service.get('latestReadyRevision'))==latest)
            if reached and not service.get('reconciling'):
                require(active(service)==expected_active,'unexpected traffic after update')
                return service
            require(service.get('terminalCondition',{}).get('state')!='CONDITION_FAILED','service update failed; preserve checkpoints')
            require(time.monotonic()<deadline,'service still reconciling; recover saved intent, do not redeploy')
            time.sleep(3)
    def prepare(self):
        self.guard();snap=self.read('snapshot.json')
        existing=self.cloud.api(self.new,missing=True)
        if existing is None:
            require(not self.recovering,'interrupted prepare has no exact revision; never redeploy blindly')
            service=self.check_live(snap,snap['old_revision'],snap['service']['etag'])
            template=copy.deepcopy(service['template']);template['revision']=revision_id(self.new)
            container(template)['image']=self.image
            for item in container(template)['env']:
                if item['name']=='DATION_RELEASE_SHA':item['value']=self.plan['application_sha']
            # Pin old traffic explicitly; a former LATEST target must never move on prepare.
            self.guard()
            self.cloud.api(method='PATCH',query='template,traffic',body={'name':RESOURCE,'etag':service['etag'],
                'template':template,'traffic':targets(snap['old_revision'],self.tag,self.new)})
        service=self.settle(snap['old_revision'],generation=int(snap['service']['generation'])+1,latest=self.new)
        service=self.check_live(snap,snap['old_revision'])
        require(canonical(service.get('latestCreatedRevision'))==self.new and
            int(service['generation'])==int(snap['service']['generation'])+1,'another deploy/generation interfered')
        self.verify_revision(self.new,self.image,snap['settings']['template'])
        require(release_sha(service['template'])==self.plan['application_sha'] and container(service['template'])['image']==self.image,'prepared template identity differs')
        tagged=[t for t in service.get('trafficStatuses',[]) if t.get('tag')==self.tag]
        require(len(tagged)==1 and canonical(tagged[0].get('revision'))==self.new and tagged[0].get('percent',0)==0,'smoke tag does not address exact zero-traffic candidate')
        uri=tagged[0].get('uri');require(uri,'candidate-specific URI missing')
        return self.save('prepared.json',{'etag':service['etag'],'generation':service['generation'],'new_revision':self.new,'candidate_url':uri,'old_revision':snap['old_revision'],'image':self.image})
    def smoke(self):
        self.guard();snap=self.read('snapshot.json');prepared=self.read('prepared.json')
        service=self.check_live(snap,snap['old_revision'],prepared['etag'])
        require(canonical(service.get('latestCreatedRevision'))==self.new,'candidate changed before smoke')
        self.verify_revision(self.new,self.image,snap['settings']['template'])
        try: result=health(prepared['candidate_url'])
        except RuntimeError as error:
            # Remove only our temporary tag; preserve image, revision and old100 traffic.
            live=self.check_live(snap,snap['old_revision'],prepared['etag'])
            require(canonical(live.get('latestCreatedRevision'))==self.new,'candidate ownership lost during failed smoke')
            self.cloud.api(method='PATCH',query='traffic',body={'name':RESOURCE,'etag':live['etag'],'traffic':targets(snap['old_revision'])})
            cleaned=self.settle(snap['old_revision'],generation=int(live['generation'])+1,latest=self.new);self.check_live(snap,snap['old_revision'],cleaned['etag'])
            self.receipt('FAILED_PREPARED_CLEANED',cleaned,str(error))
            raise
        return self.save('smoke.json',{'status':'PASS','new_revision':self.new,'image':self.image,'http':result})
    def promotion_intent(self):
        self.guard();snap=self.read('snapshot.json');prepared=self.read('prepared.json');smoke=self.read('smoke.json')
        require(smoke.get('status')=='PASS' and smoke.get('new_revision')==self.new and smoke.get('image')==self.image,'candidate HTTP smoke not verified')
        service=self.check_live(snap,snap['old_revision'],prepared['etag'])
        require(canonical(service.get('latestCreatedRevision'))==self.new,'concurrent deploy before promotion')
        self.verify_revision(self.new,self.image,snap['settings']['template'])
        return self.save('promotion-intent.json',{'etag':service['etag'],'generation':service['generation'],'old_revision':snap['old_revision'],'new_revision':self.new,'image':self.image})
    def receipt(self,status,service,reason=None):
        snap=self.read('snapshot.json')
        return self.save('G6_RELEASE_RECEIPT.json',{'status':status,'reason':reason,
            'APPLICATION_SHA':self.plan['application_sha'],'CI_PASS':True,'PUBLISH_PASS':True,
            'gate_run_id':self.plan['gate_run_id'],'publish_run_id':self.pub['publish_run_id'],
            'IMAGE_DIGEST':self.image,'READY_REVISION':self.new,'ROLLBACK_REVISION':snap['old_revision'],
            'TRAFFIC':100 if active(service)==self.new else 0,'HEALTH_PASS':status=='ACTIVATED',
            'settings_fingerprint':snap['settings_fingerprint'],'iam_fingerprint':snap['iam_fingerprint'],
            'service_etag':service.get('etag'),'service_generation':service.get('generation'),
            'operation_run_id':os.environ.get('GITHUB_RUN_ID'),'control_sha':os.environ.get('GITHUB_SHA'),
            'url':snap['url']+'/app','at_utc':datetime.now(timezone.utc).isoformat(),
            'pr_number':self.plan['pr_number'],'jobs_executed':0,'cloud_execution_enabled':False,'apply_unlocked':False})
    def promote(self):
        self.guard();snap=self.read('snapshot.json');intent=self.read('promotion-intent.json')
        service=self.check_live(snap,snap['old_revision'],intent['etag'])
        require(canonical(service.get('latestCreatedRevision'))==self.new and service['generation']==intent['generation'],'promotion ownership lost')
        self.guard()
        self.cloud.api(method='PATCH',query='traffic',body={'name':RESOURCE,'etag':service['etag'],'traffic':targets(self.new)})
        service=self.settle(self.new,generation=int(intent['generation'])+1,latest=self.new);service=self.check_live(snap,self.new)
        require(canonical(service.get('latestCreatedRevision'))==self.new and int(service['generation'])==int(intent['generation'])+1,'post-promotion concurrency detected')
        self.save('promoted.json',{'etag':service['etag'],'generation':service['generation'],'new_revision':self.new})
        try:
            health(snap['url'])
            final=self.check_live(snap,self.new,service['etag'])
            require(not any(t.get('tag') for t in final.get('trafficStatuses',[])),'temporary tag remains after promotion')
            return self.receipt('ACTIVATED',final)
        except Exception as error:
            # Only our unchanged promoted generation may be rolled back automatically.
            self.rollback(expected=service,automatic=True)
            self.receipt('FAILED_ROLLED_BACK',self.cloud.api(),str(error))
            raise RuntimeError('NO_GO: post-promotion health failed; safe rollback completed') from None
    def rollback(self,expected=None,automatic=False):
        snap=self.read('snapshot.json');receipt=None
        if expected is None:
            receipt=self.read('G6_RELEASE_RECEIPT.json')
            require(receipt.get('status') in ('ACTIVATED','FAILED_ROLLED_BACK'),'no completed release receipt to roll back')
            expected={'etag':receipt['service_etag'],'generation':receipt['service_generation']}
        service=self.check_live(snap)
        if active(service)==snap['old_revision']:
            require(not automatic,'automatic rollback requires current release ownership')
            return self.receipt('ROLLED_BACK',service)
        require(active(service)==self.new and canonical(service.get('latestCreatedRevision'))==self.new and
            service.get('etag')==expected['etag'] and service.get('generation')==expected['generation'],'later deploy/update exists; refusing rollback')
        self.verify_revision(snap['old_revision'],snap['old_image'],snap['settings']['template'])
        self.cloud.api(method='PATCH',query='traffic',body={'name':RESOURCE,'etag':service['etag'],'traffic':targets(snap['old_revision'])})
        result=self.settle(snap['old_revision'],generation=int(service['generation'])+1,latest=self.new);self.check_live(snap,snap['old_revision'],result['etag'])
        health(snap['url'])
        return self.receipt('ROLLED_BACK',result)
    def recover_promoted(self):
        snap=self.read('snapshot.json');intent=self.read('promotion-intent.json')
        service=self.check_live(snap,self.new)
        require(canonical(service.get('latestCreatedRevision'))==self.new and int(service['generation'])==int(intent['generation'])+1,'interrupted promotion ownership ambiguous')
        self.verify_revision(self.new,self.image,snap['settings']['template'])
        health(snap['url'])
        return self.receipt('ACTIVATED',service)


def restore_checkpoints(gh, source, out):
    plan=download_plan(gh,source)
    for phase,file in [('publication','publication.json'),('snapshot','snapshot.json'),('prepared','prepared.json'),
        ('smoke','smoke.json'),('promotion-intent','promotion-intent.json'),('release','G6_RELEASE_RECEIPT.json')]:
        bundle=gh.artifact(source,'g6-'+phase+'-'+str(source),optional=True)
        if bundle:
            value=bundle[file]
            require(value.get('release_id')==plan['release_id'] and value.get('application_sha')==plan['application_sha'],'checkpoint/source mismatch')
            write(out/file,value)
    write(out/'plan.json',plan)
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('restore','snapshot','prepare','smoke','promotion-intent','promote','rollback','recover-promoted','inspect-recovery','preflight'))
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--source-run')
    parser.add_argument('--confirm',default='')
    args=parser.parse_args();os.umask(0o077);args.out.mkdir(parents=True,exist_ok=True)
    try:
        mode='auto' if os.environ.get('GITHUB_EVENT_NAME')=='workflow_run' else 'ops';context(mode)
        from g6_orchestrator import scope
        require(scope.git('rev-parse','HEAD')==os.environ['GITHUB_SHA'], 'checked-out controls differ from workflow SHA')
        require(os.environ.get('DATION_UX_BOOTSTRAP_APPROVED')=='true','bootstrap approval missing')
        gh=GitHub()
        if args.phase=='restore':
            restore_checkpoints(gh,args.source_run or os.environ['GITHUB_RUN_ID'],args.out);return
        if args.phase=='preflight':
            gh.protected();cloud=CloudRun(read_only=True,tools=args.out/'registry');service=cloud.api();config=settings(service)
            exact=cloud.api(active(service));require(ready(exact),'active revision is not READY')
            cloud.permission_probe();cloud.iam()
            verified_sha=cloud.application_sha(container(exact)['image'])
            write(args.out/'G6_RELEASE_RECEIPT.json',{'status':'READ_ONLY_IDENTITY_VERIFIED','service':RESOURCE,
                'active_revision':active(service),'active_application_sha':verified_sha,'environment_release_sha':release_sha(exact),'settings_fingerprint':fingerprint(config),'TRAFFIC_CHANGED':False})
            return
        plan=validate_plan(json.loads((args.out/'plan.json').read_text()))
        publication=json.loads((args.out/'publication.json').read_text())
        release=Release(gh,CloudRun(tools=args.out/'registry'),plan,publication,args.out,recovering=mode=='ops')
        if args.phase=='inspect-recovery':
            snap=release.read('snapshot.json');live=release.check_live(snap)
            require(active(live) in (snap['old_revision'],release.new),'unknown recovery traffic')
            require(canonical(live.get('latestCreatedRevision'))==release.new,'newer revision exists; recovery denied')
            from g6_common import outputs
            outputs(already_promoted=str(active(live)==release.new).lower());return
        if args.phase=='rollback':
            require(mode=='ops' and args.confirm=='ROLLBACK_100','explicit owner rollback confirmation required')
            release.rollback();return
        if args.phase=='recover-promoted':
            require(mode=='ops' and args.confirm=='RECOVER_SAME_RELEASE','explicit recovery confirmation required');release.recover_promoted();return
        {'snapshot':release.snapshot,'prepare':release.prepare,'smoke':release.smoke,'promotion-intent':release.promotion_intent,'promote':release.promote}[args.phase]()
    except Exception as error:
        reason=str(error) if isinstance(error,RuntimeError) else type(error).__name__
        path=args.out/'G6_RELEASE_RECEIPT.json'
        # Preserve a successful safe-rollback receipt even though the job fails.
        prior=json.loads(path.read_text()) if path.exists() else {}
        if prior.get('status') not in ('FAILED_ROLLED_BACK','FAILED_PREPARED_CLEANED'):write(path,{**prior,'status':'FAILED','reason':reason})
        print(reason);raise SystemExit(1)

if __name__=='__main__':main()
