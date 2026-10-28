"""S2: real complete-catalog fresh/upgrade, tenancy, immutable metadata and readers.

All rows are synthetic persistence fixtures; no engine, artifact bytes, publisher,
LLM or product activation is involved. Missing owned infrastructure is an ERROR.
"""
import json
import os
import re
from pathlib import Path
import unittest
from uuid import uuid4

from ultimate_sql_support import UltimateSQLSandbox, REPO

WORK=Path(os.environ.get('DATION_T2_EVIDENCE','/tmp/dation-t2-evidence'))
USER_A,USER_B,VIEWER,DISABLED=[str(uuid4()) for _ in range(4)]
H='a'*64


def literal(value):return "'"+json.dumps(value,separators=(',',':')).replace("'","''")+"'::jsonb"


class UltimateSchemaTests(UltimateSQLSandbox,unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass();WORK.mkdir(parents=True,exist_ok=True)
        cls.command("UPDATE dation_private.platform_release SET admissions_open=true,workflow_gates_enabled=true;")
        for uid in (USER_A,USER_B,VIEWER,DISABLED):
            cls.command(f"INSERT INTO auth.users VALUES('{uid}','{uid}@example.test',now());")
        cls.wa=json.loads(cls.command(f"SELECT platform_create_workspace('{USER_A}','T2 A','AR','UTC','ARS');").stdout)['workspace_id']
        cls.wb=json.loads(cls.command(f"SELECT platform_create_workspace('{USER_B}','T2 B','AR','UTC','ARS');").stdout)['workspace_id']
        cls.command(f"INSERT INTO profiles(id) VALUES('{VIEWER}'),('{DISABLED}'); INSERT INTO workspace_members(workspace_id,user_id,access_role,status) VALUES('{cls.wa}','{VIEWER}','viewer','active'),('{cls.wa}','{DISABLED}','operator','disabled');")
        cls.ma,cls.mb,cls.va,cls.vb=[str(uuid4()) for _ in range(4)]
        cls.command(f"INSERT INTO dation_private.decision_definition_versions VALUES('ULTIMATE_GRAPH_V1','{H}','{{}}',now());")
        for wid,uid,mid,vid in [(cls.wa,USER_A,cls.ma,cls.va),(cls.wb,USER_B,cls.mb,cls.vb)]:
            cls.command(f"""INSERT INTO logistics_models(id,workspace_id,name,created_by) VALUES('{mid}','{wid}','Operación','{uid}');
            INSERT INTO logistics_model_versions(id,workspace_id,model_id,version,graph_definition_version,config_schema_version,
             config_jsonb,contract_descriptor_jsonb,config_hash,contract_hash,contract_registry_version,published_by)
            VALUES('{vid}','{wid}','{mid}',1,'ULTIMATE_GRAPH_V1','logistics_model_v1','{{}}','{{}}','{H}','{H}','SEMANTIC_FIELDS_V1','{uid}');""")

    def sql(self,sql):return self.command(sql).stdout.strip()

    def reject(self,sql,*codes):
        result=self.command(sql,check=False)
        self.assertNotEqual(result.returncode,0,'Invalid write was accepted: '+sql)
        if codes:self.assertTrue(any(code in result.stderr for code in codes),result.stderr)
        return result.stderr

    def case_sql(self, *, workspace=None, model=None, user=None, demand=False):
        w=workspace or self.wa;model=model or self.va;u=user or USER_A
        ids=dict(id=str(uuid4()),pack=str(uuid4()),version=str(uuid4()),dataset=str(uuid4()),workspace=w)
        c,p,v,d=ids['id'],ids['pack'],ids['version'],ids['dataset']
        sql=f"""INSERT INTO decision_cases(id,workspace_id,workflow_version,logistics_model_version_id,
         planning_start,planning_end,operating_mode,case_policy_schema_version,case_policy_jsonb,case_policy_hash,
         graph_definition_version,context_frozen_at,label)
         VALUES('{c}','{w}',2,'{model}','2026-11-02','2026-11-08','OPERATIONAL','case_policy_v1',
          '{{"version":1,"primary_goal":"MINIMIZE_COST"}}','{H}','ULTIMATE_GRAPH_V1',now(),'T2 Case');
         INSERT INTO case_data_packs(id,workspace_id,case_id) VALUES('{p}','{w}','{c}');
         INSERT INTO case_data_pack_versions(id,workspace_id,case_id,pack_id,version,manifest_hash,contract_set_hash,created_by)
          VALUES('{v}','{w}','{c}','{p}',1,'{H}','{H}','{u}');"""
        if demand:
            raw=uuid4().hex*2
            sql+=f"""INSERT INTO datasets(id,workspace_id,dataset_type,original_filename,storage_path,sha256,
              data_contract_id,data_contract_hash,normalizer_version,canonical_sha256,schema_version)
              VALUES('{d}','{w}','transport_demand','demand.csv','{w}/{d}/demand.csv','{raw}',
              'transport_demand_v1','{H}','DEMAND_V1','{H}','transport_demand_v1');
             INSERT INTO case_data_pack_entries(pack_version_id,slot_key,workspace_id,case_id,dataset_id,contract_id,contract_hash,
              raw_sha256,canonical_sha256,normalizer_version,normalized_bucket,normalized_path,record_count)
              VALUES('{v}','transport_demand','{w}','{c}','{d}','transport_demand_v1','{H}','{raw}','{H}',
              'DEMAND_V1','dda-inputs','{w}/normalized/{d}/{H}.json',1);"""
        sql+=f"UPDATE case_data_packs SET current_version_id='{v}' WHERE id='{p}';"
        return ids,sql

    def make_case(self,**kwargs):
        ids,sql=self.case_sql(**kwargs);self.sql('BEGIN;'+sql+'COMMIT;');return ids

    def run_sql(self,c, *, run_id=None, manifest=None, complete=True, model=None):
        rid=run_id or str(uuid4());w=c['workspace'];model=model or self.va
        result=dict(result_schema='transport_plan_v1',result_schema_version=1,assembler_version='RESULT_ASSEMBLER_V1',
            fingerprints=dict(result_fingerprint='b'*64,core_result_fingerprint='c'*64),artifact_manifest=dict(version=1,artifacts=manifest or []))
        publication=(",result_package_version,assembler_version,artifact_manifest_hash,core_fingerprint,result_fingerprint,result_json" if complete else '')
        values=(f",1,'RESULT_ASSEMBLER_V1','{H}','{'c'*64}','{'b'*64}',{literal(result)}" if complete else '')
        sql=f"""INSERT INTO decision_runs(id,workspace_id,dataset_id,decision_case_id,node_id,workflow_version,
         logistics_model_version_id,data_pack_version_id,graph_definition_version,case_policy_hash,node_policy_hash,
         contract_hash,input_context_hash,transit_model_version,runtime_profile,result_schema_version,engine_name,engine_version,
         schema_version,status{publication}) VALUES('{rid}','{w}','{c['dataset']}','{c['id']}','logistics_assignment',2,
         '{model}','{c['version']}','ULTIMATE_GRAPH_V1','{H}','{H}','{H}','{H}','DATION_TRANSIT_V1',
         'transport_plan_v1',1,'transport_plan','2.0.0','transport_plan_v1','{'completed' if complete else 'queued'}'{values});"""
        return rid,sql

    def artifact(self, *, state='PREPARED', workspace=None, bad_manifest=False):
        c=self.make_case(demand=True);rid=str(uuid4());aid=str(uuid4());w=workspace or c['workspace']
        descriptor=dict(artifact_id=aid,workspace_id=w,run_id=rid,kind='CORE',part_key='main',artifact_schema='engine_core_v1',
            schema_version=1,content_sha256=H,size_bytes=12,media_type='application/json',core_fingerprint='c'*64,assembler_version='RESULT_ASSEMBLER_V1')
        _,run=self.run_sql(c,run_id=rid,manifest=[] if bad_manifest else [descriptor])
        self.sql(run)
        fp='NULL' if state=='PREPARED' else "'"+'b'*64+"'"
        sql=f"""INSERT INTO decision_result_artifacts(id,workspace_id,run_id,kind,part_key,artifact_schema,schema_version,
         content_sha256,size_bytes,media_type,storage_bucket,storage_path,assembler_version,core_fingerprint,result_fingerprint,
         publication_state,producer_lease_token,producer_generation,producer_metadata)
         VALUES('{aid}','{w}','{rid}','CORE','main','engine_core_v1',1,'{H}',12,'application/json','dda-inputs',
          '{w}/runs/{rid}/core/main/{H}.json','RESULT_ASSEMBLER_V1','{'c'*64}',{fp},'{state}','{uuid4()}',1,'{{"engine":"transport_plan"}}');"""
        return c,rid,aid,sql

    def test_01_fresh_and_upgrade_catalog_match_without_rewriting_legacy(self):
        db=self.create_database(ultimate=False)
        try:
            w='00000000-0000-4000-8000-00000000da71';o,f,c,r=[str(uuid4()) for _ in range(4)]
            self.command(f"""INSERT INTO datasets(id,workspace_id,dataset_type,original_filename,storage_path)
             VALUES('{o}','{w}','orders','o.csv','{w}/{o}/o.csv'),('{f}','{w}','fleet','f.csv','{w}/{f}/f.csv');
             INSERT INTO decision_cases(id,workspace_id,orders_dataset_id,fleet_dataset_id,input_signature)
             VALUES('{c}','{w}','{o}','{f}','{o}:{f}');
             INSERT INTO decision_runs(id,workspace_id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,
              engine_name,engine_version,schema_version,status,result_json,approved_at,approved_by)
             VALUES('{r}','{w}','{o}','{o}','{f}','{c}','logistics_assignment','logistics-assignment-engine','1.0.0',
              'assignment_v1','completed','{{"schema_version":"assignment_v1","legacy_evidence":[1,2]}}',now(),'shared_workspace:dation');
             INSERT INTO decision_approval_events(workspace_id,run_id,case_id,node_id,action,actor)
              VALUES('{w}','{r}','{c}','logistics_assignment','approved','shared_workspace:dation');""",database=db)
            before=self.catalog(db)
            tables=['datasets','decision_cases','decision_runs','decision_approval_events','decision_interpretation_sources']
            originals={t:[row['column_name'] for row in before['columns'] if row['table_name']==t and row['table_schema']=='public'] for t in tables}
            def rows():
                return {t:json.loads(self.command('SELECT coalesce(jsonb_agg(to_jsonb(t)),\'[]\') FROM (SELECT '+','.join(originals[t])+' FROM public.'+t+' ORDER BY id) t;',database=db).stdout) for t in tables}
            old=rows();self.migrate(db,only_t2=True);after=self.catalog(db)
            self.assertEqual(rows(),old);self.assertEqual(after,self.catalog())
            self.assertEqual(before['defaults'],after['defaults'])
            (WORK/'post-t1-catalog.json').write_text(json.dumps(before,indent=2)+'\n')
            (WORK/'fresh-catalog.json').write_text(json.dumps(self.catalog(),indent=2)+'\n')
            (WORK/'upgrade-catalog.json').write_text(json.dumps(after,indent=2)+'\n')
            (WORK/'upgrade-preservation.json').write_text(json.dumps(dict(catalog_equal=True,legacy_rows_equal=True,
                default_acls_unchanged=True,tables=tables,rows=sum(map(len,old.values()))),indent=2)+'\n')
        finally:self.drop_database(db)

    def test_02_empty_case_initial_pack_is_atomic_and_legacy_pair_stays_required(self):
        ids,sql=self.case_sql();self.sql('BEGIN;'+sql+'COMMIT;')
        self.assertEqual(self.sql(f"SELECT orders_dataset_id IS NULL AND fleet_dataset_id IS NULL AND workflow_version=2 AND workflow_policy_version=1 FROM decision_cases WHERE id='{ids['id']}';"),'t')
        _,incomplete=self.case_sql()
        self.reject(incomplete.split('INSERT INTO case_data_packs')[0],'23514')
        self.reject(f"INSERT INTO decision_cases(workspace_id) VALUES('{self.wa}');",'23514')

    def test_03_model_version_fk_is_tenant_safe(self):
        self.reject(f"""INSERT INTO logistics_model_versions(workspace_id,model_id,version,graph_definition_version,config_schema_version,
         config_jsonb,contract_descriptor_jsonb,config_hash,contract_hash,contract_registry_version,published_by)
         VALUES('{self.wb}','{self.ma}',2,'ULTIMATE_GRAPH_V1','logistics_model_v1','{{}}','{{}}','{H}','{H}','V1','{USER_B}');""",'23503')

    def test_04_case_model_fk_is_tenant_safe(self):
        _,sql=self.case_sql(model=self.vb)
        self.reject('BEGIN;'+sql+'COMMIT;','23503')

    def test_05_pack_case_fk_is_tenant_safe(self):
        c=self.make_case()
        self.reject(f"INSERT INTO case_data_packs(workspace_id,case_id) VALUES('{self.wb}','{c['id']}');",'23503')

    def test_06_pack_version_and_current_pointer_cannot_cross_case(self):
        a=self.make_case();b=self.make_case()
        self.reject(f"UPDATE case_data_packs SET current_version_id='{b['version']}' WHERE id='{a['pack']}';",'23503')
        self.reject(f"UPDATE case_data_packs SET current_version_id=NULL WHERE id='{a['pack']}';",'23514')
        self.reject(f"""INSERT INTO case_data_pack_versions(workspace_id,case_id,pack_id,version,manifest_hash,contract_set_hash,created_by)
         VALUES('{self.wa}','{a['id']}','{b['pack']}',2,'{H}','{H}','{USER_A}');""",'23503')

    def test_07_entry_dataset_fk_rejects_cross_tenant(self):
        b=self.make_case(workspace=self.wb,model=self.vb,user=USER_B,demand=True)
        _,sql=self.case_sql(demand=True)
        prefix,entry=sql.split('INSERT INTO case_data_pack_entries',1)
        # Replace only the dataset UUID, retaining correct A version/Case ownership.
        original=re.search(r"INSERT INTO datasets\(.*?VALUES\('([^']+)'",prefix,re.S).group(1)
        entry=entry.replace(original,b['dataset'])
        self.reject('BEGIN;'+prefix+'INSERT INTO case_data_pack_entries'+entry+'COMMIT;','23503')

    def test_08_published_versions_and_entries_are_immutable(self):
        c=self.make_case(demand=True)
        for statement in [f"UPDATE logistics_model_versions SET config_hash='{'b'*64}' WHERE id='{self.va}';",
            f"DELETE FROM logistics_model_versions WHERE id='{self.va}';",
            f"UPDATE case_data_pack_versions SET manifest_hash='{'b'*64}' WHERE id='{c['version']}';",
            f"UPDATE case_data_pack_entries SET record_count=2 WHERE pack_version_id='{c['version']}';",
            "UPDATE dation_private.decision_definition_versions SET definition_jsonb='{}';"]:
            with self.subTest(statement=statement):self.reject(statement,'22023')
        self.reject(f"INSERT INTO case_data_pack_entries SELECT * FROM case_data_pack_entries WHERE pack_version_id='{c['version']}';",'22023')

    def test_09_case_binding_and_frozen_policy_cannot_be_rewritten(self):
        c=self.make_case()
        for change in ["workflow_version=1",f"logistics_model_version_id='{self.vb}'","planning_end='2026-11-09'",
                       "state_json='{\"nodes\":{}}'",f"case_policy_hash='{'b'*64}'"]:
            with self.subTest(change=change):self.reject(f"UPDATE decision_cases SET {change} WHERE id='{c['id']}';",'22023')
        self.sql(f"UPDATE decision_cases SET description='Metadata editable' WHERE id='{c['id']}';")

    def test_10_dataset_interpretation_is_required_immutable_and_dedup_is_versioned(self):
        c=self.make_case(demand=True);d=c['dataset']
        self.reject(f"UPDATE datasets SET data_contract_hash='{'b'*64}' WHERE id='{d}';",'22023')
        self.reject(f"INSERT INTO datasets(workspace_id,dataset_type,original_filename,storage_path) VALUES('{self.wa}','transport_resources','r.csv','{self.wa}/{uuid4()}/r.csv');",'23514','22023')
        def duplicate(contract):
            nd=str(uuid4())
            return f"""INSERT INTO datasets(id,workspace_id,dataset_type,original_filename,storage_path,sha256,schema_version,
              data_contract_id,data_contract_hash,normalizer_version,canonical_sha256)
             SELECT '{nd}',workspace_id,dataset_type,'clone.csv','{self.wa}/{nd}/clone.csv',sha256,schema_version,
              data_contract_id,'{contract}',normalizer_version,canonical_sha256 FROM datasets WHERE id='{d}';"""
        self.reject(duplicate(H),'23505');self.sql(duplicate('b'*64))
        self.assertIn("dataset_type = ANY (ARRAY['orders'::text, 'fleet'::text])",self.sql("SELECT indexdef FROM pg_indexes WHERE indexname='datasets_dispatch_hash_key';"))

    def test_11_run_pins_case_model_pack_and_is_immutable(self):
        c=self.make_case(demand=True);rid,sql=self.run_sql(c,complete=False);self.sql(sql)
        self.reject(f"UPDATE decision_runs SET data_pack_version_id='{uuid4()}' WHERE id='{rid}';",'22023')
        _,wrong=self.run_sql(c,model=self.vb,complete=False)
        self.reject(wrong,'23503')
        self.reject(f"UPDATE decision_runs SET workflow_version=1 WHERE id='{rid}';",'22023')

    def test_12_run_cannot_use_another_cases_pack_or_unpinned_primary_dataset(self):
        a=self.make_case(demand=True);b=self.make_case(demand=True)
        _,sql=self.run_sql(a,complete=False)
        self.reject(sql.replace(a['version'],b['version']),'22023','23503')
        self.reject(sql.replace(a['dataset'],b['dataset']),'22023')

    def test_13_prepared_metadata_does_not_mean_ready(self):
        c,rid,aid,sql=self.artifact();self.sql(sql)
        self.assertEqual(self.sql(f"SELECT publication_state||':'||(result_fingerprint IS NULL)::text FROM decision_result_artifacts WHERE id='{aid}';"),'PREPARED:true')
        self.reject(f"UPDATE decision_result_artifacts SET publication_state='READY' WHERE id='{aid}';",'23514')

    def test_14_ready_requires_exact_run_manifest_and_fingerprint(self):
        c,rid,aid,sql=self.artifact(state='READY',bad_manifest=True)
        self.reject(sql,'23514')
        c,rid,aid,sql=self.artifact(state='READY')
        self.reject(sql.replace("'"+'b'*64+"'","'"+'d'*64+"'"),'23503','23514')
        self.sql(sql)
        self.reject(f"UPDATE decision_result_artifacts SET size_bytes=13 WHERE id='{aid}';",'22023')
        self.reject(f"DELETE FROM decision_result_artifacts WHERE id='{aid}';",'22023')

    def test_15_artifact_tenant_path_schema_and_size_are_closed(self):
        c,rid,aid,sql=self.artifact(workspace=self.wb)
        self.reject(sql,'22023','23503')
        c,rid,aid,sql=self.artifact()
        for invalid in [sql.replace("'engine_core_v1'","'unknown_v9'"),sql.replace(',12,',',-1,'),
                        sql.replace('/runs/','/../'),sql.replace("'application/json'","'text/plain'")]:
            with self.subTest(invalid=invalid):self.reject(invalid,'23514')

    def test_16_legacy_null_provenance_remains_valid(self):
        # Old interpretation rows can remain wholly NULL; no v2 reinterpretation.
        catalog=self.catalog()
        columns=[x for x in catalog['columns'] if x['table_name']=='decision_interpretation_sources' and x['column_name'] in
                 {'provenance_version','result_fingerprint','decision_context_schema','decision_context_hash','mode','selected_entity','evidence_refs'}]
        self.assertEqual(len(columns),7);self.assertTrue(all(x['is_nullable']=='YES' for x in columns))
        o,f,c,r,ex=[str(uuid4()) for _ in range(5)]
        self.sql(f"""INSERT INTO datasets(id,workspace_id,dataset_type,original_filename,storage_path)
         VALUES('{o}','{self.wa}','orders','o.csv','{self.wa}/{o}/o.csv'),('{f}','{self.wa}','fleet','f.csv','{self.wa}/{f}/f.csv');
         INSERT INTO decision_cases(id,workspace_id,orders_dataset_id,fleet_dataset_id,input_signature)
         VALUES('{c}','{self.wa}','{o}','{f}','{o}:{f}');
         INSERT INTO decision_runs(id,workspace_id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,
          engine_name,engine_version,schema_version,status,result_json)
         VALUES('{r}','{self.wa}','{o}','{o}','{f}','{c}','logistics_assignment','logistics-assignment-engine','1.0.0',
          'assignment_v1','completed','{{"schema_version":"assignment_v1"}}');
         INSERT INTO decision_explanations(id,workspace_id,run_id,provider,model,knowledge_version,prompt_version,response_json)
          VALUES('{ex}','{self.wa}','{r}','fixture','fixture','v1','v1','{{}}');
         INSERT INTO decision_interpretation_sources(workspace_id,run_id,explanation_id) VALUES('{self.wa}','{r}','{ex}');""")
        self.assertEqual(self.sql(f"SELECT provenance_version IS NULL AND result_fingerprint IS NULL AND evidence_refs IS NULL FROM decision_interpretation_sources WHERE explanation_id='{ex}';"),'t')

    def test_17_provenance_uses_same_run_fingerprint_and_ready_artifact(self):
        c,rid,aid,sql=self.artifact(state='READY');self.sql(sql);ex=str(uuid4())
        self.sql(f"INSERT INTO decision_explanations(id,workspace_id,run_id,provider,model,knowledge_version,prompt_version,response_json) VALUES('{ex}','{self.wa}','{rid}','fixture','fixture','v1','v1','{{}}');")
        base=f"""INSERT INTO decision_interpretation_sources(workspace_id,run_id,explanation_id,provenance_version,
         result_fingerprint,decision_context_schema,decision_context_hash,mode,selected_entity,evidence_refs)
         VALUES('{self.wa}','{rid}','{ex}',2,'{'b'*64}','decision_context_v1','{H}','REVIEW',
          '{{"type":"TRIP","id":"VIA-001"}}','[{{"artifact_id":"{aid}","content_sha256":"{H}"}}]');"""
        self.reject(base.replace("'REVIEW'","'OPTIMIZE'"),'23514')
        self.reject(base.replace(aid,str(uuid4())),'22023')
        self.reject(base.replace("'"+'b'*64+"'","'"+'d'*64+"'"),'22023','23503')
        self.sql(base)
        self.reject(f"UPDATE decision_interpretation_sources SET decision_context_hash='{'b'*64}' WHERE explanation_id='{ex}';",'22023')

    def test_18_rls_membership_read_positives_and_negatives(self):
        for uid,count in [(USER_A,1),(USER_B,0),(VIEWER,1),(DISABLED,0)]:
            with self.subTest(uid=uid):
                self.assertEqual(self.sql(f"SET ROLE authenticated; SET request.jwt.claims='{json.dumps({'sub':uid})}'; SELECT count(*) FROM logistics_models WHERE id='{self.ma}';"),str(count))
        self.assertEqual(self.sql("SET ROLE service_role; SELECT count(*)>0 FROM logistics_models;"),'t')

    def test_19_no_client_or_service_direct_writes_and_private_registry_is_release_only(self):
        for role in ['anon','authenticated','service_role']:
            with self.subTest(role=role):
                self.reject(f"SET ROLE {role}; INSERT INTO logistics_models(workspace_id,name,created_by) VALUES('{self.wa}','Denied','{USER_A}');",'42501')
                self.reject(f"SET ROLE {role}; SELECT * FROM dation_private.decision_definition_versions;",'42501')
        self.reject('SET ROLE authenticated; SELECT * FROM decision_result_artifacts;','42501')
        self.reject('SET ROLE anon; SELECT * FROM logistics_models;','42501')

    def test_20_no_public_grants_new_functions_or_tables_and_defaults_preserved(self):
        c=self.catalog();new=[r for r in c['relations'] if r['name'] in {'logistics_models','logistics_model_versions',
          'case_data_packs','case_data_pack_versions','case_data_pack_entries','decision_result_artifacts','decision_definition_versions'}]
        self.assertEqual(len(new),7);self.assertTrue(all(r['relrowsecurity'] and r['relforcerowsecurity'] for r in new))
        for row in new:self.assertIsNone(re.search(r'(?:\{|,)=',row['acl'] or ''))
        funcs=[r for r in c['functions'] if r['name'].startswith('ultimate_')]
        self.assertTrue(funcs)
        for f in funcs:
            self.assertFalse(f['prosecdef']);self.assertEqual(f['proconfig'],['search_path=pg_catalog'])
            self.assertIsNone(re.search(r'(?:\{|,)=',f['acl'] or ''))
        self.assertEqual(len(c['defaults']),6)

    def test_21_empty_case_home_center_and_legacy_case_list_are_read_only(self):
        c=self.make_case();stamp=self.sql(f"SELECT updated_at FROM decision_cases WHERE id='{c['id']}';")
        data=json.loads(self.sql(f"SELECT platform_home('{self.wa}','{USER_A}');"))
        self.assertIn(c['id'],[b['case']['id'] for b in data['recent_cases']])
        item=next(b for b in data['recent_cases'] if b['case']['id']==c['id'])
        self.assertEqual(item['case']['workflow_version'],2)
        detail=json.loads(self.sql(f"SELECT platform_decision_center('{self.wa}','{USER_A}',target_case_id=>'{c['id']}');"))
        self.assertIsNone(detail['orders']);self.assertIsNone(detail['fleet'])
        rows=json.loads(self.sql(f"SET dation.workspace_id='{self.wa}'; SELECT jsonb_agg(to_jsonb(x)) FROM dation_private.list_decision_cases(NULL,100,0,true) x;"))
        self.assertIn(c['id'],[r['case_row']['id'] for r in rows])
        self.assertIsNone(next(r for r in rows if r['case_row']['id']==c['id'])['orders'])
        self.assertEqual(self.sql(f"SELECT updated_at FROM decision_cases WHERE id='{c['id']}';"),stamp)
        self.reject(f"SELECT platform_decision_center('{self.wa}','{USER_B}',target_case_id=>'{c['id']}');",'42501')

    def test_22_data_hub_tracks_pack_usage_and_prevents_object_deletion(self):
        c=self.make_case(demand=True)
        self.assertEqual(self.sql(f"SELECT dation_private.dataset_referenced('{self.wa}','{c['dataset']}');"),'t')
        detail=json.loads(self.sql(f"SELECT platform_dataset_library('{self.wa}','{USER_A}',target_dataset_id=>'{c['dataset']}');"))
        self.assertEqual(detail['case_total'],1);self.assertFalse(detail['can_delete'])
        self.assertEqual(detail['used_in'][0]['id'],c['id'])
        self.reject(f"DELETE FROM datasets WHERE id='{c['dataset']}';",'23503')

    def test_23_catalog_has_composite_fks_for_all_required_edges(self):
        fks=[x for x in self.catalog()['constraints'] if x['contype']=='f']
        expected={'ultimate_case_model','ultimate_pack_current_version','ultimate_run_model','ultimate_run_pack',
            'ultimate_artifact_published_run','ultimate_interpretation_result'}
        self.assertTrue(expected<={x['name'] for x in fks})
        for name in expected:
            self.assertIn('FOREIGN KEY (workspace_id,',next(x['definition'] for x in fks if x['name']==name))
        ready=next(x for x in fks if x['name']=='ultimate_artifact_published_run')
        self.assertTrue(ready['condeferrable'] and ready['condeferred'])
        (WORK/'fk-constraint-matrix.json').write_text(json.dumps(fks,indent=2)+'\n')

    def test_24_terminal_publication_metadata_and_history_cannot_be_rewritten(self):
        c=self.make_case(demand=True);rid,sql=self.run_sql(c);self.sql(sql)
        self.reject(f"UPDATE decision_runs SET artifact_manifest_hash='{'b'*64}' WHERE id='{rid}';",'22023')
        self.reject(f"UPDATE decision_runs SET result_json='{{}}' WHERE id='{rid}';",'22023')
        self.reject(f"DELETE FROM decision_cases WHERE id='{c['id']}';",'23503')

    def test_25_entry_version_fk_cannot_cross_case(self):
        other=self.make_case();c,sql=self.case_sql(demand=True)
        prefix,entry=sql.split('INSERT INTO case_data_pack_entries',1)
        entry=entry.replace(c['id'],other['id'])
        self.reject('BEGIN;'+prefix+'INSERT INTO case_data_pack_entries'+entry+'COMMIT;','23503')

    def test_26_prepared_to_ready_binding_can_commit_without_rewriting_identity(self):
        c,rid,aid,sql=self.artifact();self.sql(sql)
        self.reject(f"UPDATE decision_result_artifacts SET size_bytes=999 WHERE id='{aid}';",'22023')
        self.sql(f"UPDATE decision_result_artifacts SET publication_state='READY',result_fingerprint='{'b'*64}' WHERE id='{aid}';")
        self.assertEqual(self.sql(f"SELECT publication_state FROM decision_result_artifacts WHERE id='{aid}';"),'READY')


if __name__=='__main__':unittest.main()
