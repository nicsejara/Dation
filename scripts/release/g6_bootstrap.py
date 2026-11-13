#!/usr/bin/env python3
"""Preview by default. GCP apply requires a separate, exact owner GO and plan hash."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

from g6_common import POLICY, POLICY_FILE, PROVIDER, DEPLOYER, RESOURCE, fingerprint, require


def plan():
    prefix="assertion.repository == 'nicsejara/Dation' && assertion.repository_id == '1114679650' && assertion.repository_owner_id == '249153366' && assertion.ref == 'refs/heads/main' && assertion.sub == 'repo:nicsejara/Dation:environment:ux-mvp-auto'"
    routes="((assertion.event_name == 'workflow_run' && assertion.workflow_ref == 'nicsejara/Dation/.github/workflows/dation-ux-autorelease.yml@refs/heads/main') || (assertion.event_name == 'workflow_dispatch' && assertion.workflow_ref == 'nicsejara/Dation/.github/workflows/dation-ux-ops.yml@refs/heads/main'))"
    runtime='dation-runtime@'+POLICY['project']+'.iam.gserviceaccount.com'
    return {'project':POLICY['project'],'project_number':POLICY['project_number'],'region':POLICY['region'],
        'account_id':POLICY['deployer_account'],'service_account':DEPLOYER,'pool':POLICY['pool'],'provider_id':POLICY['provider'],
        'provider':PROVIDER,'issuer':'https://token.actions.githubusercontent.com','audience':'https://iam.googleapis.com/'+PROVIDER,
        'attribute_mapping':{'google.subject':'assertion.repository_id'},'attribute_condition':prefix+' && '+routes,
        'federated_principal':'principal://iam.googleapis.com/projects/'+POLICY['project_number']+'/locations/global/workloadIdentityPools/'+POLICY['pool']+'/subject/1114679650',
        'custom_role':{'role_id':POLICY['service_role'],'title':'Dation UX existing service releaser','stage':'GA','includedPermissions':POLICY['service_permissions']},
        'bindings':[
            {'resource':RESOURCE,'role':'projects/'+POLICY['project']+'/roles/'+POLICY['service_role'],'member':'serviceAccount:'+DEPLOYER},
            {'resource':'projects/'+POLICY['project']+'/locations/'+POLICY['region']+'/repositories/dation-runtime','role':'roles/artifactregistry.reader','member':'serviceAccount:'+DEPLOYER},
            {'resource':'projects/'+POLICY['project']+'/serviceAccounts/'+runtime,'role':'roles/iam.serviceAccountUser','member':'serviceAccount:'+DEPLOYER},
            {'resource':'projects/'+POLICY['project']+'/serviceAccounts/'+DEPLOYER,'role':'roles/iam.workloadIdentityUser',
             'member':'principal://iam.googleapis.com/projects/'+POLICY['project_number']+'/locations/global/workloadIdentityPools/'+POLICY['pool']+'/subject/1114679650'}],
        'project_roles_granted':[], 'keys_created':False,'apis_enabled':[],
        'current_live_iam':'UNVERIFIED: Codex read returned HTTP401 ACCESS_TOKEN_TYPE_UNSUPPORTED; apply must read and compare first',
        'auto_deploy_enabled':False,'service_traffic_changed':False}


def apply(value, confirmation, approved_hash):
    require(confirmation=='GO_G6_BOOTSTRAP_IDENTITY' and approved_hash==fingerprint(value), 'exact separate owner GO and reviewed plan SHA256 required')
    project=value['project'];member='serviceAccount:'+DEPLOYER
    def gc(*args, raw=False):
        r=subprocess.run(['gcloud',*args,'--project='+project,'--billing-project='+project,'--quiet',*([] if raw else ['--format=json'])],capture_output=True,text=True,timeout=120)
        require(r.returncode==0,'bootstrap gcloud command failed: '+' '.join(args[:3])+'; inspect locally, never broaden roles')
        return r.stdout.strip() if raw else json.loads(r.stdout or 'null')
    def get(url):
        token=gc('auth','print-access-token',raw=True)
        req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token})
        from g6_common import NoRedirect
        try:
            with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            try:detail=json.loads(error.read(65536)).get('error',{})
            except (ValueError,AttributeError):detail={}
            if error.code==404 and isinstance(detail,dict) and detail.get('code')==404 and detail.get('status')=='NOT_FOUND':return None
            raise RuntimeError('NO_GO: bootstrap read HTTP'+str(error.code)+'; no mutation permission inferred') from None
    def roles(policy,who):
        rows=[b for b in (policy or {}).get('bindings',[]) if who in b.get('members',[])]
        require(not any(b.get('condition') for b in rows),'unexpected conditional IAM; do not overwrite')
        return {b['role'] for b in rows}
    identity=gc('projects','describe',project)
    require((identity.get('projectId'),identity.get('projectNumber'),identity.get('lifecycleState'))==(project,value['project_number'],'ACTIVE') and not identity.get('parent'),'project mismatch or unreviewed inherited IAM')
    enabled={x.get('config',{}).get('name') for x in gc('services','list','--enabled')}
    require({'iam.googleapis.com','iamcredentials.googleapis.com','sts.googleapis.com','run.googleapis.com','artifactregistry.googleapis.com'}<=enabled,'missing API; bootstrap does not enable APIs')
    require(not {'cloudbuild.googleapis.com','cloudscheduler.googleapis.com'} & enabled,'unexpected Cloud Build/Scheduler state; do not change it here')
    project_policy=gc('projects','get-iam-policy',project)
    require(not roles(project_policy,member),'new deployer has unexpected project-wide grants')
    require(not any(set(b.get('members',[])) & {'allUsers','allAuthenticatedUsers'} for b in project_policy.get('bindings',[])),'public project IAM broadens new identity')
    sa_url='https://iam.googleapis.com/v1/projects/'+project+'/serviceAccounts/'+DEPLOYER
    account=get(sa_url)
    sa_policy={}
    if account:
        require(account.get('email')==DEPLOYER and not account.get('disabled'),'unexpected deployer identity')
        require(not gc('iam','service-accounts','keys','list','--iam-account='+DEPLOYER,'--managed-by=user'),'permanent deployer keys forbidden')
        sa_policy=gc('iam','service-accounts','get-iam-policy',DEPLOYER)
        require(all(b.get('role')=='roles/iam.workloadIdentityUser' and set(b.get('members',[]))<={value['federated_principal']} and not b.get('condition') for b in sa_policy.get('bindings',[])),'unexpected impersonation grant')
    pool_resource='projects/'+value['project_number']+'/locations/global/workloadIdentityPools/'+value['pool']
    pool=get('https://iam.googleapis.com/v1/'+pool_resource)
    if pool:
        require(pool.get('state')=='ACTIVE' and not pool.get('disabled'),'inactive/deleted pool')
        providers=gc('iam','workload-identity-pools','providers','list','--location=global','--workload-identity-pool='+value['pool'])
        require(all(p.get('name')==PROVIDER for p in providers),'another provider can access this numeric subject')
    provider=get('https://iam.googleapis.com/v1/'+PROVIDER) if pool else None
    def verify_provider(current):
        require(current and current.get('state')=='ACTIVE' and not current.get('disabled') and current.get('attributeMapping')==value['attribute_mapping'] and
            current.get('attributeCondition')==value['attribute_condition'] and current.get('oidc',{}).get('issuerUri')==value['issuer'] and
            current.get('oidc',{}).get('allowedAudiences')==[value['audience']],'provider differs; no broadening/update')
    if provider:verify_provider(provider)
    role_name='projects/'+project+'/roles/'+value['custom_role']['role_id']
    role=get('https://iam.googleapis.com/v1/'+role_name)
    if role:require(not role.get('deleted') and role.get('stage')=='GA' and set(role.get('includedPermissions',[]))==set(value['custom_role']['includedPermissions']),'existing custom role differs')
    service=gc('run','services','describe',POLICY['service'],'--region='+value['region'])
    require(service.get('metadata',{}).get('name')==POLICY['service'],'existing service not verified')
    service_policy=gc('run','services','get-iam-policy',POLICY['service'],'--region='+value['region'])
    registry_policy=gc('artifacts','repositories','get-iam-policy','dation-runtime','--location='+value['region'])
    runtime=value['bindings'][2]['resource'].rsplit('/',1)[1]
    runtime_policy=gc('iam','service-accounts','get-iam-policy',runtime)
    policies=[service_policy,registry_policy,runtime_policy,sa_policy]
    for binding,policy in zip(value['bindings'],policies):require(roles(policy,binding['member'])<={binding['role']},'unexpected existing grant on specific resource')
    preview={'status':'LIVE_IAM_DIFF_VERIFIED','plan_sha256':fingerprint(value),'diff':[
        {'resource':b['resource'],'etag':p.get('etag'),'before_roles':sorted(roles(p,b['member'])),'add':None if b['role'] in roles(p,b['member']) else b['role'],'member':b['member']} for b,p in zip(value['bindings'],policies)]}
    print(json.dumps(preview,indent=2))
    # Only the exact preflighted delta is applied. No service deploy/traffic/API enable.
    if not account:gc('iam','service-accounts','create',value['account_id'],'--display-name=Dation scoped UX release')
    if not pool:gc('iam','workload-identity-pools','create',value['pool'],'--location=global','--display-name=Dation G6 trusted workflows only')
    if not provider:gc('iam','workload-identity-pools','providers','create-oidc',value['provider_id'],'--location=global','--workload-identity-pool='+value['pool'],
        '--issuer-uri='+value['issuer'],'--allowed-audiences='+value['audience'],'--attribute-mapping=google.subject=assertion.repository_id','--attribute-condition='+value['attribute_condition'])
    if not role:gc('iam','roles','create',value['custom_role']['role_id'],'--title='+value['custom_role']['title'],'--stage=GA','--permissions='+','.join(value['custom_role']['includedPermissions']))
    commands=[('run','services','add-iam-policy-binding',POLICY['service'],'--region='+value['region']),
        ('artifacts','repositories','add-iam-policy-binding','dation-runtime','--location='+value['region']),
        ('iam','service-accounts','add-iam-policy-binding',runtime),('iam','service-accounts','add-iam-policy-binding',DEPLOYER)]
    for binding,policy,command in zip(value['bindings'],policies,commands):
        if binding['role'] not in roles(policy,binding['member']):gc(*command,'--role='+binding['role'],'--member='+binding['member'],'--condition=None')
    verify_provider(get('https://iam.googleapis.com/v1/'+PROVIDER))
    checked_role=get('https://iam.googleapis.com/v1/'+role_name)
    require(not checked_role.get('deleted') and checked_role.get('stage')=='GA' and set(checked_role.get('includedPermissions',[]))==set(value['custom_role']['includedPermissions']),'final custom role changed')
    final=[gc('run','services','get-iam-policy',POLICY['service'],'--region='+value['region']),gc('artifacts','repositories','get-iam-policy','dation-runtime','--location='+value['region']),gc('iam','service-accounts','get-iam-policy',runtime),gc('iam','service-accounts','get-iam-policy',DEPLOYER)]
    for binding,policy in zip(value['bindings'],final):require(roles(policy,binding['member'])=={binding['role']},'exact scoped grant not verified')
    require(not roles(gc('projects','get-iam-policy',project),member),'project roles unexpectedly appeared')
    print(json.dumps({'status':'G6_IDENTITY_METADATA_VERIFIED','deployer':DEPLOYER,'plan_sha256':fingerprint(value),
        'live_authentication':'PENDING_READ_ONLY_GITHUB_JOB','auto_deploy_enabled':False,'service_traffic_changed':False,'keys_created':False},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true');parser.add_argument('--owner-go',default='');parser.add_argument('--plan-sha256',default='')
    args=parser.parse_args();value=plan()
    if not args.apply:
        print(json.dumps({'status':'PREVIEW_ONLY','plan_sha256':fingerprint(value),'plan':value},indent=2));return
    apply(value,args.owner_go,args.plan_sha256)

if __name__=='__main__':main()
