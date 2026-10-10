"""Bounded case lists on the actual schema, live history and private read access."""
import json
import unittest
from uuid import uuid4
from sql_support import SQLSandbox, CONTAINER

ORDERS='00000000-0000-4000-8000-000000000001'
FLEET='00000000-0000-4000-8000-000000000002'


@unittest.skipUnless(CONTAINER,'Requires disposable PostgreSQL 17')
class CaseListSQLTests(SQLSandbox,unittest.TestCase):
    def sql(self,sql):return self.command(sql).stdout.strip()

    def setUp(self):
        self.sql('TRUNCATE datasets,decision_runs,decision_cases,decision_approval_events CASCADE;')
        self.sql(f"INSERT INTO datasets(id,dataset_type,original_filename,storage_path,profile_json) VALUES "
                 f"('{ORDERS}','orders','orders.csv','qa/orders.csv',jsonb_build_object('large',repeat('x',100000))),"
                 f"('{FLEET}','fleet','fleet.csv','qa/fleet.csv','{{}}');"
                 f"INSERT INTO decision_cases(id,orders_dataset_id,fleet_dataset_id,input_signature,status,last_activity_at) "
                 f"SELECT ('00000001-0000-4000-8000-'||lpad(i::text,12,'0'))::uuid,'{ORDERS}','{FLEET}',"
                 f"'{ORDERS}:{FLEET}',CASE WHEN i<=101 THEN 'active' ELSE 'archived' END,'2026-10-10' "
                 f"FROM generate_series(1,102) i;")

    def page(self,status="'active'",limit=100,offset=0,summary='true'):
        sql=f"SET ROLE service_role; BEGIN READ ONLY; SELECT coalesce(jsonb_agg(t),'[]') FROM list_decision_cases({status},{limit},{offset},{summary}) t; COMMIT;"
        return json.loads(self.sql(sql).splitlines()[2])

    def test_page_bounds_stable_ties_all_statuses_and_full_metadata_compatibility(self):
        first=self.page();tail=self.page(offset=100)
        self.assertEqual(len(first),100);self.assertEqual(len(tail),1)
        self.assertEqual(first[0]['case_row']['id'],'00000001-0000-4000-8000-000000000101')
        self.assertFalse({r['case_row']['id'] for r in first}&{r['case_row']['id'] for r in tail})
        self.assertEqual(len(self.page(status='NULL',offset=100)),2)
        self.assertEqual(len(self.page(status="'archived'")),1)
        self.assertEqual(self.page(offset=1000),[])
        self.assertNotIn('profile_json',first[0]['orders'])
        self.assertLess(len(json.dumps(first)),200000)
        full=self.page(limit=1,summary='false')[0]
        self.assertEqual(len(full['orders']['profile_json']['large']),100000)
        for row in first:
            self.assertEqual(row['orders']['id'],ORDERS)
            self.assertEqual(row['summaries']['logistics_assignment']['run_count'],0)

    def test_counts_old_approval_latest_and_replacements_are_live_without_heavy_artifacts(self):
        case='00000001-0000-4000-8000-000000000101';old=str(uuid4())
        identity=json.dumps({'decision_case':{'case_id':case,'node_id':'logistics_assignment','status':'review'}})
        self.sql(f"INSERT INTO decision_runs(id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,"
                 f"engine_name,engine_version,schema_version,status,result_json,configuration_json,created_at) VALUES "
                 f"('{old}','{ORDERS}','{ORDERS}','{FLEET}','{case}','logistics_assignment','qa','1','assignment_v1',"
                 f"'completed','{identity}','{identity}','2020-01-01');"
                 f"SELECT id FROM approve_decision_run_version('{old}','{case}','logistics_assignment');")
        self.sql(f"INSERT INTO decision_runs(id,dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,"
                 f"engine_name,engine_version,schema_version,status,result_json,configuration_json,created_at) "
                 f"SELECT ('00000002-0000-4000-8000-'||lpad(i::text,12,'0'))::uuid,'{ORDERS}','{ORDERS}','{FLEET}',"
                 f"'{case}','logistics_assignment','qa','1','assignment_v1','completed',"
                 f"jsonb_build_object('large',repeat('x',10000))||'{identity}'::jsonb,'{identity}','2026-10-10' FROM generate_series(1,1005) i;")
        summary=self.page(limit=1)[0]['summaries']['logistics_assignment']
        latest='00000002-0000-4000-8000-000000001005'
        self.assertEqual(summary['run_count'],1006)
        self.assertEqual(summary['approved']['id'],old)
        self.assertEqual(summary['latest']['id'],latest)
        self.assertNotIn('result_json',summary['latest'])
        self.assertNotIn('configuration_json',summary['latest'])
        self.sql(f"SELECT id FROM approve_decision_run_version('{latest}','{case}','logistics_assignment');")
        self.assertEqual(self.page(limit=1)[0]['summaries']['logistics_assignment']['approved']['id'],latest)

    def test_invalid_bounds_and_untrusted_roles_cannot_execute(self):
        for args in ["'invalid',1,0,false","'active',0,0,false","'active',101,0,false",
                     "'active',1,-1,false","'active',NULL,0,false"]:
            result=self.command(f'SELECT * FROM list_decision_cases({args});',check=False)
            self.assertNotEqual(result.returncode,0)
        for role in ['anon','authenticated']:
            result=self.command(f'SET ROLE {role}; SELECT * FROM list_decision_cases();',check=False)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('permission denied',result.stderr)

    def test_summary_uses_bounded_page_and_existing_history_indexes(self):
        self.sql(f"INSERT INTO decision_runs(dataset_id,orders_dataset_id,fleet_dataset_id,decision_case_id,node_id,"
                 f"engine_name,engine_version,schema_version,status) SELECT '{ORDERS}','{ORDERS}','{FLEET}',c.id,"
                 f"'logistics_assignment','qa','1','assignment_v1','queued' FROM decision_cases c CROSS JOIN generate_series(1,50) i;")
        self.sql('ANALYZE decision_cases; ANALYZE decision_runs;')
        # Inspect the actual SQL body, not the outer PL/pgSQL Function Scan.
        from sql_support import REPO
        import re
        body=(REPO/'supabase/migrations/20261010220000_case_list_performance.sql').read_text().split(' RETURN QUERY\n',1)[1].split('\nEND;',1)[0]
        for name,value in {'case_status':"'active'",'page_limit':'100','page_offset':'0','summary_only':'true'}.items():
            body=re.sub(r'\b'+name+r'\b',value,body)
        plan=json.loads(self.sql('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+body))
        self.assertEqual(plan[0]['Plan']['Actual Rows'],100)
        serialized=json.dumps(plan)
        def scans(node):
            if node.get('Relation Name')=='decision_runs':yield node
            for child in node.get('Plans',[]):yield from scans(child)
        history_scans=list(scans(plan[0]['Plan']))
        self.assertTrue(history_scans)
        self.assertTrue(all('Index' in scan['Node Type'] or scan['Node Type']=='Bitmap Heap Scan'
                            for scan in history_scans))
        self.assertIn('decision_runs_one_current_approval_idx',serialized)
        self.assertNotIn('result_json',serialized)
