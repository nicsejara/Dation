"""D2 uses fixed D1 Trips, quantities and source publication binding."""
from dataclasses import replace
from uuid import uuid4
import unittest
from app.engines.assignment.cargo_inputs import run_cargo_policy
from app.engines.scheduling.day_contracts import DaySchedulingInput
from app.engines.scheduling.day_scheduling import run_day_scheduling
from app.engines.scheduling.day_validator import certify_schedule
from app.results.assembler import assemble
from app.results.canonical import canonical_bytes,core_result_fingerprint
from app.results import contracts as c
from tests.saga10_fixtures import cargo_request
from tests.test_saga10_assignment import truck


class Saga10SchedulingTests(unittest.TestCase):
    def source(self):
        req=cargo_request(resources=[truck(pallets='6',services=2)])
        result=run_cargo_policy(req,alternative_budget=0)
        package=assemble(result).package
        return DaySchedulingInput(model=req.model,context=req.context,source_core=result.recommended.output.core,
            source_evidence=result.recommended.output.evidence,source_transport_plan={'run_id':req.run_id,'result_fingerprint':package.fingerprints.result_fingerprint},
            resources=req.resources,input_summary=result.recommended.input_summary,run_id=uuid4(),result_generated_at=req.result_generated_at)

    def test_exact_two_trip_handoff_and_artifacts(self):
        request=self.source();before=canonical_bytes(request.source_core)
        result=run_day_scheduling(request);bundle=assemble(result)
        self.assertEqual(canonical_bytes(request.source_core),before)
        self.assertEqual(result.output.core.schedule.cargo,request.source_core.transport_plan.cargo)
        self.assertEqual({t.trip_id for t in result.output.core.schedule.trips},{t.trip_id for t in request.source_core.transport_plan.trips})
        self.assertEqual(sum(a.quantity for a in result.output.core.schedule.cargo.allocations),12)
        self.assertEqual(result.output.core.metrics.scheduled_trips.scheduled,2)
        self.assertEqual(bundle.package.source_transport_plan,request.source_transport_plan)
        core=next(a for a in bundle.artifacts if a.reference.kind=='CORE')
        self.assertIn(b'cargo_assignment_v2',core.content)

    def test_rebound_changed_quantity_or_lost_certificate_rejected(self):
        request=self.source();result=run_day_scheduling(request)
        for missing in [True,False]:
            data=result.output.core.model_dump()
            if missing:data['schedule']['cargo']=None
            else:data['schedule']['cargo']['allocations'][0]['quantity']+=1
            core=c.EngineCoreResult.model_validate(data)
            evidence=result.output.evidence.model_copy(update={'core_result_fingerprint':core_result_fingerprint(core)})
            with self.subTest(missing=missing),self.assertRaises(ValueError):certify_schedule(replace(result,output=c.EngineOutput(core=core,evidence=evidence)))
