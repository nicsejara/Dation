import asyncio
import json

import httpx

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
)


DEFAULTS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-5-mini",
    },
}


def llm_settings() -> dict:
    provider = (LLM_PROVIDER or "groq").strip().lower()

    if provider not in DEFAULTS:
        raise RuntimeError(
            "Unsupported LLM_PROVIDER. Use 'groq' or 'openai'."
        )

    defaults = DEFAULTS[provider]

    return {
        "provider": provider,
        "base_url": (
            LLM_BASE_URL.rstrip("/")
            if LLM_BASE_URL
            else defaults["base_url"]
        ),
        "model": LLM_MODEL or defaults["model"],
        "configured": bool(LLM_API_KEY),
    }


def llm_configured() -> bool:
    return llm_settings()["configured"]


def _retry_delay(response: httpx.Response) -> float:
    value = response.headers.get("retry-after")

    if value:
        try:
            return max(float(value), 1.0)
        except ValueError:
            pass

    return 3.0


async def chat_completion(
    *,
    messages: list[dict],
    response_schema: dict | None = None,
) -> dict:
    settings = llm_settings()

    if not settings["configured"]:
        raise RuntimeError(
            "LLM is not configured. Add LLM_API_KEY in Cloud Run."
        )

    payload: dict = {
        "model": settings["model"],
        "messages": messages,
        "max_completion_tokens": 1200 if response_schema else 500,
    }

    if settings["provider"] == "groq":
        payload["reasoning_effort"] = "low"

    if response_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "dation_decision_explanation",
                "strict": True,
                "schema": response_schema,
            },
        }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        # Free tiers can momentarily hit tokens-per-minute limits.
        # Retry once using the provider's requested cooldown.
        if response.status_code == 429:
            await asyncio.sleep(_retry_delay(response))
            response = await client.post(
                f"{settings['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        response.raise_for_status()

    body = response.json()
    content = body["choices"][0]["message"]["content"]

    return {
        "provider": settings["provider"],
        "model": settings["model"],
        "content": content,
        "usage": body.get("usage", {}),
        "raw_id": body.get("id"),
    }


async def structured_completion(
    *,
    messages: list[dict],
    response_schema: dict,
) -> dict:
    response = await chat_completion(
        messages=messages,
        response_schema=response_schema,
    )

    try:
        parsed = json.loads(response["content"])
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The LLM returned invalid JSON."
        ) from exc

    response["parsed"] = parsed
    return response
