"""E8: real API + SQL + standalone worker, private Storage contract fixture."""
import concurrent.futures,json,sys,time,unittest
from pathlib import Path
from uuid import uuid4
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ultimate_result_fixture import ResultSandbox
from ultimate_result_helpers import *
from auth_fixture import USER_B,VIEWER
from app.results.canonical import result_fingerprint,canonical_bytes

class UltimateResultE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=ResultSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def setUp(self):self.cid=setup_case(self.s)
    def tearDown(self):
        self.s.stop(self.s.worker,kill=True)
        import os,re
        evidence=os.getenv('DATION_E2E_ARTIFACTS')
        if evidence:
            directory=Path(evidence)/self._testMethodName;directory.mkdir(parents=True,exist_ok=True)
            for p in [*(Path(f.name) for f in self.s.logs),self.s.storage/'t8-rpc-errors.jsonl']:
                if p.exists():
                    text=re.sub(r'(?im)^.*(?:authorization:|apikey:|cookie:).*$', '[fixture auth headers redacted]',p.read_text())
                    (directory/p.name).write_text(text)
        for p in self.s.storage.glob('*t8*'):p.unlink()
    def start(self):self.s.start_worker()
    def submit(self,body=None):
        rid,body,r=submit(self.s,self.cid,body=body);ok(r);return rid,body
    def completed(self):
        rid,_=self.submit();self.start();return rid,wait_run(self.s,rid)
    def until(self,predicate):
        end=time.monotonic()+25
        while time.monotonic()<end:
            if predicate():return
            time.sleep(.08)
        self.fail('Timed out waiting for controlled crash boundary')
    def files(self,rid):return list((self.s.storage/'dda-inputs'/self.s.workspace_a/'runs'/rid).rglob('*.json'))
    def test_01_complete_publication_retrieval_review_human_approval(self):
        rid,r=self.completed();fp=r['result_fingerprint'];self.assertEqual(result_fingerprint(r['result_json']),fp)
        light=ok(endpoint(self.s,rid));self.assertEqual(light['provenance']['result_fingerprint'],fp)
        self.assertIn('INTEGRITY_CHECK_REQUIRED',light['approval_overlay']['approval_blockers'])
        details=ok(endpoint(self.s,rid,'details/demand'));self.assertEqual(details['total'],1)
        evidence=ok(endpoint(self.s,rid,'details/evidence'));e=evidence['rows'][0]
        entity=ok(endpoint(self.s,rid,'entities/'+e['entity_type']+'/'+e['entity_id']));self.assertEqual(entity['entity'],e)
        aid=r['result_json']['artifact_manifest']['artifacts'][0]['artifact_id'];ok(endpoint(self.s,rid,'artifacts/'+aid))
        review=ok(endpoint(self.s,rid,'approval-review'));self.assertTrue(review['approval_overlay']['approval_allowed'],review)
        approved=ok(approval(self.s,self.cid,rid));self.assertEqual(approved['result_fingerprint'],fp)
        self.assertEqual(ok(approval(self.s,self.cid,rid)),approved)
        graph=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/graph'))['graph']['nodes']
        self.assertEqual(graph[0]['node_state'],'APPROVED');self.assertEqual(graph[1]['node_state'],'READY');self.assertFalse(graph[1]['runtime_available'])
        self.assertEqual(row(self.s,rid)['result_json'],r['result_json'])
    def test_02_duplicate_concurrent_submit_and_intention_conflict(self):
        body=intention(self.s,self.cid);rid=str(uuid4())
        def send():
            with httpx.Client(base_url=self.s.api_url,headers=self.s.api_client.headers,trust_env=False,timeout=30) as a:return a.post('/api/runs',params={'run_id':rid},json=body)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:responses=list(pool.map(lambda _:send(),range(2)))
        for r in responses:self.assertEqual(r.status_code,202,r.text)
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{self.cid}';"),'1')
        changed={**body,'expected_context_hash':'a'*64};self.assertEqual(self.s.api_client.post('/api/runs',params={'run_id':rid},json=changed).status_code,409)
        self.start();wait_run(self.s,rid)
    def test_03_crash_before_upload_and_after_upload_reclaim_immutable_prepared(self):
        for boundary in ['upload','finish']:
            with self.subTest(boundary=boundary):
                if boundary=='finish':self.cid=setup_case(self.s)
                marker=self.s.storage/('block-t8-'+boundary);marker.touch();rid,_=self.submit();self.start()
                self.until(lambda:self.s.sql(f"SELECT count(*)>0 FROM decision_result_artifacts WHERE run_id='{rid}';")=='t')
                if boundary=='finish':self.until(lambda:len(self.files(rid))==int(self.s.sql(f"SELECT count(*) FROM decision_result_artifacts WHERE run_id='{rid}';")))
                self.assertNotEqual(row(self.s,rid)['status'],'completed')
                prepared=self.s.sql(f"SELECT jsonb_agg(to_jsonb(a) ORDER BY id) FROM decision_result_artifacts a WHERE run_id='{rid}';")
                self.s.stop(self.s.worker,kill=True)
                self.s.sql(f"UPDATE dispatch_run_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}';")
                marker.unlink()
                self.start();r=wait_run(self.s,rid);self.assertIsNotNone(r['result_fingerprint'])
                final=json.loads(self.s.sql(f"SELECT jsonb_agg(to_jsonb(a) ORDER BY id) FROM decision_result_artifacts a WHERE run_id='{rid}';"))
                for before,after in zip(json.loads(prepared),final):
                    for k in before:
                        if k not in ['publication_state','result_fingerprint']:self.assertEqual(after[k],before[k],k)
                self.s.stop(self.s.worker,kill=True)
    def test_04_partial_upload_and_lost_prepare_response_recover(self):
        for fault in ['fail-t8-after-first-upload','lose-t8-prepare-response']:
            with self.subTest(fault=fault):
                if fault.startswith('lose'):self.cid=setup_case(self.s)
                (self.s.storage/fault).touch();rid,_=self.submit();self.start()
                self.until(lambda:not (self.s.storage/fault).exists())
                self.until(lambda:self.s.sql(f"SELECT count(*)>0 FROM decision_result_artifacts WHERE run_id='{rid}';")=='t')
                # Wait for the failing RPC/upload to finish before reclaiming.
                time.sleep(.3);self.s.stop(self.s.worker,kill=True)
                self.s.sql(f"UPDATE dispatch_run_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}';")
                self.start();r=wait_run(self.s,rid,timeout=40)
                self.assertEqual(len(self.files(rid)),len(r['result_json']['artifact_manifest']['artifacts']))
                self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_result_artifacts WHERE run_id='{rid}' AND publication_state<>'READY';"),'0')
                self.s.stop(self.s.worker,kill=True)
    def test_05_lost_finish_response_and_duplicate_finish(self):
        (self.s.storage/'lose-t8-finish-response').touch();rid,r=self.completed()
        response=self.s.db.post('rpc/platform_ultimate_execution',json={'target_workspace_id':self.s.workspace_a,'actor_user_id':None,'operation':'finish','arguments':{'run_id':rid,'worker_token':str(uuid4()),'result_fingerprint':r['result_fingerprint'],'verified_manifest_hash':r['artifact_manifest_hash']}})
        self.assertTrue(ok(response)['replayed']);self.assertEqual(row(self.s,rid)['result_json'],r['result_json'])
    def test_06_corrupt_missing_wrong_fingerprint_and_foreign_access_fail_closed(self):
        rid,r=self.completed();self.assertEqual(endpoint(self.s,rid,fingerprint='a'*64).status_code,409)
        self.assertEqual(approval(self.s,self.cid,rid,fp='a'*64).status_code,409)
        self.assertEqual(approval(self.s,str(uuid4()),rid).status_code,409)
        self.assertEqual(endpoint(self.s,rid,'artifacts/'+str(uuid4())).status_code,404)
        other_case=setup_case(self.s);other,_,response=submit(self.s,other_case);ok(response);foreign=wait_run(self.s,other)['result_json']['artifact_manifest']['artifacts'][0]['artifact_id']
        self.assertEqual(endpoint(self.s,rid,'artifacts/'+foreign).status_code,404)
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as b:
            self.assertIn(b.get('/api/runs/'+rid+'/result',params={'expected_result_fingerprint':r['result_fingerprint']}).status_code,[403,404])
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as v:self.assertEqual(approval(self.s,self.cid,rid,client=v).status_code,403)
        p=self.files(rid)[0];blob=p.read_bytes();p.write_bytes(b'{}')
        self.assertEqual(endpoint(self.s,rid,'approval-review').status_code,409);self.assertEqual(approval(self.s,self.cid,rid).status_code,409)
        p.unlink();self.assertEqual(endpoint(self.s,rid,'approval-review').status_code,409)
        p.write_bytes(blob);self.assertTrue(ok(endpoint(self.s,rid,'approval-review'))['approval_overlay']['approval_allowed'])
    def test_07_pack_changes_while_running_publish_frozen_history_deny_approval(self):
        marker=self.s.storage/'block-t8-finish';marker.touch();rid,body=self.submit();self.start()
        self.until(lambda:self.s.sql(f"SELECT count(*)>0 FROM decision_result_artifacts WHERE run_id='{rid}';")=='t')
        publish(self.s,self.cid,change={'order_id':'ORD-CHANGED'})
        marker.unlink();r=wait_run(self.s,rid)
        self.assertEqual(r['data_pack_version_id'],body['data_pack_version_id']);self.assertIsNotNone(r['superseded_at'])
        self.assertFalse(ok(endpoint(self.s,rid,'approval-review'))['approval_overlay']['approval_allowed'])
        self.assertEqual(approval(self.s,self.cid,rid).status_code,403)
    def test_08_old_intention_after_new_run_preserves_history_and_actor(self):
        rid,body=self.submit();self.start();original=wait_run(self.s,rid);ok(approval(self.s,self.cid,rid));before=row(self.s,rid)
        # Opening configuration is pure, as is abandoning it.
        intention(self.s,self.cid);intention(self.s,self.cid);self.assertIsNone(row(self.s,rid)['superseded_at'])
        newer,_=self.submit();wait_run(self.s,newer)
        retired=row(self.s,rid);self.assertEqual(retired['approved_by_user_id'],before['approved_by_user_id']);self.assertEqual(retired['approved_at'],before['approved_at']);self.assertEqual(retired['result_json'],original['result_json'])
        count=self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE case_id='{self.cid}';")
        response=self.s.api_client.post('/api/runs',params={'run_id':rid},json=body);self.assertEqual(response.status_code,202,response.text)
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE case_id='{self.cid}';"),count)
        self.assertEqual(row(self.s,rid),retired);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{self.cid}';"),'2')

if __name__=='__main__':unittest.main()
