"""Bounded HTTP connections owned by the API/worker event-loop lifecycle.

Headers stay request-local; neither credentials nor business responses are cached.
Standalone scripts/tests own and close a temporary client instead.
"""
import asyncio
from contextlib import asynccontextmanager
from weakref import WeakKeyDictionary

import httpx
from app.observability import instrument_http

_clients = WeakKeyDictionary()


@asynccontextmanager
async def http_pool():
    loop = asyncio.get_running_loop()
    if loop in _clients:
        raise RuntimeError("An HTTP pool already exists for this event loop.")
    async with httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=32, max_keepalive_connections=16,
                            keepalive_expiry=30.0),
    ) as client:
        instrument_http(client)
        _clients[loop] = client
        try:
            yield client
        finally:
            del _clients[loop]


@asynccontextmanager
async def http_client():
    client = _clients.get(asyncio.get_running_loop())
    if client is not None:
        yield client
    else:
        async with httpx.AsyncClient(timeout=30.0) as temporary:
            instrument_http(temporary)
            yield temporary
