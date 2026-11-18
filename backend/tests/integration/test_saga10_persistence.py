"""Saga 10 G1: real isolated PostgreSQL/RPC/API; no remote Supabase."""
import sys,json,unittest
from pathlib import Path
from uuid import uuid4
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from journey_fixture import JourneySandbox
from auth_fixture import USER_A,USER_B
from app.services.logistics_model_service import configuration_snapshot
from tests.saga10_fixtures import catalog_config,direct_config
from tests.test_ultimate_case_models import config

class Saga10PersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=JourneySandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
        cls.default_flags=json.loads(cls.s.sql("SELECT jsonb_build_array(saga10_schema_enabled,saga10_ui_enabled,saga10_optimization_enabled) FROM dation_private.platform_release;"))
    def setUp(self):self.s.sql('UPDATE dation_private.platform_release SET saga10_schema_enabled=false,saga10_ui_enabled=false,saga10_optimization_enabled=false;')
    def enable(self):self.s.sql('UPDATE dation_private.platform_release SET saga10_schema_enabled=true,saga10_ui_enabled=true;')
    def ok(self,r):self.assertTrue(r.is_success,r.text);return r.json()
    def create(self,value=None):return self.s.api_client.post('/api/platform/logistics-models',json={'id':str(uuid4()),'name':'Modelo Saga 10','configuration':value or catalog_config()})
    def publish(self,model,revision=1):return self.ok(self.s.api_client.post('/api/platform/logistics-models/'+model['id']+'/versions',json={'version_id':str(uuid4()),'expected_revision':revision}))['version']
    def test_01_closed_defaults_and_legacy_persistence(self):
        self.assertEqual(self.default_flags,[False,False,False]);self.assertEqual(self.create().status_code,409)
        old=self.ok(self.create(config().model_dump(mode='json')))['model'];v=self.publish(old)
        self.assertEqual(v['config_jsonb']['version'],1);self.assertEqual(v['contract_registry_version'],'ULTIMATE_DOMAIN_V1')
        caps=self.ok(self.s.api_client.get('/api/platform/ultimate-foundation/capabilities'))
        self.assertFalse(caps['saga10_optimization_enabled']);self.assertFalse(caps['saga10_ui_enabled'])
    def test_02_v2_round_trip_idempotent_publish_and_historical_immutability(self):
        self.enable();value=catalog_config();created=self.ok(self.create(value));m=created['model'];v=self.publish(m)
        self.assertEqual(v['config_schema_version'],'logistics_model_config_v2');self.assertEqual(v['contract_registry_version'],'SAGA10_DOMAIN_V2')
        self.assertEqual(v['config_jsonb'],configuration_snapshot(value)[0]);original=json.dumps(v,sort_keys=True)
        replay=self.ok(self.s.api_client.post('/api/platform/logistics-models/'+m['id']+'/versions',json={'version_id':v['id'],'expected_revision':1}));self.assertTrue(replay['replayed'])
        value['cargo']['logistic_units'][0]['tare_mass']['value']='30'
        for p in value['cargo']['presentations']:p.pop('gross_mass')
        updated=self.ok(self.s.api_client.put('/api/platform/logistics-models/'+m['id'],json={'expected_revision':2,'name':'Nueva configuración','configuration':value}))
        second=self.publish(m,updated['model']['revision']);self.assertNotEqual(second['config_hash'],v['config_hash'])
        detail=self.ok(self.s.api_client.get('/api/platform/logistics-models/'+m['id']));again=next(x for x in detail['versions'] if x['id']==v['id']);self.assertEqual(json.dumps(again,sort_keys=True),original)
        with self.assertRaises(AssertionError):self.s.sql("UPDATE logistics_model_versions SET config_jsonb='{}' WHERE id='"+v['id']+"';")
    def test_03_sql_references_and_no_implicit_downgrade(self):
        self.enable();m=self.ok(self.create())['model'];value=configuration_snapshot(catalog_config())[0];value['cargo']['logistic_units']=[]
        literal="'"+json.dumps(value).replace("'","''")+"'::jsonb"
        self.assertEqual(self.s.sql('SELECT dation_private.t3_configuration_valid('+literal+');'),'f')
        r=self.s.api_client.put('/api/platform/logistics-models/'+m['id'],json={'expected_revision':1,'name':'Downgrade','configuration':config().model_dump(mode='json')});self.assertEqual(r.status_code,409,r.text)
        unchanged=self.ok(self.s.api_client.get('/api/platform/logistics-models/'+m['id']))['model']
        self.assertEqual(unchanged['draft_config_jsonb']['version'],2);self.assertEqual(unchanged['revision'],1)
    def test_04_tenant_and_role_guards_retained(self):
        self.enable();m=self.ok(self.create())['model']
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[USER_B]},trust_env=False) as other:
            self.assertEqual(other.get('/api/platform/logistics-models/'+m['id']).status_code,404)
        for role in ['anon','authenticated']:
            with self.assertRaises(AssertionError):self.s.sql('SET ROLE '+role+"; SELECT public.platform_ultimate_foundation('"+self.s.workspace_a+"','"+USER_B+"','capabilities','{}');")
            with self.assertRaises(AssertionError):self.s.sql('SET ROLE '+role+'; SELECT * FROM dation_private.platform_release;')
    def test_05_migration_replay_preserves_flags_and_versions(self):
        self.enable();m=self.ok(self.create(direct_config()))['model'];v=self.publish(m)
        migration=next((Path(__file__).resolve().parents[3]/'supabase/migrations').glob('*_saga10_logistics_model_v2.sql'))
        self.s.sql(migration.read_text());caps=self.ok(self.s.api_client.get('/api/platform/ultimate-foundation/capabilities'))
        self.assertTrue(caps['saga10_schema_enabled']);self.assertFalse(caps['saga10_optimization_enabled'])
        detail=self.ok(self.s.api_client.get('/api/platform/logistics-models/'+m['id']));self.assertEqual(detail['versions'][0]['config_hash'],v['config_hash'])
    def test_06_v2_optimization_gate_closed_even_for_rpc(self):
        self.enable();m=self.ok(self.create())['model'];v=self.publish(m)
        case=self.ok(self.s.api_client.post('/api/platform/logistics-cases',json={'id':str(uuid4()),'name':'Case con ruta cerrada','logistics_model_version_id':v['id'],'planning_start':'2026-11-02','planning_end':'2026-11-08','horizon_type':'WEEKLY','case_policy':{'primary_goal':'MINIMIZE_COST'},'decision_owner_user_id':USER_A}))['case']
        arguments=json.dumps({'case_id':case['id'],'run_id':str(uuid4())})
        with self.assertRaisesRegex(AssertionError,'Saga10 optimization closed'):
            self.s.sql("SELECT platform_ultimate_execution('"+self.s.workspace_a+"','"+USER_A+"','admit','"+arguments+"'::jsonb);")
        self.assertEqual(self.s.sql("SELECT count(*) FROM decision_runs WHERE decision_case_id='"+case['id']+"';"),'0')
