"""Explicit T11/T12 smoke interface. Read-only by default, no literal secrets.

Deployment image identity must be observed out-of-band (Docker/pipeline/service)
and recorded in the manifest; an HTTP health response cannot prove an image ID.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import sys
import time
from uuid import UUID,uuid4

import httpx

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from app.results.canonical import content_sha256,artifact_bytes,result_fingerprint


class Smoke:
    def __init__(self,manifest,base_url,workspace,token):
        UUID(workspace)
        if manifest['workspace_id']!=workspace:raise ValueError('Manifest workspace mismatch')
        identity=manifest['deployment_observation']
        if not identity.get('source') or identity['image_id']!=manifest['candidate_image_id']:
            raise ValueError('Observed deployment identity does not match candidate')
        self.manifest=manifest;self.workspace=workspace;self.calls=[]
        self.client=httpx.Client(base_url=base_url.rstrip('/'),headers={'Authorization':'Bearer '+token},trust_env=False,timeout=60)
    def request(self,method,path,**kwargs):
        before=time.perf_counter();r=self.client.request(method,path,**kwargs)
        self.calls.append({'method':method,'path':path,'status':r.status_code,'bytes':len(r.content),'seconds':time.perf_counter()-before})
        if not r.is_success:raise AssertionError(f'{method} {path}: HTTP {r.status_code}')
        return r
    def get(self,path,**kwargs):return self.request('GET',path,**kwargs).json()
    def write(self,method,path,**kwargs):return self.request(method,path,**kwargs).json()
    def wait_run(self,rid):
        end=time.monotonic()+90
        while time.monotonic()<end:
            r=self.get('/api/runs/'+rid)
            if r['status']=='completed':return r
            if r['status'] in ('error','failed','cancelled'):raise AssertionError('Pilot Run failed')
            time.sleep(.15)
        raise AssertionError('Pilot Run timeout')
    def pilot(self):
        if self.manifest.get('pilot_write_authorized') is not True:raise ValueError('Pilot write not explicitly authorized in manifest')
        cfg=self.manifest['pilot'];owner=str(UUID(cfg['actor_user_id']))
        m=self.write('POST','/api/platform/logistics-models',json={'id':str(uuid4()),'name':'[DATION SYNTHETIC PILOT] Model','configuration':cfg['configuration']})['model']
        v=self.write('POST','/api/platform/logistics-models/'+m['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':m['revision']})['version']
        case=self.write('POST','/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'[DATION SYNTHETIC PILOT] Case','logistics_model_version_id':v['id'],'planning_start':cfg['planning_start'],'planning_end':cfg['planning_end'],'horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':owner})['case']
        base='/api/platform/logistics-cases/'+case['id']
        self.write('PUT','/api/platform/decisions/'+case['id']+'/responsibilities/data_owner',json={'expected_updated_at':None,'owner_user_id':owner})
        for entity in ['transport_demand','transport_resources']:
            state=self.get(base+'/data');template=self.request('GET',base+'/data/templates/'+entity).text
            reader=csv.DictReader(io.StringIO(template));row=next(reader);out=io.StringIO()
            writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\n');writer.writeheader();writer.writerow(row)
            upload=self.write('POST',base+'/data/uploads/'+entity,params={'upload_id':str(uuid4()),'contract_hash':state['contracts'][entity]['contract_hash']},files={'file':('synthetic.csv',out.getvalue().encode(),'text/csv')})
            self.write('POST',base+'/data/publish',json={'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':[{'slot_key':entity,'upload_id':upload['id']}]})
        chain=[]
        for node in ['logistics_assignment','logistics_scheduling']:
            context=self.get(base+'/run-context',params={'node_id':node});rid=str(uuid4())
            body={'request_schema':'ultimate_run_request_v1','workflow_version':2,'case_id':case['id'],'node_id':node,**{key:context[key] for key in ['expected_context_hash','model_version_id','data_pack_version_id','node_policy']}}
            if node=='logistics_scheduling':body['source_transport_plan']=context['source_transport_plan']
            self.write('POST','/api/runs',params={'run_id':rid},json=body);run=self.wait_run(rid);fp=run['result_fingerprint']
            review=self.get('/api/runs/'+rid+'/approval-review',params={'expected_result_fingerprint':fp})
            if not review['approval_overlay']['approval_allowed']:raise AssertionError('Pilot approval blocked')
            self.write('POST','/api/runs/'+rid+'/approve',json={'case_id':case['id'],'node_id':node,'expected_result_fingerprint':fp})
            chain.append({'run_id':rid,'result_fingerprint':fp})
        return chain
    def verify(self,chain):
        self.get('/health');packages=[];saved_turns={}
        for expected in chain:
            rid=str(UUID(expected['run_id']));fp=expected['result_fingerprint'];base='/api/runs/'+rid;q={'expected_result_fingerprint':fp}
            p=self.get(base+'/result',params=q)['package']
            run=self.get(base)
            if not run.get('approved_at'):raise AssertionError('Synthetic chain must be approved')
            if p['context']['workspace_id']!=self.workspace:raise AssertionError('Run workspace mismatch')
            if result_fingerprint(p)!=fp:raise AssertionError('Package fingerprint mismatch')
            if p['engine']['engine_version']!=self.manifest['engine_version']:raise AssertionError('Engine version mismatch')
            if p['result_schema'] not in ['transport_plan_v1','day_scheduling_v1']:raise AssertionError('Unknown result schema')
            self.get(base+'/primary-visual',params=q)
            for d in p['details']:self.get(base+'/details/'+d['dataset_id'],params=q)
            self.request('GET',base+'/decision-export',params={**q,'format':'csv'})
            full=self.get(base+'/decision-export',params={**q,'format':'json'})
            if full.get('complete') is not True or full['package']!=p:raise AssertionError('Incomplete export')
            for ref in p['artifact_manifest']['artifacts']:
                if content_sha256(artifact_bytes(full['artifacts'][ref['artifact_id']]))!=ref['content_sha256']:raise AssertionError('Artifact hash mismatch')
            history=self.get(base+'/copilot-history',params=q);saved_turns[rid]=len(history['rows'])
            review=self.get(base+'/approval-review',params=q)
            if review['approval_review']!=p['approval_review']:raise AssertionError('Review mismatch')
            if review['approval_overlay']['freshness']!='CURRENT':raise AssertionError('Synthetic chain is no longer current')
            packages.append(p)
        if len(packages)!=2 or packages[1]['source_transport_plan']!={'run_id':chain[0]['run_id'],'result_fingerprint':chain[0]['result_fingerprint']}:
            raise AssertionError('Exact D1→D2 lineage required')
        return {'result':'PASS','workspace_id':self.workspace,'chain':chain,'calls':self.calls,
                'candidate_image_id':self.manifest['candidate_image_id'],'deployment_observation':self.manifest['deployment_observation'],
                'saved_copilot_turn_counts':saved_turns}


def main(argv=None):
    parser=argparse.ArgumentParser()
    for name in ['manifest','base-url','workspace-id','token-env','output']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--mode',choices=['read-only','pilot-write'],default='read-only')
    args=parser.parse_args(argv);report={'result':'FAIL','mode':args.mode}
    smoke=None
    try:
        token=os.environ.get(args.token_env)
        if not token:raise ValueError('Token environment variable is empty')
        manifest=json.loads(Path(args.manifest).read_text());smoke=Smoke(manifest,args.base_url,args.workspace_id,token)
        chain=smoke.pilot() if args.mode=='pilot-write' else manifest['chain']
        report=smoke.verify(chain);report['mode']=args.mode
        if args.mode=='read-only' and any(c['method']!='GET' for c in smoke.calls):raise AssertionError('Read-only smoke attempted mutation')
        return_code=0
    except Exception as error:
        report.update(error_type=type(error).__name__,error=str(error),calls=smoke.calls if smoke else [])
        return_code=1
    finally:
        if smoke:smoke.client.close()
        out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'result':report['result'],'mode':args.mode,'report':args.output}))
    return return_code


if __name__=='__main__':sys.exit(main())
