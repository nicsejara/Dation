"""U7 R1-R8: pure assembly, complete projections and adversarial integrity."""
from dataclasses import replace
from decimal import Decimal as D
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import UUID

from app.engines.assignment.transport_policy_result import run_transport_policy
from app.results import contracts as c,registry
from app.results.assembler import assemble,ArtifactBuilder,PreparedArtifact,AssemblyError
from app.results.validation import validate_bundle,read_delivery
from app.results.canonical import canonical_bytes,artifact_bytes,content_sha256,result_fingerprint,core_result_fingerprint,decision_context_hash
from app.results.export_rows import transport_export_rows
from app.results.projections import sankey,summary
from tests.test_transport_plan_core import request,order,resource
from tests.test_transport_plan_policies import policy_request


class TransportResultPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.consolidated=run_transport_policy(policy_request([order('A','6',split=False),order('B','8',split=False)],[resource(services=1)]),alternative_budget=0)
        cls.consolidated_bundle=assemble(cls.consolidated)
        cls.partial=run_transport_policy(policy_request(),alternative_budget=0)
        cls.unknown=run_transport_policy(policy_request([order(pallets='1')],[resource(services=1,external_cost={'cost_model':'PER_TRIP','rate':None,'billing_basis':None})],goal='MAXIMIZE_SERVICE'),alternative_budget=0)

    def data(self,bundle,delivery):return read_delivery(delivery,bundle.artifacts)

    def test_R1_trip_cost_recognized_once_not_proportionally_distributed(self):
        b=self.consolidated_bundle;rows=self.data(b,b.package.exports.csv.rows)
        self.assertEqual(len(rows),2)
        self.assertEqual([r['estimated_cost'] for r in rows],['100',None])
        self.assertEqual(sum(D(r['estimated_cost']) for r in rows if r['estimated_cost'] is not None),b.package.metrics.total_cost.amount)

    def test_R2_weighted_utilization_not_average_percentages(self):
        r=run_transport_policy(policy_request([order('A','1',destination_id='X'),order('B','3',destination_id='Y')],
            [resource('A','2',1,lanes=[['A','X']]),resource('B','10',1,lanes=[['A','Y']])]),alternative_budget=0)
        b=assemble(r)
        self.assertEqual(b.package.metrics.capacity_utilization.weighted_ratio,D('.3333'))
        self.assertNotEqual(b.package.metrics.capacity_utilization.weighted_ratio,D('.4'))

    def test_R3_sankey_one_cut_not_double_counted_or_residual_trip(self):
        b=assemble(self.partial);v=b.package.primary_visual.projection;nodes={n.id:n for n in v.nodes}
        first=sum(l.value for l in v.links if nodes[l.source].type=='DESTINATION')
        second=sum(l.value for l in v.links if nodes[l.source].type=='TRIP')
        self.assertEqual(first,52);self.assertEqual(second,52)
        self.assertEqual(sum(l.value for l in v.links),104)
        self.assertEqual(len([n for n in v.nodes if n.type=='TRIP']),2)
        self.assertEqual(b.package.metrics.demand_coverage.unassigned,18)

    def test_R4_unknown_cost_preserved_as_null_in_every_projection(self):
        b=assemble(self.unknown)
        self.assertIsNone(b.package.metrics.total_cost)
        self.assertIsNone(b.context.metrics.total_cost)
        self.assertIsNone(b.package.summary.facts['total_cost'])
        self.assertTrue(all(r['estimated_cost'] is None for r in self.data(b,b.package.exports.csv.rows)))
        self.assertTrue(all(r['total_cost'] is None for r in self.data(b,next(d.data for d in b.package.details if d.dataset_id=='resources'))))

    def test_R5_assembler_cannot_invent_causal_reason(self):
        b=self.consolidated_bundle
        reasons=self.data(b,b.package.evidence.reason_emissions)
        self.assertEqual([r['code'] for r in reasons],[r.code for r in self.consolidated.recommended.output.evidence.reasons])
        self.assertTrue(all(r['evidence_refs'] for r in reasons))

    def test_R6_unknown_schema_and_assembler_version_safe_fail(self):
        with self.assertRaises(AssemblyError):assemble(self.consolidated,versions='UNKNOWN_V9')
        for schema in ['unknown','dispatch_v2']:
            core=self.consolidated.recommended.output.core.model_copy(update={'result_schema':schema})
            output=self.consolidated.recommended.output.model_copy(update={'core':core})
            with self.assertRaises(AssemblyError):assemble(replace(self.consolidated,recommended=replace(self.consolidated.recommended,output=output)))

    def test_R7_alternative_artifacts_metrics_deltas_and_status(self):
        r=run_transport_policy(policy_request([order(pallets='1')],[resource('E','2',1),resource('OWN','2',1,source='OWN',operating_cost_per_km='10')]))
        b=assemble(r)
        self.assertTrue(1<=len(b.package.alternatives)<=3)
        for a in b.package.alternatives:
            self.assertTrue(self.data(b,a.plan));self.assertTrue(self.data(b,a.evidence))
            self.assertEqual(a.metrics.total_cost-b.package.metrics.total_cost.amount,a.difference_vs_recommended.cost_delta)
        self.assertEqual(b.package.alternatives_state,'COMPUTED')
        empty=self.consolidated_bundle
        self.assertEqual(empty.package.alternatives_state,'NOT_COMPUTED')
        analysis=next(d for d in empty.package.evidence.parts if d.dataset_id=='analysis-status')
        self.assertEqual(self.data(empty,analysis)[0]['facts']['alternatives_status'],'BUDGET_LIMIT')

    def test_R8_dag_exact_bytes_versions_and_no_future_self_reference(self):
        b=self.consolidated_bundle
        self.assertEqual(result_fingerprint(b.package),b.package.fingerprints.result_fingerprint)
        self.assertEqual(core_result_fingerprint(self.consolidated.recommended.output.core),b.package.fingerprints.core_result_fingerprint)
        for a in b.artifacts:
            self.assertEqual(content_sha256(a.content),a.reference.content_sha256)
            self.assertNotIn(b'"result_fingerprint"',a.content)
            self.assertNotIn(b'signed_url',a.content)
            self.assertNotIn(b'approval_allowed',a.content)
        self.assertEqual(decision_context_hash(b.context),b.context.context_hash)
        raw=self.data(b,b.package.ai_context.base_context)[0]
        self.assertEqual(raw['core_result_fingerprint'],b.package.fingerprints.core_result_fingerprint)
        self.assertNotIn('provenance',raw)

    def test_six_details_have_schemas_keys_ordering_units_and_full_refs(self):
        b=self.consolidated_bundle
        self.assertEqual([d.dataset_id for d in b.package.details],['plan','demand','resources','alternatives','exceptions','evidence'])
        for d in b.package.details:
            self.assertTrue(d.columns and d.primary_key and d.stable_order)
            for ref in d.data.artifacts:self.assertTrue(ref.content_sha256 and ref.schema_version==1)
            self.assertEqual(len(self.data(b,d.data)),d.data.row_count)

    def test_demand_split_residual_resources_and_status_are_engine_facts(self):
        b=assemble(self.partial)
        rows=self.data(b,next(d.data for d in b.package.details if d.dataset_id=='demand'))
        self.assertEqual(rows[0]['facts']['requested_pallets'],'70')
        self.assertEqual(rows[0]['facts']['assigned_pallets'],'52')
        self.assertEqual(rows[0]['facts']['residual_pallets'],'18')
        self.assertEqual(rows[0]['facts']['resource_ids'],['E1'])
        self.assertEqual(rows[0]['facts']['status'],'PARTIALLY_COVERED')
        self.assertEqual(rows[0]['facts']['coverage_ratio'],'0.7429')

    def test_sankey_index_uses_real_entity_ids_without_parsing_labels(self):
        b=self.consolidated_bundle
        index=self.data(b,next(d for d in b.package.evidence.parts if d.dataset_id=='sankey-entity-index'))
        nodes={n.id:n for n in b.package.primary_visual.projection.nodes}
        self.assertEqual({r['facts']['graph_node_id'] for r in index},set(nodes))
        for row in index:
            if row['entity_type']=='TRIP':self.assertIn(row['entity_id'],[t.trip_id for t in self.consolidated.recommended.output.core.transport_plan.trips])
            if row['facts']['scope']=='DESTINATION_FILTER':self.assertEqual(row['facts']['destination_id'],'B')

    def test_O_assumptions_preserve_source_no_confirmed_actor_invention(self):
        r=run_transport_policy(policy_request(resources=[resource(services=1,availability_source='ASSUMED')]),alternative_budget=0)
        b=assemble(r)
        self.assertEqual(len(b.package.assumptions),1)
        assumption=b.package.assumptions[0]
        self.assertEqual((assumption.value,assumption.source),(1,'DERIVED'))
        self.assertEqual(b.context.assumptions,b.package.assumptions)
        self.assertGreaterEqual(len(b.package.approval_review.review_items),1)

    def test_partial_review_ready_is_separate_from_approval_permission(self):
        b=assemble(self.partial)
        self.assertTrue(b.package.approval_review.decision_ready_for_review)
        self.assertEqual(b.package.approval_review.coverage_status,'PARTIAL')
        self.assertNotIn('approval_allowed',b.package.model_dump_json())

    def test_infeasible_guardrail_and_UNKNOWN_are_not_approval_ready(self):
        for req in [policy_request(guards=[{'kind':'MINIMUM_DEMAND_COVERAGE','limit':'1'}]),policy_request(options={'deterministic_budget':0})]:
            b=assemble(run_transport_policy(req,alternative_budget=0))
            self.assertFalse(b.package.approval_review.decision_ready_for_review)
            self.assertTrue(b.package.approval_review.review_items)
            self.assertIsNone(b.package.metrics.total_cost)
            self.assertFalse(b.package.exports.csv.available)
            self.assertIsNone(b.package.exports.csv.rows)

    def test_zero_demand_has_null_ratios_known_zero_cost_and_empty_projection(self):
        b=assemble(run_transport_policy(policy_request([]),alternative_budget=0))
        self.assertEqual(b.package.metrics.total_cost.amount,0)
        self.assertIsNone(b.package.metrics.demand_coverage.ratio)
        self.assertIsNone(b.package.metrics.capacity_utilization.weighted_ratio)
        self.assertEqual(b.package.primary_visual.projection.links,())

    def test_AI_base_is_full_context_not_raw_csv_or_LLM_output(self):
        b=self.consolidated_bundle;context=b.context
        self.assertEqual(context.case,b.package.context)
        self.assertEqual(context.metrics,b.package.metrics)
        self.assertEqual(context.approval_review,b.package.approval_review)
        self.assertEqual(context.provenance.result_fingerprint,b.package.fingerprints.result_fingerprint)
        self.assertEqual(context.input_summary.orders,2)
        self.assertIsNone(context.selected_entity)
        self.assertFalse(any(k in context.model_dump_json() for k in ['raw_csv','llm_response']))

    def test_assembly_is_deterministic_and_leaves_certified_input_unchanged(self):
        before=canonical_bytes(self.consolidated.recommended.output)
        a=assemble(self.consolidated);b=assemble(self.consolidated)
        self.assertEqual(canonical_bytes(a.package),canonical_bytes(b.package))
        self.assertEqual([p.content for p in a.artifacts],[p.content for p in b.artifacts])
        self.assertEqual(before,canonical_bytes(self.consolidated.recommended.output))

    def test_chunked_delivery_retains_every_row_and_detects_missing_or_corrupt(self):
        builder=ArtifactBuilder(self.consolidated.recommended.output.core)
        dataset=builder.dataset('rows','export_rows_v1',tuple({'id':str(i)} for i in range(205)),'EXPORT_ROWS')
        self.assertEqual(len(dataset.artifacts),3)
        self.assertEqual(len(read_delivery(dataset,builder.parts)),205)
        with self.assertRaises(ValueError):read_delivery(dataset,builder.parts[:-1])
        bad=[replace(builder.parts[0],content=b'{}'),*builder.parts[1:]]
        with self.assertRaises(ValueError):read_delivery(dataset,bad)

    def test_partitioned_evidence_reconstructs_complete_typed_facts(self):
        from app.results.validation import reassemble_evidence
        b=self.consolidated_bundle
        proof=next(d for d in b.package.evidence.parts if d.dataset_id=='engine-evidence')
        restored=reassemble_evidence(self.data(b,proof))
        original=self.consolidated.recommended.output.evidence
        self.assertEqual({r.emission_id:r for r in restored.reasons},{r.emission_id:r for r in original.reasons})
        self.assertEqual({r.evidence_id:r for r in restored.constraints},{r.evidence_id:r for r in original.constraints})

    def test_large_evidence_is_partitioned_without_truncation_or_oversize_row(self):
        from app.results.projections import evidence_shards
        from app.results.validation import reassemble_evidence
        original=self.consolidated.recommended.output.evidence
        large=c.EngineEvidence.model_validate({**original.model_dump(),'constraints':[*original.constraints,
            *(c.ConstraintEvidence(evidence_id='TEST-'+str(i),code='TEST_PROVENANCE',status='SATISFIED',hard=False,
                facts={'scope':'SYNTHETIC_FIXTURE','text':'x'*2000}) for i in range(600))]})
        self.assertGreater(len(artifact_bytes(large)),c.EVIDENCE_CHUNK_MAX_BYTES)
        builder=ArtifactBuilder(self.consolidated.recommended.output.core)
        delivery=builder.dataset('large-evidence','engine_evidence_v1',evidence_shards(large),'EVIDENCE','PARTITIONED_ENGINE_EVIDENCE_V1')
        self.assertGreater(len(delivery.artifacts),1)
        restored=reassemble_evidence(read_delivery(delivery,builder.parts))
        self.assertEqual({r.evidence_id:r for r in restored.constraints},{r.evidence_id:r for r in large.constraints})

    def test_oversize_row_fails_closed_instead_of_truncating(self):
        builder=ArtifactBuilder(self.consolidated.recommended.output.core)
        with self.assertRaises(AssemblyError):builder.dataset('oversized','export_rows_v1',({'text':'x'*(1024*1024)},),'EXPORT_ROWS')

    def test_validator_rejects_export_cost_duplication_with_valid_artifact_hashes(self):
        def duplicated(core):
            rows=[dict(r) for r in transport_export_rows(core)]
            rows[1]['estimated_cost']=rows[0]['estimated_cost'];return tuple(rows)
        with patch('app.results.assembler.transport_export_rows',duplicated):
            with self.assertRaisesRegex(AssemblyError,'Export duplicates'):assemble(self.consolidated)

    def test_validator_rejects_sankey_double_count_and_summary_invention(self):
        def bad_visual(core):
            visual=sankey(core)
            links=[c.SankeyLink.model_validate({**l.model_dump(),'value':l.value*2}) for l in visual.links]
            return c.SankeyProjection.model_validate({**visual.model_dump(),'links':links})
        with patch('app.results.assembler.sankey',bad_visual):
            with self.assertRaisesRegex(AssemblyError,'Sankey flow differs'):assemble(self.consolidated)
        def bad_summary(core):return c.ExecutiveSummary.model_validate({**summary(core).model_dump(),'facts':{'total_cost':'999'}})
        with patch('app.results.assembler.summary',bad_summary):
            with self.assertRaisesRegex(AssemblyError,'Summary facts contradict'):assemble(self.consolidated)

    def test_missing_or_corrupt_bundle_artifact_is_not_empty_dataset(self):
        b=self.consolidated_bundle
        with self.assertRaises(ValueError):validate_bundle(replace(b,artifacts=b.artifacts[:-1]))
        with self.assertRaises(ValueError):validate_bundle(replace(b,artifacts=(replace(b.artifacts[0],content=b'{}'),*b.artifacts[1:])))

    def test_wrong_frozen_context_and_changed_core_fail_without_repair(self):
        context=self.consolidated.recommended.output.core.context.model_copy(update={'case_name':'Different'})
        with self.assertRaisesRegex(AssemblyError,'Frozen context mismatch'):assemble(self.consolidated,context)
        plan=self.consolidated.recommended
        data=plan.output.core.model_dump();data['metrics']['total_cost']['amount']=D(1)
        core=c.EngineCoreResult.model_validate(data)
        evidence=c.EngineEvidence.model_validate({**plan.output.evidence.model_dump(),'core_result_fingerprint':core_result_fingerprint(core)})
        output=c.EngineOutput(core=core,evidence=evidence)
        with self.assertRaises(AssemblyError):assemble(replace(self.consolidated,recommended=replace(plan,output=output)))

    def test_references_have_same_run_tenant_core_and_no_new_legacy_capability(self):
        b=self.consolidated_bundle
        for a in b.artifacts:
            self.assertEqual((a.reference.run_id,a.reference.workspace_id,a.reference.core_fingerprint),(b.package.decision.run_id,b.package.context.workspace_id,b.package.fingerprints.core_result_fingerprint))
        self.assertFalse(registry.resolve_runtime(self.consolidated.recommended.output.core.runtime_identity).available)


if __name__=='__main__':unittest.main()
