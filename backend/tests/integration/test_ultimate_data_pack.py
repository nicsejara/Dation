"""S4: real checked SQL/API/Storage-contract publication, faults and isolation."""
from concurrent.futures import ThreadPoolExecutor
import csv,io,json
from pathlib import Path
import sys,unittest
from uuid import uuid4
import httpx

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from ultimate_data_fixture import DataPackSandbox
from auth_fixture import USER_A,USER_B,VIEWER,DISABLED
from tests.test_ultimate_data_contracts import model as domain_model


class UltimateDataPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=DataPackSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def ok(self,r):self.assertTrue(r.is_success,r.text);return r.json()
    def setUp(self):
        self.a=self.s.api_client;self.m=self.ok(self.a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'S4 operación','configuration':domain_model()['config_jsonb']}))
        self.v=self.ok(self.a.post('/api/platform/logistics-models/'+self.m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))
        self.c=self.new_case();self.cid=self.c['case']['id'];self.base='/api/platform/logistics-cases/'+self.cid+'/data'
    def new_case(self,version=None):return self.ok(self.a.post('/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'S4 sin CSV','logistics_model_version_id':version or self.v['version']['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}))
    def state(self):return self.ok(self.a.get(self.base))
    def template(self,entity='transport_demand'):return self.a.get(self.base+'/templates/'+entity).content
    def upload_response(self,entity='transport_demand',body=None,uid=None):
        uid=uid or str(uuid4());contract=self.state()['contracts'][entity];body=body if body is not None else self.template(entity)
        return uid,self.a.post(self.base+'/uploads/'+entity,params={'upload_id':uid,'contract_hash':contract['contract_hash']},files={'file':('operacion.csv',body,'text/csv')})
    def upload(self,entity='transport_demand',body=None):return self.ok(self.upload_response(entity,body)[1])
    def publication(self,selection,revision=None,pid=None):return {'publication_id':pid or str(uuid4()),'expected_revision':revision or self.state()['pack']['revision'],'selection':selection}
    def publish(self,j):return self.ok(self.a.post(self.base+'/publish',json=self.publication([{'slot_key':j['entity'],'upload_id':j['id']}])))
    def sql(self,text):return self.s.sql(text)
    def marker(self,name):(self.s.storage/name).touch()
    def raw_path(self,j):return self.s.storage/'dda-inputs'/self.sql(f"SELECT workspace_id::text||'/'||reserved_dataset_id::text||'/input.csv' FROM dation_private.ultimate_input_uploads WHERE id='{j}';")
    def test_01_empty_case_contracts_and_flag_keep_execution_closed(self):
        state=self.state();self.assertEqual(state['entries'],[]);self.assertEqual(state['version']['version'],1);self.assertEqual(state['inputs_available'],{'transport_demand':False,'transport_resources':False});self.assertIsNone(state['decision_readiness']);self.assertFalse(state['runtime_execution_available'])
    def test_02_template_validate_and_snapshot_identity_agree(self):
        for entity in ['transport_demand','transport_resources']:
            contract=self.state()['contracts'][entity];raw=self.template(entity);response=self.a.post(self.base+'/validate/'+entity,params={'contract_hash':contract['contract_hash']},files={'file':('input.csv',raw,'text/csv')});report=self.ok(response);self.assertTrue(report['valid']);self.assertEqual(report['rows'],5);self.assertEqual(report['contract_hash'],contract['contract_hash'])
        self.assertEqual(self.state()['pack']['revision'],1)
    def test_03_upload_is_candidate_not_published_and_reloads(self):
        before=self.state();j=self.upload();after=self.state();self.assertEqual(after['pack'],before['pack']);self.assertEqual(after['entries'],[]);self.assertEqual(j['status'],'READY');self.assertEqual(after['uploads'][0]['id'],j['id']);self.assertNotIn('storage_path',j)
    def test_04_demand_publish_is_immutable_complete_manifest(self):
        j=self.upload();result=self.publish(j);state=self.state();self.assertEqual(result['version']['version'],2);self.assertEqual(state['version']['id'],result['version']['id']);self.assertEqual([e['slot_key'] for e in state['entries']],['transport_demand'])
        old=self.ok(self.a.get(self.base+'/versions/'+self.c['planning_context']['data_pack_version_id']));self.assertEqual(old['entries'],[])
    def test_05_resources_publication_carries_demand_forward(self):
        d=self.upload();first=self.publish(d);r=self.upload('transport_resources');second=self.publish(r);state=self.state();self.assertEqual(second['version']['version'],3);self.assertEqual(len(state['entries']),2)
        historic=self.ok(self.a.get(self.base+'/versions/'+first['version']['id']));self.assertEqual(len(historic['entries']),1);self.assertEqual(historic['entries'][0]['dataset_id'],d['dataset_id']);self.assertEqual(next(e for e in state['entries'] if e['slot_key']=='transport_demand')['dataset_id'],d['dataset_id'])
        self.assertEqual([x['slot_key'] for x in second['publication']['changes']],['transport_resources'])
    def test_06_storage_yes_database_no_recovers_without_pointer_move(self):
        self.marker('fail-t4-store');uid,response=self.upload_response();self.assertEqual(response.status_code,503);self.assertTrue(self.raw_path(uid).exists());self.assertEqual(self.state()['pack']['revision'],1)
        recovered=self.ok(self.a.post(self.base+'/uploads/'+uid+'/recover'));self.assertEqual(recovered['status'],'READY');self.assertEqual(self.state()['pack']['revision'],1);self.publish(recovered)
    def test_07_metadata_commit_lost_response_recovers_same_dataset(self):
        self.marker('lose-t4-store-response');uid,response=self.upload_response();self.assertEqual(response.status_code,503);count=self.sql(f"SELECT count(*) FROM datasets WHERE id=(SELECT dataset_id FROM dation_private.ultimate_input_uploads WHERE id='{uid}');");self.assertEqual(count,'1')
        a=self.ok(self.a.post(self.base+'/uploads/'+uid+'/recover'));b=self.ok(self.a.post(self.base+'/uploads/'+uid+'/recover'));self.assertEqual(a['dataset_id'],b['dataset_id']);self.assertEqual(self.state()['pack']['revision'],1)
    def test_08_publish_commit_lost_response_replays_exact_version(self):
        j=self.upload();body=self.publication([{'slot_key':j['entity'],'upload_id':j['id']}]);self.marker('lose-t4-publish-response');r=self.a.post(self.base+'/publish',json=body);self.assertEqual(r.status_code,503)
        after=self.state();reply=self.ok(self.a.post(self.base+'/publish',json=body));self.assertTrue(reply['replayed']);self.assertEqual(reply['version']['id'],after['version']['id']);self.assertEqual(self.state()['history_total'],2)
    def test_09_interrupted_raw_can_retry_same_upload_identity(self):
        self.marker('fail-t4-raw');raw=self.template();uid,response=self.upload_response(body=raw);self.assertEqual(response.status_code,503);self.assertEqual(self.a.post(self.base+'/uploads/'+uid+'/recover').status_code,409)
        same,result=self.upload_response(body=raw,uid=uid);self.assertEqual(self.ok(result)['id'],uid);self.assertEqual(self.state()['pack']['revision'],1)
    def test_10_interrupted_normalized_object_recovers_from_raw(self):
        self.marker('fail-t4-normalized');uid,response=self.upload_response();self.assertEqual(response.status_code,503);self.assertTrue(self.raw_path(uid).exists());recovered=self.ok(self.a.post(self.base+'/uploads/'+uid+'/recover'));self.assertEqual(recovered['status'],'READY');self.publish(recovered)
    def test_11_cas_conflict_preserves_candidate_and_current(self):
        a=self.upload();b=self.upload('transport_resources');old=self.publication([{'slot_key':b['entity'],'upload_id':b['id']}],revision=1);self.publish(a);before=self.state();self.assertEqual(self.a.post(self.base+'/publish',json=old).status_code,409);after=self.state();self.assertEqual(after['pack'],before['pack']);self.assertTrue(any(j['id']==b['id'] and j['status']=='READY' for j in after['uploads']))
    def test_12_same_raw_and_contract_deduplicate_without_replacing_bytes(self):
        a=self.upload();raw=self.raw_path(a['id']).read_bytes();b=self.upload();self.assertEqual(a['dataset_id'],b['dataset_id']);self.assertEqual(self.raw_path(a['id']).read_bytes(),raw);self.assertFalse(self.raw_path(b['id']).exists());self.assertEqual(self.state()['pack']['revision'],1)
    def test_13_reuse_same_version_across_cases_is_explicit(self):
        j=self.upload();other=self.new_case();base='/api/platform/logistics-cases/'+other['case']['id']+'/data';items=self.ok(self.a.get(base+'/reuse/transport_demand'))['items'];self.assertIn(j['dataset_id'],[x['id'] for x in items])
        body={'publication_id':str(uuid4()),'expected_revision':1,'selection':[{'slot_key':'transport_demand','dataset_id':j['dataset_id']}]};self.ok(self.a.post(base+'/publish',json=body));self.assertEqual(self.state()['entries'],[])
    def test_14_same_raw_different_contract_is_a_distinct_logical_dataset(self):
        first=self.upload();config=domain_model(operating_role='HYBRID')['config_jsonb'];m=self.ok(self.a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'Otra interpretación','configuration':config}));v=self.ok(self.a.post('/api/platform/logistics-models/'+m['model']['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}));other=self.new_case(v['version']['id']);base='/api/platform/logistics-cases/'+other['case']['id']+'/data';state=self.ok(self.a.get(base));raw=self.template()
        second=self.ok(self.a.post(base+'/uploads/transport_demand',params={'upload_id':str(uuid4()),'contract_hash':state['contracts']['transport_demand']['contract_hash']},files={'file':('operacion.csv',raw,'text/csv')}));self.assertEqual(first['raw_sha256'],second['raw_sha256']);self.assertNotEqual(first['dataset_id'],second['dataset_id']);self.assertNotEqual(first['contract_hash'],second['contract_hash'])
        bad={'publication_id':str(uuid4()),'expected_revision':1,'selection':[{'slot_key':'transport_demand','dataset_id':first['dataset_id']}]};self.assertEqual(self.a.post(base+'/publish',json=bad).status_code,409)
    def test_15_cross_workspace_case_dataset_and_storage_are_denied(self):
        j=self.upload();self.publish(j)
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as b:
            self.assertEqual(b.get(self.base).status_code,404);self.assertEqual(b.get('/api/platform/data/datasets/'+j['dataset_id']+'/preview').status_code,404)
            self.assertEqual(b.post(self.base+'/uploads/'+j['id']+'/recover').status_code,404)
        self.assertEqual(self.s.http.get(self.s.env['SUPABASE_URL']+'/storage/v1/object/dda-inputs/'+str(self.raw_path(j['id']).relative_to(self.s.storage/'dda-inputs'))).status_code,401)
    def test_16_viewer_reads_but_cannot_upload_or_publish(self):
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False) as viewer:
            self.assertFalse(self.ok(viewer.get(self.base))['can_edit']);raw=self.template();hash_=self.state()['contracts']['transport_demand']['contract_hash']
            r=viewer.post(self.base+'/uploads/transport_demand',params={'upload_id':str(uuid4()),'contract_hash':hash_},files={'file':('input.csv',raw,'text/csv')});self.assertEqual(r.status_code,403)
            self.assertEqual(viewer.post(self.base+'/publish',json=self.publication([{'slot_key':'transport_demand','dataset_id':str(uuid4())}])).status_code,403)
        self.assertEqual(self.state()['entries'],[])
    def test_17_default_closed_flag_and_read_only_rollback(self):
        j=self.upload();self.publish(j);before=self.state();self.sql('UPDATE dation_private.platform_release SET ultimate_data_pack_enabled=false;')
        try:
            self.assertFalse(self.state()['can_edit']);self.assertEqual(self.state()['entries'],before['entries']);self.assertEqual(self.upload_response()[1].status_code,404)
        finally:self.sql('UPDATE dation_private.platform_release SET ultimate_data_pack_enabled=true;')
    def test_18_version_metadata_and_objects_are_immutable(self):
        j=self.upload();v=self.publish(j)['version']['id']
        for sql in [f"UPDATE case_data_pack_versions SET manifest_hash='{'b'*64}' WHERE id='{v}';",f"UPDATE case_data_pack_entries SET record_count=1 WHERE pack_version_id='{v}';",f"DELETE FROM dation_private.ultimate_input_objects WHERE dataset_id='{j['dataset_id']}';"]:
            with self.assertRaises(AssertionError):self.sql(sql)
        path=str(self.raw_path(j['id']).relative_to(self.s.storage));r=self.s.http.post(self.s.env['SUPABASE_URL']+'/storage/v1/object/'+path,headers={'Authorization':'Bearer '+self.s.token,'apikey':self.s.token,'Content-Type':'text/csv','x-upsert':'false'},content=b'replacement');self.assertEqual(r.status_code,409)
    def test_19_referenced_input_cannot_be_deleted_by_legacy_hub(self):
        j=self.upload();self.publish(j);self.ok(self.a.post('/api/platform/data/datasets/'+j['dataset_id']+'/archive'));self.assertEqual(self.a.delete('/api/platform/data/datasets/'+j['dataset_id']).status_code,409);self.assertTrue(self.raw_path(j['id']).exists())
    def test_20_no_pointer_to_missing_or_wrong_bytes(self):
        j=self.upload();path=self.raw_path(j['id']);raw=path.read_bytes();path.write_bytes(b'corrupted')
        try:self.assertEqual(self.a.post(self.base+'/publish',json=self.publication([{'slot_key':j['entity'],'upload_id':j['id']}])).status_code,409);self.assertEqual(self.state()['pack']['revision'],1)
        finally:path.write_bytes(raw)
        self.publish(j)
    def test_21_schema_extra_pii_never_enters_journal_or_storage(self):
        raw=self.template().decode().splitlines();raw[0]+=',customer_name'
        for i in range(1,len(raw)):raw[i]+=',PRIVATE-DO-NOT-STORE'
        before=self.sql(f"SELECT count(*) FROM dation_private.ultimate_input_uploads WHERE case_id='{self.cid}';");_,r=self.upload_response(body=('\n'.join(raw)+'\n').encode());self.assertEqual(r.status_code,422);self.assertNotIn('PRIVATE-DO-NOT-STORE',r.text);self.assertEqual(before,self.sql(f"SELECT count(*) FROM dation_private.ultimate_input_uploads WHERE case_id='{self.cid}';"))
    def test_22_client_paths_and_contract_forgery_are_rejected(self):
        body=self.publication([{'slot_key':'transport_demand','dataset_id':str(uuid4())}]);body['storage_path']='another-tenant/object';self.assertEqual(self.a.post(self.base+'/publish',json=body).status_code,422)
        self.assertEqual(self.a.post(self.base+'/uploads/transport_demand',params={'upload_id':str(uuid4()),'contract_hash':'a'*64},files={'file':('input.csv',self.template(),'text/csv')}).status_code,409)
        for role in ['anon','authenticated']:
            with self.assertRaises(AssertionError):self.sql(f"SET ROLE {role}; SELECT platform_ultimate_data_pack('{self.s.workspace_a}','{USER_A}','state','{{}}');")
    def test_23_concurrent_publications_have_one_cas_winner(self):
        a=self.upload();b=self.upload('transport_resources');bodies=[self.publication([{'slot_key':j['entity'],'upload_id':j['id']}],revision=1) for j in [a,b]]
        def post(body):
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_A]},trust_env=False,timeout=30) as client:return client.post(self.base+'/publish',json=body).status_code
        with ThreadPoolExecutor(2) as pool:statuses=list(pool.map(post,bodies))
        self.assertEqual(sorted(statuses),[200,409]);self.assertEqual(self.state()['history_total'],2)
    def test_24_replay_precedes_mutable_flag_and_revision(self):
        j=self.upload();body=self.publication([{'slot_key':j['entity'],'upload_id':j['id']}]);first=self.ok(self.a.post(self.base+'/publish',json=body));self.sql('UPDATE dation_private.platform_release SET ultimate_data_pack_enabled=false;')
        try:again=self.ok(self.a.post(self.base+'/publish',json=body));self.assertTrue(again['replayed']);self.assertEqual(first['version'],again['version'])
        finally:self.sql('UPDATE dation_private.platform_release SET ultimate_data_pack_enabled=true;')
    def test_25_discard_interrupted_candidate_is_safe_and_idempotent(self):
        self.marker('fail-t4-normalized');uid,response=self.upload_response();self.assertEqual(response.status_code,503);path=self.raw_path(uid);self.assertTrue(path.exists())
        self.ok(self.a.post(self.base+'/uploads/'+uid+'/discard'));self.assertFalse(path.exists());self.ok(self.a.post(self.base+'/uploads/'+uid+'/discard'));self.assertEqual(self.state()['entries'],[]);self.assertEqual(self.a.post(self.base+'/uploads/'+uid+'/recover').status_code,409)
    def test_26_normalized_preview_and_hub_use_same_hash(self):
        j=self.upload();self.publish(j);a=self.ok(self.a.get(self.base+'/preview/'+j['dataset_id']));b=self.ok(self.a.get('/api/platform/data/datasets/'+j['dataset_id']+'/preview'));self.assertEqual(a['canonical_sha256'],j['canonical_sha256']);self.assertEqual(a['canonical_sha256'],b['canonical_sha256']);self.assertEqual(len(a['records']),5);self.assertNotIn('product',a['records'][0])
    def test_27_upload_intent_cannot_be_rebound_to_changed_bytes(self):
        raw=self.template();uid,r=self.upload_response(body=raw);self.ok(r);changed=raw.replace(b'ORD-001',b'ORD-999');_,retry=self.upload_response(body=changed,uid=uid);self.assertEqual(retry.status_code,409);self.assertEqual(self.state()['pack']['revision'],1)
    def test_28_private_catalog_and_case_context_ownership_stay_intact(self):
        before=self.c['responsibilities']['stages'];j=self.upload();self.publish(j);after=self.ok(self.a.get('/api/platform/logistics-cases/'+self.cid+'/context'));self.assertEqual(before,after['responsibilities']['stages']);self.assertIsNone(after['case']['context_frozen_at'])
        for table in ['ultimate_input_objects','ultimate_input_uploads','ultimate_pack_publications']:
            with self.assertRaises(AssertionError):self.sql('SET ROLE service_role; SELECT * FROM dation_private.'+table+';')
    def test_29_missing_normalized_bytes_cannot_publish_a_partial_pack(self):
        j=self.upload();relative=self.sql(f"SELECT normalized_bucket||'/'||normalized_path FROM dation_private.ultimate_input_objects WHERE dataset_id='{j['dataset_id']}';");path=self.s.storage/relative;contents=path.read_bytes();path.unlink()
        try:
            r=self.a.post(self.base+'/publish',json=self.publication([{'slot_key':j['entity'],'upload_id':j['id']}]));self.assertEqual(r.status_code,503);self.assertEqual(self.state()['pack']['revision'],1)
        finally:path.write_bytes(contents)
    def test_30_concurrent_equal_uploads_reuse_one_dataset_and_clean_only_orphans(self):
        raw=self.template();hash_=self.state()['contracts']['transport_demand']['contract_hash'];ids=[str(uuid4()),str(uuid4())]
        def store(uid):
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_A]},trust_env=False,timeout=30) as client:
                r=client.post(self.base+'/uploads/transport_demand',params={'upload_id':uid,'contract_hash':hash_},files={'file':('operacion.csv',raw,'text/csv')});self.assertEqual(r.status_code,200,r.text);return r.json()
        with ThreadPoolExecutor(2) as pool:stored=list(pool.map(store,ids))
        self.assertEqual(stored[0]['dataset_id'],stored[1]['dataset_id']);self.assertEqual(sum(self.raw_path(uid).exists() for uid in ids),1);self.assertEqual(self.state()['pack']['revision'],1)


if __name__=='__main__':unittest.main()
