import httpx

from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL, supabase_configured


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Accept": "application/json",
    }


async def check_supabase_connection() -> dict:
    if not supabase_configured():
        return {
            "ok": False,
            "error": "Supabase environment variables are not fully configured.",
        }

    url = f"{SUPABASE_URL}/rest/v1/datasets"
    params = {
        "select": "id",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers=_headers(),
                params=params,
            )

        if response.is_success:
            return {
                "ok": True,
                "database": "reachable",
                "table": "datasets",
                "http_status": response.status_code,
            }

        return {
            "ok": False,
            "database": "unreachable",
            "http_status": response.status_code,
            "error": response.text[:500],
        }

    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "database": "unreachable",
            "error": str(exc),
        }
