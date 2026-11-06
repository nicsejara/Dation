"""Real SQL/REST/API/Storage and finite processes; no resident worker or GCP."""
import concurrent.futures
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Lock, Thread
import unittest
from uuid import uuid4

from ultimate_day_fixture import DaySandbox
from ultimate_result_helpers import setup_case,submit,intention,ok,row,approval
from test_ultimate_d2_lineage import day_submit,day_approve
from auth_fixture import USER_A,USER_B,VIEWER
from sandbox import ROOT,wait_for


class FakeJobs:
    def __init__(self):
        self.pending=[];self.lock=Lock();self.drop=False;self.reject=False
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.reply(200,{'ready':True})
            def reply(self,status,body):
                data=json.dumps(body).encode();self.send_response(status)
                self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data)
            def do_POST(self):
                value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if owner.reject:self.reply(503,{});return
                with owner.lock:owner.pending.append(value)
                # Persisted provider admission followed by a lost response.
                if owner.drop:self.connection.shutdown(2);self.connection.close();return
                self.reply(200,{'name':'local/operations/'+str(uuid4())})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def take(self):
        with self.lock:return self.pending.pop(0) if self.pending else None


class JobsSandbox(DaySandbox):
    def start_api(self):
        self.fake=FakeJobs()
        self.env.update(DATION_EXECUTION_MODE='jobs',DATION_TEST_RUNTIME='1',DATION_DISPATCH_FAKE_URL=self.fake.url)
        self.sql("SELECT execution_runtime('configure','{\"enabled\":true,\"admissions_open\":true}'); SELECT execution_runtime('recover');")
        return super().start_api()
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:
            if hasattr(self,'fake'):self.fake.close()
    def rpc(self,operation,arguments=None,**authority):
        r=self.db.post('rpc/execution_runtime',json={'operation':operation,'arguments':arguments or {},**authority})
        assert r.is_success,(r.status_code,r.text)
        return r.json()
    def finite(self,delivery=None,recover=False,container=False):
        args=['--recover'] if recover else ['--intent-id',delivery['intent_id'],'--delivery-token',delivery['delivery_token']]
        command=[sys.executable,'event_worker.py',*args]
        if container:
            values={k:self.env[k] for k in ['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_INPUT_BUCKET','NO_PROXY','DATION_EXECUTION_MODE','DATION_TEST_RUNTIME','DATION_DISPATCH_FAKE_URL']}
            envfile=self.directory/'finite-local.env';envfile.write_text('\n'.join(k+'='+v for k,v in values.items())+'\n');envfile.chmod(0o600)
            name=self.identifier+'-finite-'+uuid4().hex[:8];self.containers.append(name)
            command=['docker','run','--name',name,'--rm','--network','host','--memory','1g','--memory-swap','1g','--cpus','1','--pids-limit','128',
                '--read-only','--tmpfs','/tmp','--env-file',str(envfile),'--label','dation.qa.phase=S02',
                '--entrypoint','python',os.getenv('DATION_S02_IMAGE','dation-ci-compatibility:test'),'event_worker.py',*args]
        result=subprocess.run(command,cwd=ROOT,env=self.env,
            capture_output=True,text=True,timeout=90 if container else 45)
        if result.returncode:raise AssertionError('Finite worker exit '+str(result.returncode)+'\n'+result.stdout[-1800:]+result.stderr[-1800:])
        return result
    def drain(self):
        for _ in range(20):
            delivery=self.fake.take()
            if delivery is None:return
            self.finite(delivery)
        raise AssertionError('Unexpected activation cycle')


class ZeroIdleRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=JobsSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def setUp(self):
        self.s.fake.drop=False;self.s.fake.reject=False
        self.s.rpc('configure',{'enabled':True,'admissions_open':True,'workspace_daily_limit':50})
        self.s.rpc('recover');self.s.drain()
    def test_01_D1_approval_D2_approval_and_case_without_resident_process(self):
        s=self.s;cid=setup_case(s);rid,_,r=submit(s,cid);self.assertEqual(r.status_code,202,r.text)
        s.drain();d1=row(s,rid);self.assertEqual(d1['status'],'completed');ok(approval(s,cid,rid));s.drain()
        approved=row(s,rid);child,_,response=day_submit(s,cid);ok(response);s.drain()
        self.assertEqual(row(s,child)['status'],'completed');self.assertEqual(row(s,child)['upstream_run_id'],rid)
        self.assertEqual(row(s,rid),approved);ok(day_approve(s,cid,child));s.drain()
        nodes=ok(s.api_client.get('/api/platform/logistics-cases/'+cid+'/graph'))['graph']['nodes']
        self.assertEqual([n['node_state'] for n in nodes],['APPROVED','APPROVED'])
        self.assertIsNone(s.worker)
        self.assertEqual(s.sql("SELECT count(*) FROM dation_private.execution_outbox WHERE state NOT IN('done','dead');"),'0')
    def test_02_provider_ack_loss_duplicate_and_paused_replay(self):
        s=self.s;cid=setup_case(s);s.fake.drop=True
        rid,body,r=submit(s,cid);self.assertEqual(r.status_code,202,r.text)
        delivery=s.fake.take();self.assertIsNotNone(delivery);s.fake.drop=False
        s.rpc('configure',{'admissions_open':False})
        self.assertEqual(submit(s,cid,rid,body)[2].status_code,202)
        s.finite(delivery);before=row(s,rid);self.assertEqual(before['status'],'completed')
        s.finite(delivery);self.assertEqual(row(s,rid),before);s.drain()
        self.assertEqual(s.sql(f"SELECT attempts FROM dispatch_run_jobs WHERE run_id='{rid}';"),'1')
    def test_03_lost_wakeup_recovery_and_stale_epoch(self):
        s=self.s;cid=setup_case(s);s.fake.reject=True;rid,_,r=submit(s,cid);ok(r)
        original=json.loads(s.sql(f"SELECT to_jsonb(o) FROM dation_private.execution_outbox o WHERE run_id='{rid}';"))
        self.assertEqual(original['last_error'],'provider_unavailable');s.fake.reject=False
        s.sql(f"UPDATE dation_private.execution_outbox SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}';")
        s.finite(recover=True)
        delivery=s.fake.take();self.assertNotEqual(delivery['delivery_token'],original['delivery_token'])
        stale={'intent_id':original['id'],'delivery_token':original['delivery_token']}
        self.assertEqual(s.rpc('claim',stale)['outcome'],'stale');self.assertFalse(s.rpc('ack',stale))
        s.finite(delivery);s.drain();self.assertEqual(row(s,rid)['status'],'completed')
    def test_04_atomic_quota_rejection_rolls_back_run_and_outbox(self):
        s=self.s;cid=setup_case(s);body=intention(s,cid)
        seed,_,accepted=submit(s,cid);ok(accepted);s.drain()
        s.rpc('configure',{'workspace_daily_limit':1})
        rid=str(uuid4());response=submit(s,cid,rid,body)[2]
        self.assertEqual(response.status_code,429,response.text)
        self.assertEqual(s.sql(f"SELECT count(*) FROM decision_runs WHERE id='{rid}';"),'0')
        self.assertEqual(s.sql(f"SELECT count(*) FROM dation_private.execution_outbox WHERE run_id='{rid}';"),'0')
    def test_05_access_control_and_zero_workers_readiness_read_only(self):
        s=self.s;before=s.sql('SELECT md5(row_to_json(p)::text) FROM dation_private.execution_dispatch_policy p;')
        snapshot=s.rpc('snapshot',target_workspace_id=s.workspace_a,actor_user_id=USER_A)
        self.assertEqual(snapshot['pending'],0)
        self.assertEqual(s.api_client.get('/ready').status_code,200)
        operations=ok(s.api_client.get('/api/system/operations'))
        self.assertEqual(operations['workers']['healthy'],0);self.assertTrue(operations['ready'])
        self.assertNotIn('worker_unavailable',operations['alerts'])
        for operation,uid,workspace in [('configure',USER_A,s.workspace_a),('reserve',VIEWER,s.workspace_a),('snapshot',USER_B,s.workspace_a)]:
            response=s.db.post('rpc/execution_runtime',json={'operation':operation,'target_workspace_id':workspace,'actor_user_id':uid})
            self.assertEqual(response.status_code,403,response.text)
        self.assertEqual(s.sql('SELECT md5(row_to_json(p)::text) FROM dation_private.execution_dispatch_policy p;'),before)
        self.assertEqual(s.sql("SELECT has_function_privilege('anon','public.execution_runtime(text,jsonb,uuid,uuid)','execute') OR has_function_privilege('authenticated','public.execution_runtime(text,jsonb,uuid,uuid)','execute');"),'f')
    def test_06_exhausted_delivery_terminates_accepted_intention(self):
        s=self.s;cid=setup_case(s);s.fake.reject=True;rid,_,r=submit(s,cid);ok(r)
        s.sql(f"UPDATE dation_private.execution_outbox SET delivery_attempts=3,lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}';")
        s.fake.reject=False;s.finite(recover=True);s.drain()
        self.assertEqual(row(s,rid)['status'],'error')
    def test_08_real_solver_in_bounded_readonly_container_exits(self):
        s=self.s;cid=setup_case(s);rid,_,response=submit(s,cid);ok(response)
        result=s.finite(s.fake.take(),container=True);s.drain()
        self.assertEqual(row(s,rid)['status'],'completed')
        events=[json.loads(line) for line in result.stderr.splitlines() if line.startswith('{')]
        completed=[e for e in events if e.get('event')=='finite_execution_exit']
        self.assertEqual(len(completed),1);self.assertEqual(completed[0]['child_exit'],0)
        peak=completed[0]['child_peak_rss_kib']+completed[0]['parent_peak_rss_kib']
        self.assertLess(peak,1024*1024)

    def test_07_idle_recovery_exits_and_duplicate_claim_is_busy(self):
        s=self.s;s.finite(recover=True);self.assertIsNone(s.fake.take())
        cid=setup_case(s);rid,_,r=submit(s,cid);ok(r);delivery=s.fake.take()
        identity={k:delivery[k] for k in ('intent_id','delivery_token')}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            claims=list(pool.map(lambda _:s.rpc('claim',identity),range(2)))
        self.assertCountEqual([c['outcome'] for c in claims],['claimed','busy'])
        # Cancellation is authoritative and delayed delivery cannot resurrect it.
        ok(s.api_client.post('/api/runs/'+rid+'/cancel'));s.finite(delivery);s.drain()
        self.assertEqual(row(s,rid)['status'],'error')

    def test_09_comparative_analysis_preserves_base_without_resident_worker(self):
        from fixtures import csv_input
        from workflow_fixture import prepare_stage
        s=self.s;a=s.api_client
        inputs={kind:ok(a.post('/api/datasets/upload',params={'dataset_type':kind},data={'is_sample':'true'},
            files={'file':(kind+'.csv',csv_input(kind),'text/csv')}))['dataset'] for kind in ['orders','fleet']}
        cid=str(uuid4());ok(a.post('/api/decision-cases',json={'id':cid,'orders_dataset_id':inputs['orders']['id'],'fleet_dataset_id':inputs['fleet']['id']}))
        prepare_stage(a,cid,'logistics_assignment',uid=USER_A)
        rid=str(uuid4());body={'orders_dataset_id':inputs['orders']['id'],'fleet_dataset_id':inputs['fleet']['id'],
            'decision_case':{'case_id':cid,'node_id':'logistics_assignment'},'configuration':{'objective':'min_trips'},
            'options':{'total_time_limit_s':20,'solve_time_limit_s':3,'deterministic_limit':.05,'analysis_depth':'essential'}}
        ok(a.post('/api/runs',params={'run_id':rid},json=body));s.drain();before=row(s,rid)
        self.assertEqual(before['status'],'completed')
        result=ok(a.post('/api/runs/'+rid+'/comparative'));s.drain()
        completed=ok(a.get('/api/runs/'+rid+'/comparative'))
        self.assertEqual(completed['id'],result['id']);self.assertEqual(completed['status'],'completed')
        self.assertEqual(row(s,rid),before)
        self.assertEqual(completed['result_json']['scenarios']['selected'],before['result_json']['scenarios']['selected'])

    def test_10_crash_after_claim_recovers_with_new_fence_and_one_terminal_result(self):
        s=self.s;cid=setup_case(s);rid,_,r=submit(s,cid);ok(r);old=s.fake.take()
        identity={k:old[k] for k in ('intent_id','delivery_token')};claim=s.rpc('claim',identity)
        self.assertEqual(claim['outcome'],'claimed')
        s.sql(f"UPDATE dispatch_run_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}'; UPDATE dation_private.execution_outbox SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}';")
        s.finite(recover=True);self.assertEqual(s.rpc('claim',identity)['outcome'],'stale');s.drain()
        terminal=row(s,rid);self.assertEqual(terminal['status'],'completed')
        s.finite(old);self.assertEqual(row(s,rid),terminal)
        self.assertEqual(s.sql(f"SELECT attempts FROM dispatch_run_jobs WHERE run_id='{rid}';"),'2')

    def test_11_SIGTERM_reaps_solver_and_durable_work_recovers(self):
        s=self.s;cid=setup_case(s);marker=s.storage/'block-t8-upload';marker.touch()
        self.addCleanup(lambda:marker.unlink(missing_ok=True))
        rid,_,r=submit(s,cid);ok(r);delivery=s.fake.take()
        process=s.start_process('finite-termination',['event_worker.py','--intent-id',delivery['intent_id'],'--delivery-token',delivery['delivery_token']])
        wait_for(lambda:int(s.sql(f"SELECT count(*) FROM decision_result_artifacts WHERE run_id='{rid}';"))>0,'durable prepare before termination')
        logfile=Path(s.logs[-1].name)
        self.assertIsNone(process.poll(),logfile.read_text()[-3000:])
        s.stop(process);self.assertEqual(process.returncode,75)
        exits=[json.loads(line) for line in logfile.read_text().splitlines() if line.startswith('{') and json.loads(line).get('event')=='finite_execution_exit']
        self.assertEqual(len(exits),1);self.assertLess(exits[0]['child_exit'],0)
        marker.unlink()
        s.sql(f"UPDATE dispatch_run_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}'; UPDATE dation_private.execution_outbox SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}';")
        s.finite(recover=True);s.drain();self.assertEqual(row(s,rid)['status'],'completed')

    def test_12_reconciliation_epoch_and_source_timestamp_prevent_ABA_ack(self):
        s=self.s;cid=setup_case(s)
        s.sql(f"SELECT dation_private.request_case_reconciliation('{cid}');")
        original=s.rpc('reserve',{'kind':'reconciliation','entity_id':cid})[0]
        identity={'intent_id':original['id'],'delivery_token':original['delivery_token']}
        claim=s.rpc('claim',identity);self.assertEqual(claim['outcome'],'claimed');old=claim['job']
        s.sql(f"DELETE FROM decision_case_reconciliations WHERE case_id='{cid}'; SELECT dation_private.request_case_reconciliation('{cid}');")
        source=json.loads(s.sql(f"SELECT to_jsonb(r) FROM decision_case_reconciliations r WHERE case_id='{cid}';"))
        self.assertEqual(source['version'],1)
        self.assertFalse(s.rpc('ack_case',{**identity,'source_version':old['version'],'source_updated_at':old['updated_at']}))
        renewed=s.rpc('reserve',{'kind':'reconciliation','entity_id':cid})[0]
        new_identity={'intent_id':renewed['id'],'delivery_token':renewed['delivery_token']}
        self.assertGreater(renewed['generation'],original['generation']);s.rpc('claim',new_identity)
        self.assertFalse(s.rpc('ack_case',{**new_identity,'source_version':1,'source_updated_at':old['updated_at']}))
        self.assertTrue(s.rpc('ack_case',{**new_identity,'source_version':1,'source_updated_at':source['updated_at']}))
        self.assertTrue(s.rpc('ack',new_identity))

    def test_13_global_capacity_limits_distinct_compute_and_hands_off_backlog(self):
        s=self.s;cid=setup_case(s);body=intention(s,cid)
        ids=[]
        for _ in range(3):
            rid,_,response=submit(s,cid,body=body);ok(response);ids.append(rid)
        self.assertEqual(s.sql("SELECT count(*) FROM dation_private.execution_outbox WHERE kind<>'reconciliation' AND state IN('dispatching','submitted','running') AND lease_expires_at>clock_timestamp();"),'2')
        self.assertEqual(s.rpc('reserve',{'kind':'dispatch','limit':3}),[])
        s.drain()
        for rid in ids:self.assertEqual(row(s,rid)['status'],'completed')
        self.assertEqual(s.sql("SELECT count(*) FROM dation_private.execution_outbox WHERE kind<>'reconciliation' AND state IN('dispatching','submitted','running');"),'0')
