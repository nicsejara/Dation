"""Exercise real Postgres transactions, leases, concurrency and privilege boundaries."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import unittest
from uuid import uuid4
from sql_support import SQLSandbox

REPO = Path(__file__).resolve().parents[3]
CONTAINER = os.getenv("DATION_SQL_TEST_CONTAINER")
CASE = "00000000-0000-4000-8000-000000000003"
ORDERS = "00000000-0000-4000-8000-000000000001"
FLEET = "00000000-0000-4000-8000-000000000002"


@unittest.skipUnless(CONTAINER,"Set DATION_SQL_TEST_CONTAINER to a disposable PostgreSQL container")
class DurableQueueSQLTests(SQLSandbox, unittest.TestCase):

    def setUp(self):
        self.command("truncate public.datasets,public.decision_runs,public.decision_cases,public.dispatch_run_jobs,public.decision_case_reconciliations cascade;")
        self.command(f"insert into public.datasets(id,dataset_type,original_filename,storage_path) values ('{ORDERS}','orders','orders.csv','qa/orders.csv'),('{FLEET}','fleet','fleet.csv','qa/fleet.csv');"
            f"insert into public.decision_cases(id,orders_dataset_id,fleet_dataset_id,input_signature) values ('{CASE}','{ORDERS}','{FLEET}','{ORDERS}:{FLEET}');")

    def sql(self, sql):
        return self.command(sql).stdout.strip()

    def enqueue(self, run_id=None, fingerprint="intent", limit=32, check=True):
        rid=run_id or str(uuid4())
        payload={"id":rid,"dataset_id":ORDERS,"orders_dataset_id":ORDERS,"fleet_dataset_id":FLEET,
            "decision_case_id":CASE,"node_id":"logistics_assignment","configuration_json":{},
            "engine_name":"assignment","engine_version":"1","schema_version":"assignment_v1"}
        sql=f"select id from enqueue_dispatch_run('{json.dumps(payload)}'::jsonb,'{{}}'::jsonb,'{fingerprint}',{limit});"
        result=self.command(sql,check=check)
        return rid,result

    def claim(self, token=None):
        token=token or str(uuid4())
        output=self.sql(f"select row_to_json(j) from claim_dispatch_job('{token}',120) j;")
        return json.loads(output) if output else None

    def finish(self, rid, token):
        values={"status":"completed","result_json":{"schema_version":"assignment_v1"},"result_fingerprint":"same-result","duration_ms":100}
        return self.sql(f"select id from finish_dispatch_job('{rid}','{token}','{json.dumps(values)}'::jsonb);")

    def test_enqueue_is_atomic_and_queued(self):
        rid,_=self.enqueue()
        self.assertEqual(self.sql(f"select status from decision_runs where id='{rid}';"),"queued")
        self.assertEqual(self.sql("select count(*) from dispatch_run_jobs;"),"1")
        self.assertEqual(self.sql("select count(*) from decision_case_reconciliations;"),"1")

    def test_idempotent_replay_and_conflicting_intention(self):
        rid,_=self.enqueue()
        self.enqueue(rid)
        _,conflict=self.enqueue(rid,fingerprint="different",check=False)
        self.assertNotEqual(conflict.returncode,0)
        self.assertEqual(self.sql("select count(*) from decision_runs;"),"1")

    def test_admission_bound_and_no_orphan_run(self):
        self.enqueue(limit=1)
        rid,full=self.enqueue(limit=1,check=False)
        self.assertNotEqual(full.returncode,0)
        self.assertEqual(self.sql(f"select count(*) from decision_runs where id='{rid}';"),"0")

    def test_concurrent_workers_claim_different_jobs(self):
        self.enqueue();self.enqueue()
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=list(pool.map(lambda _:self.claim(),range(2)))
        self.assertNotEqual(jobs[0]["run_id"],jobs[1]["run_id"])
        self.assertIsNone(self.claim())

    def test_crashed_worker_recovers_same_id_and_fences_old_writer(self):
        rid,_=self.enqueue();first=self.claim()
        self.sql(f"update dispatch_run_jobs set lease_expires_at=now()-interval '1 second' where run_id='{rid}';")
        second=self.claim()
        self.assertEqual(second["run_id"],rid)
        self.assertEqual(second["attempts"],2)
        self.assertEqual(self.finish(rid,first["lease_token"]),"")
        self.assertEqual(self.finish(rid,second["lease_token"]),rid)
        self.assertEqual(self.sql("select count(*) from decision_runs;"),"1")
        self.assertEqual(self.sql(f"select result_fingerprint from decision_runs where id='{rid}';"),"same-result")

    def test_heartbeat_cannot_revive_expired_lease(self):
        rid,_=self.enqueue();job=self.claim()
        self.sql(f"update dispatch_run_jobs set lease_expires_at=now()-interval '1 second' where run_id='{rid}';")
        self.assertEqual(self.sql(f"select heartbeat_dispatch_job('{rid}','{job['lease_token']}');"),"f")

    def test_maintenance_bounds_restart_attempts(self):
        rid,_=self.enqueue();self.claim()
        self.sql(f"update dispatch_run_jobs set attempts=max_attempts,lease_expires_at=now()-interval '1 second' where run_id='{rid}';")
        self.assertEqual(self.sql("select maintain_dispatch_jobs();"),"1")
        self.assertEqual(self.sql(f"select status from decision_runs where id='{rid}';"),"error")
        self.assertIsNone(self.claim())

    def test_deadline_expires_queued_work_without_get_side_effects(self):
        rid,_=self.enqueue()
        self.sql(f"update dispatch_run_jobs set deadline_at=now()-interval '1 second' where run_id='{rid}';")
        self.assertEqual(self.sql(f"select status from decision_runs where id='{rid}';"),"queued")
        self.sql("select maintain_dispatch_jobs();")
        self.assertEqual(self.sql(f"select status from decision_runs where id='{rid}';"),"error")

    def test_cancel_fences_worker_and_does_not_overwrite_completion(self):
        rid,_=self.enqueue();job=self.claim()
        self.sql(f"select id from cancel_dispatch_job('{rid}');")
        self.assertEqual(self.finish(rid,job["lease_token"]),"")
        self.assertEqual(self.sql(f"select progress_json->>'stage' from decision_runs where id='{rid}';"),"cancelled")
        other,_=self.enqueue();job=self.claim();self.finish(other,job["lease_token"])
        self.sql(f"select id from cancel_dispatch_job('{other}');")
        self.assertEqual(self.sql(f"select status from decision_runs where id='{other}';"),"completed")

    def test_projection_ack_does_not_lose_concurrent_approval(self):
        rid,_=self.enqueue();job=self.claim();self.finish(rid,job["lease_token"])
        version=int(self.sql("select version from decision_case_reconciliations;"))
        self.sql(f"update decision_runs set approved_at=now() where id='{rid}';")
        self.sql(f"select ack_case_reconciliation('{CASE}',{version});")
        self.assertEqual(self.sql("select count(*) from decision_case_reconciliations;"),"1")
        current=self.sql("select version from decision_case_reconciliations;")
        self.sql(f"select ack_case_reconciliation('{CASE}',{current});")
        self.assertEqual(self.sql("select count(*) from decision_case_reconciliations;"),"0")

    def test_completed_run_survives_failed_projection(self):
        rid,_=self.enqueue();job=self.claim();self.finish(rid,job["lease_token"])
        failure=self.command("update decision_cases set status='invalid';",check=False)
        self.assertNotEqual(failure.returncode,0)
        self.assertEqual(self.sql(f"select status from decision_runs where id='{rid}';"),"completed")
        self.assertEqual(self.sql("select count(*) from decision_case_reconciliations;"),"1")

    def test_anonymous_role_cannot_claim_or_read_jobs(self):
        read=self.command("set role anon;select * from dispatch_run_jobs;",check=False)
        claim=self.command(f"set role anon;select * from claim_dispatch_job('{uuid4()}');",check=False)
        self.assertNotEqual(read.returncode,0)
        self.assertNotEqual(claim.returncode,0)


if __name__ == "__main__": unittest.main(verbosity=2)
