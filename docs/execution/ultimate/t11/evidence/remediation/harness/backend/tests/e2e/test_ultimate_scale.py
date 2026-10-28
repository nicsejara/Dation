"""PERF11 complete first-job execution on a real, bounded owned image worker."""
import csv
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import unittest
from uuid import uuid4
import httpx

BACKEND=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(BACKEND),str(BACKEND/'tests/integration')]
from ultimate_certification_support import CertificationSandbox
from ultimate_result_helpers import ok,row,intention
from sandbox import port,wait_for
from auth_fixture import USER_A
from tests.test_ultimate_performance import scale_request
from tests.test_ultimate_data_contracts import model
from test_ultimate_restore import image_env

OUT=Path(os.getenv('DATION_T11_R_SCALE','/tmp/dation-t11-r-scale'))
IMAGE=os.getenv('DATION_T11_R_IMAGE','dation-certification:t11-r-under-test')


class UltimateScaleRehearsalTests(unittest.TestCase):
    def test_complete_cold_job_matches_envelope_and_existing_budget(self):
        for repetition in (1,2):
            with self.subTest(cold_first_job=repetition):self.measure_complete_cold_job(repetition)

    def measure_complete_cold_job(self,repetition):
        OUT.mkdir(parents=True,exist_ok=True);requested=scale_request()
        with CertificationSandbox() as s:
            api_port=port();api_env=s.directory/'scale-api.env';image_env(s,api_env,api_port)
            api_name=s.identifier+'-scale-api';s.containers.append(api_name)
            s.docker('run','-d','--name',api_name,'--label','dation.qa.execution=T11-R','--label','dation.qa.owner=codex-dation',
                '--network','host','--memory','512m','--read-only','--tmpfs','/tmp','--env-file',str(api_env),IMAGE)
            image_base='http://127.0.0.1:'+str(api_port)
            wait_for(lambda:s.reachable(image_base+'/health'),'owned candidate image API',timeout=45)
            s.api_client.close()
            s.api_client=httpx.Client(base_url=image_base,headers={'Authorization':'Bearer '+s.user_tokens[USER_A]},trust_env=False,timeout=30)
            config=model(split_permitted=True)['config_jsonb'];api=s.api_client
            m=ok(api.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'T11-R scale owned','configuration':config}))
            v=ok(api.post('/api/platform/logistics-models/'+m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))
            case=ok(api.post('/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'T11-R 500/50/31','logistics_model_version_id':v['version']['id'],
                'planning_start':str(requested.context.planning_start),'planning_end':str(requested.context.planning_end),'horizon_type':'CUSTOM',
                'case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}))
            cid=case['case']['id'];base='/api/platform/logistics-cases/'+cid
            ok(api.put('/api/platform/decisions/'+cid+'/responsibilities/data_owner',json={'expected_updated_at':None,'owner_user_id':USER_A}))
            for entity,records in [('transport_demand',requested.demands),('transport_resources',requested.resources)]:
                state=ok(api.get(base+'/data'));template=api.get(base+'/data/templates/'+entity);self.assertEqual(template.status_code,200)
                headers=next(csv.reader(io.StringIO(template.content.decode())))
                stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=headers,lineterminator='\n');writer.writeheader()
                for record in records:
                    values=dict.fromkeys(headers,'')
                    if entity=='transport_demand':
                        values.update(order_id=record.order_id,origin_id=record.origin_id,destination_id=record.destination_id,distance_km=str(record.distance_km),
                            ready_date=str(record.ready_date),delivery_due_date=str(record.delivery_due_date),priority=record.priority,
                            split_allowed=str(record.split_allowed).lower(),demand_pallets=str(record.requested.pallets),compatibility_groups=record.compatibility_groups[0])
                    else:
                        self.assertEqual(record.source,'EXTERNAL');self.assertEqual(record.external_cost.cost_model,'PER_TRIP')
                        values.update(resource_id=record.resource_id,source=record.source,lanes=json.dumps(record.lanes),guaranteed_pallets=str(record.guaranteed_capacity.pallets),
                            services_available=str(record.services_available),availability_source=record.availability_source,cost_model='PER_TRIP',
                            trip_rate=str(record.external_cost.rate),compatibility_groups=record.compatibility_groups[0])
                    writer.writerow(values)
                uploaded=ok(api.post(base+'/data/uploads/'+entity,params={'upload_id':str(uuid4()),'contract_hash':state['contracts'][entity]['contract_hash']},
                    files={'file':('scale.csv',stream.getvalue().encode(),'text/csv')}))
                ok(api.post(base+'/data/publish',json={'publication_id':str(uuid4()),'expected_revision':state['pack']['revision'],'selection':[{'slot_key':entity,'upload_id':uploaded['id']}]}))
            name=s.identifier+'-scale-worker';s.containers.append(name);worker_port=port();env=s.directory/'scale-worker.env';image_env(s,env,worker_port)
            startup=time.perf_counter()
            s.docker('run','-d','--name',name,'--label','dation.qa.execution=T11-R','--label','dation.qa.owner=codex-dation',
                '--network','host','--memory','1g','--cpus','2','--read-only','--tmpfs','/tmp','--env-file',str(env),
                '--mount','type=bind,src='+str(BACKEND/'tests/e2e/ultimate_scale_worker.py')+',dst=/qa/ultimate_scale_worker.py,readonly',IMAGE,'python','/qa/ultimate_scale_worker.py')
            try:wait_for(lambda:s.reachable('http://127.0.0.1:'+str(worker_port)+'/'),'cold owned image worker',timeout=45)
            except BaseException:
                logs=subprocess.run(['docker','--host=unix:///var/run/docker.sock','logs',name],capture_output=True,text=True,check=True)
                (OUT/('worker-startup-%d.log'%repetition)).write_text(logs.stdout+logs.stderr)
                raise
            startup_seconds=time.perf_counter()-startup
            rid=str(uuid4());body=intention(s,cid);before=time.perf_counter();response=api.post('/api/runs',params={'run_id':rid},json=body)
            admission_seconds=time.perf_counter()-before;self.assertEqual(response.status_code,202,response.text)
            # Observation deadline unchanged from the existing probe. The gate
            # remains90s; waiting longer records the failure instead of hiding it.
            while time.perf_counter()-before<180:
                run=row(s,rid)
                if run['status'] in ('completed','error'):break
                time.sleep(.25)
            observed_seconds=time.perf_counter()-before
            self.assertEqual(run['status'],'completed',run.get('error_message'))
            wait_for(lambda:subprocess.run(['docker','exec',name,'test','-f','/tmp/t11-r-worker-metrics.json'],capture_output=True).returncode==0,'worker metrics',timeout=5)
            metrics=json.loads(s.docker('exec',name,'cat','/tmp/t11-r-worker-metrics.json'))
            resources=json.loads(s.docker('inspect','--format','{{json .HostConfig}}',name))
            p=run['result_json'];self.assertEqual(p['metrics']['trip_count'],128);self.assertEqual(p['engine']['solver_status'],'FEASIBLE')
            self.assertEqual(len(p['artifact_manifest']['artifacts']),83)
            retrieval=[]
            for part in ['result','primary-visual','details/plan']:
                times=[];sizes=[]
                for _ in range(5):
                    now=time.perf_counter();got=api.get('/api/runs/'+rid+'/'+part,params={'expected_result_fingerprint':run['result_fingerprint']});times.append(time.perf_counter()-now)
                    self.assertEqual(got.status_code,200,got.text);sizes.append(len(got.content))
                retrieval.append({'path':part,'n':5,'p50_seconds':statistics.median(times),'p95_nearest_rank_seconds':max(times),'max_bytes':max(sizes)})
            report={'repetition':repetition,'run_id':rid,'workspace_id':s.workspace_a,'cold_process_first_job':True,'orders':500,'resources':50,'horizon_days':31,
                'startup_seconds_before_admission':startup_seconds,'admission_seconds':admission_seconds,'admission_to_observed_complete_seconds':observed_seconds,
                'worker':metrics,'image_id':s.docker('inspect','--format','{{.Image}}',name),
                'api_image_id':s.docker('inspect','--format','{{.Image}}',api_name),'api_image_used_for_all_business_actions':True,
                'limits':{'memory_bytes':resources['Memory'],'nano_cpus':resources['NanoCpus']},'retrieval':retrieval,
                'result_fingerprint':run['result_fingerprint'],'package':p,'production_touched':False}
            (OUT/('complete-cold-job-%d.json'%repetition)).write_text(json.dumps(report,indent=2)+'\n')
            self.assertLessEqual(observed_seconds,90)
            self.assertLessEqual(metrics['complete_execution_seconds'],90)
            self.assertEqual(resources['Memory'],1024**3)
            self.assertEqual(int(metrics['memory.max']),resources['Memory'])
            self.assertLess(int(metrics['memory.peak']),resources['Memory']*.9)


if __name__=='__main__':unittest.main()
