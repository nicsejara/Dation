import httpx

from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }


async def list_datasets(limit: int = 25) -> list[dict]:
    params = {
        "select": (
            "id,created_at,original_filename,storage_bucket,storage_path,"
            "mime_type,size_bytes,sha256,status,row_count,column_count,"
            "error_message"
        ),
        "order": "created_at.desc",
        "limit": str(limit),
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/datasets",
            headers=_headers(),
            params=params,
        )
        response.raise_for_status()

    return response.json()


async def list_runs(
    *,
    limit: int = 40,
    dataset_id: str | None = None,
) -> list[dict]:
    params = {
        "select": (
            "id,dataset_id,created_at,started_at,finished_at,"
            "engine_name,engine_version,configuration_json,status,"
            "duration_ms,error_message"
        ),
        "order": "created_at.desc",
        "limit": str(limit),
    }

    if dataset_id:
        params["dataset_id"] = f"eq.{dataset_id}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/decision_runs",
            headers=_headers(),
            params=params,
        )
        response.raise_for_status()

    return response.json()


async def workspace_summary() -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        datasets_response, runs_response = await (
            client.get(
                f"{SUPABASE_URL}/rest/v1/datasets",
                headers={
                    **_headers(),
                    "Prefer": "count=exact",
                    "Range": "0-0",
                },
                params={"select": "id"},
            ),
            client.get(
                f"{SUPABASE_URL}/rest/v1/decision_runs",
                headers={
                    **_headers(),
                    "Prefer": "count=exact",
                    "Range": "0-0",
                },
                params={"select": "id"},
            ),
        )

        datasets_response.raise_for_status()
        runs_response.raise_for_status()

    def count_from(response: httpx.Response) -> int:
        content_range = response.headers.get("content-range", "0-0/0")
        try:
            return int(content_range.rsplit("/", 1)[1])
        except (IndexError, ValueError):
            return 0

    return {
        "datasets": count_from(datasets_response),
        "runs": count_from(runs_response),
    }
