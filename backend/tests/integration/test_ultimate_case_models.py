"""S3: checked T3 RPCs and locking against the complete PostgreSQL 17 catalog.

Synthetic admission rows exercise freeze only: no ingestion, publisher or engine.
Missing owned infrastructure fails rather than skips.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID,uuid4

from ultimate_sql_support import UltimateSQLSandbox, CONTAINER, DOCKER
from app.models.ultimate_foundation import ModelCreate, ModelUpdate, ModelPublish, UltimateCaseCreate, UltimateCaseUpdate
from app.services import logistics_model_service as service
from tests.test_ultimate_case_models import config

ADMIN,OTHER,OPERATOR,VIEWER,DISABLED=[str(uuid4()) for _ in range(5)]
H='a'*64

def literal(value):return "'"+json.dumps(value,separators=(',',':')).replace("'","''")+"'::jsonb"


class UltimateCaseSQLTests(UltimateSQLSandbox,unittest.TestCase):
    @classmethod
    def verify_owner(cls):
        result=subprocess.run([*DOCKER,'inspect','--format','{{index .Config.Labels "dation.qa.phase"}}|{{index .Config.Labels "dation.qa.owner"}}',CONTAINER or ''],capture_output=True,text=True,timeout=10)
        if result.returncode or result.stdout.strip()!='T3|codex-dation':raise RuntimeError('S3 requires its labelled owned T3 sandbox')
        if not 170000<=int(cls.command('SHOW server_version_num;',database='postgres').stdout)<180000:raise RuntimeError('PostgreSQL 17 required')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.command('UPDATE dation_private.platform_release SET admissions_open=true,workflow_gates_enabled=true;')
        for uid in [ADMIN,OTHER,OPERATOR,VIEWER,DISABLED]:cls.command(f"INSERT INTO auth.users VALUES('{uid}','{uid}@example.test',now());")
        cls.wa=json.loads(cls.command(f"SELECT platform_create_workspace('{ADMIN}','T3 A','AR','UTC','ARS');").stdout)['workspace_id']
        cls.wb=json.loads(cls.command(f"SELECT platform_create_workspace('{OTHER}','T3 B','AR','UTC','ARS');").stdout)['workspace_id']
        for wid,uid in [(cls.wa,ADMIN),(cls.wb,OTHER)]:
            cls.command(f"SELECT platform_set_member_responsibilities('{wid}','{uid}','{uid}',(SELECT updated_at FROM workspace_members WHERE workspace_id='{wid}' AND user_id='{uid}'),ARRAY['decision_owner']);")
        cls.command(f"INSERT INTO profiles(id) VALUES('{OPERATOR}'),('{VIEWER}'),('{DISABLED}'); INSERT INTO workspace_members(workspace_id,user_id,access_role,status) VALUES('{cls.wa}','{OPERATOR}','operator','active'),('{cls.wa}','{VIEWER}','viewer','active'),('{cls.wa}','{DISABLED}','operator','disabled');")
        cls.command('UPDATE dation_private.platform_release SET ultimate_foundation_enabled=true;')

    def sql(self,sql):return self.command(sql).stdout.strip()
    def reject(self,sql,*codes):
        result=self.command(sql,check=False);self.assertNotEqual(result.returncode,0,sql)
        if codes:self.assertTrue(any(code in result.stderr for code in codes),result.stderr)
        return result.stderr
    def rpc_sql(self,operation,args=None,user=ADMIN,workspace=None):
        return f"SET ROLE service_role; SELECT public.platform_ultimate_foundation('{workspace or self.wa}','{user}','{operation}',{literal(args or {})});"
    def rpc(self,operation,args=None,**ctx):return json.loads(self.sql(self.rpc_sql(operation,args,**ctx)))
    def invoke(self,method,*args,user=ADMIN,workspace=None):
        ctx=SimpleNamespace(workspace_id=workspace or self.wa,user_id=user)
        async def bridge(_name,body):return self.rpc(body['operation'],body['arguments'],user=body['actor_user_id'],workspace=body['target_workspace_id'])
        with patch.object(service,'platform_call',bridge):return asyncio.run(method(ctx,*args))
    def model(self,**changes):
        return self.invoke(service.create_model,ModelCreate(id=uuid4(),name='Operación '+str(uuid4())[:8],configuration=config(**changes)))
    def publish(self,model):
        return self.invoke(service.publish_model,model['model']['id'],ModelPublish(version_id=uuid4(),expected_revision=model['model']['revision']))
    def case(self,version=None,**changes):
        version=version or self.publish(self.model())['version']['id']
        values=dict(id=uuid4(),name='Semana 45',logistics_model_version_id=version,planning_start='2026-11-02',planning_end='2026-11-08',horizon_type='WEEKLY',case_policy={'primary_goal':'MINIMIZE_COST'},decision_owner_user_id=ADMIN)
        values.update(changes)
        return self.invoke(service.create_case,UltimateCaseCreate(**values))
    def update(self,c,**changes):
        return self.invoke(service.update_case_context,c['case']['id'],UltimateCaseUpdate(expected_updated_at=c['case']['updated_at'],**changes))
    def test_01_model_create_list_search_and_identity_replay(self):
        payload=ModelCreate(id=uuid4(),name='Unicode · Operación ñ',configuration=config())
        a=self.invoke(service.create_model,payload);b=self.invoke(service.create_model,payload)
        self.assertEqual(a,b);listed=self.rpc('model_list',{'search_text':'Operación ñ','limit':1})
        self.assertEqual(listed['total'],1);self.assertEqual(listed['items'][0]['id'],str(payload.id))
        self.assertNotIn('draft_config_jsonb',listed['items'][0])
        with self.assertRaises(AssertionError):self.invoke(service.create_model,payload.model_copy(update={'name':'Changed'}))
    def test_02_publish_is_append_only_and_replay_survives_draft_edit(self):
        m=self.model();payload=ModelPublish(version_id=uuid4(),expected_revision=1);first=self.invoke(service.publish_model,m['model']['id'],payload)
        edited=self.invoke(service.update_model,m['model']['id'],ModelUpdate(expected_revision=2,name='Nuevo borrador',configuration=config(split_permitted=True)))
        replay=self.invoke(service.publish_model,m['model']['id'],payload);self.assertTrue(replay['replayed']);self.assertEqual(first['version'],replay['version'])
        second=self.publish(edited);self.assertEqual(second['version']['version'],2);self.assertNotEqual(second['version']['config_hash'],first['version']['config_hash'])
        for sql in [f"UPDATE logistics_model_versions SET config_hash='{H}' WHERE id='{payload.version_id}';",f"DELETE FROM logistics_model_versions WHERE id='{payload.version_id}';"]:self.reject(sql,'22023')
    def test_03_cases_reuse_one_version_and_new_version_does_not_rebind(self):
        m=self.model();v=self.publish(m);a=self.case(v['version']['id']);b=self.case(v['version']['id'])
        self.assertEqual(a['model_version'],b['model_version']);self.assertNotEqual(a['pack']['id'],b['pack']['id'])
        latest=self.rpc('model_get',{'model_id':m['model']['id']});self.publish(latest)
        reread=self.invoke(service.get_case_context,a['case']['id']);self.assertEqual(reread['model_version']['id'],v['version']['id'])
    def test_04_empty_case_pack_is_atomic_tenant_bound_and_reloads(self):
        c=self.case();row=c['case'];self.assertIsNone(row['orders_dataset_id']);self.assertIsNone(row['fleet_dataset_id']);self.assertEqual(c['entry_count'],0)
        self.assertEqual(c['pack']['workspace_id'],self.wa);self.assertEqual(c['pack']['case_id'],row['id']);self.assertEqual(c['pack']['current_version_id'],c['pack_version']['id']);self.assertEqual(c['pack_version']['version'],1)
        self.assertFalse(c['planning_context']['admission_available']);self.assertEqual(c,self.invoke(service.get_case_context,row['id']))
    def test_05_binding_is_immutable_even_before_admission(self):
        c=self.case();v=self.publish(self.model())['version']['id'];self.reject(f"UPDATE decision_cases SET logistics_model_version_id='{v}' WHERE id='{c['case']['id']}';",'22023')
        self.reject(self.rpc_sql('case_update',{'case_id':c['case']['id'],'expected_updated_at':c['case']['updated_at'],'changes':{'logistics_model_version_id':v},'owner_updates':[]}),'22023')
    def test_06_invalid_horizon_rolls_back_case_pack_and_owners(self):
        c=self.case();before=self.sql('SELECT count(*) FROM case_data_packs;')
        self.reject(self.rpc_sql('case_update',{'case_id':c['case']['id'],'expected_updated_at':c['case']['updated_at'],'changes':{'planning_end':'2026-10-01'},'owner_updates':[]}),'23514')
        self.assertEqual(self.invoke(service.get_case_context,c['case']['id'])['case']['planning_end'],'2026-11-08');self.assertEqual(before,self.sql('SELECT count(*) FROM case_data_packs;'))
    def test_07_policy_and_modes_are_persisted_not_executed(self):
        for goal in ['MINIMIZE_COST','MAXIMIZE_SERVICE','MAXIMIZE_OWN_CAPACITY','MINIMIZE_TRIPS','BALANCED','CUSTOM']:
            policy={'primary_goal':goal}
            if goal=='CUSTOM':policy.update(preferences=[{'kind':'COST','weight':'.6'},{'kind':'SERVICE','weight':'.4'}],guardrails=[{'kind':'MINIMUM_DEMAND_COVERAGE','limit':'.9','hard':True}])
            c=self.case(case_policy=policy,operating_mode='SIMULATION');self.assertEqual(c['planning_context']['case_policy']['primary_goal'],goal);self.assertEqual(c['case']['operating_mode'],'SIMULATION')
        self.assertFalse(self.rpc('capabilities')['runtime_execution_available'])
    def test_08_pre_admission_math_edit_changes_context_hash(self):
        c=self.case();updated=self.update(c,planning_end='2026-11-09',horizon_type='CUSTOM',case_policy={'primary_goal':'BALANCED'})
        self.assertNotEqual(c['planning_context_hash'],updated['planning_context_hash']);self.assertIsNone(updated['case']['context_frozen_at'])
    def test_09_case_and_owner_cas_preserve_atomicity(self):
        c=self.case();new=self.update(c,name='Nombre actual')
        with self.assertRaises(AssertionError):self.update(c,name='Obsoleto')
        with self.assertRaises(AssertionError):self.update(new,name='No debe guardarse',owner_updates=[{'node_id':'logistics_assignment','owner_user_id':None,'expected_updated_at':None}])
        self.assertEqual(self.invoke(service.get_case_context,c['case']['id'])['case']['label'],'Nombre actual')
    def test_10_admin_owner_is_required_eligible_and_atomic(self):
        for owner in [None,VIEWER,OTHER,DISABLED]:
            before=self.sql('SELECT count(*) FROM decision_cases;')
            with self.assertRaises(AssertionError):self.case(decision_owner_user_id=owner)
            self.assertEqual(before,self.sql('SELECT count(*) FROM decision_cases;'))
        c=self.case();self.assertEqual(c['responsibilities']['stages']['logistics_assignment']['owner']['id'],ADMIN)
        self.assertEqual(c['responsibilities']['stages']['logistics_scheduling']['owner']['id'],ADMIN)
    def test_11_operator_can_create_pending_but_not_assign_or_publish(self):
        v=self.publish(self.model())['version']['id'];p=UltimateCaseCreate(id=uuid4(),name='Owner pendiente',logistics_model_version_id=v,planning_start='2026-11-02',planning_end='2026-11-02',horizon_type='DAILY',case_policy={'primary_goal':'MINIMIZE_COST'})
        c=self.invoke(service.create_case,p,user=OPERATOR);self.assertIsNone(c['responsibilities']['stages']['logistics_assignment']['owner'])
        with self.assertRaises(AssertionError):self.invoke(service.create_case,p.model_copy(update={'id':uuid4(),'decision_owner_user_id':UUID(ADMIN)}),user=OPERATOR)
        self.reject(self.rpc_sql('model_create',{},user=OPERATOR),'42501')
        self.reject(self.rpc_sql('model_publish',{},user=OPERATOR),'42501')
    def test_12_viewer_read_only_and_disabled_member_rejected(self):
        c=self.case();self.assertFalse(self.rpc('case_get',{'case_id':c['case']['id']},user=VIEWER)['permissions']['can_edit'])
        for operation in ['case_update','case_create','model_update']:self.reject(self.rpc_sql(operation,{},user=VIEWER),'42501')
        self.reject(self.rpc_sql('capabilities',{},user=DISABLED),'42501')
    def test_13_cross_workspace_cannot_read_or_bind(self):
        c=self.case()
        for op,args in [('case_get',{'case_id':c['case']['id']}),('model_get',{'model_id':c['model']['id']})]:self.reject(self.rpc_sql(op,args,user=OTHER,workspace=self.wb),'P0002')
        self.reject(self.rpc_sql('capabilities',{},user=OTHER),'42501')
        p=UltimateCaseCreate(id=uuid4(),name='Cross tenant',logistics_model_version_id=c['model_version']['id'],planning_start='2026-11-02',planning_end='2026-11-02',horizon_type='DAILY',case_policy={'primary_goal':'MINIMIZE_COST'},decision_owner_user_id=OTHER)
        with self.assertRaises(AssertionError):self.invoke(service.create_case,p,user=OTHER,workspace=self.wb)
    def test_14_closed_flag_blocks_writes_keeps_existing_context_readable(self):
        c=self.case();self.sql('UPDATE dation_private.platform_release SET ultimate_foundation_enabled=false;')
        try:
            self.assertFalse(self.rpc('capabilities')['enabled']);self.assertEqual(self.rpc('case_get',{'case_id':c['case']['id']})['case']['id'],c['case']['id'])
            self.assertFalse(self.rpc('case_get',{'case_id':c['case']['id']})['permissions']['can_edit'])
            self.reject(self.rpc_sql('case_update',{}),'P0002')
        finally:self.sql('UPDATE dation_private.platform_release SET ultimate_foundation_enabled=true;')
    def test_15_role_does_not_grant_permission_or_select_runtime(self):
        for role in ['SHIPPER','LOGISTICS_PROVIDER','HYBRID']:
            c=self.case(self.publish(self.model(operating_role=role))['version']['id']);self.assertEqual(c['case']['graph_definition_version'],service.GRAPH_VERSION)
            self.assertFalse(c['planning_context']['admission_available']);self.assertFalse(self.rpc('case_get',{'case_id':c['case']['id']},user=VIEWER)['permissions']['can_edit'])
    def test_16_archived_model_prevents_new_binding_preserves_existing(self):
        m=self.model();v=self.publish(m);c=self.case(v['version']['id'])
        self.invoke(service.update_model,m['model']['id'],ModelUpdate(expected_revision=2,name='Archivado',status='archived',configuration=config()))
        self.assertEqual(self.invoke(service.get_case_context,c['case']['id'])['model_version']['id'],v['version']['id'])
        with self.assertRaises(AssertionError):self.case(v['version']['id'])
    def test_17_concurrent_publish_has_one_cas_winner(self):
        m=self.model();configuration,h=service.configuration_snapshot(config());descriptor,ch=service.contract_reference(h)
        def publish(_):return self.command(self.rpc_sql('model_publish',{'model_id':m['model']['id'],'version_id':str(uuid4()),'expected_revision':1,'configuration_hash':h,'contract_descriptor':descriptor,'contract_hash':ch}),check=False)
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(publish,range(2)))
        self.assertEqual(sum(r.returncode==0 for r in results),1);self.assertTrue(any('55006' in r.stderr for r in results))
    def test_18_private_acl_and_direct_write_denials(self):
        for role in ['anon','authenticated']:
            self.reject(f"SET ROLE {role}; SELECT public.platform_ultimate_foundation('{self.wa}','{ADMIN}','capabilities');",'42501')
        for table in ['logistics_models','logistics_model_versions','case_data_packs','case_data_pack_versions']:
            self.reject(f'SET ROLE service_role; DELETE FROM {table};','42501')
        self.reject('SET ROLE service_role; UPDATE dation_private.platform_release SET ultimate_foundation_enabled=true;','42501')
    def test_19_sql_rejects_invalid_policy_and_config_without_api(self):
        c=self.case();invalid={'version':1,'primary_goal':'CUSTOM','guardrails':[],'preferences':[]}
        self.reject(self.rpc_sql('case_update',{'case_id':c['case']['id'],'expected_updated_at':c['case']['updated_at'],'changes':{'case_policy':invalid,'case_policy_hash':H},'owner_updates':[]}),'22023')
        m=self.model();configuration,h=service.configuration_snapshot(config());configuration['operating_role']='ADMIN'
        self.reject(self.rpc_sql('model_update',{'model_id':m['model']['id'],'expected_revision':1,'configuration':configuration,'configuration_hash':h,'name':'Invalid','status':'active'}),'22023')
    def test_23_pack_failure_rolls_back_new_case_and_pack(self):
        c=self.case();cid=str(uuid4());args=dict(id=cid,name='Atomic failure',logistics_model_version_id=c['model_version']['id'],planning_start='2026-11-02',planning_end='2026-11-08',horizon_type='WEEKLY',operating_mode='OPERATIONAL',case_policy=c['case']['case_policy_jsonb'],case_policy_hash=c['case']['case_policy_hash'],decision_owner_user_id=ADMIN,creation_intent_hash=H,**service.empty_pack_snapshot(self.wa,cid))
        args['pack_version_id']=c['pack_version']['id'];before=self.sql('SELECT (SELECT count(*) FROM decision_cases)||\':\'||(SELECT count(*) FROM case_data_packs);')
        self.reject(self.rpc_sql('case_create',args),'23505');self.assertEqual(before,self.sql('SELECT (SELECT count(*) FROM decision_cases)||\':\'||(SELECT count(*) FROM case_data_packs);'))
    def test_24_disabled_dda_denies_foundation_and_stale_model_cas(self):
        m=self.model();self.publish(m)
        with self.assertRaises(AssertionError):self.invoke(service.update_model,m['model']['id'],ModelUpdate(expected_revision=1,name='Stale',configuration=config()))
        self.sql(f"UPDATE workspace_ddas SET status='disabled' WHERE workspace_id='{self.wa}' AND dda_id='logistics';")
        try:
            self.assertFalse(self.rpc('capabilities')['enabled']);self.reject(self.rpc_sql('model_get',{'model_id':m['model']['id']}),'42501')
        finally:self.sql(f"UPDATE workspace_ddas SET status='enabled' WHERE workspace_id='{self.wa}' AND dda_id='logistics';")
    def test_25_existing_archive_restore_keeps_binding_owners_and_pack(self):
        c=self.case();cid=c['case']['id']
        def archive(stamp,value):self.sql(f"SELECT platform_update_case(actor_user_id=>'{ADMIN}',target_workspace_id=>'{self.wa}',target_case_id=>'{cid}',expected_updated_at=>'{stamp}'::timestamptz,change_label=>false,new_label=>NULL,archive=>{str(value).lower()});")
        archive(c['case']['updated_at'],True);archived=self.invoke(service.get_case_context,cid);self.assertFalse(archived['permissions']['can_edit']);self.assertEqual(archived['case']['status'],'archived')
        archive(archived['case']['updated_at'],False);restored=self.invoke(service.get_case_context,cid);self.assertEqual(restored['pack'],c['pack']);self.assertEqual(restored['model_version'],c['model_version']);self.assertEqual(restored['responsibilities']['stages'],c['responsibilities']['stages'])

    def admission_fixture(self,c):
        """Create immutable metadata fixtures only, never call a T4 publisher."""
        w=self.wa;cid=c['case']['id'];p=c['pack']['id'];pv,d,r=[str(uuid4()) for _ in range(3)];raw=uuid4().hex*2
        self.sql(f"""BEGIN; INSERT INTO datasets(id,workspace_id,dataset_type,original_filename,storage_path,sha256,data_contract_id,data_contract_hash,normalizer_version,canonical_sha256,schema_version)
         VALUES('{d}','{w}','transport_demand','fixture.csv','{w}/{d}/fixture.csv','{raw}','transport_demand_v1','{H}','DEMAND_V1','{H}','transport_demand_v1');
         INSERT INTO case_data_pack_versions(id,workspace_id,case_id,pack_id,version,manifest_hash,contract_set_hash,created_by)
          VALUES('{pv}','{w}','{cid}','{p}',2,'{H}','{H}','{ADMIN}');
         INSERT INTO case_data_pack_entries(pack_version_id,slot_key,workspace_id,case_id,dataset_id,contract_id,contract_hash,raw_sha256,canonical_sha256,normalizer_version,normalized_bucket,normalized_path,record_count)
          VALUES('{pv}','transport_demand','{w}','{cid}','{d}','transport_demand_v1','{H}','{raw}','{H}','DEMAND_V1','dda-inputs','{w}/normalized/{d}/{H}.json',1); COMMIT;""")
        return r,f"""INSERT INTO decision_runs(id,workspace_id,dataset_id,decision_case_id,node_id,workflow_version,logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,node_policy_hash,contract_hash,input_context_hash,transit_model_version,runtime_profile,result_schema_version,engine_name,engine_version,schema_version,status,created_by_user_id)
          VALUES('{r}','{w}','{d}','{cid}','logistics_assignment',2,'{c['model_version']['id']}','{pv}','{service.GRAPH_VERSION}','{c['case']['case_policy_hash']}','{H}','{H}','{H}','DATION_TRANSIT_V1','transport_plan_v1',1,'transport_plan','2.0.0','transport_plan_v1','queued','{ADMIN}');"""
    def test_20_first_admission_freezes_sql_math_metadata_and_owner_remain_editable(self):
        c=self.case();rid,sql=self.admission_fixture(c);self.sql(sql);frozen=self.invoke(service.get_case_context,c['case']['id']);self.assertIsNotNone(frozen['case']['context_frozen_at']);self.assertFalse(frozen['permissions']['can_edit_mathematical'])
        for change in ["planning_end='2026-11-09'","horizon_type='CUSTOM'","operating_mode='SIMULATION'",f"case_policy_hash='{H}'"]:self.reject(f"UPDATE decision_cases SET {change} WHERE id='{c['case']['id']}';",'22023')
        before=self.sql(f"SELECT to_jsonb(r) FROM decision_runs r WHERE id='{rid}';")
        owner=frozen['responsibilities']['stages']['logistics_assignment'];changed=self.update(frozen,name='Nombre nuevo',description='Metadata permitida',owner_updates=[{'node_id':'logistics_assignment','owner_user_id':None,'expected_updated_at':owner['updated_at']}])
        self.assertEqual(changed['planning_context_hash'],frozen['planning_context_hash']);self.assertEqual(before,self.sql(f"SELECT to_jsonb(r) FROM decision_runs r WHERE id='{rid}';"));self.assertIsNone(changed['responsibilities']['stages']['logistics_assignment']['owner'])
        self.assertGreater(int(self.sql(f"SELECT count(*) FROM audit_events WHERE decision_case_id='{c['case']['id']}';")),0)
    def test_21_failed_admission_rolls_back_freeze(self):
        c=self.case();_,sql=self.admission_fixture(c);self.reject(sql.replace(c['case']['case_policy_hash'],'b'*64),'22023')
        self.assertIsNone(self.invoke(service.get_case_context,c['case']['id'])['case']['context_frozen_at'])
        self.update(c,planning_end='2026-11-09')
    def test_22_admission_and_context_update_serialize_on_workspace_lock(self):
        c=self.case();_,sql=self.admission_fixture(c)
        env=os.environ.copy()
        for key in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH']:env.pop(key,None)
        process=subprocess.Popen([*DOCKER,'exec','-i',CONTAINER,'psql','-U','postgres','-d',self.database,'-X','-q','-A','-t','-v','ON_ERROR_STOP=1'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        try:
            process.stdin.write("BEGIN; SET application_name='dation_t3_admission_race';"+sql+"SELECT 'ADMISSION_LOCKED';\n");process.stdin.flush()
            self.assertEqual(process.stdout.readline().strip(),'ADMISSION_LOCKED')
            with ThreadPoolExecutor(1) as pool:
                future=pool.submit(self.command,self.rpc_sql('case_update',{'case_id':c['case']['id'],'expected_updated_at':c['case']['updated_at'],'changes':{'planning_end':'2026-11-09'},'owner_updates':[]}),check=False)
                deadline=time.monotonic()+5;blocked=False
                while time.monotonic()<deadline:
                    if self.sql("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%platform_ultimate_foundation%';")!='0':blocked=True;break
                    time.sleep(.03)
                self.assertTrue(blocked,'Context update must wait on the admission transaction')
                process.stdin.write('COMMIT;\n');process.stdin.flush();process.stdin.close();self.assertEqual(process.wait(10),0)
                result=future.result(10);self.assertNotEqual(result.returncode,0);self.assertIn('55006',result.stderr)
            self.assertEqual(self.invoke(service.get_case_context,c['case']['id'])['case']['planning_end'],'2026-11-08')
        finally:
            if process.poll() is None:process.terminate();process.wait(5)
            process.stdout.close();process.stderr.close()


if __name__=='__main__':unittest.main()
