"""U8: immutable binding, scoped bytes, lightweight readers and current review."""
import copy,json,unittest
from uuid import uuid4
from unittest.mock import AsyncMock,patch
from fastapi import HTTPException
import httpx
from app.services import result_package_service as packages,result_artifact_service as artifacts,ultimate_run_service as runs
from app.platform.context import RequestContext
from app.results.assembler import assemble
from app.engines.assignment.transport_policy_result import run_transport_policy
from app.results.canonical import canonical_tree
from tests.test_transport_plan_policies import policy_request
from tests.test_transport_plan_core import order,resource

def fixture():
    bundle=assemble(run_transport_policy(policy_request([order(pallets='1')],[resource(cap='2',services=1)]),alternative_budget=0))
    rows=[]
    for part in bundle.artifacts:
        r=canonical_tree(part.reference);r['id']=r.pop('artifact_id');r.update(storage_bucket='dda-inputs',publication_state='READY',result_fingerprint=bundle.package.fingerprints.result_fingerprint)
        r['storage_path']=f"{r['workspace_id']}/runs/{r['run_id']}/{r['kind'].lower()}/{r['part_key']}/{r['content_sha256']}.json";rows.append(r)
    return bundle,rows

class ResultServiceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):cls.bundle,cls.rows=fixture()
    def setUp(self):
        self.package=self.bundle.package;self.rid=self.package.decision.run_id;self.fp=self.package.fingerprints.result_fingerprint
        self.ctx=RequestContext(str(uuid4()),str(self.package.context.workspace_id),'operator')
        self.data={'run':{'result_json':canonical_tree(self.package)},'artifacts':copy.deepcopy(self.rows),'overlay':{'run_id':str(self.rid),'result_fingerprint':self.fp,'approval_allowed':True,'approval_blockers':[],'freshness':'CURRENT'}}
    async def test_lightweight_result_never_fetches_artifact_bytes(self):
        with patch.object(packages,'call',AsyncMock(return_value=self.data)),patch.object(artifacts,'read',AsyncMock(side_effect=AssertionError('heavy fetch'))):
            response=await packages.result(self.ctx,self.rid,self.fp)
        self.assertEqual(response.provenance.result_fingerprint,self.fp);self.assertFalse(response.approval_overlay.approval_allowed)
    async def test_review_checks_integrity_then_refreshes_current_overlay(self):
        stale=copy.deepcopy(self.data);stale['overlay'].update(approval_allowed=False,approval_blockers=['STALE_CONTEXT'],freshness='STALE')
        with patch.object(packages,'call',AsyncMock(side_effect=[self.data,stale])) as call,patch.object(artifacts,'verify_all',AsyncMock(return_value=True)) as verify:
            response=await packages.review(self.ctx,self.rid,self.fp)
        verify.assert_awaited_once();self.assertEqual(call.await_count,2);self.assertFalse(response.approval_overlay.approval_allowed)
    async def test_approve_missing_artifact_never_calls_mutation(self):
        with patch.object(packages,'call',AsyncMock(return_value=self.data)) as call,patch.object(artifacts,'verify_all',AsyncMock(side_effect=HTTPException(409,'ARTIFACT_MISSING'))):
            with self.assertRaises(HTTPException):await packages.approve(self.ctx,self.rid,uuid4(),'logistics_assignment',self.fp)
        self.assertEqual(call.await_count,1)
    async def test_approve_posts_exact_verified_manifest_and_fingerprint(self):
        receipt={'run':{'approved_at':'2026-11-01T00:00:00Z','approved_by':'user:owner','approved_by_user_id':str(uuid4())}}
        with patch.object(packages,'call',AsyncMock(side_effect=[self.data,receipt])) as call,patch.object(artifacts,'verify_all',AsyncMock(return_value=True)):
            response=await packages.approve(self.ctx,self.rid,uuid4(),'logistics_assignment',self.fp)
        self.assertEqual(call.await_args.kwargs['result_fingerprint'],self.fp);self.assertEqual(len(call.await_args.kwargs['verified_manifest_hash']),64);self.assertEqual(response['result_fingerprint'],self.fp)
    async def test_unknown_dataset_and_artifact_do_not_fetch(self):
        with patch.object(packages,'call',AsyncMock(return_value=self.data)),patch.object(artifacts,'read',AsyncMock()) as read:
            for coroutine in [packages.details(self.ctx,self.rid,self.fp,'unknown'),packages.artifact(self.ctx,self.rid,self.fp,uuid4())]:
                with self.assertRaises(HTTPException) as error:await coroutine
                self.assertEqual(error.exception.status_code,404)
        read.assert_not_awaited()
    async def test_manifest_mismatch_foreign_run_and_tenant_rejected(self):
        variants=[self.rows[:-1]]
        for key in ['workspace_id','run_id','content_sha256']:
            rows=copy.deepcopy(self.rows);rows[0][key]='a'*64 if key=='content_sha256' else str(uuid4());variants.append(rows)
        for rows in variants:
            with self.assertRaises((HTTPException,ValueError)):artifacts.bound_rows(self.package,rows)
    async def test_arbitrary_storage_path_and_public_bucket_rejected(self):
        for key,value in [('storage_path','https://attacker.invalid/object'),('storage_path','../outside'),('storage_bucket','public'),('size_bytes',1048577)]:
            row={**self.rows[0],key:value}
            with self.assertRaises(HTTPException):artifacts.locator(row)
    async def test_unknown_package_schema_safe_failure(self):
        data=canonical_tree(self.package);data['result_schema']='unknown'
        with self.assertRaises(ValueError):artifacts.bound_rows(data,self.rows)
    async def test_retrieval_never_reassembles_history(self):
        with patch.object(packages,'call',AsyncMock(return_value=self.data)),patch('app.results.assembler.assemble',side_effect=AssertionError('reassembly')):
            await packages.result(self.ctx,self.rid,self.fp)
    async def test_replay_returns_original_before_current_state_validation(self):
        from app.results.contracts import UltimateRunRequest
        body=UltimateRunRequest(case_id=self.package.context.case_id,node_id='logistics_assignment',expected_context_hash='a'*64,model_version_id=self.package.context.logistics_model_version_id,data_pack_version_id=self.package.context.data_pack_version_id,node_policy=self.package.context.node_policy)
        old={'id':str(self.rid),'superseded_at':'2026-11-01'}
        with patch.object(runs,'call',AsyncMock(return_value={'replayed':True,'run':old})) as call,patch.object(runs,'verify_inputs',AsyncMock(side_effect=AssertionError('mutable input read'))):
            self.assertEqual(await runs.enqueue(self.ctx,body,self.rid),old)
        self.assertEqual(call.await_count,1);self.assertEqual(call.await_args.args[1],'replay')
    async def test_input_path_validation_precedes_storage_fetch(self):
        row={'workspace_id':self.ctx.workspace_id,'dataset_id':str(uuid4()),'canonical_sha256':'a'*64,'normalized_path':'https://attacker.invalid/inputs'}
        with patch.object(runs.inputs,'read_object',AsyncMock()) as read:
            with self.assertRaises(HTTPException):await runs.verify_inputs([row])
        read.assert_not_awaited()
    async def test_corrupt_bytes_and_missing_storage_are_distinct_failures(self):
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def client():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'{}'))) as c:yield c
        with patch.object(artifacts,'SUPABASE_URL','http://owned.test'),patch.object(artifacts,'headers',return_value={}),patch.object(artifacts,'http_client',client):
            with self.assertRaises(HTTPException) as error:await artifacts.read(self.rows[0])
            self.assertEqual(error.exception.detail,'ARTIFACT_INTEGRITY_ERROR')
    async def test_dataset_full_cardinality_and_chunk_binding(self):
        delivery=next(d.data for d in self.package.details if d.dataset_id=='demand');part=next(a for a in self.bundle.artifacts if a.reference.artifact_id==delivery.artifacts[0].artifact_id)
        body=json.loads(part.content);body['total_rows']+=1
        with patch.object(artifacts,'read',AsyncMock(return_value=json.dumps(body).encode())):
            with self.assertRaises(HTTPException):await artifacts.dataset(delivery,self.rows)
    async def test_details_page_and_entity_lookup_fetch_only_relevant_chunks(self):
        from app.results.assembler import ArtifactBuilder
        from app.results import contracts as c
        from types import SimpleNamespace
        builder=ArtifactBuilder(self.bundle.result.recommended.output.core)
        delivery=builder.dataset('indexed-test','entity_evidence_v1',[c.EntityEvidence(entity_type='ORDER',entity_id='O'+str(n),facts={},reason_refs=()) for n in range(250)])
        indexes=artifacts.indexes(SimpleNamespace(artifacts=builder.parts));rows=[];blobs={}
        for a in builder.parts:
            ref=canonical_tree(a.reference);aid=ref.pop('artifact_id');meta=indexes[aid]
            rows.append({'id':aid,**ref,'producer_metadata':{'retrieval_index':{k:v for k,v in meta.items() if k!='entities'}},'lookup_keys':['/'.join(e) for e in meta['entities']]});blobs[aid]=a.content
        async def read(row):return blobs[row['id']]
        with patch.object(artifacts,'read',AsyncMock(side_effect=read)) as fetch:
            page=await artifacts.dataset(delivery,rows,offset=125,limit=25)
            self.assertEqual([r['entity_id'] for r in page],['O'+str(n) for n in range(125,150)]);self.assertEqual(fetch.await_count,1)
            fetch.reset_mock();entity=await artifacts.dataset(delivery,rows,entity=('ORDER','O249'));self.assertEqual(entity[0]['entity_id'],'O249');self.assertEqual(fetch.await_count,1)

if __name__=='__main__':unittest.main()
