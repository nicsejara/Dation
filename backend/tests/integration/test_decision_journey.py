"""UX04 real local SQL/API/Storage: isolation, recovery, CAS and lifecycle."""
import sys,json,unittest
from pathlib import Path
from uuid import uuid4
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from journey_fixture import JourneySandbox
from auth_fixture import USER_A,USER_B,VIEWER
from tests.test_ultimate_data_contracts import model
from app.domain.logistics.data_contracts import compile_contract,template_csv
from ultimate_graph_state import install_run

class DecisionJourneyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=JourneySandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def ok(self,r):self.assertTrue(r.is_success,r.text);return r.json()
    def setUp(self):
        self.a=self.s.api_client
        self.m=self.ok(self.a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'UX04 Model','configuration':model()['config_jsonb']}))
        self.v=self.ok(self.a.post('/api/platform/logistics-models/'+self.m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))['version']
        self.pid=str(uuid4());self.base='/api/platform/data-preparations/'+self.pid
        self.prep=self.ok(self.a.post('/api/platform/data-preparations',json={'id':self.pid,'model_version_id':self.v['id']}))
    def tearDown(self):
        # Preserve FINALIZING for test assertions, then expire only synthetic sessions between independent scenarios.
        self.s.sql("UPDATE dation_private.journey_preparations SET status='EXPIRED' WHERE status IN('DRAFT','VALIDATED','FINALIZING');")
        ids=json.loads(self.s.sql("SELECT coalesce(jsonb_agg(id),'[]') FROM dation_private.journey_preparations WHERE created_by='"+USER_A+"';"))
        for pid in ids:self.ok(self.a.post('/api/platform/data-preparations/'+pid+'/cleanup'))
    def read(self):return self.ok(self.a.get(self.base))
    def raw(self,e='transport_demand'):return template_csv(compile_contract(self.v,e))
    def upload(self,e='transport_demand',raw=None,uid=None,revision=None):
        d=self.read();return self.a.post(self.base+'/uploads/'+e,params={'upload_id':uid or str(uuid4()),'expected_revision':revision or d['session']['revision'],'contract_hash':d['contracts'][e]['contract_hash']},files={'file':('op.csv',raw or self.raw(e),'text/csv')})
    def body(self):return {'expected_revision':self.read()['session']['revision'],'case':{'id':str(uuid4()),'name':'UX04 Case','logistics_model_version_id':self.v['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}}
    def finish(self,body=None):return self.a.post(self.base+'/finalize',json=body or self.body())
    def test_01_private_stage_no_case_and_exact_contracts(self):
        before=self.s.sql('SELECT count(*) FROM decision_cases;');self.ok(self.upload());self.ok(self.upload('transport_resources'));d=self.read()
        self.assertEqual(d['session']['status'],'VALIDATED');self.assertEqual(before,self.s.sql('SELECT count(*) FROM decision_cases;'));self.assertEqual(len(d['uploads']),2);self.assertNotIn('storage_path',json.dumps(d));self.assertTrue(all(u['report']['rows']==5 for u in d['uploads']))
    def test_02_bad_csv_never_stored_wrong_hash_and_extra_fields(self):
        r=self.upload(raw=b'wrong\nPII-NOT-STORED\n');self.assertEqual(r.status_code,422);self.assertEqual(self.read()['uploads'],[])
        self.assertEqual(self.a.post(self.base+'/finalize',json={**self.body(),'storage_path':'forged'}).status_code,422)
        self.assertEqual(self.a.get(self.base).status_code,200)
    def test_03_cross_workspace_actor_viewer_and_sql_denied(self):
        for uid,code in [(USER_B,404),(VIEWER,404)]:
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[uid]},trust_env=False) as other:self.assertEqual(other.get(self.base).status_code,code)
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:self.assertEqual(viewer.post('/api/platform/data-preparations',json={'id':str(uuid4()),'model_version_id':self.v['id']}).status_code,403)
        for role in ['anon','authenticated','service_role']:
            with self.assertRaises(AssertionError):self.s.sql('SET ROLE '+role+'; SELECT * FROM dation_private.journey_preparations;')
        for role in ['anon','authenticated']:
            with self.assertRaises(AssertionError):self.s.sql(f"SET ROLE {role}; SELECT platform_decision_journey('{self.s.workspace_a}','{USER_A}','get','{{}}');")
    def test_04_finalize_two_files_one_case_pack_and_owner(self):
        self.ok(self.upload());self.ok(self.upload('transport_resources'));d=self.read();self.ok(self.a.put(self.base+'/owner',json={'expected_revision':d['session']['revision'],'data_owner_user_id':USER_A}));b=self.body();result=self.ok(self.finish(b));cid=result['context']['case']['id']
        self.assertEqual(cid,b['case']['id']);self.assertEqual(result['context']['entry_count'],2);self.assertEqual(result['context']['responsibilities']['stages']['data_owner']['owner']['id'],USER_A);self.assertEqual(result['preparation']['session']['status'],'CONSUMED')
        again=self.ok(self.finish(b));self.assertEqual(again['context']['pack_version']['id'],result['context']['pack_version']['id']);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{cid}';"),'0')
    def test_05_empty_case_graph_requires_data(self):
        d=self.ok(self.finish());self.assertEqual(d['context']['entry_count'],0);self.assertEqual(d['graph']['nodes'][0]['node_state'],'DATA_REQUIRED')
    def test_06_publish_fault_recovers_same_case_and_publication(self):
        self.ok(self.upload());b=self.body();(self.s.storage/'fail-t4-publish').touch();r=self.finish(b);self.assertEqual(r.status_code,503,r.text)
        self.assertEqual(self.read()['session']['status'],'FINALIZING');self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_cases WHERE id='{b['case']['id']}';"),'1')
        d=self.ok(self.finish(b));again=self.ok(self.finish(b));self.assertEqual(d['context']['pack_version']['id'],again['context']['pack_version']['id']);self.assertEqual(self.s.sql(f"SELECT count(*) FROM case_data_pack_versions WHERE case_id='{b['case']['id']}';"),'2')
    def test_07_lost_publication_response_reconciles_and_changed_intent_denied(self):
        self.ok(self.upload());b=self.body();(self.s.storage/'lose-t4-publish-response').touch();self.assertEqual(self.finish(b).status_code,503);self.ok(self.finish(b));b['case']['name']='Changed';self.assertEqual(self.finish(b).status_code,409)
    def test_08_expired_session_and_consumed_cleanup_only(self):
        self.ok(self.upload());self.assertEqual(self.a.post(self.base+'/cleanup').status_code,409);d=self.ok(self.finish());self.assertEqual(self.ok(self.a.post(self.base+'/cleanup'))['removed_uploads'],1)
        self.assertEqual(self.ok(self.a.get('/api/platform/logistics-cases/'+d['context']['case']['id']+'/data'))['entries'][0]['record_count'],5)
    def test_09_stale_revision_and_upload_identity_cannot_mix(self):
        uid=str(uuid4());self.ok(self.upload(uid=uid));self.assertEqual(self.upload('transport_resources',revision=1).status_code,409)
        self.assertEqual(self.upload(uid=uid,raw=self.raw().replace(b'ORD-001',b'ORD-999')).status_code,409)
    def test_10_derivative_is_new_identity_lineage_no_approval_copy(self):
        original=self.ok(self.finish())['context']['case']['id'];other=str(uuid4());b={'id':other,'model_version_id':self.v['id'],'parent_case_id':original};self.ok(self.a.post('/api/platform/data-preparations',json=b));self.pid=other;self.base='/api/platform/data-preparations/'+other;d=self.ok(self.finish());new=d['context']['case']['id']
        self.assertNotEqual(original,new);self.assertEqual(self.s.sql(f"SELECT parent_case_id FROM dation_private.journey_case_events WHERE case_id='{new}';"),original);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{new}';"),'0')
    def test_11_close_blocks_incomplete_and_distinguishes_archive(self):
        d=self.ok(self.finish());cid=d['context']['case']['id'];base='/api/platform/logistics-cases/'+cid;state=self.ok(self.a.get(base+'/journey'));self.assertFalse(state['can_close']);self.assertEqual(self.a.post(base+'/close',json={'token':state['token']}).status_code,409);self.assertEqual(self.ok(self.a.get(base+'/context'))['case']['status'],'active')
    def test_12_closed_graph_uses_current_approvals_and_audit(self):
        self.ok(self.upload());self.ok(self.upload('transport_resources'));d=self.ok(self.finish());cid=d['context']['case']['id'];base='/api/platform/logistics-cases/'+cid
        install_run(self.s,self.a,cid,approved=True,trip_count=0);state=self.ok(self.a.get(base+'/journey'));self.assertTrue(state['can_close'],state);self.ok(self.a.post(base+'/close',json={'token':state['token']}));self.assertEqual(self.ok(self.a.get(base+'/context'))['case']['status'],'archived');self.assertIsNotNone(self.ok(self.a.get(base+'/journey'))['lifecycle']['closed_at']);self.assertEqual(self.s.sql(f"SELECT count(*) FROM audit_events WHERE decision_case_id='{cid}' AND event_type='decision_case.closed';"),'1')

    def test_13_missing_private_bytes_prevents_case_creation(self):
        self.ok(self.upload());u=self.read()['uploads'][0];raw=self.s.storage/'dda-inputs'/self.s.workspace_a/'preparations'/self.pid/u['id']/'input.csv';raw.unlink();b=self.body();self.assertEqual(self.finish(b).status_code,503);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_cases WHERE id='{b['case']['id']}';"),'0');self.assertEqual(self.read()['session']['status'],'DRAFT')
    def test_14_concurrent_finalize_has_one_case_and_one_publication(self):
        from concurrent.futures import ThreadPoolExecutor
        self.ok(self.upload());self.ok(self.upload('transport_resources'));b=self.body()
        def post(_):
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_A]},trust_env=False,timeout=30) as c:return c.post(self.base+'/finalize',json=b)
        with ThreadPoolExecutor(2) as pool:rs=list(pool.map(post,range(2)))
        for r in rs:self.ok(r)
        cid=b['case']['id'];self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_cases WHERE id='{cid}';"),'1');self.assertEqual(self.s.sql(f"SELECT count(*) FROM case_data_pack_versions WHERE case_id='{cid}';"),'2')
    def test_15_expiration_and_session_limit_are_server_authority(self):
        for _ in range(4):self.ok(self.a.post('/api/platform/data-preparations',json={'id':str(uuid4()),'model_version_id':self.v['id']}))
        self.assertEqual(self.a.post('/api/platform/data-preparations',json={'id':str(uuid4()),'model_version_id':self.v['id']}).status_code,409)
        self.s.sql(f"UPDATE dation_private.journey_preparations SET expires_at=now()-interval '1 second' WHERE id='{self.pid}';");self.assertEqual(self.a.post(self.base+'/finalize',json={'expected_revision':1,'case':{'id':str(uuid4()),'name':'Expired','logistics_model_version_id':self.v['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}}).status_code,409)
    def test_16_rollout_flag_closed_read_only_runtime_contract(self):
        self.s.sql('UPDATE dation_private.platform_release SET unified_journey_enabled=false;')
        try:self.assertFalse(self.ok(self.a.get('/api/platform/ultimate-foundation/capabilities'))['unified_journey_enabled']);self.assertEqual(self.a.get(self.base).status_code,404)
        finally:self.s.sql('UPDATE dation_private.platform_release SET unified_journey_enabled=true;')
    def test_17_owner_eligibility_is_rechecked_at_finalize(self):
        self.assertEqual(self.a.put(self.base+'/owner',json={'expected_revision':1,'data_owner_user_id':VIEWER}).status_code,403)
        self.ok(self.a.put(self.base+'/owner',json={'expected_revision':1,'data_owner_user_id':USER_A}));self.s.sql(f"DELETE FROM dation_private.member_responsibilities WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_A}';")
        try:self.assertEqual(self.finish().status_code,403)
        finally:self.s.sql(f"INSERT INTO dation_private.member_responsibilities SELECT '{self.s.workspace_a}','{USER_A}',x FROM unnest(ARRAY['data_steward','decision_owner','approver']) x ON CONFLICT DO NOTHING;")
    def test_18_guided_publication_rechecks_run_admitted_race(self):
        self.ok(self.upload());self.ok(self.upload('transport_resources'));d=self.ok(self.finish());cid=d['context']['case']['id'];base='/api/platform/logistics-cases/'+cid
        rid=install_run(self.s,self.a,cid,status='queued');self.s.sql(f"UPDATE decision_runs SET status='error',error_message='Synthetic failure' WHERE id='{rid}';");state=self.ok(self.a.get(base+'/data'));old=state['pack']['revision'];body={'publication_id':str(uuid4()),'expected_revision':old,'selection':[{'slot_key':'transport_demand','dataset_id':state['entries'][0]['dataset_id']}]}
        # Select the actual demand identity regardless of manifest order.
        body['selection'][0]['dataset_id']=next(e['dataset_id'] for e in state['entries'] if e['slot_key']=='transport_demand')
        self.assertEqual(self.a.post(base+'/journey/publish',json=body).status_code,409);self.assertEqual(self.ok(self.a.get(base+'/data'))['pack']['revision'],old)
        self.ok(self.a.post(base+'/data/publish',json=body)) # historical Pack API keeps its version/STAlE compatibility.
    def test_19_close_two_approvals_concurrency_and_pending_work(self):
        self.ok(self.upload());self.ok(self.upload('transport_resources'));d=self.ok(self.finish());cid=d['context']['case']['id'];base='/api/platform/logistics-cases/'+cid
        install_run(self.s,self.a,cid,approved=True);install_run(self.s,self.a,cid,'logistics_scheduling',approved=True);state=self.ok(self.a.get(base+'/journey'));self.assertTrue(state['can_close']);
        row=self.ok(self.a.get(base+'/context'))['case'];self.ok(self.a.patch(base+'/context',json={'expected_updated_at':row['updated_at'],'name':'Cambió antes del cierre'}));self.assertEqual(self.a.post(base+'/close',json={'token':state['token']}).status_code,409)
        state=self.ok(self.a.get(base+'/journey'));self.ok(self.a.post(base+'/close',json={'token':state['token']}));self.ok(self.a.post(base+'/close',json={'token':state['token']}));self.assertEqual(self.s.sql(f"SELECT count(*) FROM audit_events WHERE decision_case_id='{cid}' AND event_type='decision_case.closed';"),'1')
    def test_20_interrupted_stage_upload_recovers_same_identity(self):
        uid=str(uuid4());(self.s.storage/'fail-t4-normalized').touch();self.assertEqual(self.upload(uid=uid).status_code,503);self.assertFalse(self.read()['uploads'][0]['ready']);self.ok(self.a.post(self.base+'/uploads/'+uid+'/recover'));self.assertTrue(self.read()['uploads'][0]['ready']);self.assertEqual(len(self.read()['uploads']),1)
