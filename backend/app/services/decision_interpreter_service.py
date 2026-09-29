import json
from uuid import uuid4

import httpx

from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.services.decision_context import build_decision_context
from app.services.knowledge_service import load_logistics_knowledge
from app.services.llm_service import (
    chat_completion,
    llm_settings,
    structured_completion,
)
from app.services.run_service import get_run


PROMPT_VERSION = "decision_interpreter_v0.1"

EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "recommendation": {"type": "string"},
        "why_recommended": {"type": "string"},
        "business_impact": {
            "type": "object",
            "properties": {
                "cost": {"type": "string"},
                "trips": {"type": "string"},
                "distance": {"type": "string"},
            },
            "required": ["cost", "trips", "distance"],
            "additionalProperties": False,
        },
        "key_drivers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tradeoffs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "assumptions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "caveats": {
            "type": "array",
            "items": {"type": "string"},
        },
        "suggested_questions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "executive_summary",
        "recommendation",
        "why_recommended",
        "business_impact",
        "key_drivers",
        "tradeoffs",
        "assumptions",
        "caveats",
        "suggested_questions",
    ],
    "additionalProperties": False,
}


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }


def _system_prompt(knowledge: dict, context: dict) -> str:
    return f"""You are Dation Decision Interpreter for the Logistics DDA.

Your job is to explain a deterministic decision result in business Spanish.
The Python engine has already calculated the decision. Do not replace it,
re-optimize it, or invent missing data.

KNOWLEDGE VERSION:
{knowledge['version']}

KNOWLEDGE BASE:
{knowledge['content']}

DECISION EVIDENCE:
{json.dumps(context, ensure_ascii=False)}

Follow the knowledge contract strictly. Every quantitative statement must be
grounded in DECISION EVIDENCE. Treat the recommendation as conditional on the
selected objective and the model assumptions. If the evidence cannot answer a
question, say what additional data or model capability would be needed.
"""


async def _insert_explanation(
    *,
    run_id: str,
    provider: str,
    model: str,
    knowledge_version: str,
    response_json: dict,
    usage_json: dict,
) -> dict:
    payload = {
        "id": str(uuid4()),
        "run_id": run_id,
        "provider": provider,
        "model": model,
        "knowledge_version": knowledge_version,
        "prompt_version": PROMPT_VERSION,
        "response_json": response_json,
        "usage_json": usage_json,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/decision_explanations",
            headers={
                **_headers(),
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=payload,
        )
        response.raise_for_status()

    return response.json()[0]


async def _recent_messages(run_id: str, limit: int = 8) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/decision_messages",
            headers=_headers(),
            params={
                "select": "role,content,created_at",
                "run_id": f"eq.{run_id}",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        response.raise_for_status()

    messages = response.json()
    messages.reverse()

    return [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in messages
    ]


async def _insert_message(
    *,
    run_id: str,
    role: str,
    content: str,
    provider: str | None = None,
    model: str | None = None,
    knowledge_version: str | None = None,
) -> None:
    payload = {
        "id": str(uuid4()),
        "run_id": run_id,
        "role": role,
        "content": content,
        "provider": provider,
        "model": model,
        "knowledge_version": knowledge_version,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/decision_messages",
            headers={
                **_headers(),
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()


async def _load_completed_run(run_id: str) -> dict:
    run = await get_run(run_id)

    if not run:
        raise LookupError("Decision run not found.")

    if run.get("status") != "completed" or not run.get("result_json"):
        raise ValueError(
            "The decision run must be completed before it can be interpreted."
        )

    return run


async def generate_explanation(run_id: str) -> dict:
    run = await _load_completed_run(run_id)
    knowledge = load_logistics_knowledge()
    context = build_decision_context(run["result_json"])

    response = await structured_completion(
        messages=[
            {
                "role": "system",
                "content": _system_prompt(knowledge, context),
            },
            {
                "role": "user",
                "content": (
                    "Generá la explicación ejecutiva inicial de esta decisión. "
                    "Respondé en español y respetá estrictamente el JSON Schema."
                ),
            },
        ],
        response_schema=EXPLANATION_SCHEMA,
    )

    stored = await _insert_explanation(
        run_id=run_id,
        provider=response["provider"],
        model=response["model"],
        knowledge_version=knowledge["version"],
        response_json=response["parsed"],
        usage_json=response.get("usage", {}),
    )

    return {
        "id": stored["id"],
        "run_id": run_id,
        "provider": response["provider"],
        "model": response["model"],
        "knowledge_version": knowledge["version"],
        "prompt_version": PROMPT_VERSION,
        "explanation": response["parsed"],
        "usage": response.get("usage", {}),
    }


async def answer_question(
    *,
    run_id: str,
    question: str,
) -> dict:
    run = await _load_completed_run(run_id)
    knowledge = load_logistics_knowledge()
    context = build_decision_context(run["result_json"])
    history = await _recent_messages(run_id)

    response = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": _system_prompt(knowledge, context),
            },
            *history,
            {
                "role": "user",
                "content": question,
            },
        ]
    )

    await _insert_message(
        run_id=run_id,
        role="user",
        content=question,
        knowledge_version=knowledge["version"],
    )
    await _insert_message(
        run_id=run_id,
        role="assistant",
        content=response["content"],
        provider=response["provider"],
        model=response["model"],
        knowledge_version=knowledge["version"],
    )

    return {
        "run_id": run_id,
        "provider": response["provider"],
        "model": response["model"],
        "knowledge_version": knowledge["version"],
        "answer": response["content"],
        "usage": response.get("usage", {}),
    }


def interpreter_status() -> dict:
    settings = llm_settings()
    knowledge = load_logistics_knowledge()

    return {
        "configured": settings["configured"],
        "provider": settings["provider"],
        "model": settings["model"],
        "knowledge_version": knowledge["version"],
        "knowledge_files": knowledge["files"],
        "prompt_version": PROMPT_VERSION,
    }
