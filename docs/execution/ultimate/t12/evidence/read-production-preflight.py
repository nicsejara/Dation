"""T12 read-only provider preflight. Never logs secrets or changes a service."""
import concurrent.futures,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx

OUT=Path('/workspace/work/dation-t12')
GCP={'Authorization':'Bearer '+os.environ['GCP_ACCESS_TOKEN']}
SB={'Authorization':'Bearer '+os.environ['SUPABASE_ACCESS_TOKEN']}
targets=[
 ('gcp-project','https://cloudresourcemanager.googleapis.com/v1/projects/dation-510100',GCP),
 ('cloud-run-api','https://run.googleapis.com/v1/projects/dation-510100/locations/us-west1/services/dation-core',GCP),
 ('cloud-run-worker','https://run.googleapis.com/v1/projects/dation-510100/locations/us-west1/services/dation-core-worker',GCP),
 ('supabase-backups','https://api.supabase.com/v1/projects/gijiinufjjurgfeehufj/database/backups',SB),
 ('production-health','https://dation-core-469052310590.us-west1.run.app/health',{}),
 ('supabase-changelog','https://supabase.com/changelog.md',{})]

def safe_service(v):
 spec=v.get('spec',{});template=spec.get('template',{});body=template.get('spec',{});containers=[]
 for c in body.get('containers',[]):
  public={'image':c.get('image'),'command':c.get('command'),'args':c.get('args'),'resources':c.get('resources'),'env_names':[],'secret_refs':[],'public_config':{}}
  for e in c.get('env',[]):
   public['env_names'].append(e['name'])
   if 'valueFrom' in e:public['secret_refs'].append({'name':e['name'],'reference':e['valueFrom']})
   elif e['name'] in ('SUPABASE_URL','SUPABASE_INPUT_BUCKET','DATION_BUILD_SHA','PORT'):public['public_config'][e['name']]=e.get('value')
  containers.append(public)
 return {'name':v.get('metadata',{}).get('name'),'namespace':v.get('metadata',{}).get('namespace'),'labels':v.get('metadata',{}).get('labels'),'template_annotations':template.get('metadata',{}).get('annotations'),'service_account':body.get('serviceAccountName'),'container_concurrency':body.get('containerConcurrency'),'timeout_seconds':body.get('timeoutSeconds'),'containers':containers,'traffic':spec.get('traffic'),'status':v.get('status')}

def safe_backups(value):
 if isinstance(value,dict):
  return {key:('[REDACTED]' if any(term in key.lower() for term in ('token','password','secret','url','credential','connection','dsn')) else safe_backups(item)) for key,item in value.items()}
 if isinstance(value,list):return [safe_backups(item) for item in value]
 return value

def check(item):
 name,url,headers=item;start=time.perf_counter();record={'observed_at_utc':datetime.now(timezone.utc).isoformat(),'operation':'GET','url':url,'production_mutation':False}
 try:
  response=httpx.get(url,headers=headers,timeout=30,follow_redirects=False)
  record.update(status=response.status_code,seconds=time.perf_counter()-start)
  if response.status_code>=400:
   try:body=response.json();record['error']=str(body.get('error',body))[:600]
   except ValueError:record['error']=response.text[:300]
  elif name.startswith('cloud-run'):record['result']=safe_service(response.json())
  elif name=='gcp-project':record['result']={k:response.json().get(k) for k in ['projectId','projectNumber','name','lifecycleState']}
  elif name=='supabase-backups':record['result']=safe_backups(response.json())
  elif name=='production-health':record['result']=response.json()
  else:
   (OUT/'supabase-changelog.md').write_text(response.text);record['bytes']=len(response.content)
 except Exception as error:record.update(error_type=type(error).__name__,error=str(error)[:400])
 (OUT/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n');return {'name':name,'status':record.get('status'),'error':record.get('error')}

assert urlparse(os.environ['SUPABASE_URL']).hostname=='gijiinufjjurgfeehufj.supabase.co'
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for value in pool.map(check,targets):print(json.dumps(value),flush=True)
