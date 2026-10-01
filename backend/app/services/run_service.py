import asyncio
import os
from datetime import datetime, timezone
from time import perf_counter
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.engines.logistics.engine import (
    ENGINE_NAME,
    ENGINE_VERSION,
    run_logistics_engine,
)
from app.models.decision_config import DecisionRunConfig


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }


async def get_dataset(dataset_id: str) -> dict | None:
    params = {
        "select": "*",
        "id": f"eq.{dataset_id}",
        "limit": "1",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/datasets",
            headers=_headers(),
            params=params,
        )
        response.raise_for_status()

    data = response.json()
    return data[0] if data else None


async def download_dataset(dataset: dict) -> bytes:
    bucket = dataset["storage_bucket"]
    path = quote(dataset["storage_path"], safe="/")

    url = (
        f"{SUPABASE_URL}/storage/v1/object/authenticated/"
        f"{bucket}/{path}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
            headers=_headers(),
        )
        response.raise_for_status()

    return response.content


async def _insert_run(run: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/decision_runs",
            headers={
                **_headers(),
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=run,
        )
        response.raise_for_status()

    return response.json()[0]


async def _update_run(run_id: str, values: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/decision_runs",
            headers={
                **_headers(),
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            params={"id": f"eq.{run_id}"},
            json=values,
        )
        response.raise_for_status()

    return response.json()[0]


async def _update_dataset(
    dataset_id: str,
    values: dict,
) -> None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/datasets",
            headers={
                **_headers(),
                "Content-Type": "application/json",
            },
            params={"id": f"eq.{dataset_id}"},
            json=values,
        )
        response.raise_for_status()


async def execute_logistics_run(
    dataset_id: str,
    configuration: dict | None = None,
    *,
    objective: str | None = None,
    run_id: str | None = None,
) -> dict:
    dataset = await get_dataset(dataset_id)

    if not dataset:
        raise LookupError("No se encontró el dataset solicitado.")

    if configuration is None:
        configuration = DecisionRunConfig.from_legacy_objective(
            objective
        ).model_dump()

    run_id = run_id or str(uuid4())
    started_at = datetime.now(timezone.utc)
    start = perf_counter()

    await _insert_run(
        {
            "id": run_id,
            "dataset_id": dataset_id,
            "engine_name": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "configuration_json": configuration,
            "status": "running",
            "started_at": started_at.isoformat(),
        }
    )

    await _update_dataset(
        dataset_id,
        {"status": "processing"},
    )

    try:
        contents = await download_dataset(dataset)

        result = await asyncio.to_thread(
            run_logistics_engine, contents,
            configuration=configuration,
        )

        duration_ms = int(
            (perf_counter() - start) * 1000
        )
        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        completed = await _update_run(
            run_id,
            {
                "status": "completed",
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "result_json": result,
                "error_message": None,
            },
        )

        await _update_dataset(
            dataset_id,
            {
                "status": "processed",
                "error_message": None,
            },
        )

        return completed

    except Exception as exc:
        duration_ms = int(
            (perf_counter() - start) * 1000
        )
        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        await _update_run(
            run_id,
            {
                "status": "error",
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "error_message": str(exc)[:2000],
            },
        )

        await _update_dataset(
            dataset_id,
            {
                "status": "error",
                "error_message": str(exc)[:2000],
            },
        )

        raise


async def get_run(run_id: str) -> dict | None:
    params = {
        "select": "*",
        "id": f"eq.{run_id}",
        "limit": "1",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/decision_runs",
            headers=_headers(),
            params=params,
        )
        response.raise_for_status()

    data = response.json()
    run = data[0] if data else None
    if run and run.get('status') == 'running' and run.get('started_at'):
        started = datetime.fromisoformat(run['started_at'].replace('Z', '+00:00'))
        if (datetime.now(timezone.utc)-started).total_seconds() > max(300, int(os.getenv('DATION_STALE_RUN_SECONDS', '600'))):
            values = {'status':'error','error_message':'La corrida excedió el tiempo máximo. Volvé a ejecutarla.',
                      'finished_at':datetime.now(timezone.utc).isoformat()}
            from app.services.dispatch_service import db
            updated = await db('PATCH', 'decision_runs', params={'id':f'eq.{run_id}','status':'eq.running'}, body=values)
            if updated: run = updated[0]
    return run
