"""U9 source fixtures use real T7 outputs; counterfactual K is marked defensive."""
from uuid import uuid4
from app.engines.assignment.transport_policy_result import run_transport_policy
from app.engines.scheduling.day_contracts import DaySchedulingInput
from app.results.assembler import assemble
from tests.test_transport_plan_policies import policy_request
from tests.test_transport_plan_core import order,resource

def request(trips=1,units=1,source='EXTERNAL',distance='480',ready='2026-11-02',due='2026-11-08'):
    demands=[order('O'+str(i),pallets='26',distance_km=distance,ready_date=ready,delivery_due_date=due) for i in range(trips)]
    r=resource('R1',cap='26',services=units if source=='OWN' else trips,source=source,operating_cost_per_km='1') if source=='OWN' else resource('R1',cap='26',services=trips)
    input_=policy_request(demands,[r]);result=run_transport_policy(input_,alternative_budget=0);bundle=assemble(result)
    return DaySchedulingInput(model=input_.model,context=input_.context,source_core=result.recommended.output.core,source_evidence=result.recommended.output.evidence,source_transport_plan={'run_id':input_.run_id,'result_fingerprint':bundle.package.fingerprints.result_fingerprint},
        resources=input_.resources,input_summary=result.recommended.input_summary,run_id=uuid4(),result_generated_at=input_.result_generated_at)

def defensive(req,**trip_changes):
    core=req.source_core;trips=tuple(t.model_copy(update=trip_changes) for t in core.transport_plan.trips)
    core=core.model_copy(update={'transport_plan':core.transport_plan.model_copy(update={'trips':trips})})
    from app.results.canonical import core_result_fingerprint
    return req.model_copy(update={'source_core':core,'source_evidence':req.source_evidence.model_copy(update={'core_result_fingerprint':core_result_fingerprint(core)}),'source_temporal_certified':False})
