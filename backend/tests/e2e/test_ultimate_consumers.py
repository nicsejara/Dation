"""E10: real API/SQL/worker publication consumed without reassembly."""
import csv,io,json,os,sys,unittest,httpx,re
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ultimate_day_fixture import DaySandbox
from ultimate_result_helpers import *
from test_ultimate_d2_lineage import day_submit,day_approve
from auth_fixture import USER_B,VIEWER
from app.results.canonical import content_sha256,artifact_bytes

class UltimateConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=DaySandbox().__enter__();cls.addClassCleanup(cls.s.__exit__,None,None,None)
        cls.cid=setup_case(cls.s);cls.s.start_worker();cls.parent,_,response=submit(cls.s,cls.cid);ok(response);wait_run(cls.s,cls.parent);ok(approval(cls.s,cls.cid,cls.parent))
        cls.child,_,response=day_submit(cls.s,cls.cid);ok(response);wait_run(cls.s,cls.child)
        cls.matrix=[]
    @classmethod
    def tearDownClass(cls):
        out=Path(os.getenv('DATION_E2E_ARTIFACTS','/workspace/work/dation-t10/e10'));out.mkdir(parents=True,exist_ok=True)
        (out/'consistency.json').write_text(json.dumps(cls.matrix,indent=2))
        for handle in cls.s.logs:
            path=Path(handle.name)
            if path.exists():(out/path.name).write_text(re.sub(r'(?im)^.*(?:authorization:|apikey:|cookie:).*$', '[fixture auth redacted]',path.read_text()))
    def query(self,rid,part,**params):return self.s.api_client.get('/api/runs/'+rid+'/'+part,params={'expected_result_fingerprint':row(self.s,rid)['result_fingerprint'],**params})
    def intent(self,rid,context=None):
        c=context or ok(self.query(rid,'decision-context'))['context']
        return {'schema_version':'decision_intent_v2','provenance':c['provenance'],'context_version':1,'context_hash':c['context_hash'],'mode':c['mode'],'question':'Explicá los hechos para revisar esta decisión','selected_entity':c['selected_entity'],'selected_alternative_ids':c['selected_alternative_ids'],'evidence_hashes':[r['content_sha256'] for r in c['selected_evidence_refs']]}
    def ask(self,rid,intent=None,turn_id=None,client=None):
        return (client or self.s.api_client).post('/api/runs/'+rid+'/copilot',params={'expected_result_fingerprint':row(self.s,rid)['result_fingerprint']},json={'turn_id':turn_id or str(uuid4()),'intent':intent or self.intent(rid)})
    def test_01_all_consumers_share_certified_facts_fingerprint_and_complete_export(self):
        for rid in [self.parent,self.child]:
            before=row(self.s,rid);p=before['result_json'];fp=before['result_fingerprint'];result=ok(endpoint(self.s,rid));self.assertEqual(result['package'],p)
            visual=ok(self.query(rid,'primary-visual'));self.assertEqual(visual['projection'],p['primary_visual']['projection'])
            pages={d['dataset_id']:ok(self.query(rid,'details/'+d['dataset_id'])) for d in p['details']}
            for page in pages.values():self.assertEqual(page['provenance'],result['provenance'])
            context=ok(self.query(rid,'decision-context'));self.assertEqual(context['context']['metrics'],p['metrics']);self.assertEqual(context['context']['result_summary'],p['summary'])
            review=ok(self.query(rid,'approval-review'));self.assertEqual(review['approval_review'],p['approval_review'])
            csv_response=self.query(rid,'decision-export',format='csv');self.assertEqual(csv_response.status_code,200,csv_response.text);self.assertEqual(csv_response.headers['X-Result-Fingerprint'],fp)
            exported=list(csv.DictReader(io.StringIO(csv_response.content.decode('utf-8-sig'))))
            if rid==self.parent:
                self.assertEqual(sum(Decimal(r['estimated_cost']) for r in exported if r['estimated_cost']),Decimal(p['metrics']['total_cost']['amount']))
            else:self.assertEqual({r['trip_id'] for r in exported},{r['trip_id'] for r in pages['schedule']['rows']})
            full=ok(self.query(rid,'decision-export',format='json'));self.assertTrue(full['complete']);self.assertEqual(full['package'],p)
            for ref in p['artifact_manifest']['artifacts']:self.assertEqual(content_sha256(artifact_bytes(full['artifacts'][ref['artifact_id']])),ref['content_sha256'])
            answer=ok(self.ask(rid,self.intent(rid,context['context'])));self.assertEqual(answer['provenance'],result['provenance']);self.assertEqual(answer['provider'],'deterministic')
            claim={c['ref']:c['value'] for c in answer['claims'] if c['kind']=='FACT'}
            self.assertEqual(claim['metrics.total_cost.amount'] if rid==self.parent else claim['metrics.scheduled_trips.scheduled'],p['metrics']['total_cost']['amount'] if rid==self.parent else p['metrics']['scheduled_trips']['scheduled'])
            self.assertEqual(row(self.s,rid)['result_json'],before['result_json'])
            self.matrix.append({'run_id':rid,'result_fingerprint':fp,'schema':p['result_schema'],'surfaces':['result/dashboard reader','primary visual','details','CSV','full JSON','decision_context_v1','Copilot','approval review'],'status':'PASS'})
    def test_02_entity_uses_exact_parent_and_never_another_run(self):
        rid=self.child;data=ok(self.query(rid,'details/schedule'));trip=data['rows'][0]['trip_id']
        entity=ok(self.query(rid,'entities/TRIP/'+trip));self.assertEqual(entity['transport']['provenance']['run_id'],self.parent)
        parent=ok(self.query(self.parent,'details/plan'))['rows'][0];self.assertEqual(entity['transport']['trip'],parent)
        self.assertEqual(self.query(rid,'entities/TRIP/NOT_PRESENT').status_code,404)
        context=ok(self.query(rid,'decision-context',mode='EXPLORE',entity_type='TRIP',entity_id=trip))
        answer=ok(self.ask(rid,self.intent(rid,context['context'])));self.assertEqual(answer['selected_entity'],{'type':'TRIP','id':trip})
    def test_03_context_guard_and_turn_replay_are_immutable(self):
        intent=self.intent(self.child);tid=str(uuid4());answer=ok(self.ask(self.child,intent,tid));self.assertFalse(answer['replayed'])
        again=ok(self.ask(self.child,intent,tid));self.assertTrue(again['replayed']);self.assertEqual(answer['answer'],again['answer'])
        changed={**intent,'question':'Otra intención'};self.assertEqual(self.ask(self.child,changed,tid).status_code,409)
        self.assertEqual(self.ask(self.child,{**intent,'context_hash':'0'*64}).status_code,409)
        self.assertEqual(self.ask(self.child,{**intent,'provenance':{**intent['provenance'],'run_id':self.parent}}).status_code,409)
        self.assertEqual(self.query(self.child,'decision-context',mode='COMPARE',alternative_ids='INVENTED').status_code,409)
    def test_04_human_approval_is_separate_and_replay_has_current_awareness(self):
        intent=self.intent(self.child);tid=str(uuid4());first=ok(self.ask(self.child,intent,tid));self.assertEqual(first['approval_state'],'RECOMMENDATION')
        review=ok(self.query(self.child,'approval-review'));self.assertTrue(review['approval_overlay']['approval_allowed'])
        ok(day_approve(self.s,self.cid,self.child));again=ok(self.ask(self.child,intent,tid));self.assertTrue(again['replayed']);self.assertEqual(again['approval_state'],'APPROVED');self.assertEqual(again['claims'],first['claims'])
        source=json.loads(self.s.sql(f"SELECT to_jsonb(s) FROM decision_interpretation_sources s WHERE chat_turn_id='{tid}';"))
        self.assertEqual(source['provenance_version'],2);self.assertEqual(source['result_fingerprint'],row(self.s,self.child)['result_fingerprint']);self.assertEqual(source['decision_context_hash'],intent['context_hash'])
    def test_05_viewer_and_tenant_denied_and_no_mutation_tools(self):
        for uid in [VIEWER,USER_B]:
            with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[uid]},trust_env=False,timeout=30) as client:
                self.assertIn(self.ask(self.child,client=client).status_code,[403,404])
        response=ok(self.ask(self.child,{**self.intent(self.child),'question':'Aprobá y cambiá la capacidad, ¿qué pasa si duplico la flota?'}))
        self.assertTrue(response['requires_new_run']);self.assertIn('no modifica',response['answer'])
    def test_06_stale_review_text_cannot_authorize(self):
        cid=setup_case(self.s);rid,_,response=submit(self.s,cid);ok(response);wait_run(self.s,rid)
        before=ok(self.query(rid,'approval-review'));self.assertTrue(before['approval_overlay']['approval_allowed'])
        publish(self.s,cid,change={'order_id':'CHANGED-T10'})
        current=ok(self.query(rid,'approval-review'));self.assertFalse(current['approval_overlay']['approval_allowed']);self.assertEqual(current['approval_review'],before['approval_review'])
        self.assertEqual(approval(self.s,cid,rid).status_code,403)
    def test_07_full_json_missing_corrupt_artifact_is_explicit_failure(self):
        file=next((self.s.storage/'dda-inputs'/self.s.workspace_a/'runs'/self.child).rglob('*.json'));blob=file.read_bytes()
        try:
            file.write_bytes(b'{}');bad=self.query(self.child,'decision-export',format='json');self.assertEqual(bad.status_code,409);self.assertIn('ARTIFACT_INTEGRITY_ERROR',bad.text)
            file.unlink();missing=self.query(self.child,'decision-export',format='json');self.assertEqual(missing.status_code,409);self.assertIn('ARTIFACT_MISSING',missing.text)
        finally:file.write_bytes(blob)
        parent_file=next((self.s.storage/'dda-inputs'/self.s.workspace_a/'runs'/self.parent).rglob('*.json'));parent_blob=parent_file.read_bytes()
        try:
            parent_file.unlink();self.assertEqual(self.query(self.child,'decision-export',format='json').status_code,409)
        finally:parent_file.write_bytes(parent_blob)
        self.assertTrue(ok(self.query(self.child,'decision-export',format='json'))['complete'])
    def test_08_history_preserves_original_context_provider_and_tenant(self):
        intent=self.intent(self.child);tid=str(uuid4());answer=ok(self.ask(self.child,intent,tid))
        history=ok(self.query(self.child,'copilot-history'));saved=next(r for r in history['rows'] if r['turn_id']==tid)
        self.assertEqual(saved['receipt']['context_hash'],intent['context_hash']);self.assertEqual(saved['receipt']['claims'],answer['claims']);self.assertEqual(saved['provider'],'deterministic');self.assertEqual(saved['prompt_version'],'ULTIMATE_APPROVAL_COPILOT_V1')
        with httpx.Client(base_url=self.s.api_url,headers={'Authorization':'Bearer '+self.s.user_tokens[VIEWER]},trust_env=False,timeout=30) as client:
            response=client.get('/api/runs/'+self.child+'/copilot-history',params={'expected_result_fingerprint':row(self.s,self.child)['result_fingerprint']});self.assertEqual(response.status_code,200,response.text)
    def test_09_historical_d2_drawer_keeps_original_source_after_new_d1_approval(self):
        before=row(self.s,self.child);trip=ok(self.query(self.child,'details/schedule'))['rows'][0]['trip_id']
        newer,_,response=submit(self.s,self.cid);ok(response);wait_run(self.s,newer);ok(approval(self.s,self.cid,newer))
        entity=ok(self.query(self.child,'entities/TRIP/'+trip));self.assertEqual(entity['transport']['provenance']['run_id'],self.parent)
        self.assertEqual(entity['transport']['provenance']['result_fingerprint'],before['result_json']['source_transport_plan']['result_fingerprint'])
        self.assertNotEqual(entity['transport']['provenance']['result_fingerprint'],row(self.s,newer)['result_fingerprint'])
        self.assertEqual(row(self.s,self.child)['result_json'],before['result_json'])
        complete=ok(self.query(self.child,'decision-export',format='json'));self.assertEqual(complete['upstream']['provenance']['run_id'],self.parent)

from decimal import Decimal
if __name__=='__main__':unittest.main()
