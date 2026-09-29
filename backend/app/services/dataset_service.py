import hashlib
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.config import (
    SUPABASE_INPUT_BUCKET,
    SUPABASE_SECRET_KEY,
    SUPABASE_URL,
)


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }


async def find_dataset_by_hash(file_hash: str) -> dict | None:
    url = f"{SUPABASE_URL}/rest/v1/datasets"
    params = {
        "select": "id,original_filename,status,created_at",
        "sha256": f"eq.{file_hash}",
        "limit": "1",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=_headers(), params=params)
        response.raise_for_status()

    data = response.json()
    return data[0] if data else None


async def upload_dataset(
    *,
    filename: str,
    contents: bytes,
    mime_type: str,
    row_count: int,
    column_count: int,
) -> dict:
    dataset_id = str(uuid4())
    file_hash = hashlib.sha256(contents).hexdigest()
    storage_path = f"{dataset_id}/input.csv"

    existing = await find_dataset_by_hash(file_hash)
    if existing:
        return {
            "duplicate": True,
            "existing_dataset": existing,
            "sha256": file_hash,
        }

    storage_url = (
        f"{SUPABASE_URL}/storage/v1/object/"
        f"{SUPABASE_INPUT_BUCKET}/{quote(storage_path, safe='/')}"
    )

    storage_headers = {
        **_headers(),
        "Content-Type": mime_type or "text/csv",
        "x-upsert": "false",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        storage_response = await client.post(
            storage_url,
            headers=storage_headers,
            content=contents,
        )
        storage_response.raise_for_status()

        metadata = {
            "id": dataset_id,
            "original_filename": filename,
            "storage_bucket": SUPABASE_INPUT_BUCKET,
            "storage_path": storage_path,
            "mime_type": mime_type or "text/csv",
            "size_bytes": len(contents),
            "sha256": file_hash,
            "status": "uploaded",
            "row_count": row_count,
            "column_count": column_count,
        }

        db_response = await client.post(
            f"{SUPABASE_URL}/rest/v1/datasets",
            headers={
                **_headers(),
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=metadata,
        )

        if not db_response.is_success:
            # Best-effort rollback so Storage and database do not drift.
            await client.delete(storage_url, headers=_headers())
            db_response.raise_for_status()

    created = db_response.json()[0]

    return {
        "duplicate": False,
        "dataset": created,
        "sha256": file_hash,
    }
