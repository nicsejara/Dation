"""U9 R9–R13: one certified D2 across Core, Gantt, details, CSV and context."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4
import unittest
from unittest.mock import patch
from app.engines.scheduling.day_scheduling import run_day_scheduling
from app.engines.scheduling.day_contracts import DaySchedulingInput
from app.results.assembler import assemble,AssemblyError
from app.results.validation import read_delivery,validate_bundle
from app.results.canonical import canonical_bytes,canonical_tree,result_fingerprint,content_sha256
from app.results import contracts as c
from tests.day_fixtures import request,defensive

class DayPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=run_day_scheduling(request(3,2,source='OWN'));cls.bundle=assemble(cls.result)
    def rows(self,b,d):return read_delivery(d,b.artifacts)
    def test_R9_core_gantt_service_csv_context_identical_dates(self):
        b=self.bundle;p=b.package;core=b.result.output.core;schedule={r.trip_id:r for r in core.schedule.trips}
        self.assertEqual(self.rows(b,p.schedule.trips),canonical_tree(core.schedule.trips))
        for item in p.primary_visual.projection.items:
            t=schedule[item.trip_id];self.assertEqual((item.dispatch_date,item.arrival_date,item.occupancy_end),(t.dispatch_date,t.expected_arrival_date,t.available_again))
        service=self.rows(b,next(d.data for d in p.details if d.dataset_id=='service'))
        for row in service:
            t=schedule[row['trip_id']];self.assertEqual((row['dispatch_date'],row['arrival_date'],row['margin_days']),(t.dispatch_date.isoformat(),t.expected_arrival_date.isoformat(),t.schedule_margin_days))
        for row in self.rows(b,p.exports.csv.rows):
            t=schedule[row['trip_id']];self.assertEqual((row['dispatch_date'],row['expected_arrival_date'],row['available_again']),(t.dispatch_date.isoformat(),t.expected_arrival_date.isoformat(),t.available_again.isoformat()))
        self.assertEqual(b.context.metrics,core.metrics);self.assertEqual(b.context.result_summary.facts['upstream_result_fingerprint'],p.source_transport_plan.result_fingerprint)
    def test_R10_same_day_visible_exclusive_own_and_no_external_return(self):
        own=self.bundle.package.primary_visual.projection.items[0]
        self.assertEqual(own.dispatch_date,own.arrival_date);self.assertGreater(own.occupancy_end,own.dispatch_date)
        b=assemble(run_day_scheduling(request(distance='120')));item=b.package.primary_visual.projection.items[0]
        self.assertEqual(item.dispatch_date,item.arrival_date);self.assertIsNone(item.occupancy_start);self.assertIsNone(item.occupancy_end)
    def test_horizon_does_not_clip_arrival_or_own_occupancy(self):
        b=assemble(run_day_scheduling(request(source='OWN',ready='2026-11-08',due='2026-11-10',distance='1150')))
        item=b.package.primary_visual.projection.items[0];self.assertEqual(item.arrival_date,date(2026,11,10));self.assertEqual(item.occupancy_end,date(2026,11,13))
    def test_R11_defensive_pre_horizon_and_unscheduled_rows_are_not_dropped(self):
        for q in [defensive(request(distance='1150'),ready_date=date(2026,11,1),delivery_due_date=date(2026,11,3)),defensive(request(2,source='OWN'),delivery_due_date=date(2026,11,2))]:
            b=assemble(run_day_scheduling(q));count=len(q.source_core.transport_plan.trips)
            self.assertEqual(len(self.rows(b,b.package.schedule.trips)),count);self.assertEqual(len(self.rows(b,b.package.exports.csv.rows)),count)
            self.assertFalse(b.package.approval_review.decision_ready_for_review);self.assertEqual(b.package.metrics.service_level.late,0)
    def test_R12_expected_compliance_is_not_strict_on_time(self):
        from tests.test_transport_plan_core import order,resource
        from tests.test_transport_plan_policies import policy_request
        from app.engines.assignment.transport_policy_result import run_transport_policy
        p=policy_request([order('O'+str(n),pallets='26',split=False,distance_km='120',delivery_due_date='2026-11-03' if n<6 else '2026-11-02') for n in range(8)],[resource(cap='26',services=8)])
        r=run_transport_policy(p,alternative_budget=0);source=assemble(r)
        q=DaySchedulingInput(model=p.model,context=p.context,source_core=r.recommended.output.core,source_evidence=r.recommended.output.evidence,
            source_transport_plan={'run_id':p.run_id,'result_fingerprint':source.package.fingerprints.result_fingerprint},resources=p.resources,input_summary=r.recommended.input_summary,run_id=uuid4(),result_generated_at=p.result_generated_at)
        b=assemble(run_day_scheduling(q));m=b.package.metrics
        self.assertEqual((m.service_level.on_time,m.service_level.at_risk),(6,2));self.assertEqual(m.on_time_ratio,1)
        self.assertEqual(Decimal(b.package.summary.facts['strict_on_time_ratio']),Decimal('.75'));self.assertEqual(b.package.approval_review.expected_delivery_compliance,1)
    def test_all_six_datasets_are_complete_and_service_margin_sorted(self):
        b=self.bundle;ds={d.dataset_id:d for d in b.package.details};self.assertEqual(set(ds),{'schedule','trips','resources','service','exceptions','evidence'})
        self.assertEqual(len(self.rows(b,ds['trips'].data)),3)
        rows=self.rows(b,ds['service'].data);self.assertEqual([r['margin_days'] for r in rows],sorted(r['margin_days'] for r in rows))
    def test_trip_facts_preserve_d1_allocations_and_loads(self):
        b=self.bundle;source={t.trip_id:t for t in b.result.source.source_core.transport_plan.trips}
        rows=self.rows(b,next(d.data for d in b.package.details if d.dataset_id=='trips'))
        for row in rows:
            t=source[row['entity_id']];f=row['facts'];self.assertEqual(f['order_ids'],[a.order_id for a in t.orders]);self.assertEqual(Decimal(f['total_load_pallets']),t.total_load.pallets)
            for i,a in enumerate(t.orders):self.assertEqual(Decimal(f['allocation_fraction_'+str(i)]),a.allocation_fraction)
    def test_assembler_never_resolves_a_calendar(self):
        with patch('app.engines.scheduling.day_scheduling.run_day_scheduling',side_effect=AssertionError('second producer')),patch('app.engines.common.day_resource_feasibility.day_resource_feasibility',side_effect=AssertionError('second solver')):
            self.assertEqual(assemble(self.result).package,self.bundle.package)
    def test_gantt_tampering_rehashed_package_still_fails_certifier(self):
        b=self.bundle;p=canonical_tree(b.package);p['primary_visual']['projection']['items'][0]['arrival_date']='2026-11-07'
        p['fingerprints']['result_fingerprint']=result_fingerprint(p)
        package=c.DecisionResultPackageV1.model_validate(p)
        with self.assertRaises(ValueError):validate_bundle(replace(b,package=package))
    def test_resource_timeline_cannot_diverge_from_core(self):
        r=self.result;timeline=list(r.resource_timeline);t=timeline[0];occ=list(t.occupancy);occ[0]=occ[0].model_copy(update={'busy_until':date(2026,11,8)});timeline[0]=t.model_copy(update={'occupancy':tuple(occ)})
        with self.assertRaises(ValueError):assemble(replace(r,resource_timeline=tuple(timeline)))
    def test_artifact_hash_dag_and_upstream_identity(self):
        b=self.bundle;self.assertEqual(result_fingerprint(b.package),b.package.fingerprints.result_fingerprint)
        self.assertEqual(b.package.fingerprints.upstream_result_fingerprint,b.result.source.source_transport_plan.result_fingerprint)
        for a in b.artifacts:self.assertEqual(content_sha256(a.content),a.reference.content_sha256)
    def test_unsupported_assembler_version_and_context_fail(self):
        with self.assertRaises(AssemblyError):assemble(self.result,versions='WRONG_V9')
        with self.assertRaises(AssemblyError):assemble(self.result,self.result.source.context.model_copy(update={'case_name':'wrong'}))

if __name__=='__main__':unittest.main()
