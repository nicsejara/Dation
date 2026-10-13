"""Real SQL admission, fencing, evidence provenance and business-state isolation."""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import unittest
from uuid import uuid4
from sql_support import SQLSandbox


def literal(value):
    return "'"+json.dumps(value).replace("'","''")+"'::jsonb"


@unittest.skipUnless(os.getenv('DATION_SQL_TEST_CONTAINER'),'Owned PostgreSQL container required')
class ProgressiveSQLTests(SQLSandbox,unittest.TestCase):
    def setUp(self):
        self.command('TRUNCATE datasets,decision_cases,decision_runs CASCADE;')
        fixture=json.loads((Path(__file__).parents[1]/'browser/fixtures.json').read_text())
        self.base=fixture['runs']['assignment'];self.rid=str(uuid4());self.cid=str(uuid4())
        self.result=copy.deepcopy(self.base['result_json'])
        self.result['configuration']['options']['analysis_depth']='essential'
        self.result['analysis']['depth']='essential'
        self.request={'base_run_id':self.rid,'engine_name':self.base['engine_name'],
            'engine_version':self.base['engine_version'],'schema_version':'assignment_v1',
            'configuration':{k:v for k,v in self.result['configuration'].items() if k!='options'},
            'options':{**self.result['configuration']['options'],'analysis_depth':'comparative'}}
        orders,fleet=str(uuid4()),str(uuid4())
        self.command(f"INSERT INTO datasets(id,dataset_type,original_filename,storage_path) VALUES('{orders}','orders','orders.csv','qa/orders.csv'),('{fleet}','fleet','fleet.csv','qa/fleet.csv');"
            f"INSERT INTO decision_cases(id,orders_dataset_id,fleet_dataset_id,input_signature,state_json) VALUES('{self.cid}','{orders}','{fleet}','{orders}:{fleet}','{{}}');"
            f"INSERT INTO decision_runs(id,status,decision_case_id,node_id,dataset_id,orders_dataset_id,fleet_dataset_id,engine_name,engine_version,schema_version,result_json,result_fingerprint,approved_at) "
            f"VALUES('{self.rid}','completed','{self.cid}','logistics_assignment','{orders}','{orders}','{fleet}','{self.base['engine_name']}','{self.base['engine_version']}',"
            f"'assignment_v1',{literal(self.result)},'base-fingerprint',now());")

    def sql(self,text):return self.command(text).stdout.strip()
    def enqueue(self,existing=False,retry=False):
        text=f"SELECT row_to_json(a) FROM enqueue_comparative_analysis('{self.rid}',{literal(self.request)},{literal(self.result) if existing else 'NULL'},{str(retry).lower()}) a;"
        return json.loads(self.sql(text))
    def claim(self):
        text=self.sql(f"SELECT row_to_json(a) FROM claim_comparative_analysis('{uuid4()}') a;")
        return json.loads(text) if text else None
    def derived(self):
        result=copy.deepcopy(self.result);result['configuration']['options']['analysis_depth']='comparative'
        result['analysis']['depth']='comparative';return result
    def finish(self,job,result=None,status='completed',check=True):
        values={'status':status,'result_json':result or self.derived(),'result_fingerprint':'derived-fp','duration_ms':12,'error_message':'test failure' if status=='error' else None}
        return self.command(f"SELECT id FROM finish_comparative_analysis('{job['id']}','{job['lease_token']}',{literal(values)});",check=check)
    def business(self):
        return self.sql("SELECT jsonb_build_object('runs',(SELECT jsonb_agg(to_jsonb(r) ORDER BY id) FROM decision_runs r),"
            "'cases',(SELECT jsonb_agg(to_jsonb(c) ORDER BY id) FROM decision_cases c),"
            "'approvals',(SELECT jsonb_agg(to_jsonb(e) ORDER BY id) FROM decision_approval_events e),"
            "'outbox',(SELECT jsonb_agg(to_jsonb(q) ORDER BY case_id) FROM decision_case_reconciliations q));")

    def test_concurrent_admission_is_one_artifact_and_no_business_write(self):
        before=self.business()
        with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda _:self.enqueue(),range(4)))
        self.assertEqual(len({r['id'] for r in rows}),1);self.assertEqual(rows[0]['status'],'queued')
        job=self.claim();self.finish(job)
        self.assertEqual(self.enqueue()['id'],job['id']);self.assertEqual(self.business(),before)

    def test_reuse_is_completed_without_worker_and_completed_artifact_is_immutable(self):
        before=self.business();row=self.enqueue(existing=True)
        self.assertEqual(row['status'],'completed');self.assertEqual(row['source_mode'],'existing')
        self.assertEqual(row['result_json'],self.result);self.assertIsNone(self.claim())
        failure=self.command("UPDATE decision_comparative_analyses SET result_fingerprint='changed';",check=False)
        self.assertNotEqual(failure.returncode,0);self.assertEqual(self.business(),before)

    def test_invalid_intention_and_unfinished_base_cannot_enter_queue(self):
        self.request['configuration']['objective']='different'
        with self.assertRaises(AssertionError):self.enqueue()
        self.request['configuration']=self.result['configuration'].copy();self.request['configuration'].pop('options')
        self.command('TRUNCATE datasets,decision_cases,decision_runs CASCADE;')
        self.command(f"INSERT INTO datasets(id,dataset_type,original_filename,storage_path) VALUES('{self.rid}','orders','qa.csv','qa');"
            f"INSERT INTO decision_runs(id,dataset_id,status,engine_name,engine_version,schema_version) VALUES('{self.rid}','{self.rid}','running','assignment','1','assignment_v1');")
        with self.assertRaises(AssertionError):self.enqueue()
        self.assertEqual(self.sql('SELECT count(*) FROM decision_comparative_analyses;'),'0')

    def test_restart_fences_old_worker_and_heartbeat_cannot_revive_it(self):
        self.enqueue();first=self.claim()
        self.command("UPDATE decision_comparative_analyses SET lease_expires_at=now()-interval '1 second';")
        self.assertEqual(self.sql(f"SELECT heartbeat_comparative_analysis('{first['id']}','{first['lease_token']}');"),'f')
        second=self.claim();self.assertEqual(first['id'],second['id']);self.assertEqual(second['attempts'],2)
        self.assertEqual(self.finish(first).stdout.strip(),'');self.assertEqual(self.finish(second).stdout.strip(),first['id'])

    def test_exhaustion_deadline_and_explicit_retry_keep_same_identity(self):
        artifact=self.enqueue();job=self.claim()
        self.command("UPDATE decision_comparative_analyses SET attempts=max_attempts,lease_expires_at=now()-interval '1 second';")
        self.assertIsNone(self.claim());failed=self.enqueue();self.assertEqual(failed['status'],'error')
        retried=self.enqueue(retry=True);self.assertEqual(retried['id'],artifact['id']);self.assertEqual(retried['generation'],2)
        self.assertIsNone(retried['error_message']);self.assertEqual(retried['attempts'],0)
        self.command("UPDATE decision_comparative_analyses SET deadline_at=now()-interval '1 second';")
        self.assertIsNone(self.claim());self.assertEqual(self.enqueue()['status'],'error')

    def test_finish_rejects_changed_selection_business_configuration_or_options(self):
        self.enqueue();job=self.claim()
        for kind in ('selected','configuration','options','inputs','schema'):
            derived=self.derived()
            if kind=='selected':derived['scenarios']['selected']['name']='other'
            elif kind=='configuration':derived['configuration']['objective']='other'
            elif kind=='options':derived['configuration']['options']['total_time_limit_s']=99
            elif kind=='inputs':derived['inputs']={}
            else:derived['schema_version']='scheduling_v1'
            self.assertNotEqual(self.finish(job,derived,check=False).returncode,0,kind)
        self.assertEqual(self.finish(job).stdout.strip(),job['id'])

    def test_private_roles_and_least_privilege(self):
        for role in ('anon','authenticated'):
            for sql in ('SELECT * FROM decision_comparative_analyses','SELECT * FROM decision_interpretation_sources',
                        f"SELECT * FROM claim_comparative_analysis('{uuid4()}')"):
                self.assertNotEqual(self.command('SET ROLE '+role+';'+sql+';',check=False).returncode,0)
        self.assertNotEqual(self.command('SET ROLE service_role;DELETE FROM decision_comparative_analyses;',check=False).returncode,0)

    def explain(self,evidence=None):
        identifier=str(uuid4());payload={'id':identifier,'run_id':self.rid,'provider':'qa','model':'qa','knowledge_version':'qa','prompt_version':'qa','response_json':{'summary':'test'}}
        self.command(f"SELECT id FROM record_decision_explanation_with_evidence({literal(payload)},{repr(evidence) if evidence else 'NULL'});")
        return identifier

    def test_explanation_scope_prefers_enriched_evidence_over_late_original(self):
        original=self.explain();self.enqueue();job=self.claim();self.finish(job)
        self.assertEqual(self.sql(f"SELECT id FROM current_decision_explanation('{self.rid}');"),original)
        enriched=self.explain(job['id']);self.explain()
        self.assertEqual(self.sql(f"SELECT id FROM current_decision_explanation('{self.rid}');"),enriched)

    def test_chat_provenance_is_atomic_and_idempotent(self):
        self.enqueue();job=self.claim();self.finish(job);turn=str(uuid4())
        metadata={'provider':'qa','model':'qa','knowledge_version':'qa','prompt_version':'qa'}
        text=f"SELECT record_decision_chat_turn_with_evidence('{turn}','{self.rid}','{'1'*64}','question','answer',{literal(metadata)},'{job['id']}');"
        first=json.loads(self.sql(text));second=json.loads(self.sql(text))
        self.assertEqual(first,second);self.assertEqual(first['evidence_analysis_id'],job['id'])
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages;'),'2')
        bad=text.replace(turn,str(uuid4())).replace(job['id'],str(uuid4()))
        self.assertNotEqual(self.command(bad,check=False).returncode,0)
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages;'),'2')

    def test_catalog_install_is_idempotent_and_rejects_drift(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
        import apply_production_comparative as installer
        from unittest.mock import patch
        def query(sql):
            output=self.command(sql).stdout.strip().splitlines()
            return [{'catalog':json.loads(line)} for line in output if line.startswith('{')]
        with patch.object(installer,'query',query):installer.main();installer.main()
        self.command('REVOKE EXECUTE ON FUNCTION claim_comparative_analysis(uuid,integer) FROM service_role;')
        with patch.object(installer,'query',query),self.assertRaisesRegex(RuntimeError,'drift'):installer.main()
