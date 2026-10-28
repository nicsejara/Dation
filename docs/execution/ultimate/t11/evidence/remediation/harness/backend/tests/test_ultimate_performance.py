"""PERF11: measured bounded engines/assemblers, never a new business formula.

Each engine sample runs in a fresh process so ru_maxrss includes native CP-SAT
memory without contamination from prior test modules. No unmeasured latency SLO.
"""
import json
import hashlib
import math
import os
from pathlib import Path
import resource as usage
import statistics
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from uuid import UUID

from ortools.sat.python import cp_model
from app.engines.assignment.transport_policy_result import run_transport_policy
from app.engines.scheduling.day_contracts import DaySchedulingInput
from app.engines.scheduling.day_scheduling import run_day_scheduling
from app.results.assembler import assemble,ArtifactBuilder
from app.results.day_assembler import assemble_day
from app.results.canonical import canonical_bytes
from app.results import contracts as c
from tests.test_transport_plan_core import order,resource,request
from tests.test_transport_plan_policies import policy_request

OUT=Path(os.getenv('DATION_T11_PERFORMANCE','/tmp/dation-t11-performance'))


def scale_request():
    """The unchanged 500/50/31 PERF11 point, also used by the real worker drill."""
    demands=[order('ORDER-%03d'%i,pallets='26',compatibility_groups=['GROUP-%02d'%(i%50)],
                   delivery_due_date='2026-12-02') for i in range(500)]
    resources=[resource('RESOURCE-%02d'%i,cap='13',services=20,
                        compatibility_groups=['GROUP-%02d'%i]) for i in range(50)]
    return request(demands,resources,context_changes={
        'planning_end':'2026-12-02','case_policy':{'primary_goal':'MINIMIZE_COST'},
        'node_policy':{'primary_goal':'MINIMIZE_COST'}})


