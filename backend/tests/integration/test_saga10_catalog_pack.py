"""G3 API/SQL/Storage integration, including pre-Case cross-file atomicity."""
import sys,json,unittest
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from journey_fixture import JourneySandbox
from auth_fixture import USER_A
from app.domain.logistics.data_contracts import compile_contract,template_csv
from tests.saga10_fixtures import catalog_config,direct_config
from tests.test_saga10_data_contracts import csv_bytes,sample_rows
from tests.test_ultimate_case_models import config

class Saga10CatalogPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=JourneySandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    def ok(self,r):self.assertTrue(r.is_success,r.text);return r.json()
    def setUp(self):
        self.a=self.s.api_client;self.s.sql('UPDATE dation_private.platform_release SET saga10_schema_enabled=true,saga10_ui_enabled=true;')
        m=self.ok(self.a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'Catálogo G3','configuration':catalog_config()}))['model']
        self.v=self.ok(self.a.post('/api/platform/logistics-models/'+m['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))['version']
        self.pid=str(uuid4());self.base='/api/platform/data-preparations/'+self.pid
        self.ok(self.a.post('/api/platform/data-preparations',json={'id':self.pid,'model_version_id':self.v['id']}))
    def tearDown(self):
        self.s.sql("UPDATE dation_private.journey_preparations SET status='EXPIRED' WHERE status IN('DRAFT','VALIDATED','FINALIZING');")
        ids=json.loads(self.s.sql("SELECT coalesce(jsonb_agg(id),'[]') FROM dation_private.journey_preparations WHERE created_by='"+USER_A+"';"))
        for pid in ids:self.ok(self.a.post('/api/platform/data-preparations/'+pid+'/cleanup'))
    def read(self):return self.ok(self.a.get(self.base))
    def upload(self,entity,raw=None):
        d=self.read();c=compile_contract(self.v,entity)
        return self.a.post(self.base+'/uploads/'+entity,params={'upload_id':str(uuid4()),'expected_revision':d['session']['revision'],'contract_hash':c.contract_hash},files={'file':('datos.csv',raw or template_csv(c),'text/csv')})
    def body(self):return {'expected_revision':self.read()['session']['revision'],'case':{'id':str(uuid4()),'name':'Case catálogo G3','logistics_model_version_id':self.v['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}}
    def test_01_three_templates_private_preparation_and_one_publication(self):
        before=self.s.sql('SELECT count(*) FROM decision_cases;');d=self.read();self.assertEqual(len(d['contracts']),3);self.assertTrue(d['bundle_validation_required'])
        for e in ['transport_demand','order_lines','transport_resources']:self.ok(self.upload(e))
        d=self.read();self.assertEqual(d['session']['status'],'VALIDATED');self.assertEqual(before,self.s.sql('SELECT count(*) FROM decision_cases;'))
        valid=self.ok(self.a.post(self.base+'/validate-bundle',json={'expected_revision':d['session']['revision']}));self.assertEqual((valid['order_count'],valid['line_count']),(5,5));self.assertEqual(len(valid['normalized_hashes']),3)
        b=self.body();result=self.ok(self.a.post(self.base+'/finalize',json=b));self.assertEqual(result['context']['entry_count'],3);self.assertEqual(result['preparation']['session']['status'],'CONSUMED')
        again=self.ok(self.a.post(self.base+'/finalize',json=b));self.assertEqual(again['context']['pack_version']['id'],result['context']['pack_version']['id'])
        self.assertEqual(self.s.sql("SELECT count(*) FROM case_data_pack_versions WHERE case_id='"+b['case']['id']+"';"),'2')
    def test_02_orphan_cross_validation_prevents_case_and_freeze(self):
        self.ok(self.upload('transport_demand'));c=compile_contract(self.v,'order_lines');rows=sample_rows(c);rows[0]['order_id']='UNKNOWN';self.ok(self.upload('order_lines',csv_bytes(c,rows)))
        self.ok(self.upload('transport_resources'));d=self.read();r=self.a.post(self.base+'/validate-bundle',json={'expected_revision':d['session']['revision']});self.assertEqual(r.status_code,422,r.text)
        self.assertEqual(r.json()['detail']['errors'][0]['code'],'ORPHAN_LINE');b=self.body();self.assertEqual(self.a.post(self.base+'/finalize',json=b).status_code,422)
        self.assertEqual(self.s.sql("SELECT count(*) FROM decision_cases WHERE id='"+b['case']['id']+"';"),'0');self.assertIsNone(self.read()['session']['creation_intent'])
    def test_03_orders_and_lines_are_atomic_but_empty_case_retained(self):
        self.ok(self.upload('transport_demand'));b=self.body();r=self.a.post(self.base+'/finalize',json=b);self.assertEqual(r.status_code,422,r.text)
        d=self.read();self.ok(self.a.post(self.base+'/unselect/transport_demand',json={'expected_revision':d['session']['revision']}))
        result=self.ok(self.a.post(self.base+'/finalize',json=self.body()));self.assertEqual(result['context']['entry_count'],0)
        self.assertIn('order_lines',[x['slot'] for x in result['graph']['nodes'][0]['requirements'] if x.get('code')=='MISSING_INPUT'])
    def test_04_failed_publish_recovers_same_three_file_case(self):
        for e in ['transport_demand','order_lines','transport_resources']:self.ok(self.upload(e))
        b=self.body();(self.s.storage/'fail-t4-publish').touch();r=self.a.post(self.base+'/finalize',json=b);self.assertEqual(r.status_code,503,r.text)
        self.assertEqual(self.read()['session']['status'],'FINALIZING')
        result=self.ok(self.a.post(self.base+'/finalize',json=b));again=self.ok(self.a.post(self.base+'/finalize',json=b))
        self.assertEqual(result['context']['case']['id'],b['case']['id']);self.assertEqual(result['context']['pack_version']['id'],again['context']['pack_version']['id']);self.assertEqual(result['context']['entry_count'],3)
    def test_05_invalid_discrete_csv_never_persists_and_revision_is_bound(self):
        c=compile_contract(self.v,'order_lines');rows=sample_rows(c)[:1];rows[0]['quantity']='1.5';r=self.upload('order_lines',csv_bytes(c,rows));self.assertEqual(r.status_code,422,r.text);self.assertEqual(self.read()['uploads'],[])
        self.ok(self.upload('transport_demand'));r=self.a.post(self.base+'/validate-bundle',json={'expected_revision':1});self.assertEqual(r.status_code,409)
    def test_06_migration_replay_and_closed_flags(self):
        migration=next((Path(__file__).resolve().parents[3]/'supabase/migrations').glob('*_saga10_catalog_data_contracts.sql'));self.s.sql(migration.read_text())
        self.assertFalse(self.ok(self.a.get('/api/platform/ultimate-foundation/capabilities'))['saga10_optimization_enabled'])
        self.s.sql('UPDATE dation_private.platform_release SET saga10_schema_enabled=false,saga10_ui_enabled=false;')
        self.assertEqual(self.upload('order_lines').status_code,403)
    def test_07_legacy_model_never_accepts_an_order_lines_slot(self):
        m=self.ok(self.a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'Legacy G3','configuration':config().model_dump(mode='json')}))['model']
        v=self.ok(self.a.post('/api/platform/logistics-models/'+m['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))['version'];pid=str(uuid4())
        self.ok(self.a.post('/api/platform/data-preparations',json={'id':pid,'model_version_id':v['id']}))
        r=self.a.post('/api/platform/data-preparations/'+pid+'/uploads/order_lines',params={'upload_id':str(uuid4()),'expected_revision':1,'contract_hash':'a'*64},files={'file':('lineas.csv',b'order_id,presentation_id,quantity\nORD-001,PAL-JUICE,1\n','text/csv')})
        self.assertEqual(r.status_code,404,r.text)
        r=self.a.post('/api/platform/logistics-models/contract-preview/templates/order_lines',json={'model_id':m['id'],'version_id':v['id']});self.assertEqual(r.status_code,404,r.text)
    def test_08_normalized_dataset_from_another_snapshot_cannot_be_reused(self):
        for e in ['transport_demand','order_lines','transport_resources']:self.ok(self.upload(e))
        result=self.ok(self.a.post(self.base+'/finalize',json=self.body()));cid=result['context']['case']['id'];state=self.ok(self.a.get('/api/platform/logistics-cases/'+cid+'/data'))
        source=next(e for e in state['entries'] if e['slot_key']=='order_lines')['dataset_id']
        m=self.ok(self.a.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'Otro snapshot','configuration':catalog_config()}))['model']
        v=self.ok(self.a.post('/api/platform/logistics-models/'+m['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':1}))['version'];pid=str(uuid4())
        self.ok(self.a.post('/api/platform/data-preparations',json={'id':pid,'model_version_id':v['id']}))
        r=self.a.post('/api/platform/data-preparations/'+pid+'/reuse/order_lines',json={'expected_revision':1,'dataset_id':source});self.assertEqual(r.status_code,404,r.text)
        self.assertEqual(self.ok(self.a.get('/api/platform/data-preparations/'+pid))['uploads'],[])
        self.assertEqual(self.ok(self.a.get('/api/platform/logistics-cases/'+cid+'/data'))['entries'],state['entries'])
