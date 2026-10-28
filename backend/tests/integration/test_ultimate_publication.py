"""S8: checked RPCs, concurrent leases, atomic binding and current authority."""
import concurrent.futures,copy,json,sys,unittest
from pathlib import Path
from uuid import uuid4
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from ultimate_result_fixture import ResultSandbox
from ultimate_result_helpers import *
from ultimate_graph_state import install_run
from auth_fixture import USER_B,VIEWER
from app.engines.assignment.transport_contracts import TransportPlanInput
from app.engines.assignment.transport_policy_result import run_transport_policy
from app.results.assembler import assemble
from app.results.canonical import canonical_tree,result_fingerprint,canonical_bytes,content_sha256
from app.services.result_artifact_service import indexes

class UltimatePublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=ResultSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def setUp(self):self.cid=setup_case(self.s);self.rid=None
    def tearDown(self):
        self.s.sql("UPDATE dispatch_run_jobs SET state='error',lease_token=NULL,lease_expires_at=NULL WHERE state IN('queued','running'); UPDATE decision_runs SET status='error',error_message='S8 fixture end' WHERE status IN('queued','running');")
        self.s.sql(f"UPDATE workspace_members SET access_role='admin' WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_A}';")
    def rpc(self,op,args,actor=USER_A,wid=None):
        return self.s.db.post('rpc/platform_ultimate_execution',json={'target_workspace_id':wid or self.s.workspace_a,'actor_user_id':actor,'operation':op,'arguments':canonical_tree(args)})
    def admit(self):
        self.rid,self.body,response=submit(self.s,self.cid);ok(response);return self.rid
    def claim(self):
        return ok(self.s.db.post('rpc/claim_dispatch_job_v2',json={'worker_token':str(uuid4()),'lease_seconds':120}))[0]
    def bundle(self,job):
        request=TransportPlanInput.model_validate(job['request_json']['input']);return assemble(run_transport_policy(request),request.context)
    def prepare(self):
        self.admit();job=self.claim();bundle=self.bundle(job)
        lease={'run_id':self.rid,'worker_token':job['lease_token']}
        reserved=ok(self.rpc('prepare',{**lease,'package':bundle.package,'artifact_indexes':indexes(bundle)},actor=None))
        return job,bundle,lease,reserved
    def finish(self):
        job,bundle,lease,reserved=self.prepare()
        parts={str(p.reference.artifact_id):p.content for p in bundle.artifacts}
        for a in reserved['artifacts']:
            p=self.s.storage/a['storage_bucket']/a['storage_path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(parts[a['id']])
        args={**lease,'result_fingerprint':bundle.package.fingerprints.result_fingerprint,'verified_manifest_hash':content_sha256(canonical_bytes(bundle.package.artifact_manifest.artifacts))}
        ok(self.rpc('finish',args,actor=None));return job,bundle,args
    def test_01_empty_preparation_is_null_and_old_worker_cannot_claim_ultimate(self):
        self.admit();self.assertEqual(ok(self.s.db.post('rpc/claim_dispatch_job',json={'worker_token':str(uuid4()),'lease_seconds':120})),[])
        j=self.claim();self.assertIsNone(ok(self.rpc('prepared',{'run_id':self.rid,'worker_token':j['lease_token']},actor=None))['publication'])
    def test_02_sql_canonical_hashes_equal_t1_for_real_package_and_context(self):
        j,b,lease,reserved=self.prepare()
        self.assertEqual(self.s.sql(f"SELECT dation_private.t8_package_hash(package) FROM dation_private.ultimate_run_publications WHERE run_id='{self.rid}';"),b.package.fingerprints.result_fingerprint)
        self.assertEqual(self.s.sql(f"SELECT dation_private.t8_input_hash(configuration_json->'frozen_context') FROM decision_runs WHERE id='{self.rid}';"),row(self.s,self.rid)['input_context_hash'])
        self.assertEqual({a['publication_state'] for a in reserved['artifacts']},{'PREPARED'});self.assertEqual(row(self.s,self.rid)['status'],'running')
    def test_03_expired_lease_wrong_worker_and_late_worker_cannot_publish(self):
        j,b,lease,_=self.prepare();args={**lease,'result_fingerprint':b.package.fingerprints.result_fingerprint,'verified_manifest_hash':content_sha256(canonical_bytes(b.package.artifact_manifest.artifacts))}
        self.assertFalse(self.rpc('finish',{**args,'worker_token':str(uuid4())},actor=None).is_success)
        self.s.sql(f"UPDATE dispatch_run_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id='{self.rid}';")
        self.assertFalse(self.rpc('finish',args,actor=None).is_success);new=self.claim()
        self.assertFalse(self.rpc('prepare',{**lease,'package':b.package},actor=None).is_success)
        adopted=ok(self.rpc('prepare',{'run_id':self.rid,'worker_token':new['lease_token'],'package':b.package},actor=None))
        self.assertEqual(adopted['artifacts'][0]['producer_lease_token'],j['lease_token']);self.assertEqual(row(self.s,self.rid)['status'],'running')
    def test_04_claim_race_only_one_worker_owns_run(self):
        self.admit()
        def claim():
            with httpx.Client(base_url=self.s.db.base_url,headers=self.s.db.headers,trust_env=False,timeout=30) as db:return ok(db.post('rpc/claim_dispatch_job_v2',json={'worker_token':str(uuid4()),'lease_seconds':120}))
        with concurrent.futures.ThreadPoolExecutor(2) as p:results=list(p.map(lambda _:claim(),range(2)))
        self.assertEqual(sum(len(r) for r in results),1)
    def test_05_wrong_manifest_finish_rolls_back_all_terminal_fields(self):
        j,b,lease,_=self.prepare();before=row(self.s,self.rid)
        response=self.rpc('finish',{**lease,'result_fingerprint':b.package.fingerprints.result_fingerprint,'verified_manifest_hash':'a'*64},actor=None)
        self.assertFalse(response.is_success);self.assertEqual(row(self.s,self.rid),before)
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_result_artifacts WHERE run_id='{self.rid}' AND publication_state='READY';"),'0')
    def test_06_package_foreign_artifact_runtime_schema_and_context_rejected(self):
        self.admit();j=self.claim();b=self.bundle(j);base=canonical_tree(b.package);lease={'run_id':self.rid,'worker_token':j['lease_token']}
        for field in ['foreign','runtime','schema','context','missing-core']:
            v=copy.deepcopy(base)
            if field=='foreign':v['artifact_manifest']['artifacts'][0]['workspace_id']=self.s.workspace_b
            elif field=='runtime':v['engine']['engine_version']='9.0.0'
            elif field=='schema':v['result_schema_version']=2
            elif field=='context':v['context']['case_name']='wrong'
            else:v['artifact_manifest']['artifacts']=[a for a in v['artifact_manifest']['artifacts'] if a['kind']!='CORE']
            v['fingerprints']['result_fingerprint']=result_fingerprint(v)
            self.assertFalse(self.rpc('prepare',{**lease,'package':v},actor=None).is_success,field)
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_result_artifacts WHERE run_id='{self.rid}';"),'0')
    def test_07_owner_change_after_get_review_is_rechecked_at_post(self):
        _,b,args=self.finish();self.s.sql(f"UPDATE workspace_members SET access_role='operator' WHERE workspace_id='{self.s.workspace_a}' AND user_id='{USER_A}';")
        self.assertTrue(ok(endpoint(self.s,self.rid,'approval-review'))['approval_overlay']['approval_allowed'])
        self.s.sql(f"UPDATE decision_assignments SET owner_user_id=NULL WHERE workspace_id='{self.s.workspace_a}' AND decision_case_id='{self.cid}' AND node_id='{D1}';")
        self.assertEqual(approval(self.s,self.cid,self.rid).status_code,403);self.assertIsNone(row(self.s,self.rid)['approved_at'])
    def test_08_published_ready_bytes_and_actor_identity_are_immutable(self):
        _,b,args=self.finish();ok(approval(self.s,self.cid,self.rid));before=row(self.s,self.rid)
        with self.assertRaises(AssertionError):self.s.sql(f"UPDATE decision_result_artifacts SET content_sha256=repeat('a',64) WHERE run_id='{self.rid}';")
        with self.assertRaises(AssertionError):self.s.sql(f"DELETE FROM decision_result_artifacts WHERE run_id='{self.rid}';")
        with self.assertRaises(AssertionError):self.s.sql(f"UPDATE decision_runs SET result_json='{{}}' WHERE id='{self.rid}';")
        self.s.sql(f"UPDATE decision_assignments SET owner_user_id=NULL WHERE workspace_id='{self.s.workspace_a}' AND decision_case_id='{self.cid}' AND node_id='{D1}';")
        self.assertEqual(row(self.s,self.rid),before)
    def test_09_metadata_same_semantic_pack_version_preserve_d1_then_consumed_change_invalidates(self):
        _,b,args=self.finish();ok(approval(self.s,self.cid,self.rid));before=row(self.s,self.rid)
        # Re-publication with the same normalized contents is another Pack version,
        # but its D1 semantic read set is unchanged.
        publish(self.s,self.cid)
        current=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/data'))['version']['id'];self.assertNotEqual(current,before['data_pack_version_id'])
        after=row(self.s,self.rid);self.assertEqual(before,after);self.assertTrue(ok(endpoint(self.s,self.rid,'approval-review'))['approval_overlay']['approval_allowed'])
        context=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/context'))['case']
        ok(self.s.api_client.patch('/api/platform/decisions/'+self.cid,json={'expected_updated_at':context['updated_at'],'label':'Renamed display only'}))
        self.assertEqual(row(self.s,self.rid),before)
        publish(self.s,self.cid,change={'order_id':'ORD-SEMANTIC-CHANGE'})
        after=row(self.s,self.rid);self.assertIsNotNone(after['superseded_at']);self.assertEqual(after['result_json'],before['result_json']);self.assertEqual(after['approved_by_user_id'],before['approved_by_user_id'])
        self.assertEqual(self.s.sql(f"SELECT reason_code FROM decision_approval_events WHERE run_id='{self.rid}' AND action='superseded';"),'INPUT_READ_SET_CHANGED')
    def test_10_lineage_conceptual_d2_sources_and_new_d1_closure_preserve_history(self):
        _,b,args=self.finish();a=self.rid;ok(approval(self.s,self.cid,a))
        # T5 controlled D2 metadata ONLY. No Day Scheduling runtime or new output.
        child=install_run(self.s,self.s.api_client,self.cid,D2,approved=True)
        up_before=row(self.s,a);child_before=row(self.s,child)
        for _ in range(2):
            ctx=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/graph/config/'+D2));self.assertEqual(ctx['configuration_context']['upstream_run_id'],a)
        self.assertEqual(row(self.s,a),up_before);self.assertEqual(row(self.s,child),child_before)
        newer,body,response=submit(self.s,self.cid);ok(response)
        retired=row(self.s,child);self.assertEqual(retired['upstream_run_id'],a);self.assertEqual(retired['approved_at'],child_before['approved_at']);self.assertEqual(retired['approved_by_user_id'],child_before['approved_by_user_id']);self.assertIsNotNone(retired['superseded_at'])
        self.assertEqual(row(self.s,a)['approved_at'],up_before['approved_at'])
        self.assertEqual(self.s.sql(f"SELECT reason_code FROM decision_approval_events WHERE run_id='{child}' AND action='superseded';"),'UPSTREAM_INVALIDATED')
    def test_11_checked_functions_are_service_only_and_read_checks_membership(self):
        for role in ['anon','authenticated']:
            with self.assertRaises(AssertionError):self.s.sql(f"SET ROLE {role}; SELECT platform_ultimate_execution('{self.s.workspace_a}','{USER_A}','state','{{\"case_id\":\"{self.cid}\"}}');")
        self.assertEqual(self.rpc('state',{'case_id':self.cid},actor=USER_B).status_code,403)
        self.assertEqual(self.rpc('admit',{'case_id':self.cid,'run_id':str(uuid4())},actor=VIEWER).status_code,403)
    def test_12_d2_only_enrichment_metadata_does_not_invalidate_nonconsumer_d1(self):
        _,b,args=self.finish();ok(approval(self.s,self.cid,self.rid));before=row(self.s,self.rid)
        # T2 supports this future slot; its producer belongs to T9. This controlled
        # SQL metadata fixture tests read-set semantics without inventing a D2 engine.
        pv=str(uuid4());wid=self.s.workspace_a;cid=self.cid
        self.s.sql(f"""BEGIN;
        INSERT INTO case_data_pack_versions(id,workspace_id,case_id,pack_id,version,manifest_hash,contract_set_hash,created_by)
        SELECT '{pv}',v.workspace_id,v.case_id,v.pack_id,v.version+1,repeat('f',64),v.contract_set_hash,v.created_by FROM case_data_pack_versions v JOIN case_data_packs p ON p.current_version_id=v.id WHERE p.case_id='{cid}';
        INSERT INTO case_data_pack_entries SELECT '{pv}',e.slot_key,e.workspace_id,e.case_id,e.dataset_id,e.contract_id,e.contract_hash,e.raw_sha256,e.canonical_sha256,e.normalizer_version,e.normalized_bucket,e.normalized_path,e.record_count FROM case_data_pack_entries e JOIN case_data_packs p ON p.current_version_id=e.pack_version_id WHERE p.case_id='{cid}';
        INSERT INTO case_data_pack_entries SELECT '{pv}','scheduling_enrichment',e.workspace_id,e.case_id,e.dataset_id,e.contract_id,e.contract_hash,e.raw_sha256,e.canonical_sha256,e.normalizer_version,e.normalized_bucket,e.normalized_path,e.record_count FROM case_data_pack_entries e WHERE e.pack_version_id='{pv}' AND slot_key='transport_demand';
        UPDATE case_data_packs SET current_version_id='{pv}',revision=revision+1 WHERE workspace_id='{wid}' AND case_id='{cid}'; COMMIT;""")
        self.assertEqual(row(self.s,self.rid),before);self.assertTrue(ok(endpoint(self.s,self.rid,'approval-review'))['approval_overlay']['approval_allowed'])
    def test_13_service_role_cannot_admit_unbound_storage_model_or_readset(self):
        self.admit();j=self.claim();original=row(self.s,self.rid)
        for kind in ['path','model','readset']:
            rid=str(uuid4());input_=copy.deepcopy(j['request_json']['input']);input_['run_id']=rid
            entries=copy.deepcopy(j['request_json']['entries']);snapshot=copy.deepcopy(original['configuration_json']['ultimate_graph'])
            if kind=='path':entries[0]['normalized_path']='https://attacker.invalid/private'
            elif kind=='model':input_['model']['allowed_sources']=['EXTERNAL']
            else:snapshot['read_set'].pop('transport_demand')
            response=self.rpc('admit',{'case_id':self.cid,'run_id':rid,'client_request':self.body,'input':input_,'entries':entries,'graph_snapshot':snapshot,'dataset_id':original['dataset_id']})
            self.assertFalse(response.is_success,kind)
            self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE id='{rid}';"),'0')
        self.assertEqual(row(self.s,self.rid),original)

if __name__=='__main__':unittest.main()