def probe():
    tracing=os.getenv('DATION_T11_PROBE_TRACE')=='1'
    if tracing:
        import faulthandler
        faulthandler.dump_traceback_later(30,repeat=True,file=sys.stderr)
    def stage(name):
        if tracing:print('PERF11_PHASE '+name,file=sys.stderr,flush=True)
    before=time.perf_counter();req=scale_request();fixture_s=time.perf_counter()-before
    solves=[];native_solve=cp_model.CpSolver.solve;phase='D1_SCALE_500'
    def observe(solver,model,*args,**kwargs):
        before=time.perf_counter();status=native_solve(solver,model,*args,**kwargs)
        solves.append({'phase':phase,'variables':len(model.proto.variables),'constraints':len(model.proto.constraints),
                       'status':solver.status_name(status),'wall_seconds':time.perf_counter()-before,
                       'deterministic_seconds':solver.response_proto.deterministic_time})
        return status
    with patch.object(cp_model.CpSolver,'solve',observe):
        stage('D1_ENGINE_500_START')
        before=time.perf_counter();cpu_before=time.process_time();result=run_transport_policy(req,alternative_budget=3)
        engine_s=time.perf_counter()-before;engine_cpu_s=time.process_time()-cpu_before
        stage('D1_ASSEMBLER_500_START')
        before=time.perf_counter();cpu_before=time.process_time();bundle=assemble(result);assembly_s=time.perf_counter()-before;assembly_cpu_s=time.process_time()-cpu_before
        parent=result.recommended.output.core
        # A bounded/UNKNOWN large D1 can have zero trips; D2 must not run on it.
        # Measure D2 separately using a real nonempty 100-trip certified parent.
        phase='D2_SOURCE_D1_100'
        stage('D2_SOURCE_D1_100_START')
        source_req=request([order('DAY-%03d'%i,pallets='13',split=False,
            compatibility_groups=['GROUP-%02d'%(i%50)],delivery_due_date='2026-12-02') for i in range(100)],
            [resource('DAY-RESOURCE-%02d'%i,cap='13',services=2,compatibility_groups=['GROUP-%02d'%i]) for i in range(50)],
            context_changes={'planning_end':'2026-12-02','case_policy':{'primary_goal':'MINIMIZE_COST'},'node_policy':{'primary_goal':'MINIMIZE_COST'}})
        source_req=source_req.model_copy(update={'run_id':UUID(int=113)})
        before=time.perf_counter();source_result=run_transport_policy(source_req,alternative_budget=0)
        source_engine_s=time.perf_counter()-before
        before=time.perf_counter();source_bundle=assemble(source_result);source_assembly_s=time.perf_counter()-before
        source=source_result.recommended.output.core;phase='D2_SCALE_100'
        stage('D2_ENGINE_100_START')
        day_input=DaySchedulingInput(model=source_req.model,context=source_req.context,source_core=source,
            source_evidence=source_result.recommended.output.evidence,
            source_transport_plan={'run_id':source_req.run_id,'result_fingerprint':source_bundle.package.fingerprints.result_fingerprint},
            resources=source_req.resources,input_summary=source_result.recommended.input_summary,
            run_id=UUID(int=112),result_generated_at=req.result_generated_at)
        before=time.perf_counter();day=run_day_scheduling(day_input);day_s=time.perf_counter()-before
        stage('D2_ASSEMBLER_100_START')
        before=time.perf_counter();day_bundle=assemble_day(day);day_assembly_s=time.perf_counter()-before
    def artifacts(b):
        rows=[json.loads(a.content) for a in b.artifacts]
        return {'package_bytes':len(canonical_bytes(b.package)),
                'visual_bytes':len(canonical_bytes(b.package.primary_visual.projection)),
                'artifact_count':len(b.artifacts),'artifact_bytes':sum(len(a.content) for a in b.artifacts),
                'max_chunk_bytes':max(map(lambda a:len(a.content),b.artifacts),default=0),
                'max_chunk_rows':max((len(v.get('rows',[])) for v in rows),default=0),
                'fingerprint':b.package.fingerprints.result_fingerprint}
    return {'orders':500,'resources':50,'horizon_days':31,'trips_required_for_full_coverage':1000,
            'point_type':'REAL_ENGINE_REQUEST_WITH_EXISTING_BOUNDS',
            'options':req.options.model_dump(mode='json'),
            'native_solves':solves,'d1_engine_seconds':engine_s,'d1_assembler_seconds':assembly_s,
            'd1_fixture_contract_seconds':fixture_s,'d1_engine_cpu_seconds':engine_cpu_s,'d1_assembler_cpu_seconds':assembly_cpu_s,
            'd1_publication':{'package_sha256':hashlib.sha256(canonical_bytes(bundle.package)).hexdigest(),
                'result_fingerprint':bundle.package.fingerprints.result_fingerprint,
                'artifacts':[{'id':str(p.reference.artifact_id),'sha256':hashlib.sha256(p.content).hexdigest(),'size':len(p.content)} for p in bundle.artifacts]},
            'd2_engine_seconds':day_s,'d2_assembler_seconds':day_assembly_s,
            'peak_rss_kib':usage.getrusage(usage.RUSAGE_SELF).ru_maxrss,
            'candidate_slots':result.recommended.structural.search.candidate_slots,
            'declared_variable_count':result.recommended.structural.search.variable_count,
            'limits':list(result.recommended.structural.search.limits),
            'd1_status':parent.engine.solver_status,'d1_full_coverage':parent.feasibility.full_demand_coverage,
            'd1_solution_found':parent.feasibility.solution_found,'d1_review_ready':bundle.package.approval_review.decision_ready_for_review,
            'd1_trips':len(parent.transport_plan.trips),'d2_trips':len(day.output.core.schedule.trips),
            'd2_source_trips':len(source.transport_plan.trips),'d2_source_engine_seconds':source_engine_s,
            'd2_source_assembler_seconds':source_assembly_s,'d2_source_scope':'separate real certified 100-trip D1; never fabricate a parent for empty D1',
            'alternatives':len(result.alternatives),'alternatives_state':result.alternatives_status,
            'd1':artifacts(bundle),'d2':artifacts(day_bundle)}


class UltimatePerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True,exist_ok=True);cls.samples=[]
        for index in range(5):
            p=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--probe'],
                             cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=180,
                             env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])})
            if p.returncode:raise AssertionError(p.stderr[-6000:])
            cls.samples.append(json.loads(p.stdout))
            (OUT/('sample-%02d.json'%(index+1))).write_text(json.dumps(cls.samples[-1],indent=2)+'\n')
        times={}
        for key in ['d1_engine_seconds','d1_assembler_seconds','d2_engine_seconds','d2_assembler_seconds']:
            vals=sorted(s[key] for s in cls.samples)
            times[key]={'n':len(vals),'p50':statistics.median(vals),'p95_nearest_rank':vals[math.ceil(.95*len(vals))-1]}
        (OUT/'engine-assembler.json').write_text(json.dumps({'samples':cls.samples,'timing':times,
            'execution_budget_seconds':90,
            'interpretation':'5 cold-process samples, measured on owned runtime. Empirical p95 nearest rank is descriptive for n=5, not a general service SLO. Engine + assembler excludes admission/publication/Storage; the real worker drill covers the complete job. Existing slot/variable/deterministic budgets and timeout were not raised.'},indent=2)+'\n')

    def test_01_engine_scale_is_bounded_and_honest(self):
        for s in self.samples:
            self.assertEqual((s['orders'],s['resources'],s['horizon_days']),(500,50,31))
            self.assertLessEqual(s['candidate_slots'],s['options']['max_slots'])
            self.assertLessEqual(s['declared_variable_count'],s['options']['max_variables'])
            self.assertLessEqual(s['alternatives'],3)
            self.assertFalse(s['d1_full_coverage'])
            self.assertEqual(s['d2_trips'],s['d2_source_trips'])
            self.assertEqual(s['d2_source_trips'],100)
            if not s['d1_trips']:
                self.assertIn(s['d1_status'],['UNKNOWN','FEASIBLE'])
            self.assertIn('CANDIDATE_MODEL_BUDGET',s['limits'])
            self.assertGreater(s['peak_rss_kib'],0)
            self.assertTrue(s['native_solves'])
            # A fixed-trip EXTERNAL kernel can be fully constrained by variable
            # domains, with zero explicit constraints. The structural model must
            # still have the declared variables and real constraints; do not
            # confuse a valid domain-only subproblem with a vacuous benchmark.
            self.assertTrue(all(v['variables']>=0 and v['constraints']>=0 for v in s['native_solves']))
            self.assertTrue(any(v['phase']=='D1_SCALE_500' and v['variables']==s['declared_variable_count'] and v['constraints']>0 for v in s['native_solves']))
            self.assertTrue(all(v['status']!='MODEL_INVALID' for v in s['native_solves']))

    def test_02_real_d1_d2_publication_payloads_respect_contract_budgets(self):
        for s in self.samples:
            for key in ['d1','d2']:
                v=s[key]
                self.assertLessEqual(v['package_bytes'],c.PACKAGE_MAX_BYTES)
                self.assertLessEqual(v['max_chunk_bytes'],c.EVIDENCE_CHUNK_MAX_BYTES)
                self.assertLessEqual(v['max_chunk_rows'],c.EVIDENCE_CHUNK_MAX_ENTITIES)
                self.assertGreater(v['artifact_count'],0)

    def test_03_thousand_typed_rows_are_chunked_without_claiming_a_new_engine_result(self):
        req=policy_request([order(pallets='1')],[resource(services=1)])
        produced=run_transport_policy(req,alternative_budget=0)
        core=produced.recommended.output.core;seed=core.transport_plan.trips[0]
        # Serializer-only scale fixture; never published as a certified plan.
        rows=[seed.model_copy(update={'trip_id':'SERIALIZATION-%04d'%i}) for i in range(1000)]
        before=time.perf_counter();builder=ArtifactBuilder(core);descriptor=builder.dataset('stress-plan','transport_trip_v1',rows)
        elapsed=time.perf_counter()-before
        recovered=[r for a in builder.parts for r in json.loads(a.content)['rows']]
        self.assertEqual(len(recovered),1000);self.assertEqual(descriptor.row_count,1000)
        self.assertEqual([r['trip_id'] for r in recovered],[r.trip_id for r in rows])
        self.assertTrue(all(len(a.content)<=c.EVIDENCE_CHUNK_MAX_BYTES for a in builder.parts))
        self.assertTrue(all(len(json.loads(a.content)['rows'])<=100 for a in builder.parts))
        (OUT/'thousand-row-serialization.json').write_text(json.dumps({'scope':'TYPED_SERIALIZATION_ONLY_NOT_ENGINE_OUTPUT',
            'rows':1000,'chunks':len(builder.parts),'bytes':sum(len(a.content) for a in builder.parts),
            'seconds':elapsed,'no_rows_omitted':True},indent=2)+'\n')

    def test_04_input_envelope_does_not_expand_search_or_accept_unbounded_rows(self):
        from pydantic import ValidationError
        orders=[order('BOUNDARY-%03d'%i,pallets='1') for i in range(500)]
        resources=[resource('BOUNDARY-%02d'%i,services=1) for i in range(50)]
        accepted=request(orders,resources)
        self.assertEqual(accepted.options.max_slots,128)
        self.assertEqual(accepted.options.max_variables,20000)
        with self.assertRaises(ValidationError):request([*orders,order('BEYOND')],resources)
        with self.assertRaises(ValidationError):request(orders,[*resources,resource('BEYOND')])

    def test_05_engine_and_assembler_lower_bound_must_fit_existing_execution_budget(self):
        # The base plan agrees 90 seconds for the COMPLETE execution. If this
        # measured subset already exceeds it, publication cannot rescue the gate.
        # Do not replace this with only the much smaller native-solver duration.
        for sample in self.samples:
            with self.subTest(node='D1',engine_seconds=sample['d1_engine_seconds'],assembler_seconds=sample['d1_assembler_seconds']):
                self.assertLessEqual(sample['d1_fixture_contract_seconds']+sample['d1_engine_seconds']+sample['d1_assembler_seconds'],90)
            with self.subTest(node='D2'):
                self.assertLessEqual(sample['d2_engine_seconds']+sample['d2_assembler_seconds'],90)

    def test_06_complete_large_publication_matches_pre_remediation_bytes(self):
        golden=json.loads((Path(__file__).parent/'fixtures/ultimate/t11-r-scale-golden.json').read_text())
        for sample in self.samples:
            self.assertEqual(sample['d1_publication'],golden)


if __name__=='__main__':
    if sys.argv[1:]==['--probe']:print(json.dumps(probe()))
    else:unittest.main()
