"""Run independently of Uvicorn: python worker.py. Cloud Run uses instance CPU."""
import asyncio
import logging
import os
import signal

from app.config import supabase_configured
from app.services.dispatch_job_service import worker_loop
from app.services import dispatch_service
from app.services.http_service import http_pool


async def health_handler(reader, writer):
    await reader.read(4096)
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 20\r\nConnection: close\r\n\r\n{\"status\":\"healthy\"}")
    await writer.drain()
    writer.close()


async def main():
    async with http_pool():
        await run_worker()


async def run_worker():
    if not supabase_configured():
        raise RuntimeError("El worker requiere las variables de Supabase.")
    queue_ok, _ = await dispatch_service._probe_rpc_catalog([
        "claim_dispatch_job", "heartbeat_dispatch_job", "finish_dispatch_job", "ack_case_reconciliation",
    ])
    if not queue_ok:
        raise RuntimeError("La migración de la cola no está disponible para el worker.")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT): loop.add_signal_handler(sig,stop.set)
    server = await asyncio.start_server(health_handler,"0.0.0.0",int(os.getenv("PORT","8080")))
    async with server:
        await worker_loop(stop)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
