"""Operational reads and atomic chat audit on the real private schema."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import unittest
from uuid import uuid4
from sql_support import SQLSandbox,CONTAINER


@unittest.skipUnless(CONTAINER,'Requires disposable PostgreSQL 17')
class ObservabilitySQLTests(SQLSandbox,unittest.TestCase):
    def sql(self,sql):return self.command(sql).stdout.strip()

    def setUp(self):
        self.run=str(uuid4());self.turn=str(uuid4());self.worker=str(uuid4());self.intent=hashlib.sha256(b'Why?').hexdigest()
        self.sql('TRUNCATE datasets,decision_runs,decision_cases,dispatch_worker_instances CASCADE;')
        dataset=str(uuid4())
        self.sql(f"INSERT INTO datasets(id,original_filename,storage_path) VALUES('{dataset}','qa.csv','qa');"
                 f"INSERT INTO decision_runs(id,dataset_id,engine_name,engine_version,status,duration_ms,result_json) VALUES"
                 f"('{self.run}','{dataset}','qa','1','completed',2500,'{{}}');")

    def record(self,turn=None,question='Why?',answer='Answer',metadata=None,check=True,intent=None):
        metadata=metadata or {'provider':'qa','model':'fake','knowledge_version':'v1','prompt_version':'v3',
                             'usage':{'total_tokens':9,'prompt_tokens':5,'completion_tokens':4,'secret':'private'}}
        def literal(value):return "'"+str(value).replace("'","''")+"'"
        sql='SELECT record_decision_chat_turn('+','.join(map(literal,[turn or self.turn,self.run,intent or self.intent,question,answer,json.dumps(metadata)]))+');'
        return self.command(sql,check=check)

    def test_turn_commits_both_messages_and_sanitized_audit_metadata(self):
        saved=json.loads(self.record().stdout.strip())
        self.assertEqual(saved['answer'],'Answer');self.assertEqual(saved['usage'],{'total_tokens':9,'prompt_tokens':5,'completion_tokens':4})
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages;'),'2')
        self.assertEqual(self.sql('SELECT count(*) FROM decision_chat_turns;'),'1')
        self.assertEqual(self.sql("SELECT string_agg(role,',' ORDER BY created_at) FROM decision_messages;"),'user,assistant')
        self.assertEqual(self.sql('SELECT count(DISTINCT turn_id) FROM decision_messages;'),'1')

    def test_replay_returns_first_answer_and_conflict_does_not_duplicate(self):
        self.record();saved=json.loads(self.record(answer='Different answer').stdout.strip())
        self.assertEqual(saved['answer'],'Answer')
        self.assertNotEqual(self.record(intent='b'*64,check=False).returncode,0)
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages;'),'2')

    def test_concurrent_same_turn_commits_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:self.record(),range(2)))
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages;'),'2')
        self.assertEqual(self.sql('SELECT count(*) FROM decision_chat_turns;'),'1')

    def test_failed_validation_and_message_insert_roll_back_entire_turn(self):
        self.assertNotEqual(self.record(answer='',check=False).returncode,0)
        self.sql("CREATE FUNCTION qa_reject() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF new.role='assistant' THEN RAISE EXCEPTION 'synthetic failure'; END IF; RETURN new; END $$;"
                 "CREATE TRIGGER qa_reject BEFORE INSERT ON decision_messages FOR EACH ROW EXECUTE FUNCTION qa_reject();")
        try:self.assertNotEqual(self.record(check=False).returncode,0)
        finally:self.sql('DROP TRIGGER qa_reject ON decision_messages;DROP FUNCTION qa_reject();')
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages;'),'0')
        self.assertEqual(self.sql('SELECT count(*) FROM decision_chat_turns;'),'0')

    def test_historical_message_remains_unattributed_and_completed_run_required(self):
        self.sql(f"INSERT INTO decision_messages(run_id,role,content) VALUES('{self.run}','user','Historical');")
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages WHERE turn_id IS NULL;'),'1')
        dataset=self.sql(f"SELECT dataset_id FROM decision_runs WHERE id='{self.run}';")
        self.run=str(uuid4())
        self.sql(f"INSERT INTO decision_runs(id,dataset_id,engine_name,engine_version,status) VALUES('{self.run}','{dataset}','qa','1','queued');")
        self.assertNotEqual(self.record(check=False).returncode,0)
        self.assertEqual(self.sql('SELECT count(*) FROM decision_messages;'),'1')

    def test_snapshot_is_read_only_has_actual_percentile_and_fresh_worker_counts(self):
        self.sql(f"SELECT report_dispatch_worker('{self.worker}','qa-worker-1',true);")
        snapshot=json.loads(self.sql('BEGIN READ ONLY; SELECT dispatch_operational_snapshot(); COMMIT;').splitlines()[1])
        self.assertEqual(snapshot['workers']['healthy'],1)
        self.assertEqual(snapshot['runs_24h']['duration_p95_ms'],2500)
        self.assertEqual(snapshot['runs_24h']['completed'],1)
        self.assertNotIn(self.run,json.dumps(snapshot));self.assertNotIn(self.worker,json.dumps(snapshot))
        self.sql("UPDATE dispatch_worker_instances SET seen_at=now()-interval '91 seconds';")
        self.assertEqual(json.loads(self.sql('SELECT dispatch_operational_snapshot();'))['workers']['healthy'],0)

    def test_worker_shutdown_and_old_registry_cleanup(self):
        self.sql(f"SELECT report_dispatch_worker('{self.worker}','qa-worker-1',true);")
        self.sql("UPDATE dispatch_worker_instances SET seen_at=now()-interval '25 hours';")
        self.sql(f"SELECT report_dispatch_worker('{uuid4()}','qa-worker-2',false);")
        snapshot=json.loads(self.sql('SELECT dispatch_operational_snapshot();'))
        self.assertEqual(snapshot['workers'],{'healthy':0,'reporting':1})
        self.assertEqual(self.sql('SELECT count(*) FROM dispatch_worker_instances;'),'1')

    def test_catalog_matches_reviewed_manifest_and_detects_definition_drift(self):
        import sys
        from sql_support import REPO
        sys.path.insert(0,str(REPO/'scripts'))
        from apply_production_observability import CATALOG_SQL,MANIFEST
        expected=json.loads(MANIFEST.read_text())
        self.assertEqual(json.loads(self.sql(CATALOG_SQL)),expected)
        self.sql('ALTER FUNCTION report_dispatch_worker(uuid,text,boolean) SECURITY DEFINER;')
        try:self.assertNotEqual(json.loads(self.sql(CATALOG_SQL)),expected)
        finally:self.sql('ALTER FUNCTION report_dispatch_worker(uuid,text,boolean) SECURITY INVOKER;')

    def test_private_roles_cannot_read_or_invoke_operations_and_chat(self):
        for role in ['anon','authenticated']:
            for call in ['SELECT * FROM dispatch_worker_instances','SELECT * FROM decision_chat_turns',
                         'SELECT dispatch_operational_snapshot()',f"SELECT report_dispatch_worker('{self.worker}','qa',true)",
                         f"SELECT read_decision_chat_turn('{self.turn}','{self.run}','{self.intent}')"]:
                result=self.command('SET ROLE '+role+';'+call+';',check=False)
                self.assertNotEqual(result.returncode,0);self.assertIn('permission denied',result.stderr)
        self.assertEqual(self.sql('SET ROLE service_role;SELECT (dispatch_operational_snapshot()->\'workers\'->>\'healthy\');').splitlines()[-1],'0')
