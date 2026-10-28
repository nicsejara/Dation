"""U10: certified consumers, provenance, lazy retrieval and adversarial provider."""
import copy,csv,io,json,unittest
from uuid import uuid4
from unittest.mock import AsyncMock,patch
from fastapi import HTTPException
from app.results import contracts as c
from app.results.canonical import canonical_tree,decision_context_hash
from app.services import ultimate_decision_context as ia,result_consumer_service as consumers,result_package_service as packages,result_artifact_service as artifacts
from tests.consumer_fixtures import FIXTURE,ALTERNATIVES,fixtures

class DecisionContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx,self.data,self.blobs=fixtures()
        async def call(ctx,operation,**args):
            if operation!='read':raise AssertionError('Consumer attempted mutation')
            return self.data[str(args['run_id'])]
        async def read(row,**kwargs):return self.blobs[row['id']]
        self.calls=patch.object(packages,'call',AsyncMock(side_effect=call));self.calls.start()
        self.reader=patch.object(artifacts,'read',AsyncMock(side_effect=read));self.fetch=self.reader.start()
        self.addCleanup(self.calls.stop);self.addCleanup(self.reader.stop)
    def pub(self,key='d1'):
        p=FIXTURE[key]['package'];return p['decision']['run_id'],p['fingerprints']['result_fingerprint']
    async def context(self,key='d1',**kwargs):return await ia.context(self.ctx,*self.pub(key),**kwargs)
    async def test_initial_result_fetches_no_artifacts(self):
        response=await packages.result(self.ctx,*self.pub());self.assertFalse(response.approval_overlay.approval_allowed);self.fetch.assert_not_awaited()
    async def test_context_all_modes_are_hashed_and_exact(self):
        for key in ['d1','d2']:
            for mode in ['EXPLAIN','EXPLORE','REVIEW']:
                _,_,ctx,_=await self.context(key,mode=mode)
                self.assertEqual(ctx.context_hash,decision_context_hash(ctx));self.assertEqual(canonical_tree(ctx.provenance),{'run_id':self.pub(key)[0],'result_fingerprint':self.pub(key)[1]})
    async def test_unknown_alternative_and_empty_compare_are_rejected(self):
        for ids in [[],['INVENTED']]:
            with self.assertRaises(HTTPException):await self.context(mode='COMPARE',alternative_ids=ids)
    async def test_entity_drawer_and_d2_inheritance_copy_exact_d1_trip(self):
        parent=FIXTURE['d1'];trip=next(b['rows'][0] for b in parent['artifacts'].values() if b['dataset_id']=='plan')
        for key in ['d1','d2']:
            result=await consumers.entity(self.ctx,*self.pub(key),'TRIP',trip['trip_id'])
            self.assertEqual(result['transport']['trip'],trip);self.assertEqual(result['transport']['provenance']['result_fingerprint'],self.pub()[1])
            if key=='d2':self.assertEqual(result['schedule']['trip_id'],trip['trip_id'])
    async def test_missing_entity_never_looks_in_other_run(self):
        with self.assertRaises(HTTPException) as e:await consumers.entity(self.ctx,*self.pub('d2'),'TRIP','NOT_IN_THIS_RUN')
        self.assertEqual(e.exception.status_code,404)
    async def test_selected_context_binds_refs_and_specific_evidence(self):
        trip=next(b['rows'][0]['trip_id'] for b in FIXTURE['d1']['artifacts'].values() if b['dataset_id']=='plan')
        _,_,ctx,material=await self.context(selected_entity=c.EntityRef(type='TRIP',id=trip))
        self.assertEqual(ctx.selected_entity.id,trip);self.assertTrue(ctx.selected_evidence_refs)
        facts,reasons,_=ia.ledger(ctx,material);self.assertEqual(facts['transport.estimated_cost.amount'],'100')
        self.assertTrue(all(r['entity_id']==trip for r in reasons.values()))
    async def test_no_causal_claim_from_cost_only(self):
        _,_,ctx,_=await self.context();facts,_,alts=ia.ledger(ctx,None)
        result=ia.render_answer(ia.ReferenceSelection(fact_ids=('metrics.total_cost.amount',),reason_ids=(),alternative_ids=()),facts,{},alts,question='¿Por qué?',mode='EXPLAIN')
        self.assertIn('no certifica una causa',result['limitations'][0]);self.assertEqual(result['claims'][0]['value'],'100')
    async def test_provider_invented_metrics_reasons_alternatives_whatif_and_malformed_fail_closed(self):
        _,_,ctx,_=await self.context()
        for parsed in [
            {'fact_ids':['metrics.invented'],'reason_ids':[],'alternative_ids':[]},
            {'fact_ids':[],'reason_ids':['FAKE_REASON'],'alternative_ids':[]},
            {'fact_ids':[],'reason_ids':[],'alternative_ids':['NEW_ALT']},
            {'fact_ids':[],'reason_ids':[],'alternative_ids':[],'what_if_result':999},
            'not a structured response',None]:
            with self.subTest(parsed=parsed),patch.object(ia,'structured_completion',AsyncMock(return_value={'parsed':parsed})):
                result=await ia.explain(ctx,None,'¿Qué pasa si cambio la capacidad?')
                self.assertEqual(result['provider'],'deterministic');self.assertTrue(result['requires_new_run']);self.assertNotIn('999',result['answer']);self.assertNotIn('FAKE_REASON',result['answer'])
    async def test_provider_failure_has_certified_fallback(self):
        _,_,ctx,_=await self.context('d2')
        with patch.object(ia,'structured_completion',AsyncMock(side_effect=TimeoutError)):
            result=await ia.explain(ctx,None,'Explicar')
        self.assertEqual(result['provider'],'deterministic');self.assertEqual(next(c['value'] for c in result['claims'] if c['ref']=='metrics.scheduled_trips.scheduled'),1)
    async def test_valid_provider_only_selects_refs_no_free_text(self):
        _,_,ctx,_=await self.context()
        with patch.object(ia,'structured_completion',AsyncMock(return_value={'parsed':{'fact_ids':['metrics.total_cost.amount'],'reason_ids':[],'alternative_ids':[]}})):
            result=await ia.explain(ctx,None,'Costo')
        self.assertEqual(result['provider'],'verified_reference_selection');self.assertEqual(result['claims'],[{'kind':'FACT','ref':'metrics.total_cost.amount','value':'100'}])
    async def test_wrong_run_and_stale_context_never_call_provider(self):
        _,_,ctx,_=await self.context()
        for provenance,hash_ in [({'run_id':str(uuid4()),'result_fingerprint':self.pub()[1]},ctx.context_hash),(canonical_tree(ctx.provenance),'0'*64)]:
            request=ia.CopilotRequest(turn_id=uuid4(),intent=c.DecisionIntentV2(provenance=provenance,context_hash=hash_,mode='EXPLAIN',question='Costo',selected_entity=None,evidence_hashes=()))
            with patch('app.platform.identity.platform_call',AsyncMock(return_value=None)),patch.object(ia,'explain',AsyncMock()) as provider:
                with self.assertRaises(HTTPException):await ia.turn(self.ctx,*self.pub(),request)
                provider.assert_not_awaited()
    async def test_replay_precedes_provider_and_uses_current_approval_state(self):
        _,_,ctx,_=await self.context();rid,fp=self.pub()
        self.data[rid]['run']['approved_at']='2026-11-02T00:00:00Z'
        request=ia.CopilotRequest(turn_id=uuid4(),intent=c.DecisionIntentV2(provenance=ctx.provenance,context_hash=ctx.context_hash,mode='EXPLAIN',question='Costo',selected_entity=None,evidence_hashes=()))
        receipt={'provenance':canonical_tree(ctx.provenance),'answer':'100','context_hash':ctx.context_hash}
        with patch('app.platform.identity.platform_call',AsyncMock(return_value=receipt)),patch.object(ia,'explain',AsyncMock()) as provider:
            result=await ia.turn(self.ctx,rid,fp,request)
        self.assertTrue(result['replayed']);self.assertEqual(result['approval_state'],'APPROVED');provider.assert_not_awaited()
    async def test_exports_are_exact_certified_rows_and_all_artifacts(self):
        for key in ['d1','d2']:
            rid,fp=self.pub(key);p=FIXTURE[key]['package']
            name,body,_=await consumers.export(self.ctx,rid,fp,'csv');rows=list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
            original=next(b['rows'] for b in FIXTURE[key]['artifacts'].values() if b['dataset_id']==p['exports']['csv']['rows']['dataset_id'])
            self.assertEqual(len(rows),len(original));self.assertIn('Transport_Plan' if key=='d1' else 'Day_Schedule',name)
            if key=='d1':self.assertEqual([r['estimated_cost'] for r in rows],['100',''])
            if key=='d1':self.assertEqual(rows[0]['guaranteed_capacity_pallets'],'26');self.assertEqual(rows[0]['utilization_pallets'],'0.5385');self.assertEqual(rows[0]['cost_model'],'PER_TRIP')
            self.assertTrue(all(r['run_id']==rid and r['result_fingerprint']==fp for r in rows))
            _,body,_=await consumers.export(self.ctx,rid,fp,'json');full=json.loads(body)
            self.assertTrue(full['complete']);self.assertEqual(full['package'],p);self.assertEqual(full['artifacts'],FIXTURE[key]['artifacts'])
            if key=='d2':self.assertEqual(full['upstream']['package'],FIXTURE['d1']['package']);self.assertEqual(full['upstream']['artifacts'],FIXTURE['d1']['artifacts'])
    async def test_missing_artifact_never_returns_complete_json(self):
        with patch.object(artifacts,'read',AsyncMock(side_effect=HTTPException(409,'ARTIFACT_MISSING'))):
            with self.assertRaises(HTTPException):await consumers.export(self.ctx,*self.pub(),'json')
    async def test_capacity_of_unused_resource_is_published_not_recomputed(self):
        result=await consumers.resource_capacities(self.ctx,*self.pub());self.assertEqual(result['capacities'],{'EXT':{'pallets':'26'},'OWN':{'pallets':'26'}})
    async def test_alternative_budget_state_comes_from_published_analysis(self):
        result=await consumers.analysis_status(self.ctx,*self.pub());self.assertEqual(result['status'],'BUDGET_LIMIT')
    async def test_provider_context_budget_is_explicit_and_never_truncates_a_reason(self):
        _,_,ctx,material=await self.context()
        fields=ctx.model_dump();fields['case']['display_metadata']['harness_note']='x'*30000;fields['context_hash']=decision_context_hash(fields)
        large=c.DecisionContextV1.model_validate(fields)
        with patch.object(ia,'structured_completion',AsyncMock()) as provider:
            result=await ia.explain(large,material,'Explicar');provider.assert_not_awaited()
        self.assertEqual(result['provider_context']['scope'],'NOT_SENT_BUDGET_EXCEEDED');self.assertIn('presupuesto',result['answer'])
    async def test_oversized_reason_is_omitted_whole_with_reference_and_limit(self):
        facts={'cost':'100'};reason={'code':'CONSOLIDATED_COMPATIBLE_DEMAND','entity_type':'TRIP','entity_id':'A','facts':{'order_ids':['O'+str(n) for n in range(4000)]}}
        answer=ia.render_answer(ia.ReferenceSelection(fact_ids=('cost',),reason_ids=('PUBLISHED-REF',),alternative_ids=()),facts,{'PUBLISHED-REF':reason},{},question='Por qué',mode='EXPLORE')
        self.assertEqual(answer['omitted_claim_refs'],['PUBLISHED-REF']);self.assertEqual(answer['claims'],[{'kind':'FACT','ref':'cost','value':'100'}]);self.assertIn('no certifica una causa',' '.join(answer['limitations']))
    async def test_legacy_paths_reject_published_or_unknown_schema_before_provider_or_export(self):
        from app.services import decision_interpreter_service as legacy
        from app.services.decision_context import build_decision_context
        from app.platform.exports import generate
        for payload in [FIXTURE['d1']['package'],{'schema_version':'unknown_future'}]:
            with self.assertRaises(ValueError):build_decision_context(payload)
            with self.assertRaises(ValueError):generate({'id':self.pub()[0],'status':'completed','result_json':payload},'json')
            with patch.object(legacy,'get_run',AsyncMock(return_value={'status':'completed','result_json':payload})),patch.object(legacy,'completed_evidence',AsyncMock()) as comparisons:
                with self.assertRaises(ValueError):await legacy.generate_explanation(self.pub()[0])
                comparisons.assert_not_awaited()
    async def test_history_reads_saved_context_without_provider_work(self):
        receipt={'provenance':{'run_id':self.pub()[0],'result_fingerprint':self.pub()[1]},'context_hash':'a'*64,'answer':'Guardado'}
        with patch('app.platform.identity.platform_call',AsyncMock(return_value={'rows':[{'receipt':receipt}],'offset':0,'next_offset':None})),patch.object(ia,'explain',AsyncMock()) as provider:
            response=await ia.history(self.ctx,*self.pub());self.assertEqual(response['rows'][0]['receipt'],receipt);provider.assert_not_awaited()
    async def test_published_compare_copies_metrics_deltas_and_never_runs_solver(self):
        p=ALTERNATIVES['package'];aid=p['alternatives'][0]['alternative_id']
        with patch('app.engines.assignment.transport_policy_result.run_transport_policy',side_effect=AssertionError('Consumer ran solver')):
            _,_,ctx,material=await ia.context(self.ctx,p['decision']['run_id'],p['fingerprints']['result_fingerprint'],'COMPARE',alternative_ids=[aid])
            with patch.object(ia,'structured_completion',AsyncMock(side_effect=TimeoutError)):
                response=await ia.explain(ctx,material,'Compará alternativas publicadas')
        claim=next(c for c in response['claims'] if c['kind']=='ALTERNATIVE');source=p['alternatives'][0]
        self.assertEqual(claim['ref'],aid);self.assertEqual(claim['value']['metrics'],source['metrics']);self.assertEqual(claim['value']['difference_vs_recommended'],source['difference_vs_recommended']);self.assertEqual(claim['value']['material_differences'],source['material_differences'])
    async def test_review_copilot_uses_review_facts_without_granting_permission(self):
        _,_,ctx,material=await self.context(mode='REVIEW')
        with patch.object(ia,'structured_completion',AsyncMock(side_effect=TimeoutError)):
            response=await ia.explain(ctx,material,'Revisá esta decisión')
        claims={r['ref']:r['value'] for r in response['claims'] if r['kind']=='FACT'}
        self.assertEqual(claims['review.hard_constraints_satisfied'],ctx.approval_review.hard_constraints_satisfied);self.assertNotIn('approval_allowed',response)
    async def test_sankey_resolves_published_index_not_display_label(self):
        p=FIXTURE['d1']['package'];node=next(n for n in p['primary_visual']['projection']['nodes'] if n['type']=='TRIP')
        resolved=await consumers.visual_entity(self.ctx,*self.pub(),node['id'])
        self.assertEqual(resolved['selection']['entity_id'],node['label']);self.assertEqual(resolved['selection']['entity_type'],'TRIP')
        with self.assertRaises(HTTPException):await consumers.visual_entity(self.ctx,*self.pub(),'NOT_A_PUBLISHED_NODE')
    async def test_real_unknown_cost_context_keeps_null_in_copilot(self):
        from pathlib import Path
        ctx=c.DecisionContextV1.model_validate_json((Path(__file__).parent/'fixtures/ultimate/consumer_null_context.json').read_text())
        with patch.object(ia,'structured_completion',AsyncMock(side_effect=TimeoutError)):
            answer=await ia.explain(ctx,None,'¿Cuál es el costo?')
        self.assertIsNone(next(r['value'] for r in answer['claims'] if r['ref']=='metrics.total_cost'));self.assertIn('No informado',answer['answer'])
    async def test_describing_published_alternatives_is_not_a_hypothetical_new_run(self):
        response=ia.render_answer(ia.ReferenceSelection(fact_ids=(),reason_ids=(),alternative_ids=()),{},{},{},question='¿Cómo cambia el costo entre estas alternativas publicadas?',mode='COMPARE')
        self.assertFalse(response['requires_new_run'])

if __name__=='__main__':unittest.main()
