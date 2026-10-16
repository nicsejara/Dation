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

from fixtures import csv_input,assignment_matrix_inputs
from sandbox import Sandbox, ROOT, wait_for


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=Sandbox().__enter__()
        cls.addClassCleanup(cls.s.__exit__,None,None,None)

    def setUp(self):
        self.s.stop(self.s.worker)
        self.s.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events,dispatch_worker_instances CASCADE;')
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

    def test_assignment_dashboard_all_objectives_use_actual_worker_evidence(self):
        datasets={}
        for kind,content in assignment_matrix_inputs().items():
            datasets[kind]=self.checked(self.s.api_client.post('/api/datasets/upload',params={'dataset_type':kind},
                data={'is_sample':'true'},files={'file':('qa-'+kind+'.csv',content,'text/csv')}))['dataset']
        case=str(uuid4());orders,fleet=datasets['orders'],datasets['fleet']
        self.checked(self.s.api_client.post('/api/decision-cases',json={'id':case,'orders_dataset_id':orders['id'],'fleet_dataset_id':fleet['id']}))
        self.s.start_worker();runs=[]
        for objective in ('min_trips','min_cost','max_own_fleet','balanced','min_co2'):
            body=self.body(case,orders,fleet);body['configuration']={'mode':'preset','objective':objective,'dimensions':['trips','cost','own_fleet','co2']}
            body['options'].update(analysis_depth='comparative',allow_third_party=True)
            run=self.finish(self.admit(body));result=run['result_json'];selected=result['scenarios']['selected']
            self.assertEqual(result['configuration']['objective'],objective)
            self.assertEqual(selected['plan_fingerprint'],result['scenarios'][objective]['plan_fingerprint'])
            self.assertTrue(selected['feasible'])
            runs.append({'id':run['id'],'objective':objective,'plan_fingerprint':selected['plan_fingerprint'],
                'result_fingerprint':run['result_fingerprint'],'metrics':selected['metrics'],'trips':selected['trips']})
        shares=[run['metrics']['own_weight_share'] for run in runs]
        self.assertIn(1,shares);self.assertTrue(any(share<1 for share in shares),shares)
        path=self.s.directory/'assignment-matrix.json';path.write_text(json.dumps({'case_id':case,'runs':runs},indent=2))
        browser_python=os.getenv('DATION_BROWSER_PYTHON',str(ROOT/'.browser-venv/bin/python'))
        outcome=subprocess.run([browser_python,str(ROOT/'tests/e2e/assignment_matrix_journey.py')],
            cwd=ROOT,env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_E2E_MATRIX':str(path)},capture_output=True,text=True,timeout=120)
        self.assertEqual(outcome.returncode,0,(outcome.stdout+outcome.stderr)[-8000:])
        report=json.loads(path.with_name('assignment-matrix-browser-report.json').read_text());self.assertTrue(report['passed'])
        artifact=os.getenv('DATION_E2E_ARTIFACTS')
        if artifact:
            output=Path(artifact);output.mkdir(parents=True,exist_ok=True)
            (output/'assignment-matrix-browser-report.json').write_text(json.dumps(report,indent=2))
        for row in runs:self.assertEqual(self.checked(self.s.api_client.get('/api/runs/'+row['id']))['result_fingerprint'],row['result_fingerprint'])
        self.assertEqual(len(self.checked(self.s.db.get('decision_runs',params={'select':'id'}))),5)
        self.assertEqual(self.checked(self.s.db.get('decision_approval_events',params={'select':'id'})),[])

    def test_private_operations_trace_worker_readiness_and_cluster_metrics(self):
        for path in ['/ready','/metrics','/api/system/operations']:
            response=self.s.http.get(self.s.api_url+path)
            self.assertEqual(response.status_code,401)
            self.assertIn('x-request-id',response.headers)
        self.assertEqual(self.s.api_client.get('/ready').status_code,503)
        self.assertEqual(self.checked(self.s.api_client.get('/api/system/operations'))['database'],'available')
        case,orders,fleet=self.case();identifier=str(uuid4());request_id=str(uuid4());trace=uuid4().hex
        response=self.s.api_client.post('/api/runs',params={'run_id':identifier},json=self.body(case,orders,fleet),
            headers={'X-Request-ID':request_id,'traceparent':'00-'+trace+'-'+'1'*16+'-01'})
        self.checked(response,202);self.assertEqual(response.headers['x-request-id'],request_id)
        self.assertIn(trace,response.headers['traceparent'])
        metadata=self.job(identifier)['request_json']['_observability']
        self.assertEqual(metadata,{'request_id':request_id,'trace_id':trace})
        self.s.start_worker();run=self.finish(identifier)
        ready=self.checked(self.s.api_client.get('/ready'));self.assertTrue(ready['ready'])
        snapshot=self.checked(self.s.api_client.get('/api/system/operations'))
        self.assertEqual(snapshot['workers']['healthy'],1);self.assertEqual(snapshot['queue']['queued'],0)
        self.assertEqual(snapshot['runs_24h']['duration_p95_ms'],run['duration_ms'])
        metrics=self.s.api_client.get('/metrics');self.assertEqual(metrics.status_code,200)
        self.assertIn('dation_workers_healthy 1',metrics.text);self.assertNotIn(identifier,metrics.text)
        worker_metrics=self.s.http.get('http://127.0.0.1:'+str(self.s.worker_port)+'/metrics')
        self.assertEqual(worker_metrics.status_code,200)
        self.assertIn('dation_worker_execution_seconds_count',worker_metrics.text)
        records=[]
        for logfile in self.s.logs:
            for line in Path(logfile.name).read_text().splitlines():
                try:records.append(json.loads(line))
                except ValueError:pass
        lifecycle=[r for r in records if r.get('run_id')==identifier and r.get('event') in ('dispatch_admitted','dispatch_claimed','dispatch_completed')]
        self.assertEqual({r['event'] for r in lifecycle},{'dispatch_admitted','dispatch_claimed','dispatch_completed'})
        self.assertTrue(all(r['request_id']==request_id and r['trace_id']==trace for r in lifecycle))
        self.assertTrue(any(r['component']=='worker' for r in lifecycle))
        self.s.stop(self.s.worker)
        self.assertEqual(self.s.api_client.get('/ready').status_code,503)
        self.assertEqual(self.checked(self.s.api_client.get('/health')),{'status':'healthy'})

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

    def analysis(self,identifier):
        return self.checked(self.s.api_client.get('/api/runs/'+identifier+'/comparative'))

    def complete_analysis(self,identifier,status='completed'):
        rows=[]
        def terminal():
            row=self.analysis(identifier)
            if row['status'] not in ('completed','error'):return False
            self.assertEqual(row['status'],status,row.get('error_message'));rows.append(row);return True
        wait_for(terminal,'comparative completion',timeout=60)
        return rows[0]

    def test_progressive_comparative_recovers_real_worker_without_changing_case_or_history(self):
        case,orders,fleet=self.case();body=self.body(case,orders,fleet);body['configuration']['objective']='min_trips'
        self.s.start_worker();assignment=self.finish(self.admit(body));self.approve(assignment['id'],case)
        scheduling=self.finish(self.admit(self.body(case,orders,fleet,'logistics_scheduling',assignment['id'])))
        self.approve(scheduling['id'],case,'logistics_scheduling')
        wait_for(lambda:self.checked(self.s.db.get('decision_case_reconciliations'))==[],'settled original case')
        self.s.stop(self.s.worker)
        def business():
            return {table:self.checked(self.s.db.get(table,params={'order':'id.asc'}))
                for table in ('decision_runs','decision_cases','decision_approval_events')}
        before=business()
        path='/api/runs/'+assignment['id']+'/comparative'
        accepted=self.checked(self.s.api_client.post(path),202)
        self.assertEqual(self.checked(self.s.api_client.post(path),202)['id'],accepted['id'])
        self.s.stop(self.s.api);self.s.start_api()
        self.assertEqual(self.analysis(assignment['id'])['id'],accepted['id'])
        gate=self.s.storage/'block-downloads';gate.touch();self.s.start_worker()
        wait_for(lambda:self.analysis(assignment['id'])['status']=='running','comparative worker claim')
        first=self.checked(self.s.db.get('decision_comparative_analyses'))[0]
        self.s.stop(self.s.worker,kill=True)
        self.s.sql(f"UPDATE decision_comparative_analyses SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE id='{accepted['id']}';")
        gate.unlink();self.s.start_worker();artifact=self.complete_analysis(assignment['id'])
        self.assertEqual(artifact['attempts'],2);self.assertEqual(artifact['id'],accepted['id'])
        self.assertEqual(artifact['result_json']['scenarios']['selected'],assignment['result_json']['scenarios']['selected'])
        self.assertGreater(len(artifact['result_json']['scenarios']),len(assignment['result_json']['scenarios']))
        fenced=self.checked(self.s.db.post('rpc/finish_comparative_analysis',json={'target_analysis_id':accepted['id'],
            'worker_token':first['lease_token'],'terminal_values':{'status':'error','error_message':'old worker'}}))
        self.assertEqual(fenced,[]);self.assertEqual(business(),before)
        self.assertEqual(self.checked(self.s.api_client.post(path))['id'],artifact['id'])
        metrics=self.s.api_client.get('/metrics')
        self.assertIn('dation_comparative_queue_queued 0',metrics.text)

    def test_comparative_error_retry_and_existing_reference_reuse(self):
        case,orders,fleet=self.case();body=self.body(case,orders,fleet);body['configuration']['objective']='min_trips'
        self.s.start_worker();base=self.finish(self.admit(body));self.s.stop(self.s.worker)
        file=self.s.storage/orders['storage_bucket']/orders['storage_path'];original=file.read_bytes()
        file.write_bytes(original+b'\ncorrupted')
        path='/api/runs/'+base['id']+'/comparative';artifact=self.checked(self.s.api_client.post(path),202)
        self.s.start_worker();failed=self.complete_analysis(base['id'],'error')
        self.assertTrue(failed['error_message']);self.assertEqual(self.checked(self.s.api_client.post(path))['status'],'error')
        file.write_bytes(original)
        retry=self.checked(self.s.api_client.post(path,params={'retry':'true'}),202)
        self.assertEqual(retry['id'],artifact['id']);self.assertEqual(retry['generation'],2)
        self.complete_analysis(base['id'])
        balanced=self.finish(self.admit(self.body(case,orders,fleet)));self.s.stop(self.s.worker)
        reused=self.checked(self.s.api_client.post('/api/runs/'+balanced['id']+'/comparative'))
        self.assertEqual(reused['status'],'completed');self.assertEqual(reused['source_mode'],'existing')
        self.assertEqual(reused['result_json'],balanced['result_json']);self.assertEqual(reused['attempts'],0)
        self.assertEqual(len(self.checked(self.s.db.get('decision_runs'))),2)

    def test_browser_creation_execution_approval_navigation_and_mobile_history(self):
        self.browser_journey('desktop',{'width':1440,'height':1000})

    def test_browser_complete_workflow_at_mobile_width(self):
        self.browser_journey('mobile',{'width':390,'height':844})

    def browser_journey(self,scenario,viewport):
        self.s.start_worker()
        browser_python=os.getenv('DATION_BROWSER_PYTHON',str(ROOT/'.browser-venv/bin/python'))
        inputs=self.s.directory/'inputs';inputs.mkdir(exist_ok=True)
        for kind in ('orders','fleet'):(inputs/(kind+'.csv')).write_bytes(csv_input(kind))
        env={**self.s.env,'DATION_E2E_URL':self.s.api_url,'DATION_E2E_INPUTS':str(inputs),
             'DATION_E2E_VIEWPORT':json.dumps(viewport)}
        if artifacts:=os.getenv('DATION_E2E_ARTIFACTS'):
            env['DATION_E2E_ARTIFACTS']=str(Path(artifacts)/scenario)
        result=subprocess.run([browser_python,str(ROOT/'tests/e2e/browser_journey.py')],cwd=ROOT,
            env=env,
            text=True,capture_output=True,timeout=180)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout.strip().splitlines()[-1])
        self.assertTrue(report['passed']);self.assertEqual(report['javascript_errors'],[])
        self.assertTrue(report['creation_from_files']);self.assertTrue(report['refresh_during_queue'])
        self.assertTrue(report['inicio_to_overview']);self.assertTrue(report['approval_map_scheduling_configuration'])
        self.assertTrue(report['shared_workflow_visual_contract']);self.assertTrue(report['review_keyboard_cancel_and_confirmation'])
        self.assertEqual(report['ui']['viewport'],viewport)
        self.assertEqual(len(report['ui']['reviews']),2)
        self.assertEqual(len(report['ui']['toolbars']),2)
        self.assertGreaterEqual(len(report['ui']['checkpoints']),18)
        self.assertEqual(report['source_sha'],subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
        pending=next(row for row in report['ui']['checkpoints'] if row['name']=='assignment-pending')
        self.assertEqual(pending['view'],'decision-dashboard')
        rows=self.checked(self.s.db.get('decision_runs',params={'order':'created_at.asc'}))
        self.assertEqual(len(rows),3)
        self.assertEqual([r['node_id'] for r in rows],['logistics_assignment','logistics_scheduling','logistics_scheduling'])
        self.assertEqual([r['status'] for r in rows],['completed','error','completed'])
        self.assertTrue(rows[0]['approved_at'] and rows[2]['approved_at'])
        self.assertIsNone(rows[1]['approved_at']);self.assertIsNone(rows[1]['result_json'])
        self.assertTrue(rows[1]['error_message'])
        self.assertEqual(rows[1]['configuration_json']['planning_window_start'],'2026-09-01')
        self.assertEqual(rows[1]['configuration_json']['planning_window_end'],'2026-09-02')
        self.assertEqual({r['decision_case_id'] for r in rows},{rows[0]['decision_case_id']})
        self.assertEqual([r['upstream_run_id'] for r in rows[1:]],[rows[0]['id'],rows[0]['id']])
        self.assertEqual(len({r['id'] for r in rows}),3)
        case=self.checked(self.s.api_client.get('/api/decision-cases/'+rows[0]['decision_case_id']))['decision_case']
        self.assertEqual(case['nodes']['logistics_assignment']['approved_run_id'],rows[0]['id'])
        self.assertEqual(case['nodes']['logistics_scheduling']['approved_run_id'],rows[2]['id'])
        jobs=self.checked(self.s.db.get('dispatch_run_jobs',params={'order':'created_at.asc'}))
        self.assertEqual([row['state'] for row in jobs],['completed','error','completed'])
        self.assertEqual({row['run_id'] for row in jobs},{row['id'] for row in rows})
        events=self.checked(self.s.db.get('decision_approval_events'))
        self.assertEqual(len(events),2)


if __name__=='__main__':unittest.main(verbosity=2)
