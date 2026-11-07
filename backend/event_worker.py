"""Finite Cloud Run Job. A leased child owns computation; nothing polls when idle."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import signal
import sys
from time import perf_counter
from uuid import UUID

_PROCESS_BOOT=perf_counter()

from app.platform.context import worker_infrastructure
from app.services.http_service import http_pool
from app.services import execution_dispatch as activation
from app.observability import configure_logging, event


async def stop_child(process):
    if process.returncode is not None:return
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:await asyncio.wait_for(process.wait(),2)
    except TimeoutError:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        await process.wait()


async def supervise(claim, identity, stop):
    """Do not cancel a solver thread: terminate its whole owned process group."""
    job=claim['job'];intent=claim['intent']
    deadline=datetime.fromisoformat(intent['deadline_at'].replace('Z','+00:00'))
    remaining=max(0,(deadline-datetime.now(timezone.utc)).total_seconds())
    process=await asyncio.create_subprocess_exec(sys.executable,str(Path(__file__).resolve()),'--child',
        stdin=asyncio.subprocess.PIPE,start_new_session=True)
    started=perf_counter();terminal=False
    waiter=asyncio.create_task(process.wait());stopping=asyncio.create_task(stop.wait())
    try:
        process.stdin.write(json.dumps(claim).encode());await process.stdin.drain()
        process.stdin.close();await process.stdin.wait_closed()
        while not waiter.done():
            timeout=min(5,max(0,remaining-(perf_counter()-started)))
            if timeout<=0 or stop.is_set():break
            done,_=await asyncio.wait([waiter,stopping],timeout=timeout,return_when=asyncio.FIRST_COMPLETED)
            if stopping in done:break
            if waiter in done:break
            pulse=await activation.runtime_rpc('heartbeat',identity,infrastructure=True)
            if not pulse.get('alive'):
                terminal=pulse.get('terminal',False);break
    finally:
        await stop_child(process)
        stopping.cancel();await asyncio.gather(stopping,return_exceptions=True)
        await waiter
        event('finite_execution_exit',kind=intent['kind'],intent_id=intent['id'],
            total_wall_ms=(perf_counter()-started)*1000,child_exit=process.returncode,
            cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime+resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            gib_seconds=(perf_counter()-started),
            cgroup_peak_bytes=int(Path('/sys/fs/cgroup/memory.peak').read_text()) if Path('/sys/fs/cgroup/memory.peak').is_file() else None,
            child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            parent_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return terminal or process.returncode==0


async def execute(identifier, token, stop):
    identity={'intent_id':str(UUID(identifier)),'delivery_token':str(UUID(token))}
    claim=await activation.runtime_rpc('claim',identity,infrastructure=True)
    if claim['outcome'] in {'missing','stale','busy','terminal','expired'}:
        event('finite_delivery_noop',outcome=claim['outcome']);return 0
    if claim['outcome']!='claimed':return 75
    intent=claim['intent'];now=datetime.now(timezone.utc)
    age=lambda field:max(0,(now-datetime.fromisoformat(intent[field].replace('Z','+00:00'))).total_seconds()*1000)
    event('finite_execution_start',intent_id=intent['id'],kind=intent['kind'],run_id=intent.get('run_id'),
          generation=intent['generation'],retry_count=intent['delivery_attempts']-1,
          queue_wait_ms=max(0,age('available_at')-age('reserved_at')),dispatch_delay_ms=age('reserved_at'),
          worker_cold_start_ms=(perf_counter()-_PROCESS_BOOT)*1000)
    if claim['intent']['kind']=='reconciliation':
        from app.services.dispatch_job_service import reconcile_cases
        async def acknowledge(task):
            return await activation.runtime_rpc('ack_case',{**identity,'source_version':task['version'],
                'source_updated_at':task['updated_at']},infrastructure=True)
        await reconcile_cases(limit=1,case_id=claim['intent']['entity_id'],acknowledge=acknowledge)
    else:
        await supervise(claim,identity,stop)
    terminal=await activation.runtime_rpc('ack',identity,infrastructure=True)
    if terminal is not True:return 75
    # Bounded handoff; never wait for new work or hold an idle process open.
    if not stop.is_set():await activation.publish_pending(limit=3,infrastructure=True)
    return 0


async def child():
    claim=json.loads(sys.stdin.read())
    # Claim metadata is passed over a private pipe by this trusted supervisor.
    from app.services.dispatch_job_service import process_job
    from app.services.comparative_analysis_service import process_analysis_job
    async with http_pool():
        if claim['intent']['kind']=='dispatch':await process_job(claim['job'])
        elif claim['intent']['kind']=='comparative':await process_analysis_job(claim['job'])
        else:raise ValueError('Unexpected child kind')


async def main(args):
    if not activation.jobs_mode():raise RuntimeError('Finite runtime requires jobs mode')
    stop=asyncio.Event()
    loop=asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,stop.set)
    async with http_pool():
        with worker_infrastructure():
            if args.recover:
                recovered=await activation.runtime_rpc('recover',infrastructure=True)
                if recovered.get('enabled'):await activation.publish_pending(limit=3,infrastructure=True)
                return 0
            return await execute(args.intent_id,args.delivery_token,stop)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--recover',action='store_true')
    group.add_argument('--intent-id',type=lambda value:str(UUID(value)))
    group.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--delivery-token',type=lambda value:str(UUID(value)))
    args=parser.parse_args()
    if args.intent_id and not args.delivery_token:parser.error('--delivery-token is required')
    configure_logging('finite-worker')
    sys.exit(asyncio.run(child() if args.child else main(args)) or 0)
