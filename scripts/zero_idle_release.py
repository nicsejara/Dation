"""Offline release plan/validator. No implicit build, deploy, SQL or billing call."""
import argparse
import ast
import copy
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'infra/zero-idle/release.json'
sys.path.insert(0, str(ROOT/'backend'))
from app.cloud_identity import (PROJECT, PROJECT_NUMBER, REGION, SERVICE, JOBS,
    validate_environment, validate_account, validate_image)


def validate(plan):
    if (plan['project'],plan['project_number'],plan['region'])!=(PROJECT,PROJECT_NUMBER,REGION):
        raise ValueError('Project/region mismatch')
    if plan['billing_policy']!='OFF_UNTIL_EXPLICIT_OWNER_GO':raise ValueError('Billing must remain OFF')
    validate_environment(plan['environment'])
    validate_account(plan['service_account']);validate_account(plan['scheduler_service_account'])
    if plan['service_account']==plan['scheduler_service_account']:raise ValueError('Scheduler identity must be separate')
    validate_image(plan['image'])
    if plan['release_sha']!='REQUIRES_EXACT_VALIDATED_SHA' and not re.fullmatch('[0-9a-f]{40}',plan['release_sha']):
        raise ValueError('Exact release SHA required')
    if plan['merge_gate']!='MERGE_BLOCKED_DEPLOY_TRIGGER':raise ValueError('Remote trigger authorization is unverified')
    api=plan['api']
    if api['name']!=SERVICE:raise ValueError('Unexpected API target')
    if api['min_instances']!=0 or not api['cpu_idle'] or not 1<=api['max_instances']<=2:
        raise ValueError('API must scale to zero with request CPU and max 2 instances')
    if api['cpu']!='1' or api['memory']!='512Mi' or not 1<=api['concurrency']<=8:
        raise ValueError('Unexpected API resources')
    for key,memory,maximum in [('compute','1Gi',1800),('control','512Mi',120)]:
        job=plan[key]
        if (job['cpu'],job['memory'],job['task_count'],job['parallelism'],job['max_retries'])!=('1',memory,1,1,0):
            raise ValueError('Unexpected finite Job capacity')
        if job['command']!=['python','event_worker.py'] or not 1<=job['timeout_seconds']<=maximum:
            raise ValueError('Resident or unbounded worker forbidden')
        if job['args']!= ([] if key=='compute' else ['--recover']):raise ValueError('Unreviewed Job args')
    env=plan['environment']
    if env.get('DATION_EXECUTION_MODE')!='jobs' or env.get('DATION_CLOUD_EXECUTION_ENABLED')!='false':
        raise ValueError('Offline plan must leave cloud execution disabled')
    if any(k.startswith('DATION_TEST_') or k=='DATION_DISPATCH_FAKE_URL' for k in env):raise ValueError('Test transport forbidden')
    for key,name in [('compute','dation-executor'),('control','dation-recovery')]:
        if plan[key]['name']!=name or env.get('DATION_'+key.upper()+'_JOB')!=JOBS[key]:
            raise ValueError('Unexpected Job target')
    if any('KEY' in k or 'TOKEN' in k or 'PASSWORD' in k for k in env):raise ValueError('Embedded credentials forbidden')
    for name,ref in plan['secret_references'].items():
        if set(ref)!={'secret','version'} or not re.fullmatch('[a-zA-Z0-9_-]+',ref['secret']) or not re.fullmatch('[1-9][0-9]*',ref['version']):
            raise ValueError('Only pinned Secret Manager references allowed')
    schedule=plan['recovery_schedule']
    if schedule['create_by_default'] or schedule['enabled'] or schedule['schedule']!='*/15 * * * *' or schedule['time_zone']!='Etc/UTC' or schedule['target']!=plan['control']['name']:
        raise ValueError('Scheduling requires a separate future authorization')
    return plan


def scan_deploy_scripts(directory=ROOT/'scripts'):
    """Scan executable literals, including nested generated manifests, in every script."""
    issues=[]
    for path in sorted(directory.rglob('*.py')):
        tree=ast.parse(path.read_text(),filename=str(path))
        parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if isinstance(node,ast.Dict):
                for key,value in zip(node.keys,node.values):
                    if not isinstance(key,ast.Constant):continue
                    if key.value in {'autoscaling.knative.dev/minScale','minInstances','min_instances','minInstanceCount'} and isinstance(value,ast.Constant):
                        if str(value.value).isdigit() and int(value.value)>0:issues.append(str(path)+': permanent instances')
                    if key.value in {'cpuIdle','cpu_idle'} and isinstance(value,ast.Constant) and value.value is False:issues.append(str(path)+': permanent service CPU')
                    if isinstance(key.value,str) and key.value.endswith(('_KEY','_TOKEN','_PASSWORD')) and isinstance(value,ast.Constant) and isinstance(value.value,str) and value.value:issues.append(str(path)+': embedded credential')
                    if key.value=='run.googleapis.com/cpu-throttling' and isinstance(value,ast.Constant) and value.value=='false':issues.append(str(path)+': permanent CPU')
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                parent=parents.get(node)
                if isinstance(parent,ast.Compare):continue
                if isinstance(parent,ast.Call) and isinstance(parent.func,ast.Attribute) and isinstance(parent.func.value,ast.Name) and parent.func.value.id=='re':continue
                text=node.value
                if re.search(r'--min-instances[= ]+[1-9]|--no-cpu-throttling',text):issues.append(str(path)+': unsafe service flags')
                if text=='worker.py':issues.append(str(path)+': resident worker command')
    if issues:raise ValueError('\n'.join(issues))


