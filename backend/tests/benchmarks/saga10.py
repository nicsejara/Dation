"""Repeatable finite local benchmark, with the same fixtures as G4 tests.

From backend: DATION_EXECUTION_MODE=legacy python -m tests.benchmarks.saga10
"""
import hashlib,json,platform,time,tracemalloc,resource
from datetime import datetime,timezone
import ortools
from pathlib import Path
from tests.saga10_fixtures import cargo_request,catalog_config
from tests.test_saga10_assignment import truck
from app.engines.assignment.cargo_inputs import run_cargo_policy
def benchmark():
    rows=[]
    for count in [1,10,100,250]:
        cfg=catalog_config();spec=[('ORDER-'+str(i).zfill(4),[('PAL-JUICE','1')],True) for i in range(count)]
        req=cargo_request(cfg,spec,[truck(services=12)])
        tracemalloc.start();start=time.perf_counter();r=run_cargo_policy(req,alternative_budget=0).recommended;elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        rows.append(dict(orders=count,lines=count,elapsed_seconds=round(elapsed,4),python_peak_bytes=peak,rss_peak_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,status=r.output.core.engine.solver_status,assigned=str(r.output.core.metrics.demand_coverage.assigned),slots=r.structural.search.candidate_slots,variables=r.structural.search.variable_count,limits=r.structural.search.limits,objective_value=str(r.output.evidence.solver.objective_value) if r.output.evidence.solver.objective_value is not None else None,best_bound=str(r.output.evidence.solver.best_bound) if r.output.evidence.solver.best_bound is not None else None,native_statuses=r.structural.search.native_statuses))
    source=Path(__file__).resolve().parents[2]/'app'
    digest=hashlib.sha256(b'\x00'.join(str(p.relative_to(source)).encode()+b'\x00'+hashlib.sha256(p.read_bytes()).digest() for p in sorted(source.rglob('*.py')))).hexdigest()
    return {'backend_python_source_sha256':digest,'measured_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'ortools':ortools.__version__,'scope':'local CP-SAT, alternative_budget=0; tracemalloc enabled, no network','baseline':'f7fb4be3aa750b1c609a3579fd35e9180b40a9c9','results':rows}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Saga10 finite synthetic benchmark; no network or productive execution')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=json.dumps(benchmark(),indent=2)+'\n'
    if args.output:args.output.write_text(result)
    else:print(result,end='')
