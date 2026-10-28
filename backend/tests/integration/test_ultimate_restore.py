"""RESTORE11: real clean-slate/mixed-history/DB+objects/image rehearsal.

All writes and trigger suppression are confined to the labelled disposable
CertificationSandbox. Production connections are not accepted by this runner.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import uuid4

import httpx

BACKEND=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BACKEND/'tests/e2e'))
from ultimate_sql_support import CATALOG_SQL
from ultimate_certification_support import (CertificationSandbox,all_rows_digest,rows_digest,
    mark_testing_workspace,reset_testing_workspace,first_user_journey,backup_restore,activate_restored,effective_catalog)
from ultimate_result_helpers import ok,row,wait_run
from test_ultimate_d2_lineage import day_submit,day_approve
from auth_fixture import USER_A,USER_B
from fixtures import csv_input
from workflow_fixture import prepare_stage
from sandbox import port,wait_for
from tests.test_ultimate_data_contracts import model

OUT=Path(os.getenv('DATION_T11_RESTORE','/tmp/dation-t11-restore'))
IMAGE=os.getenv('DATION_T11_CANDIDATE_IMAGE','dation-certification:rollback-dual-compatible-t11')


def legacy_case(s,client):
    inputs={kind:ok(client.post('/api/datasets/upload',params={'dataset_type':kind},
        data={'is_sample':'true'},files={'file':(kind+'.csv',csv_input(kind),'text/csv')}))['dataset'] for kind in ['orders','fleet']}
    cid=str(uuid4());ok(client.post('/api/decision-cases',json={'id':cid,'orders_dataset_id':inputs['orders']['id'],'fleet_dataset_id':inputs['fleet']['id']}))
    prepare_stage(client,cid,'logistics_assignment',uid=USER_B)
    body={'orders_dataset_id':inputs['orders']['id'],'fleet_dataset_id':inputs['fleet']['id'],
        'decision_case':{'case_id':cid,'node_id':'logistics_assignment'},'configuration':{'objective':'balanced'},
        'options':{'total_time_limit_s':20,'solve_time_limit_s':3,'deterministic_limit':.05,'analysis_depth':'essential','resource_mode':'mixed'}}
    rid=str(uuid4());ok(client.post('/api/runs',params={'run_id':rid},json=body));wait_run(s,rid)
    ok(client.post('/api/runs/'+rid+'/approve',json={'case_id':cid,'node_id':'logistics_assignment'}))
    return {'case_id':cid,'run_id':rid,'body':body}


def image_env(s,path,service_port):
    # Only synthetic loopback credentials; never inherit production variables.
    values={name:s.env[name] for name in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_INPUT_BUCKET','DATION_ACCESS_PASSWORD']}
    values.update(PORT=str(service_port),PYTHONDONTWRITEBYTECODE='1',SUPABASE_ACCESS_TOKEN='',
        GCP_ACCESS_TOKEN='',LLM_API_KEY='',LLM_BASE_URL='',NO_PROXY='127.0.0.1,localhost')
    path.write_text('\n'.join(k+'='+v for k,v in values.items())+'\n');path.chmod(0o600)


class UltimateRestoreTests(unittest.TestCase):
    def test_clean_slate_upgrade_restore_and_dual_compatible_image(self):
        OUT.mkdir(parents=True,exist_ok=True)
        with CertificationSandbox() as s:
            s.start_worker()
            with httpx.Client(base_url=s.api_url,headers={'Authorization':'Bearer '+s.user_tokens[USER_B]},trust_env=False,timeout=45) as other:
                legacy=legacy_case(s,other)
            other_before=rows_digest(s,s.workspace_b)
            catalog_before=effective_catalog(s,CATALOG_SQL)
            marker=mark_testing_workspace(s,s.workspace_a)
            warm=first_user_journey(s)
            self.assertTrue(warm['parent']['approved_at'] and warm['child']['approved_at'])
            s.stop(s.worker)
            with self.assertRaises(RuntimeError):reset_testing_workspace(s,{**marker,'workspace_id':s.workspace_b})
            reset=reset_testing_workspace(s,marker);again=reset_testing_workspace(s,marker)
            self.assertEqual(other_before,rows_digest(s,s.workspace_b))
            self.assertEqual(catalog_before,effective_catalog(s,CATALOG_SQL))
            self.assertFalse(any(reset['remaining_business_rows'].values()))
            self.assertFalse(any(again['remaining_business_rows'].values()))
            self.assertTrue(row(s,legacy['run_id'])['approved_at'])
            (OUT/'clean-slate-reset.json').write_text(json.dumps({'first':reset,'second':again,
                'other_workspace_unchanged':True,'catalog_unchanged':True,'foreign_marker_denied':True,
                'populated_ultimate_rows_and_private_objects_removed':True},indent=2)+'\n')
            s.start_worker();journey=first_user_journey(s)
            parent=journey['parent'];child=journey['child']
            (OUT/'clean-slate-journey.json').write_text(json.dumps(journey,indent=2)+'\n')
            full_before={rid:ok(s.api_client.get('/api/runs/'+rid+'/decision-export',params={'expected_result_fingerprint':row(s,rid)['result_fingerprint'],'format':'json'})) for rid in [parent['id'],child['id']]}
            history_before={rid:ok(s.api_client.get('/api/runs/'+rid+'/copilot-history',params={'expected_result_fingerprint':row(s,rid)['result_fingerprint']})) for rid in full_before}
            backup_dir=OUT/('backup-'+uuid4().hex)
            report=backup_restore(s,backup_dir)
            (OUT/'latest-backup.json').write_text(json.dumps({'path':str(backup_dir),'report':report},indent=2)+'\n')
            activate_restored(s,report,backup_dir/'private-objects')
            catalog_after=effective_catalog(s,CATALOG_SQL)
            (OUT/'catalog-before.json').write_text(json.dumps(catalog_before,indent=2)+'\n')
            (OUT/'catalog-after.json').write_text(json.dumps(catalog_after,indent=2)+'\n')
            self.assertEqual(catalog_before,catalog_after)
            (OUT/'effective-catalog.json').write_text(json.dumps(catalog_before,indent=2)+'\n')
            for original in [parent,child]:
                rid=original['id'];q={'expected_result_fingerprint':original['result_fingerprint']}
                self.assertEqual(row(s,rid),original)
                self.assertEqual(ok(s.api_client.get('/api/runs/'+rid+'/decision-export',params={**q,'format':'json'})),full_before[rid])
                self.assertEqual(ok(s.api_client.get('/api/runs/'+rid+'/copilot-history',params=q)),history_before[rid])
            self.assertEqual(row(s,child['id'])['upstream_run_id'],parent['id'])
            self.assertEqual(row(s,legacy['run_id'])['schema_version'],'assignment_v1')
            self.assertTrue(row(s,legacy['run_id'])['approved_at'])
            image_id=s.docker('image','inspect','--format','{{.Id}}',IMAGE)
            api_port=port();env_file=s.directory/'image-api.env';image_env(s,env_file,api_port)
            api_name=s.identifier+'-rollback-api';s.containers.append(api_name)
            s.docker('run','-d','--name',api_name,'--network','host','--read-only','--tmpfs','/tmp',
                '--env-file',str(env_file),IMAGE)
            base='http://127.0.0.1:'+str(api_port)
            wait_for(lambda:s.reachable(base+'/health'),'dual-compatible image API',timeout=45)
            with httpx.Client(base_url=base,headers={'Authorization':'Bearer '+s.user_tokens[USER_A]},trust_env=False,timeout=45) as image_client:
                for original in [parent,child]:
                    got=ok(image_client.get('/api/runs/'+original['id']+'/result',params={'expected_result_fingerprint':original['result_fingerprint']}))
                    self.assertEqual(got['package'],original['result_json'])
            with httpx.Client(base_url=base,headers={'Authorization':'Bearer '+s.user_tokens[USER_B]},trust_env=False,timeout=45) as image_client:
                self.assertEqual(ok(image_client.get('/api/runs/'+legacy['run_id']))['result_json'],row(s,legacy['run_id'])['result_json'])
            worker_name=s.identifier+'-rollback-worker';s.containers.append(worker_name)
            worker_env=s.directory/'image-worker.env';image_env(s,worker_env,port())
            s.docker('run','-d','--name',worker_name,'--network','host','--read-only','--tmpfs','/tmp',
                '--env-file',str(worker_env),IMAGE,'python','worker.py')
            new_day,_,response=day_submit(s,journey['case_id']);ok(response)
            with httpx.Client(base_url=s.api_url,headers={'Authorization':'Bearer '+s.user_tokens[USER_B]},trust_env=False,timeout=45) as other:
                old_job=str(uuid4());ok(other.post('/api/runs',params={'run_id':old_job},json=legacy['body']))
            self.assertEqual(wait_run(s,new_day,timeout=90)['result_json']['result_schema'],'day_scheduling_v1')
            self.assertEqual(wait_run(s,old_job,timeout=90)['schema_version'],'assignment_v1')
            ok(day_approve(s,journey['case_id'],new_day));smoke_child=row(s,new_day)
            manifest={'workspace_id':s.workspace_a,'candidate_image_id':image_id,'engine_version':'2.0.0',
                'deployment_observation':{'source':'owned Docker inspect and actual image API/worker','image_id':image_id},
                'chain':[{'run_id':p['id'],'result_fingerprint':p['result_fingerprint']} for p in [parent,smoke_child]],
                'pilot_write_authorized':True,'pilot':{'actor_user_id':parent['created_by_user_id'],'configuration':model()['config_jsonb'],'planning_start':'2026-11-02','planning_end':'2026-11-08'}}
            path=OUT/'smoke-manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
            for mode in ['read-only','pilot-write']:
                env={**os.environ,'DATION_T11_SMOKE_TOKEN':s.user_tokens[USER_A]}
                p=subprocess.run([sys.executable,'-B',str(BACKEND/'tests/e2e/ultimate_release_smoke.py'),
                    '--manifest',str(path),'--base-url',base,'--mode',mode,'--workspace-id',s.workspace_a,
                    '--token-env','DATION_T11_SMOKE_TOKEN','--output',str(OUT/('smoke-'+mode+'.json'))],
                    env=env,capture_output=True,text=True,timeout=180)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            (OUT/'rollback-image.json').write_text(json.dumps({'image':IMAGE,'image_id':image_id,
                'actual_container_readers':['assignment_v1','transport_plan_v1','day_scheduling_v1'],
                'actual_container_worker_jobs':[old_job,new_day],'schema_downgrade':False,
                'read_only_and_pilot_smoke':'PASS','deployment':'owned local containers only'},indent=2)+'\n')


if __name__=='__main__':unittest.main()
