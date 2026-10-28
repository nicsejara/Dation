"""Observational launcher for an owned PERF11 worker; no business decisions."""
import asyncio
from contextvars import ContextVar
import functools
import json
from pathlib import Path
import runpy
import sys
import time

print('T11_R_LAUNCHER_START',file=sys.stderr,flush=True)
worker_root=Path.cwd()
sys.path.insert(0,str(worker_root))
from app.services import ultimate_run_service as execution
from app.services import result_artifact_service as artifacts
from app.results import assembler
print('T11_R_LAUNCHER_IMPORTS_READY',file=sys.stderr,flush=True)

current=ContextVar('t11_r_job',default=None)
events={}


def observed(label,fn):
    if asyncio.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def call(*args,**kwargs):
            rid=current.get();start=time.perf_counter();cpu=time.process_time()
            try:return await fn(*args,**kwargs)
            finally:
                if rid:events[rid].append({'stage':label,'seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu})
    else:
        @functools.wraps(fn)
        def call(*args,**kwargs):
            rid=current.get();start=time.perf_counter();cpu=time.process_time()
            try:return fn(*args,**kwargs)
            finally:
                if rid:events[rid].append({'stage':label,'seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu})
    return call


original_resolve=execution.resolve_worker_producer
def resolve(row):return observed('recommended_and_alternatives',original_resolve(row))
execution.resolve_worker_producer=resolve
execution.verify_inputs=observed('input_snapshot_loading_verification',execution.verify_inputs)
assembler.assemble=observed('result_assembly',assembler.assemble)
artifacts.indexes=observed('artifact_retrieval_index_preparation',artifacts.indexes)
artifacts.upload=observed('storage_upload',artifacts.upload)
artifacts.verify_all=observed('storage_retrieval_verification',artifacts.verify_all)
original_call=execution.call
async def call(ctx,operation,**arguments):
    return await observed('checked_rpc_'+operation,original_call)(ctx,operation,**arguments)
execution.call=call

original_execute=execution.execute_job
async def execute(job,progress=None):
    rid=job['run_id'];events[rid]=[];token=current.set(rid);start=time.perf_counter();cpu=time.process_time()
    try:
        result=await original_execute(job,progress)
        report={'run_id':rid,'complete_execution_seconds':time.perf_counter()-start,
                'complete_execution_cpu_seconds':time.process_time()-cpu,'events':events[rid]}
        for name in ['memory.peak','memory.max']:
            path=Path('/sys/fs/cgroup')/name
            if path.exists():report[name]=path.read_text().strip()
        Path('/tmp/t11-r-worker-metrics.json').write_text(json.dumps(report,indent=2)+'\n')
        return result
    finally:current.reset(token)
execution.execute_job=execute

print('T11_R_LAUNCHER_WORKER_START',file=sys.stderr,flush=True)
runpy.run_path(str(worker_root/'worker.py'),run_name='__main__')