def manifest(plan):
    """Cloud Run v2 resource bodies, references only. Does not send requests."""
    validate(plan)
    env=[{'name':k,'value':v} for k,v in plan['environment'].items()]
    env.append({'name':'DATION_RELEASE_SHA','value':plan['release_sha']})
    env += [{'name':k,'valueSource':{'secretKeyRef':v}} for k,v in plan['secret_references'].items()]
    common={'name':'runtime','image':plan['image'],'env':env}
    api=plan['api'];service={'name':f'projects/{PROJECT}/locations/{REGION}/services/'+api['name'],
        'template':{'serviceAccount':plan['service_account'],'scaling':{'minInstanceCount':0,'maxInstanceCount':api['max_instances']},
            'maxInstanceRequestConcurrency':api['concurrency'],'timeout':str(api['timeout_seconds'])+'s',
            'containers':[{**copy.deepcopy(common),'command':['sh','-c'],'args':['exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"'],
                'resources':{'limits':{'cpu':'1','memory':'512Mi'},'cpuIdle':True}}]}}
    jobs=[]
    for key in ['compute','control']:
        j=plan[key];jobs.append({'name':JOBS[key],
            'template':{'taskCount':1,'parallelism':1,'template':{'serviceAccount':plan['service_account'],
                'maxRetries':0,'timeout':str(j['timeout_seconds'])+'s',
                'containers':[{**copy.deepcopy(common),'command':j['command'],'args':j['args'],
                    'resources':{'limits':{'cpu':j['cpu'],'memory':j['memory']}}}]}}})
    return {'service':service,'jobs':jobs,**supporting_manifests(plan),
        'scheduler_created':False,'mutation_performed':False}


def supporting_manifests(plan):
    """Reviewable create/binding proposals; never read or write a cloud resource."""
    runtime=plan['service_account'];scheduler=plan['scheduler_service_account']
    role=f'projects/{PROJECT}/roles/dationFiniteJobDispatcher'
    secrets=sorted({ref['secret'] for ref in plan['secret_references'].values()})
    bindings=[{'resource':resource,'role':role,'members':['serviceAccount:'+runtime]}
              for resource in JOBS.values()]
    bindings.append({'resource':JOBS['control'],'role':'roles/run.invoker',
                     'members':['serviceAccount:'+scheduler]})
    bindings += [{'resource':f'projects/{PROJECT}/secrets/'+name,
                  'role':'roles/secretmanager.secretAccessor','members':['serviceAccount:'+runtime]}
                 for name in secrets]
    accounts=[]
    for email,title in [(runtime,'Dation finite runtime'),(scheduler,'Dation recovery scheduler')]:
        accounts.append({'parent':f'projects/{PROJECT}','accountId':email.split('@')[0],
                         'serviceAccount':{'displayName':title}})
    schedule=plan['recovery_schedule']
    return {
        'service_accounts':accounts,
        'iam':{'custom_role':{'parent':f'projects/{PROJECT}','roleId':'dationFiniteJobDispatcher',
            'role':{'title':'Dation finite Jobs dispatcher','stage':'GA',
                    'includedPermissions':['run.jobs.get','run.jobs.run','run.jobs.runWithOverrides']}},
            'bindings':bindings,'policy_updates':'Read policy, preserve bindings, merge reviewed delta with etag'},
        'secret_manager':{'create_proposals':[{'parent':f'projects/{PROJECT}','secretId':name,
            'secret':{'replication':{'automatic':{}}}} for name in secrets],
            'version_references':copy.deepcopy(plan['secret_references']),
            'values_included':False,'versions_created':False},
        'scheduler':{'enabled':False,'create_by_default':False,'desired_initial_state':'PAUSED',
            'creation_requires_explicit_go':True,
            'request':{'name':f'projects/{PROJECT}/locations/{REGION}/jobs/dation-recovery-every-15m',
                'schedule':schedule['schedule'],'timeZone':schedule['time_zone'],
                'attemptDeadline':'30s','retryConfig':{'retryCount':0},
                'httpTarget':{'uri':'https://run.googleapis.com/v2/'+JOBS['control']+':run',
                    'httpMethod':'POST','headers':{'Content-Type':'application/json'},'body':'e30=',
                    'oauthToken':{'serviceAccountEmail':scheduler,
                                 'scope':'https://www.googleapis.com/auth/cloud-platform'}}},
            'warning':'Create may start scheduling immediately; never create then pause without activation GO'},
    }


def apply_gate(plan,owner_go):
    validate(plan);scan_deploy_scripts()
    # Hard hold: this candidate has no verified remote trigger/IAM/billing state.
    # A copied flag or an old environment variable must never bypass that hold.
    if not owner_go:raise ValueError('Explicit owner authorization required')
    raise ValueError('MERGE_BLOCKED_DEPLOY_TRIGGER: live gates unverified; no production action permitted')


def rollback_plan(plan):
    validate(plan)
    return {'mutation_performed':False,'admissions':'freeze NEW admissions; retain accepted outbox and business data',
        'target':'only a separately verified zero-idle revision; otherwise maintenance/unavailability',
        'forbidden':'historical resident-worker revision','billing':'keep OFF; never link billing automatically'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','validate','apply','rollback'],default='plan',nargs='?')
    parser.add_argument('--config',type=Path,default=DEFAULT)
    parser.add_argument('--authorize',help='Future explicit owner GO; does not remove unresolved live gates')
    args=parser.parse_args();plan=json.loads(args.config.read_text());validate(plan);scan_deploy_scripts()
    if args.action=='apply':apply_gate(plan,args.authorize)
    result=rollback_plan(plan) if args.action=='rollback' else manifest(plan)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
