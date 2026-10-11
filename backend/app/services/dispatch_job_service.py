"""Durable Dispatch admission and leased execution. No worker runs in the HTTP app."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from threading import Event, Lock
from uuid import uuid4
from time import perf_counter
from app.observability import bind_context, context, event, identify, metrics

import httpx

from app.services import decision_case_service as cases
from app.services import dispatch_service as dispatch
from app.services.run_service import get_dataset, get_run

log = logging.getLogger(__name__)


class RunConflict(ValueError):
    pass


class QueueFull(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


def engine_identity(node):
    if node == "logistics_assignment":
        return dispatch.ASSIGNMENT_ENGINE_NAME, dispatch.ASSIGNMENT_ENGINE_VERSION, dispatch.ASSIGNMENT_SCHEMA_VERSION
    if node == "logistics_scheduling":
        return dispatch.SCHEDULING_ENGINE_NAME, dispatch.SCHEDULING_ENGINE_VERSION, dispatch.SCHEDULING_SCHEMA_VERSION
    return dispatch.ENGINE_NAME, dispatch.ENGINE_VERSION, dispatch.SCHEMA_VERSION


async def enqueue(orders_id, fleet_id, configuration, options, run_id, decision_case=None, source_run_id=None):
    node = (decision_case or {}).get("node_id")
    identify(run_id=run_id, case_id=(decision_case or {}).get("case_id"))
    engine_name, engine_version, schema = engine_identity(node)
    request = {"orders_id":orders_id,"fleet_id":fleet_id,"configuration":configuration,
               "options":options,"decision_case":decision_case,"source_run_id":source_run_id,
               "engine_name":engine_name,"engine_version":engine_version,"schema_version":schema}
    fingerprint = hashlib.sha256(json.dumps(request,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    # Replays resolve the SAME intention before checking mutable upstream approval.
    existing = await dispatch.db("GET","dispatch_run_jobs",params={"run_id":f"eq.{run_id}","select":"request_fingerprint","limit":"1"})
    if existing:
        if existing[0]["request_fingerprint"] != fingerprint:
            raise RunConflict("Ese run_id ya identifica una configuración diferente.")
        run = await get_run(run_id)
        if not run:
            raise RuntimeError("Falta la corrida registrada por la cola.")
        event("dispatch_replayed", node_id=node)
        return run
    if decision_case:
        await cases.ensure_case(decision_case["case_id"],orders_id,fleet_id)
        if node in cases.UPSTREAM_NODE:
            await cases.validate_upstream_run(decision_case["case_id"],node,source_run_id)
    else:
        orders, fleet = await asyncio.gather(get_dataset(orders_id),get_dataset(fleet_id))
        if not orders or not fleet:
            raise LookupError("No se encontró el Data Pack solicitado.")
        if orders.get("dataset_type") != "orders" or fleet.get("dataset_type") != "fleet":
            raise ValueError("El Data Pack no conserva sus tipos.")
    stored_config = {**configuration,"options":options}
    if decision_case: stored_config["decision_case"] = decision_case
    if source_run_id: stored_config["source_assignment_run_id"] = source_run_id
    payload = {"id":run_id,"dataset_id":orders_id,"orders_dataset_id":orders_id,"fleet_dataset_id":fleet_id,
               "configuration_json":stored_config,"schema_version":schema,"engine_name":engine_name,"engine_version":engine_version,
               "decision_case_id":(decision_case or {}).get("case_id"),"node_id":node,"upstream_run_id":source_run_id}
    if context.get():
        request["_observability"] = {k: context.get()[k] for k in ("request_id", "trace_id")}
    try:
        rows = await dispatch.db("POST","rpc/enqueue_dispatch_run",body={
            "run_payload":payload,"job_request":request,"intent_fingerprint":fingerprint,
            "queue_limit":max(1,min(256,int(os.getenv("DATION_MAX_QUEUED_RUNS","32")))),
        })
    except httpx.HTTPStatusError as exc:
        try: code = exc.response.json().get("code")
        except (ValueError,AttributeError): code = None
        if code in {"22023","23505"}: raise RunConflict("Ese run_id ya identifica otra corrida.") from exc
        if code == "53300": raise QueueFull("La cola está llena. Reintentá más tarde con el mismo run_id.") from exc
        raise
    if not rows:
        raise RuntimeError("La cola no devolvió la corrida aceptada.")
    event("dispatch_admitted", node_id=node, stage="queued")
    return rows[0]


async def cancel(run_id):
    rows = await dispatch.db("POST","rpc/cancel_dispatch_job",body={"target_run_id":run_id})
    if not rows: raise LookupError("No se encontró una ejecución recuperable con ese ID.")
    return rows[0]


async def reconcile_cases(limit=10):
    now = datetime.now(timezone.utc)
    tasks = await dispatch.db("GET","decision_case_reconciliations",params={
        "select":"*","available_at":f"lte.{now.isoformat()}","order":"available_at.asc","limit":str(limit),
    }) or []
    for task in tasks:
        case_id, version = task["case_id"], task["version"]
        try:
            await cases.sync_case_history(case_id)
            await dispatch.db("POST","rpc/ack_case_reconciliation",body={"target_case_id":case_id,"observed_version":version})
            event("case_reconciled", case_id=case_id, version=version)
        except (httpx.HTTPError,ValueError,LookupError):
            attempts = task["attempts"] + 1
            # Conditional write: never delay a newer completion or approval.
            try:
                await dispatch.db("PATCH","decision_case_reconciliations",params={"case_id":f"eq.{case_id}","version":f"eq.{version}"},
                    body={"attempts":attempts,"available_at":(now+timedelta(seconds=min(300,2**min(attempts,8)))).isoformat()})
            except httpx.HTTPError:
                pass
            event("case_reconciliation_pending", level=logging.WARNING, case_id=case_id, version=version, attempt=attempts)


async def process_job(job):
    request = job['request_json']
    case = request.get('decision_case') or {}
    with bind_context(request.get('_observability'), run_id=job['run_id'], case_id=case.get('case_id')):
        started = perf_counter()
        event('dispatch_claimed', node_id=case.get('node_id'), attempt=job['attempts'],
              wait_ms=max(0, (datetime.now(timezone.utc)-datetime.fromisoformat(job['created_at'].replace('Z','+00:00'))).total_seconds()*1000) if job.get('created_at') else None)
        try:
            return await _process_job(job)
        finally:
            metrics.observe('dation_worker_execution_seconds', perf_counter()-started,
                            (('node', case.get('node_id') if case.get('node_id') in cases.UPSTREAM_NODE or case.get('node_id') == 'logistics_assignment' else 'dispatch'),))


async def _process_job(job):
    run_id, token = job["run_id"], job["lease_token"]
    lost = Event()
    progress_lock = Lock()
    pending_progress = [0, None]

    def progress(stage):
        if lost.is_set():
            raise LeaseLost("La ejecución perdió su lease.")
        # The solver never waits for HTTP progress writes. Only the latest stage matters.
        with progress_lock:
            pending_progress[0] += 1
            pending_progress[1] = {"stage": stage}

    async def heartbeat(progress=None):
        ok = await dispatch.db("POST","rpc/heartbeat_dispatch_job",body={
            "target_run_id":run_id,"worker_token":token,"lease_seconds":120,"progress":progress})
        if ok is not True:
            lost.set()
            raise LeaseLost("La ejecución ya no pertenece a este worker.")

    async def writer(values):
        if lost.is_set(): raise LeaseLost("La ejecución perdió su lease.")
        if values.get("status") in {"completed","error"}:
            rows = await dispatch.db("POST","rpc/finish_dispatch_job",body={
                "target_run_id":run_id,"worker_token":token,"terminal_values":values})
            if not rows:
                lost.set()
                raise LeaseLost("Otro worker o una cancelación cerró esta ejecución.")
            return rows
        await heartbeat(values.get("progress_json"))
        return []

    async def keep_alive():
        observed = 0
        last_heartbeat = asyncio.get_running_loop().time()
        while True:
            await asyncio.sleep(2)
            with progress_lock:
                version, stage = pending_progress
            now = asyncio.get_running_loop().time()
            if version == observed and now - last_heartbeat < 20:
                continue
            try:
                await heartbeat(stage if version != observed else None)
                if version != observed:
                    event("dispatch_stage", stage=stage["stage"])
                observed = version
                last_heartbeat = now
            except (httpx.HTTPError,LeaseLost):
                lost.set()
                event("dispatch_lease_lost", level=logging.WARNING)
                return

    pulse = asyncio.create_task(keep_alive())
    try:
        request = job["request_json"]
        name, version, schema = engine_identity((request.get("decision_case") or {}).get("node_id"))
        if (name,version,schema) != (request["engine_name"],request["engine_version"],request["schema_version"]):
            raise ValueError("El worker no tiene la versión de motor registrada para esta corrida.")
        case = request.get("decision_case")
        if case and case["node_id"] in cases.UPSTREAM_NODE:
            await cases.validate_upstream_run(case["case_id"],case["node_id"],request["source_run_id"])
        result = await dispatch.execute(request["orders_id"],request["fleet_id"],request["configuration"],request["options"],
            run_id,case,request.get("source_run_id"),execution_writer=writer,progress_handler=progress)
        event("dispatch_completed", attempt=job["attempts"], stage="completed")
        return result
    except LeaseLost:
        event("dispatch_fenced", level=logging.WARNING)
    except httpx.HTTPError:
        # The job remains durable; expiration permits recovery after a provider outage.
        event("dispatch_dependency_unavailable", level=logging.WARNING)
    except Exception as exc:
        if not lost.is_set():
            try:
                await writer({"status":"error","progress_json":{"stage":"error"},"error_message":str(exc)[:1500]})
            except (httpx.HTTPError,LeaseLost):
                event("dispatch_error_persistence_pending", level=logging.WARNING)
        event("dispatch_failed", level=logging.WARNING, error_type=type(exc).__name__)
    finally:
        pulse.cancel()
        await asyncio.gather(pulse,return_exceptions=True)


async def worker_step():
    rows = await dispatch.db("POST","rpc/claim_dispatch_job",body={"worker_token":str(uuid4()),"lease_seconds":120}) or []
    if rows: await process_job(rows[0])
    await reconcile_cases()
    return bool(rows)


async def worker_loop(stop, health_callback=None):
    # One solver at a time per process; instance count is capped by deployment.
    while not stop.is_set():
        try:
            busy = await worker_step()
            if health_callback: health_callback(True)
        except httpx.HTTPError:
            busy = False
            if health_callback: health_callback(False)
            event("dispatch_worker_dependency_unavailable", level=logging.WARNING)
        if not busy:
            try: await asyncio.wait_for(stop.wait(),timeout=2)
            except TimeoutError: pass
