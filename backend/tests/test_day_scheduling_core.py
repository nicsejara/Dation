"""U9 H–L: literal date oracles and exhaustive finite resource schedules."""
from dataclasses import replace
from datetime import date
from itertools import product
import unittest
from unittest.mock import patch
from app.engines.scheduling.day_scheduling import run_day_scheduling
from app.engines.scheduling.day_contracts import UpstreamCertificationConflict,SchedulingNotCertified
from app.engines.scheduling.day_validator import certify_schedule
from app.engines.scheduling.day_metrics import schedule_metrics
from app.results.canonical import canonical_bytes
from app.results import contracts as c
from tests.day_fixtures import request,defensive

class DaySchedulingCoreTests(unittest.TestCase):
    def test_H_external_1150_outbound_three_no_return(self):
        t=run_day_scheduling(request(distance='1150')).output.core.schedule.trips[0]
        self.assertEqual((t.dispatch_date,t.expected_arrival_date,t.outbound_days),(date(2026,11,2),date(2026,11,4),3));self.assertIsNone(t.cycle_days);self.assertIsNone(t.available_again);self.assertIsNone(t.resource_busy_until)
    def test_I_own_one_unit_reuses_exclusive_cycle_end(self):
        rows=run_day_scheduling(request(2,source='OWN')).output.core.schedule.trips
        self.assertEqual([t.dispatch_date.day for t in rows],[2,4]);self.assertEqual([t.available_again.day for t in rows],[4,6]);self.assertTrue(all(t.cycle_days==2 for t in rows))
    def test_J_arrival_after_horizon_is_not_clipped(self):
        t=run_day_scheduling(request(distance='1150',ready='2026-11-08',due='2026-11-10')).output.core.schedule.trips[0]
        self.assertEqual((t.dispatch_date.day,t.expected_arrival_date.day),(8,10))
    def test_K_defensive_pre_horizon_is_not_scheduled_late(self):
        q=defensive(request(distance='1150'),ready_date=date(2026,11,1),delivery_due_date=date(2026,11,3));t=run_day_scheduling(q).output.core.schedule.trips[0]
        self.assertEqual(t.status,'PRE_HORIZON_DISPATCH_REQUIRED');self.assertIsNone(t.dispatch_date);self.assertIsNone(t.schedule_margin_days)
    def test_L_three_own_trips_one_and_two_units(self):
        for units,expected in [(1,[2,4,6]),(2,[2,2,4])]:
            r=run_day_scheduling(request(3,units,source='OWN'));self.assertEqual([t.dispatch_date.day for t in r.output.core.schedule.trips],expected)
    def test_R13_two_units_sweep_has_no_third_occupancy(self):
        rows=run_day_scheduling(request(5,2,source='OWN')).output.core.schedule.trips
        for day in [date(2026,11,n) for n in range(2,12)]:self.assertLessEqual(sum(t.dispatch_date<=day<t.available_again for t in rows),2)
    def test_source_core_allocations_resources_and_hash_are_unchanged(self):
        q=request(3,2,source='OWN');before=canonical_bytes(q.source_core);r=run_day_scheduling(q)
        self.assertEqual(canonical_bytes(q.source_core),before);c.validate_schedule_source(q.source_core,r.output.core,q.source_transport_plan.result_fingerprint)
    def test_T6_certified_impossible_handoff_fails_closed(self):
        q=defensive(request(distance='1150'),delivery_due_date=date(2026,11,3)).model_copy(update={'source_temporal_certified':True})
        with self.assertRaises(UpstreamCertificationConflict):run_day_scheduling(q)
    def test_infeasible_group_preserves_every_trip_and_explains_conflict(self):
        q=defensive(request(2,source='OWN'),delivery_due_date=date(2026,11,2));r=run_day_scheduling(q)
        self.assertEqual(len(r.output.core.schedule.trips),2);self.assertTrue(all(t.status=='UNSCHEDULED' for t in r.output.core.schedule.trips));self.assertIn('RESOURCE_CAPACITY_CONFLICT',[x.code for x in r.output.evidence.reasons]);self.assertEqual(r.output.core.metrics.scheduled_trips.total,2)
    def test_budget_unknown_never_claims_infeasibility(self):
        with self.assertRaises(SchedulingNotCertified):run_day_scheduling(request(),deterministic_budget=0)
    def test_ready_delay_and_zero_margin_have_fact_backed_reasons(self):
        r=run_day_scheduling(request(ready='2026-11-04',due='2026-11-04'));t=r.output.core.schedule.trips[0]
        self.assertEqual(t.status,'AT_RISK');self.assertEqual(t.schedule_margin_days,0);self.assertIn('DELAYED_BY_READY_DATE',t.reason_codes);self.assertIn('ZERO_MARGIN',t.reason_codes)
    def test_own_delay_reason_has_actual_occupied_interval(self):
        r=run_day_scheduling(request(2,source='OWN'));delayed=r.output.core.schedule.trips[1]
        self.assertIn('DELAYED_BY_RESOURCE_OCCUPANCY',delayed.reason_codes)
    def test_R11_late_contract_is_distinct_and_hard_policy_rejects_it(self):
        t=run_day_scheduling(request()).output.core.schedule.trips[0]
        late=c.ScheduleTrip.model_validate({**t.model_dump(),'delivery_due_date':date(2026,11,1),'schedule_margin_days':-1,'status':'LATE'})
        self.assertEqual(schedule_metrics([late]).service_level.late,1)
        q=request();r=run_day_scheduling(q);core=r.output.core.model_copy(update={'schedule':c.DaySchedule(trips=(late,))})
        with self.assertRaises(ValueError):certify_schedule(replace(r,output=r.output.model_copy(update={'core':core})))
    def test_average_margin_denominator_excludes_null(self):
        q=defensive(request(2),ready_date=date(2026,11,1),delivery_due_date=date(2026,11,1));r=run_day_scheduling(q)
        self.assertIsNone(r.output.core.metrics.average_schedule_margin_days);self.assertEqual(r.output.core.metrics.service_level.pre_horizon,2)
    def test_lexicographic_oracle_enumerates_finite_own_placements(self):
        q=request(3,2,source='OWN');r=run_day_scheduling(q)
        feasible=[]
        for dates in product(range(2,9),repeat=3):
            if all(sum(start<=d<start+2 for start in dates)<=2 for d in range(2,11)):feasible.append(dates)
        self.assertEqual(tuple(t.dispatch_date.day for t in r.output.core.schedule.trips),min(feasible))
    def test_new_guardrail_can_deny_review_without_reassigning_D1(self):
        q=request();ctx=q.context.model_dump();ctx['node_policy']={'primary_goal':'MINIMIZE_COST','guardrails':[{'kind':'MINIMUM_OWN_SHARE','limit':'1'}],'override':True,'override_reason':'Explicit local guard'}
        from app.domain.logistics.contracts import FrozenCaseContext
        q=q.model_copy(update={'context':FrozenCaseContext.model_validate(ctx)});r=run_day_scheduling(q)
        self.assertFalse(r.output.core.feasibility.policy_feasible);self.assertEqual(r.output.core.schedule.trips[0].resource_source,'EXTERNAL')

if __name__=='__main__':unittest.main()
