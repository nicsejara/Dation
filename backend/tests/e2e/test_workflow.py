"""Cross-layer regressions: actual HTTP, PostgreSQL/PostgREST, engines and processes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4

from fixtures import csv_input
from sandbox import Sandbox, ROOT, wait_for


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=Sandbox().__enter__()
        cls.addClassCleanup(cls.s.__exit__,None,None,None)

    def setUp(self):
        self.s.stop(self.s.worker)
        self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events CASCADE;')
        shutil.rmtree(self.s.storage);self.s.storage.mkdir()

    def tearDown(self):
        result=self._outcome.result
        if any(test is self for test,_ in result.failures+result.errors):
            self.s.diagnostics(self._testMethodName)

    def checked(self,response,status=200):
        self.assertEqual(response.status_code,status,response.text[:2000])
        return response.json()

    def upload(self,kind):
        return self.checked(self.s.api_client.post('/api/datasets/upload',params={'dataset_type':kind},
            data={'is_sample':'true'},files={'file':(kind+'.csv',csv_input(kind),'text/csv')}))['dataset']

    def case(self):
        orders,fleet=self.upload('orders'),self.upload('fleet')
        identifier=str(uuid4())
        self.checked(self.s.api_client.post('/api/decision-cases',json={
            'id':identifier,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}))
        return identifier,orders,fleet

    def body(self,case,orders,fleet,node='logistics_assignment',source=None):
        result={'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id'],
            'decision_case':{'case_id':case,'node_id':node},
            'configuration':{'objective':'balanced'} if source is None else {'strategy':'service_first'},
            'options':{'total_time_limit_s':20,'solve_time_limit_s':3,'deterministic_limit':.05}}
        if source:result['source_run_id']=source
        else:result['options'].update(analysis_depth='essential',resource_mode='mixed')
        return result

    def admit(self,body,identifier=None):
        identifier=identifier or str(uuid4())
        response=self.s.api_client.post('/api/runs',params={'run_id':identifier},json=body)
        run=self.checked(response,202)
        self.assertEqual(response.headers['location'],'/api/runs/'+identifier)
        self.assertEqual(response.headers['retry-after'],'2')
        self.assertEqual(run['id'],identifier)
        return identifier

    def finish(self,identifier,status='completed'):
        result=[]
        def terminal():
            run=self.checked(self.s.api_client.get('/api/runs/'+identifier))
            if run['status'] not in ('completed','error'):return False
            self.assertEqual(run['status'],status,run.get('error_message'))
            result.append(run);return True
        wait_for(terminal,'terminal execution '+identifier,timeout=60)
        return result[0]

    def job(self,identifier):
        return self.checked(self.s.db.get('dispatch_run_jobs',params={'run_id':'eq.'+identifier}))[0]

    def approve(self,run,case,node='logistics_assignment'):
        return self.checked(self.s.api_client.post('/api/runs/'+run+'/approve',json={'case_id':case,'node_id':node}))

    def test_private_ingestion_deduplication_and_tampered_storage_fail_closed(self):
        for path in ['/app','/api/decision-cases']:
            self.assertEqual(self.s.http.get(self.s.api_url+path).status_code,401)
        # Exercise actual PostgREST privilege enforcement; no fake success response.
        forbidden=self.s.http.post(self.s.rest_url+'/rpc/list_decision_cases',
            headers={'Authorization':'Bearer '+self.s.anon_token},json={})
        self.assertIn(forbidden.status_code,(401,403))
        self.assertEqual(forbidden.json()['code'],'42501')
        invalid=self.s.api_client.post('/api/datasets/upload',params={'dataset_type':'orders'},
            files={'file':('invalid.csv',b'wrong;columns\n1;2\n','text/csv')})
        self.assertEqual(invalid.status_code,422)
        self.assertEqual(self.checked(self.s.db.get('datasets')),[])
        case,orders,fleet=self.case()
        duplicate=self.checked(self.s.api_client.post('/api/datasets/upload',params={'dataset_type':'orders'},
            files={'file':('same.csv',csv_input('orders'),'text/csv')}))
        self.assertTrue(duplicate['duplicate']);self.assertEqual(duplicate['existing_dataset']['id'],orders['id'])
        file=self.s.storage/orders['storage_bucket']/orders['storage_path']
        self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),orders['sha256'])
        file.write_bytes(file.read_bytes()+b'\ncorrupted')
        identifier=self.admit(self.body(case,orders,fleet))
        self.s.start_worker()
        run=self.finish(identifier,status='error')
        self.assertIsNone(run.get('result_json'))
        self.assertEqual(self.job(identifier)['state'],'error')

    def test_accepted_job_survives_api_restart_and_crashed_worker_lease(self):
        case,orders,fleet=self.case();body=self.body(case,orders,fleet)
        identifier=self.admit(body)
        self.assertEqual(self.job(identifier)['state'],'queued')
        self.s.stop(self.s.api);self.s.start_api()
        self.assertEqual(self.admit(body,identifier),identifier)
        different=copy.deepcopy(body);different['options']['total_time_limit_s']=21
        self.assertEqual(self.s.api_client.post('/api/runs',params={'run_id':identifier},json=different).status_code,409)
        gate=self.s.storage/'block-downloads';gate.touch()
        self.s.start_worker()
        wait_for(lambda:self.job(identifier)['state']=='running','real worker claim')
        first=self.job(identifier);self.assertEqual(first['attempts'],1)
        self.s.stop(self.s.worker,kill=True)
        self.s.sql(f"UPDATE dispatch_run_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{identifier}';")
        gate.unlink();self.s.start_worker()
        run=self.finish(identifier)
        job=self.job(identifier)
        self.assertEqual(job['attempts'],2);self.assertEqual(job['state'],'completed')
        self.assertIsNone(job['lease_token']);self.assertTrue(run['result_fingerprint'])
        fenced=self.checked(self.s.db.post('rpc/finish_dispatch_job',json={
            'target_run_id':identifier,'worker_token':first['lease_token'],
            'terminal_values':{'status':'error','error_message':'obsolete worker'}}))
        self.assertEqual(fenced,[])
        after=self.checked(self.s.api_client.get('/api/runs/'+identifier))
        self.assertEqual(after['result_fingerprint'],run['result_fingerprint'])
        self.assertEqual(after['status'],'completed')

    def test_assignment_scheduling_and_replacement_update_history_and_compact_list(self):
        case,orders,fleet=self.case();self.s.start_worker()
        assignment=self.finish(self.admit(self.body(case,orders,fleet)))
        approved=self.approve(assignment['id'],case)
        retry=self.approve(assignment['id'],case)
        self.assertEqual(retry['approved_at'],approved['approved_at'])
        self.assertEqual(retry['approved_by'],'shared_workspace:dation')
        scheduling=self.finish(self.admit(self.body(case,orders,fleet,'logistics_scheduling',assignment['id'])))
        self.assertEqual(scheduling['upstream_run_id'],assignment['id'])
        self.approve(scheduling['id'],case,'logistics_scheduling')
        alternative=self.finish(self.admit(self.body(case,orders,fleet)))
        self.approve(alternative['id'],case)
        listed=self.checked(self.s.api_client.get('/api/decision-cases',params={'summary':'true'}))['cases'][0]
        self.assertNotIn('profile_json',listed['orders'])
        nodes=listed['decision_case']['nodes']
        self.assertEqual(nodes['logistics_assignment']['run_count'],2)
        self.assertEqual(nodes['logistics_assignment']['approved_run_id'],alternative['id'])
        self.assertEqual(nodes['logistics_scheduling']['status'],'stale')
        page=self.checked(self.s.api_client.get('/api/decision-cases/'+case+'/runs',
            params={'node_id':'logistics_assignment','limit':1,'offset':1}))
        self.assertEqual(page['total'],2)
        self.assertEqual(page['summary']['approved_run_id'],alternative['id'])
        self.assertEqual(page['runs'][0]['id'],assignment['id'])
        self.assertNotIn('result_json',page['runs'][0])
        self.assertEqual(self.s.api_client.post('/api/runs/'+assignment['id']+'/approve',
            json={'case_id':case,'node_id':'logistics_assignment'}).status_code,409)
        # Replay checks intent before mutable upstream approval, even after replacement.
        scheduling_body=self.body(case,orders,fleet,'logistics_scheduling',assignment['id'])
        self.assertEqual(self.admit(scheduling_body,scheduling['id']),scheduling['id'])
        def projected():
            return self.checked(self.s.db.get('decision_case_reconciliations',params={'case_id':'eq.'+case}))==[]
        wait_for(projected,'projection outbox acknowledgment')
        state=self.checked(self.s.db.get('decision_cases',params={'id':'eq.'+case}))[0]['state_json']
        self.assertEqual(state['nodes']['logistics_scheduling']['status'],'stale')
        events=self.checked(self.s.db.get('decision_approval_events',params={'case_id':'eq.'+case}))
        self.assertEqual(len(events),4)

    def test_browser_creation_execution_approval_navigation_and_mobile_history(self):
        self.s.start_worker()
        browser_python=os.getenv('DATION_BROWSER_PYTHON',str(ROOT/'.browser-venv/bin/python'))
        inputs=self.s.directory/'inputs';inputs.mkdir()
        for kind in ('orders','fleet'):(inputs/(kind+'.csv')).write_bytes(csv_input(kind))
        result=subprocess.run([browser_python,str(ROOT/'tests/e2e/browser_journey.py')],cwd=ROOT,
            env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_E2E_INPUTS':str(inputs)},
            text=True,capture_output=True,timeout=180)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(report['passed']);self.assertEqual(report['javascript_errors'],[])
        self.assertTrue(report['creation_from_files']);self.assertTrue(report['refresh_during_queue'])
        rows=self.checked(self.s.db.get('decision_runs',params={'order':'created_at.asc'}))
        self.assertEqual(len(rows),2)
        self.assertEqual([r['node_id'] for r in rows],['logistics_assignment','logistics_scheduling'])
        self.assertTrue(all(r['status']=='completed' and r['approved_at'] for r in rows))
        self.assertEqual(rows[1]['upstream_run_id'],rows[0]['id'])


if __name__=='__main__':unittest.main(verbosity=2)
