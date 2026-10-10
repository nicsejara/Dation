"""Real catalog baseline, >1,000 runs, approval races and immutable evidence."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import unittest
from uuid import uuid4
from sql_support import SQLSandbox, CONTAINER, REPO, BASELINE

sys.path.insert(0,str(REPO/'scripts'))
from capture_public_schema import SQL as CATALOG_SQL

CASE='00000000-0000-4000-8000-000000000003'
ORDERS='00000000-0000-4000-8000-000000000001'
FLEET='00000000-0000-4000-8000-000000000002'


def normalize(value):
    if isinstance(value,dict):
        return {k:normalize(v) for k,v in value.items() if k!='server_version_num'}
    if isinstance(value,list):
        return sorted((normalize(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
    return value


@unittest.skipUnless(CONTAINER,'Requires disposable PostgreSQL 17')
class PersistenceSQLTests(SQLSandbox,unittest.TestCase):
    def sql(self,sql): return self.command(sql).stdout.strip()

    def setUp(self):
        self.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events CASCADE;')
        self.sql(f"INSERT INTO datasets(id,dataset_type,original_filename,storage_path) VALUES ('{ORDERS}','orders','orders.csv','qa/orders.csv'),('{FLEET}','fleet','fleet.csv','qa/fleet.csv');"
                 f"INSERT INTO decision_cases(id,orders_dataset_id,fleet_dataset_id,input_signature) VALUES ('{CASE}','{ORDERS}','{FLEET}','{ORDERS}:{FLEET}');")

    def candidate(self,rid=None,node='logistics_assignment',upstream=None,created=None):
        rid=rid or str(uuid4())
        config={'decision_case':{'case_id':CASE,'node_id':node,'status':'review'}}
        result={'schema_version':'assignment_v1' if node.endswith('assignment') else 'scheduling_v1',
                'decision_case':config['decision_case'],'evidence':{'unchanged':True}}
        source="NULL" if upstream is None else "'"+upstream+"'"
        timestamp='now()' if created is None else "'"+created+"'::timestamptz"
        sql=f"""INSERT INTO decision_runs(id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,
          upstream_run_id,engine_name,engine_version,schema_version,status,configuration_json,result_json,created_at)
          VALUES('{rid}','{ORDERS}','{ORDERS}','{FLEET}','{CASE}','{node}',{source},'engine','1',
          '{result['schema_version']}','completed','{json.dumps(config)}','{json.dumps(result)}',{timestamp});"""
        self.sql(sql)
        return rid

    def approve(self,rid,node='logistics_assignment',check=True):
        return self.command(f"SET ROLE service_role; SELECT id FROM approve_decision_run_version('{rid}','{CASE}','{node}');",check=check)

    def snapshot(self,node='logistics_assignment',limit=50,offset=0):
        return json.loads(self.sql(f"BEGIN READ ONLY; SELECT decision_case_history('{CASE}','{node}',{limit},{offset}); COMMIT;").splitlines()[1])

    def test_history_counts_and_approval_survive_beyond_1000_and_tied_dates(self):
        old=self.candidate(created='2020-01-01');self.approve(old)
        self.sql(f"""INSERT INTO decision_runs(id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,
          engine_name,engine_version,schema_version,status,result_json,created_at)
          SELECT ('00000001-0000-4000-8000-'||lpad(i::text,12,'0'))::uuid,'{ORDERS}','{ORDERS}','{FLEET}','{CASE}',
            'logistics_assignment','engine','1','assignment_v1','completed','{{"schema_version":"assignment_v1"}}','2026-10-10'
          FROM generate_series(1,1005) i;""")
        first=self.snapshot();tail=self.snapshot(offset=1000)
        self.assertEqual(first['summaries']['logistics_assignment']['run_count'],1006)
        self.assertEqual(tail['summaries']['logistics_assignment']['approved']['id'],old)
        self.assertEqual(len(tail['runs']),6)
        self.assertEqual(tail['runs'][-1]['id'],old)
        self.assertNotIn('result_json',first['runs'][0])
        self.assertEqual(first['runs'][0]['id'],'00000001-0000-4000-8000-000000001005')
        second=self.snapshot(offset=50)
        self.assertFalse({r['id'] for r in first['runs']} & {r['id'] for r in second['runs']})
        self.assertEqual(self.snapshot(offset=5000)['runs'],[])

    def test_node_page_preserves_upstream_summary(self):
        assignment=self.candidate();self.approve(assignment)
        scheduling=self.candidate(node='logistics_scheduling',upstream=assignment)
        snapshot=self.snapshot('logistics_scheduling')
        self.assertEqual(snapshot['summaries']['logistics_assignment']['approved']['id'],assignment)
        self.assertEqual([r['id'] for r in snapshot['runs']],[scheduling])

    def test_concurrent_approvals_are_serialized_and_audited(self):
        a,b=self.candidate(),self.candidate()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda rid:self.approve(rid),[a,b]))
        self.assertTrue(all(r.returncode==0 for r in outcomes))
        self.assertEqual(self.sql("SELECT count(*) FROM decision_runs WHERE approved_at IS NOT NULL AND superseded_at IS NULL;"),'1')
        self.assertEqual(self.sql('SELECT count(*) FROM decision_approval_events;'),'3')
        self.assertEqual(self.sql("SELECT count(*) FROM decision_runs WHERE approved_by='shared_workspace:dation';"),'2')
        self.assertEqual(self.sql("SELECT count(*) FROM decision_approval_events WHERE action='superseded' AND replacement_run_id IS NOT NULL;"),'1')

    def test_retry_preserves_approval_and_previous_cannot_resurrect(self):
        a,b=self.candidate(),self.candidate();self.approve(a)
        before=self.sql(f"SELECT approved_at::text FROM decision_runs WHERE id='{a}';")
        self.approve(a)
        self.assertEqual(self.sql(f"SELECT approved_at::text FROM decision_runs WHERE id='{a}';"),before)
        self.assertEqual(self.sql('SELECT count(*) FROM decision_approval_events;'),'1')
        self.approve(b)
        failure=self.approve(a,check=False)
        self.assertNotEqual(failure.returncode,0)
        self.assertIn('no puede reactivarse',failure.stderr)
        self.assertEqual(self.sql('SELECT count(*) FROM decision_approval_events;'),'3')

    def test_old_upstream_cannot_admit_or_approve_new_children(self):
        a,b=self.candidate(),self.candidate();self.approve(a)
        child=self.candidate(node='logistics_scheduling',upstream=a)
        self.approve(b)
        self.assertNotEqual(self.approve(child,'logistics_scheduling',check=False).returncode,0)
        with self.assertRaisesRegex(AssertionError,'upstream'):
            self.candidate(node='logistics_scheduling',upstream=a)

    def test_parent_child_race_never_accepts_stale_approval(self):
        a,b=self.candidate(),self.candidate();self.approve(a)
        child=self.candidate(node='logistics_scheduling',upstream=a)
        # Ensure the parent replacement wins the case lock while the child request is waiting.
        name='dation_parent_'+uuid4().hex
        with ThreadPoolExecutor(max_workers=2) as pool:
            replacement=pool.submit(self.command,f"SET application_name='{name}'; BEGIN; SELECT id FROM decision_cases WHERE id='{CASE}' FOR UPDATE; SELECT pg_sleep(2); SELECT id FROM approve_decision_run_version('{b}','{CASE}','logistics_assignment'); COMMIT;")
            for _ in range(30):
                if self.sql(f"SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='{name}' AND wait_event='PgSleep');")=='t':
                    break
                time.sleep(.01)
            else:self.fail('Parent did not acquire the case lock')
            child_result=pool.submit(self.approve,child,'logistics_scheduling',False)
            self.assertEqual(replacement.result().returncode,0)
            self.assertNotEqual(child_result.result().returncode,0)

    def test_admitted_child_can_finish_after_parent_replacement(self):
        a,b=self.candidate(),self.candidate();self.approve(a)
        child=str(uuid4());token=str(uuid4())
        config={'decision_case':{'case_id':CASE,'node_id':'logistics_scheduling'},'source_assignment_run_id':a}
        payload={'id':child,'dataset_id':ORDERS,'orders_dataset_id':ORDERS,'fleet_dataset_id':FLEET,
                 'decision_case_id':CASE,'node_id':'logistics_scheduling','upstream_run_id':a,
                 'configuration_json':config,'engine_name':'engine','engine_version':'1','schema_version':'scheduling_v1'}
        self.sql(f"SELECT id FROM enqueue_dispatch_run('{json.dumps(payload)}','{{}}','intent'); SELECT run_id FROM claim_dispatch_job('{token}');")
        self.approve(b)
        values={'status':'completed','result_json':{'schema_version':'scheduling_v1','decision_case':config['decision_case']}}
        self.assertEqual(self.sql(f"SELECT id FROM finish_dispatch_job('{child}','{token}','{json.dumps(values)}');"),child)
        self.assertNotEqual(self.approve(child,'logistics_scheduling',False).returncode,0)

    def test_identity_result_and_event_mutation_are_rejected(self):
        rid=self.candidate();self.approve(rid)
        for sql in [f"UPDATE datasets SET storage_path='changed' WHERE id='{ORDERS}';",
                    "UPDATE decision_cases SET input_signature='changed';",
                    f"UPDATE decision_runs SET configuration_json='{{}}' WHERE id='{rid}';",
                    f"UPDATE decision_runs SET result_json='{{}}' WHERE id='{rid}';",
                    f"UPDATE decision_runs SET approved_by='person' WHERE id='{rid}';",
                    "UPDATE decision_approval_events SET actor='person';",
                    "DELETE FROM decision_approval_events;"]:
            with self.subTest(sql=sql):self.assertNotEqual(self.command(sql,check=False).returncode,0)
        # Presentation/profile/default/archive remain editable without changing source evidence.
        self.sql(f"UPDATE datasets SET label='Editable',archived_at=now(),profile_json='{{}}' WHERE id='{ORDERS}';")
        self.assertEqual(self.sql('SELECT count(*) FROM decision_approval_events;'),'1')

    def test_untrusted_roles_cannot_read_private_data_or_call_rpc(self):
        for role in ['anon','authenticated']:
            with self.subTest(role=role):
                result=self.command(f"SET ROLE {role}; SELECT count(*) FROM decision_runs;",check=False)
                self.assertTrue(result.returncode or result.stdout.strip().splitlines()[-1]=='0')
                self.assertNotEqual(self.command(f"SET ROLE {role}; SELECT decision_case_history('{CASE}');",check=False).returncode,0)
                self.assertNotEqual(self.command(f"SET ROLE {role}; SELECT * FROM decision_approval_events;",check=False).returncode,0)

    def test_captured_catalog_rebuild_and_upgrade_preserve_historical_evidence(self):
        other='dation_upgrade_'+uuid4().hex
        self.command('CREATE DATABASE '+other+';',database='postgres')
        try:
            self.command((Path(__file__).parent/'infrastructure.sql').read_text(),database=other)
            self.command(BASELINE.read_text(),database=other)
            rebuilt=json.loads(self.command(CATALOG_SQL,database=other).stdout.strip())
            captured=json.loads((BASELINE.parent/'20261010100000_catalog.json').read_text())
            self.assertEqual(normalize(rebuilt),normalize(captured))
            self.command(f"INSERT INTO datasets(id,original_filename,storage_path) VALUES('{ORDERS}','legacy.csv','legacy.csv');"
                         f"INSERT INTO decision_runs(dataset_id,engine_name,engine_version,status,result_json,approved_at) VALUES('{ORDERS}','legacy','0.2','completed','{{}}','2020-01-01');",database=other)
            self.upgrade(database=other)
            self.assertEqual(self.command("SELECT count(*) FROM decision_runs WHERE approved_at='2020-01-01' AND approved_by IS NULL;",database=other).stdout.strip(),'1')
            self.assertEqual(self.command('SELECT count(*) FROM decision_approval_events;',database=other).stdout.strip(),'0')
            fresh=json.loads(self.sql(CATALOG_SQL));upgraded=json.loads(self.command(CATALOG_SQL,database=other).stdout.strip())
            self.assertEqual(normalize(fresh),normalize(upgraded))
        finally:self.command('DROP DATABASE '+other+';',database='postgres')


if __name__=='__main__': unittest.main(verbosity=2)
