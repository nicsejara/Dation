"""L8 focal: T8 lineage with real D1, and explicitly conceptual D2 metadata."""
import json,sys,unittest
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'e2e'))
from tests.integration import test_ultimate_publication as publication
from ultimate_result_fixture import ResultSandbox
from ultimate_result_helpers import *
from ultimate_graph_state import install_run
from app.services.result_artifact_service import indexes
from app.results.canonical import canonical_bytes,content_sha256

class UltimateRunLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s=ResultSandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
    setUp=publication.UltimatePublicationTests.setUp
    tearDown=publication.UltimatePublicationTests.tearDown
    rpc=publication.UltimatePublicationTests.rpc
    admit=publication.UltimatePublicationTests.admit
    claim=publication.UltimatePublicationTests.claim
    bundle=publication.UltimatePublicationTests.bundle
    prepare=publication.UltimatePublicationTests.prepare
    finish=publication.UltimatePublicationTests.finish
    def complete_admitted(self,rid):
        job=self.claim();self.assertEqual(job['run_id'],rid);b=self.bundle(job);lease={'run_id':rid,'worker_token':job['lease_token']}
        reserved=ok(self.rpc('prepare',{**lease,'package':b.package,'artifact_indexes':indexes(b)},actor=None));parts={str(p.reference.artifact_id):p.content for p in b.artifacts}
        for a in reserved['artifacts']:
            p=self.s.storage/a['storage_bucket']/a['storage_path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(parts[a['id']])
        ok(self.rpc('finish',{**lease,'result_fingerprint':b.package.fingerprints.result_fingerprint,'verified_manifest_hash':content_sha256(canonical_bytes(b.package.artifact_manifest.artifacts))},actor=None))
        ok(approval(self.s,self.cid,rid));return row(self.s,rid)
    def test_L_B_C_E_two_historical_d2_sources_remain_on_A_after_approved_B(self):
        self.finish();a=self.rid;ok(approval(self.s,self.cid,a));up=row(self.s,a)
        child_a=install_run(self.s,self.s.api_client,self.cid,D2,approved=True)
        child_b=install_run(self.s,self.s.api_client,self.cid,D2,status='queued')
        originals={rid:row(self.s,rid) for rid in [child_a,child_b]}
        for _ in range(2):
            config=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/graph/config/'+D2))
            self.assertEqual(config['configuration_context']['upstream_run_id'],a)
        self.assertEqual(row(self.s,a),up)
        newer,_,response=submit(self.s,self.cid);ok(response);new=self.complete_admitted(newer)
        child_c=install_run(self.s,self.s.api_client,self.cid,D2,status='queued')
        for rid,before in originals.items():
            after=row(self.s,rid);self.assertEqual(after['upstream_run_id'],a);self.assertEqual(after['approved_at'],before['approved_at']);self.assertEqual(after['approved_by_user_id'],before['approved_by_user_id']);self.assertIsNotNone(after['superseded_at'])
            self.assertEqual(self.s.sql(f"SELECT u.result_fingerprint FROM decision_runs d JOIN decision_runs u ON u.id=d.upstream_run_id WHERE d.id='{rid}';"),up['result_fingerprint'])
        self.assertEqual(row(self.s,child_c)['upstream_run_id'],newer)
        self.assertEqual(row(self.s,a)['approved_at'],up['approved_at']);self.assertNotEqual(new['result_fingerprint'],up['result_fingerprint'])
    def test_L_A_D_F_pending_replacement_history_selection_and_replay_are_pure(self):
        first=self.admit();body=self.body;before=row(self.s,first)
        config=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/run-context'))
        self.assertEqual(config['runtime_profile'],'transport_plan_v1');self.assertEqual(config['context']['case_id'],self.cid);self.assertEqual(row(self.s,first),before)
        second,_,response=submit(self.s,self.cid);ok(response);retired=row(self.s,first)
        self.assertIsNotNone(retired['superseded_at']);self.assertIsNone(retired['approved_at'])
        selected=ok(self.s.api_client.get('/api/platform/logistics-cases/'+self.cid+'/graph',params={'node_id':D1,'run_id':first}))
        self.assertEqual(selected['selected_run']['id'],first);self.assertEqual(selected['graph']['nodes'][0]['run_id'],second)
        replay=self.s.api_client.post('/api/runs',params={'run_id':first},json=body);self.assertEqual(replay.status_code,202,replay.text)
        self.assertEqual(row(self.s,first),retired);self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_runs WHERE decision_case_id='{self.cid}';"),'2')
        self.assertEqual(self.s.sql(f"SELECT count(*) FROM decision_approval_events WHERE case_id='{self.cid}';"),'0')

if __name__=='__main__':unittest.main()
