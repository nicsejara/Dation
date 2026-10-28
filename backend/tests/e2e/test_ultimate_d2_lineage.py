"""E9: real D1→D2 API/SQL/worker and immutable upstream lineage."""
import concurrent.futures,json,os,re,sys,time,unittest
from pathlib import Path
from uuid import uuid4
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ultimate_day_fixture import DaySandbox
from ultimate_result_helpers import *
from auth_fixture import USER_B,VIEWER
from app.results.canonical import result_fingerprint

def day_intention(s,cid):
    context=ok(s.api_client.get('/api/platform/logistics-cases/'+cid+'/run-context',params={'node_id':D2}))
    return {'request_schema':'ultimate_run_request_v1','workflow_version':2,'case_id':cid,'node_id':D2,
        **{k:context[k] for k in ['expected_context_hash','model_version_id','data_pack_version_id','node_policy','source_transport_plan']}}
def day_submit(s,cid,body=None,rid=None):
    body=body or day_intention(s,cid);rid=rid or str(uuid4())
    return rid,body,s.api_client.post('/api/runs',params={'run_id':rid},json=body)
def day_approve(s,cid,rid,client=None):return (client or s.api_client).post('/api/runs/'+rid+'/approve',json={'case_id':cid,'node_id':D2,'expected_result_fingerprint':row(s,rid)['result_fingerprint']})

class UltimateDayLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=DaySandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def setUp(self):
        self.addCleanup(self.cleanup)
        self.cid=setup_case(self.s);self.s.start_worker();self.parent,_,response=submit(self.s,self.cid);ok(response);wait_run(self.s,self.parent);ok(approval(self.s,self.cid,self.parent));self.up=row(self.s,self.parent)
    def cleanup(self):
        self.s.stop(self.s.worker,kill=True)
        evidence=os.getenv('DATION_E2E_ARTIFACTS')
        if evidence:
            dest=Path(evidence)/self._testMethodName;dest.mkdir(parents=True,exist_ok=True)
            for p in [*(Path(f.name) for f in self.s.logs),self.s.storage/'t8-rpc-errors.jsonl']:
                if p.exists():(dest/p.name).write_text(re.sub(r'(?im)^.*(?:authorization:|apikey:|cookie:).*$', '[fixture auth redacted]',p.read_text()))
        for marker in self.s.storage.glob('*t8*'):marker.unlink()
    def child(self,approve=False):
        rid,body,response=day_submit(self.s,self.cid);ok(response);r=wait_run(self.s,rid)
        if approve:ok(day_approve(self.s,self.cid,rid))
        return rid,body,r
    def until(self,predicate):
        end=time.monotonic()+25
        while time.monotonic()<end:
            if predicate():return
            time.sleep(.08)
        self.fail('Controlled worker boundary timeout')
    def test_01_d2_publication_all_consumers_and_review_use_exact_source(self):
        before=row(self.s,self.parent);rid,body,r=self.child();p=r['result_json'];fp=r['result_fingerprint']
        self.assertEqual(p['result_schema'],'day_scheduling_v1');self.assertEqual(result_fingerprint(p),fp);self.assertEqual(p['source_transport_plan'],{'run_id':self.parent,'result_fingerprint':self.up['result_fingerprint']})
        self.assertEqual(row(self.s,self.parent),before);self.assertEqual(r['upstream_run_id'],self.parent)
        light=ok(endpoint(self.s,rid));self.assertEqual(light['provenance']['result_fingerprint'],fp)
        for dataset in ['schedule','trips','resources','service','exceptions','evidence']:
            data=ok(endpoint(self.s,rid,'details/'+dataset));self.assertEqual(data['provenance']['result_fingerprint'],fp)
        review=ok(endpoint(self.s,rid,'approval-review'));self.assertTrue(review['approval_overlay']['approval_allowed'],review);self.assertEqual(review['approval_review']['scheduled_ratio'],p['metrics']['scheduled_trips']['ratio'])
        ok(day_approve(self.s,self.cid,rid));self.assertEqual(row(self.s,self.parent),before)
        graph=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/graph'))['graph']['nodes']
        self.assertEqual([n['node_state'] for n in graph],['APPROVED','APPROVED']);self.assertTrue(graph[1]['runtime_available'])
        # SQL-owned T1 hash projection equals the real producer's Core identity.
        self.assertEqual(self.s.sql(f"SELECT dation_private.t9_core_hash(request_json#>'{{input,source_core}}') FROM dispatch_run_jobs WHERE run_id='{rid}';"),self.up['core_fingerprint'])
    def test_02_A_B_stay_on_D1_A_then_C_uses_approved_D1_B(self):
        a,body_a,ra=self.child(approve=True);a_approved=row(self.s,a)
        b,body_b,rb=self.child(approve=True);self.assertEqual(row(self.s,self.parent),self.up)
        self.assertEqual(row(self.s,a)['source_transport_plan'] if 'source_transport_plan' in row(self.s,a) else row(self.s,a)['upstream_run_id'],self.parent)
        newer,_,response=submit(self.s,self.cid);ok(response);wait_run(self.s,newer)
        # Latest completed is insufficient. A real human approval is required.
        self.assertEqual(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/run-context',params={'node_id':D2}).status_code,409)
        ok(approval(self.s,self.cid,newer));c,_,rc=self.child(approve=True)
        self.assertEqual(rc['upstream_run_id'],newer);self.assertEqual(rc['result_json']['source_transport_plan']['result_fingerprint'],row(self.s,newer)['result_fingerprint'])
        for rid,original in [(a,ra),(b,rb)]:
            current=row(self.s,rid);self.assertEqual(current['upstream_run_id'],self.parent);self.assertEqual(current['result_json'],original['result_json']);self.assertIsNotNone(current['superseded_at']);ok(endpoint(self.s,rid))
        self.assertEqual(row(self.s,a)['approved_at'],a_approved['approved_at']);self.assertEqual(row(self.s,a)['approved_by_user_id'],a_approved['approved_by_user_id'])
        retired=row(self.s,a);events=self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE case_id='{self.cid}';")
        self.assertEqual(day_submit(self.s,self.cid,body_a,rid=a)[2].status_code,202);self.assertEqual(row(self.s,a),retired);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE case_id='{self.cid}';"),events)
    def test_03_wrong_source_fingerprint_case_or_pending_D1_cannot_be_admitted(self):
        body=day_intention(self.s,self.cid)
        for binding in [{'run_id':self.parent,'result_fingerprint':'a'*64},{'run_id':str(uuid4()),'result_fingerprint':self.up['result_fingerprint']}]:
            response=day_submit(self.s,self.cid,{**body,'source_transport_plan':binding})[2];self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{self.cid}' AND node_id='{D2}';"),'0')
    def test_04_two_concurrent_submits_one_D2_intention_preserve_D1(self):
        rid=str(uuid4());body=day_intention(self.s,self.cid)
        def send():
            with httpx.Client(base_url=self.s.api_url,headers=self.s.api_client.headers,trust_env=False,timeout=30) as a:return a.post('/api/runs',params={'run_id':rid},json=body)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:responses=list(pool.map(lambda _:send(),range(2)))
        for response in responses:self.assertEqual(response.status_code,202,response.text)
        wait_run(self.s,rid);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{self.cid}' AND node_id='{D2}';"),'1');self.assertEqual(row(self.s,self.parent),self.up)
    def test_05_lease_recovery_and_finish_response_loss_use_T8_protocol(self):
        marker=self.s.storage/'block-t8-finish';marker.touch();rid,_,response=day_submit(self.s,self.cid);ok(response)
        self.until(lambda:self.s.sql(f"SELECT count(*)>0 FROM decision_result_artifacts WHERE run_id='{rid}';")=='t')
        self.s.stop(self.s.worker,kill=True);self.s.sql(f"UPDATE dispatch_run_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{rid}';");marker.unlink()
        (self.s.storage/'lose-t8-finish-response').touch();self.s.start_worker();r=wait_run(self.s,rid)
        self.assertEqual(r['result_json']['source_transport_plan']['run_id'],self.parent);self.assertEqual(row(self.s,self.parent),self.up)
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_result_artifacts WHERE run_id='{rid}' AND publication_state<>'READY';"),'0')
    def test_06_upstream_replaced_during_D2_execution_keeps_history_and_denies_approval(self):
        marker=self.s.storage/'block-t8-finish';marker.touch();rid,_,response=day_submit(self.s,self.cid);ok(response)
        self.until(lambda:self.s.sql(f"SELECT count(*)>0 FROM decision_result_artifacts WHERE run_id='{rid}';")=='t')
        newer,_,response=submit(self.s,self.cid);ok(response);marker.unlink();r=wait_run(self.s,rid);wait_run(self.s,newer)
        self.assertEqual(r['result_json']['source_transport_plan']['run_id'],self.parent);self.assertIsNotNone(r['superseded_at']);self.assertEqual(day_approve(self.s,self.cid,rid).status_code,403)
    def test_07_tenant_viewer_and_expected_result_fingerprint_boundaries(self):
        rid,_,r=self.child();self.assertEqual(endpoint(self.s,rid,fingerprint='a'*64).status_code,409)
        for uid,status in [(USER_B,[403,404]),(VIEWER,[403])]:
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[uid]},trust_env=False,timeout=30) as a:
                self.assertIn(day_approve(self.s,self.cid,rid,client=a).status_code,status)
    def test_08_service_role_cannot_forge_source_allocations_availability_or_certificate(self):
        import copy
        rid,body,published=self.child();job=json.loads(self.s.sql(f"SELECT request_json FROM dispatch_run_jobs WHERE run_id='{rid}';"))
        for kind in ['allocation','resource','certificate']:
            new=str(uuid4());input_=copy.deepcopy(job['input']);input_['run_id']=new
            if kind=='allocation':input_['source_core']['transport_plan']['trips'][0]['orders'][0]['allocation_fraction']='0.5'
            elif kind=='resource':input_['resources'][0]['units_available']=999
            else:input_['source_temporal_certified']=False
            response=self.s.db.post('rpc/platform_ultimate_execution',json={'target_workspace_id':self.s.workspace_a,'actor_user_id':USER_A,'operation':'admit','arguments':{
                'run_id':new,'case_id':self.cid,'client_request':body,'input':input_,'entries':job['entries'],'dataset_id':published['dataset_id'],'graph_snapshot':published['configuration_json']['ultimate_graph']}})
            self.assertFalse(response.is_success,kind);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE id='{new}';"),'0')
        self.assertEqual(row(self.s,self.parent),self.up)

if __name__=='__main__':unittest.main()
