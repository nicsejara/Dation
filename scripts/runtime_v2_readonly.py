"""Sanitized Runtime V2 inventory in Cloud Shell. GET only; never enable APIs.

Default: print the fixed read plan. --cloud-shell uses the owner's existing
gcloud login, captures its access token in memory, and never prints it.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.cloud_identity import PROJECT, PROJECT_NUMBER, REGION


def endpoints():
    return {
        'project':f'https://cloudresourcemanager.googleapis.com/v3/projects/{PROJECT}',
        'billing':f'https://cloudbilling.googleapis.com/v1/projects/{PROJECT}/billingInfo',
        'triggers_global':f'https://cloudbuild.googleapis.com/v1/projects/{PROJECT}/locations/global/triggers',
        'triggers_regional':f'https://cloudbuild.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/triggers',
        'builds_global':f'https://cloudbuild.googleapis.com/v1/projects/{PROJECT}/locations/global/builds?pageSize=100',
        'builds_regional':f'https://cloudbuild.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/builds?pageSize=100',
        'services':f'https://run.googleapis.com/v2/projects/{PROJECT}/locations/{REGION}/services',
        'jobs':f'https://run.googleapis.com/v2/projects/{PROJECT}/locations/{REGION}/jobs',
        'scheduler':f'https://cloudscheduler.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/jobs',
        'accounts':f'https://iam.googleapis.com/v1/projects/{PROJECT}/serviceAccounts',
        'repositories':f'https://artifactregistry.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/repositories',
        'secrets':f'https://secretmanager.googleapis.com/v1/projects/{PROJECT}/secrets',
        'apis':f'https://serviceusage.googleapis.com/v1/projects/{PROJECT_NUMBER}/services?filter=state:ENABLED',
    }


def sanitize(data):
    allowed={'name','id','projectId','state','status','disabled','email','billingEnabled',
             'latestReadyRevision','latestCreatedRevision','schedule','timeZone'}
    result={key:value for key,value in data.items() if key in allowed}
    for key in ['services','jobs','triggers','builds','accounts','repositories','secrets']:
        if isinstance(data.get(key),list):
            result[key]=[{k:v for k,v in item.items() if k in allowed} for item in data[key]]
    result['next_page_present']=bool(data.get('nextPageToken'))
    return result


def fetch(url,token):
    if url not in endpoints().values():raise ValueError('Only the pinned Runtime V2 read plan is permitted')
    request=Request(url,headers={'Authorization':'Bearer '+token},method='GET')
    try:
        with urlopen(request,timeout=20) as response:
            result=sanitize(json.load(response))
            return {'http_status':response.status,'verified':not result['next_page_present'],'data':result}
    except HTTPError as error:
        return {'http_status':error.code,'verified':False}
    except (OSError,ValueError):
        return {'verified':False,'error':'Read failed; no configuration changed'}


def collect(token,reader=fetch):
    urls=endpoints();project=reader(urls['project'],token)
    data=project.get('data',{})
    if not project.get('verified') or data.get('projectId')!=PROJECT or data.get('name')!='projects/'+PROJECT_NUMBER or data.get('state')!='ACTIVE':
        return {'project':project,'remaining_reads':'NOT_ATTEMPTED: project authentication/identity unverified'}
    return {'project':project,**{key:reader(url,token) for key,url in urls.items() if key!='project'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloud-shell',action='store_true',help='Perform GETs using the current Cloud Shell identity')
    args=parser.parse_args()
    if not args.cloud_shell:
        print(json.dumps({'project':PROJECT,'methods':['GET'],'urls':endpoints(),'mutation_performed':False},indent=2));return
    auth=subprocess.run(['gcloud','auth','print-access-token'],capture_output=True,text=True)
    if auth.returncode or not auth.stdout.strip():raise SystemExit('Cloud Shell authentication unavailable; no requests sent')
    result=collect(auth.stdout.strip())
    print(json.dumps({'project':PROJECT,'reads':result,'mutation_performed':False},indent=2))
    if any(not isinstance(value,dict) or not value.get('verified') for value in result.values()):raise SystemExit(1)


if __name__=='__main__':main()
