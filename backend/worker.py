"""Independent, leased worker. Health is liveness; readiness includes database heartbeats."""
import asyncio
import logging
import os
import re
import signal
from uuid import uuid4
from app.config import supabase_configured
from app.observability import configure_logging, event, metrics
from app.services.dispatch_job_service import worker_loop
from app.services import dispatch_service
from app.services.http_service import http_pool

ready = False


async def health_handler(reader, writer):
    request = await reader.read(4096)
    readiness = request.startswith(b'GET /ready ')
    scrape = request.startswith(b'GET /metrics ')
    status = 200 if not readiness or ready else 503
    body = b'{"ready":true}' if readiness and ready else b'{"ready":false}' if readiness else b'{"status":"healthy"}'
    if scrape: body = metrics.render().encode()
    content_type = 'text/plain; version=0.0.4' if scrape else 'application/json'
    writer.write(f'HTTP/1.1 {status} {"OK" if status == 200 else "Service Unavailable"}\r\nContent-Type: {content_type}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode()+body)
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main():
    async with http_pool():
        await run_worker()


async def run_worker():
    global ready
    if not supabase_configured():
        raise RuntimeError('El worker requiere las variables de Supabase.')
    queue_ok, _ = await dispatch_service._probe_rpc_catalog([
        'claim_dispatch_job', 'heartbeat_dispatch_job', 'finish_dispatch_job', 'ack_case_reconciliation',
        'report_dispatch_worker', 'dispatch_operational_snapshot',
        'claim_comparative_analysis', 'heartbeat_comparative_analysis', 'finish_comparative_analysis',
    ])
    if not queue_ok:
        raise RuntimeError('Las migraciones operativas no están disponibles para el worker.')
    identifier = str(uuid4())
    revision = os.getenv('K_REVISION', 'local')
    if not re.fullmatch('[a-zA-Z0-9-]{1,100}', revision): revision = 'unknown'
    stop = asyncio.Event()
    loop_health = True

    def update_health(value):
        nonlocal loop_health
        loop_health = value

    async def report(value):
        global ready
        try:
            async with asyncio.timeout(8):
                accepted = await dispatch_service.db('POST', 'rpc/report_dispatch_worker', body={
                    'target_worker_id': identifier, 'worker_revision': revision, 'is_ready': value})
            ready = accepted is True and value
            event('worker_readiness', outcome='ready' if ready else 'unavailable')
        except Exception as exc:
            ready = False
            event('worker_readiness', level=logging.WARNING, outcome='database_unavailable', error_type=type(exc).__name__)

    async def pulse():
        while not stop.is_set():
            await report(loop_health)
            try: await asyncio.wait_for(stop.wait(), timeout=15)
            except TimeoutError: pass

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT): loop.add_signal_handler(sig, stop.set)
    await report(True)
    if not ready: raise RuntimeError('No se pudo registrar la disponibilidad del worker.')
    heartbeat = asyncio.create_task(pulse())
    try:
        server = await asyncio.start_server(health_handler, '0.0.0.0', int(os.getenv('PORT', '8080')))
        async with server:
            await worker_loop(stop, update_health)
    finally:
        stop.set()
        heartbeat.cancel()
        await asyncio.gather(heartbeat, return_exceptions=True)
        await report(False)


if __name__ == '__main__':
    configure_logging('worker')
    asyncio.run(main())
