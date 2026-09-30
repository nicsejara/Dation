import json
from uuid import uuid4

import httpx

from app.config import (
    SUPABASE_SECRET_KEY,
    SUPABASE_URL,
)
from app.services.decision_context import (
    build_decision_context,
)
from app.services.knowledge_service import (
    load_logistics_knowledge,
    load_logistics_knowledge_for_question,
)
from app.services.llm_service import (
    chat_completion,
    llm_settings,
    structured_completion,
)
from app.services.run_service import get_run


PROMPT_VERSION = "decision_interpreter_v0.3"

EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {
            "type": "string"
        },
        "recommendation": {
            "type": "string"
        },
        "why_recommended": {
            "type": "string"
        },
        "business_impact": {
            "type": "object",
            "properties": {
                "cost": {
                    "type": "string"
                },
                "trips": {
                    "type": "string"
                },
                "distance": {
                    "type": "string"
                },
            },
            "required": [
                "cost",
                "trips",
                "distance",
            ],
            "additionalProperties": False,
        },
        "key_drivers": {
            "type": "array",
            "items": {
                "type": "string"
            },
        },
        "tradeoffs": {
            "type": "array",
            "items": {
                "type": "string"
            },
        },
        "assumptions": {
            "type": "array",
            "items": {
                "type": "string"
            },
        },
        "caveats": {
            "type": "array",
            "items": {
                "type": "string"
            },
        },
        "suggested_questions": {
            "type": "array",
            "items": {
                "type": "string"
            },
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
        "Authorization": (
            f"Bearer {SUPABASE_SECRET_KEY}"
        ),
    }


def _system_prompt(
    knowledge: dict,
    context: dict,
) -> str:
    return f"""Sos Dation Decision Interpreter para el DDA Logística.

Tu tarea es explicar en español profesional una decisión ya calculada
por un motor determinístico. No reemplaces el cálculo, no vuelvas a
optimizar y no inventes datos faltantes.

La evidencia puede incluir una configuración predefinida o una
ponderación personalizada entre costo y viajes. Si existe sensibilidad,
compará la configuración seleccionada con los extremos 100% costo y
100% viajes únicamente a partir de los valores provistos.

REGLA CRÍTICA DE IDENTIDAD DE LA DECISIÓN:
Si selection_semantics.requested_mode es "custom", la decisión debe
nombrarse siempre como "Configuración personalizada" e incluir sus pesos.
Aunque la asignación coincida con min_cost, min_trips o ambos extremos,
esa coincidencia es un hallazgo de sensibilidad. Nunca renombres una
decisión personalizada como "Costo mínimo" o "Viajes mínimos".

REGLA CRÍTICA DE GLOSARIO:
baseline representa la asignación de vehículo informada en el CSV y en
la experiencia de producto debe llamarse siempre "Asignación actual".
La solución calculada debe llamarse "Decisión recomendada". No expongas
la palabra baseline, nombres snake_case ni códigos crudos de vehículos.
Usá Camión S, Camión M y Camión L. Formateá números y porcentajes en
estilo es-AR, por ejemplo 26,3 % y 150.610 km.

VERSIÓN DE CONOCIMIENTO:
{knowledge['version']}

BASE DE CONOCIMIENTO:
{knowledge['content']}

EVIDENCIA DE LA DECISIÓN:
{json.dumps(context, ensure_ascii=False)}

Seguí estrictamente el contrato de conocimiento. Toda afirmación
cuantitativa debe estar sustentada por EVIDENCIA DE LA DECISIÓN.
La recomendación siempre es condicional a la configuración seleccionada
y a los supuestos del modelo. Nunca la presentes como la mejor opción
en términos absolutos. Si la evidencia no permite responder algo,
indicá qué dato o capacidad del modelo haría falta.
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
        "knowledge_version": (
            knowledge_version
        ),
        "prompt_version": PROMPT_VERSION,
        "response_json": response_json,
        "usage_json": usage_json,
    }

    async with httpx.AsyncClient(
        timeout=15.0
    ) as client:
        response = await client.post(
            (
                f"{SUPABASE_URL}/rest/v1/"
                "decision_explanations"
            ),
            headers={
                **_headers(),
                "Content-Type": (
                    "application/json"
                ),
                "Prefer": (
                    "return=representation"
                ),
            },
            json=payload,
        )
        response.raise_for_status()

    return response.json()[0]


async def _recent_messages(
    run_id: str,
    limit: int = 2,
) -> list[dict]:
    async with httpx.AsyncClient(
        timeout=15.0
    ) as client:
        response = await client.get(
            (
                f"{SUPABASE_URL}/rest/v1/"
                "decision_messages"
            ),
            headers=_headers(),
            params={
                "select": (
                    "role,content,created_at"
                ),
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
        "knowledge_version": (
            knowledge_version
        ),
    }

    async with httpx.AsyncClient(
        timeout=15.0
    ) as client:
        response = await client.post(
            (
                f"{SUPABASE_URL}/rest/v1/"
                "decision_messages"
            ),
            headers={
                **_headers(),
                "Content-Type": (
                    "application/json"
                ),
            },
            json=payload,
        )
        response.raise_for_status()


async def _load_completed_run(
    run_id: str,
) -> dict:
    run = await get_run(run_id)

    if not run:
        raise LookupError(
            "No se encontró la corrida solicitada."
        )

    if (
        run.get("status") != "completed"
        or not run.get("result_json")
    ):
        raise ValueError(
            "La corrida debe estar completada "
            "antes de poder interpretarla."
        )

    return run


async def generate_explanation(
    run_id: str,
) -> dict:
    run = await _load_completed_run(
        run_id
    )
    knowledge = (
        load_logistics_knowledge()
    )
    context = build_decision_context(
        run["result_json"],
        run.get("configuration_json"),
    )

    response = await structured_completion(
        messages=[
            {
                "role": "system",
                "content": _system_prompt(
                    knowledge,
                    context,
                ),
            },
            {
                "role": "user",
                "content": (
                    "Generá la explicación ejecutiva "
                    "inicial de esta decisión. "
                    "Respondé únicamente en español "
                    "y respetá estrictamente el "
                    "JSON Schema."
                ),
            },
        ],
        response_schema=(
            EXPLANATION_SCHEMA
        ),
    )

    stored = await _insert_explanation(
        run_id=run_id,
        provider=response["provider"],
        model=response["model"],
        knowledge_version=(
            knowledge["version"]
        ),
        response_json=response["parsed"],
        usage_json=response.get(
            "usage",
            {},
        ),
    )

    return {
        "id": stored["id"],
        "run_id": run_id,
        "provider": response["provider"],
        "model": response["model"],
        "knowledge_version": (
            knowledge["version"]
        ),
        "prompt_version": PROMPT_VERSION,
        "explanation": response["parsed"],
        "usage": response.get(
            "usage",
            {},
        ),
    }


async def answer_question(
    *,
    run_id: str,
    question: str,
) -> dict:
    run = await _load_completed_run(
        run_id
    )
    knowledge = (
        load_logistics_knowledge_for_question(
            question
        )
    )
    context = build_decision_context(
        run["result_json"],
        run.get("configuration_json"),
    )
    history = await _recent_messages(
        run_id
    )

    response = await chat_completion(
        messages=[
            {
                "role": "system",
                "content": _system_prompt(
                    knowledge,
                    context,
                ),
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
        knowledge_version=(
            knowledge["version"]
        ),
    )
    await _insert_message(
        run_id=run_id,
        role="assistant",
        content=response["content"],
        provider=response["provider"],
        model=response["model"],
        knowledge_version=(
            knowledge["version"]
        ),
    )

    return {
        "run_id": run_id,
        "provider": response["provider"],
        "model": response["model"],
        "knowledge_version": (
            knowledge["version"]
        ),
        "answer": response["content"],
        "usage": response.get(
            "usage",
            {},
        ),
    }


async def get_saved_interpretation(
    run_id: str,
) -> dict:
    async with httpx.AsyncClient(
        timeout=15.0
    ) as client:
        explanation_response = (
            await client.get(
                (
                    f"{SUPABASE_URL}/rest/v1/"
                    "decision_explanations"
                ),
                headers=_headers(),
                params={
                    "select": "*",
                    "run_id": (
                        f"eq.{run_id}"
                    ),
                    "order": (
                        "created_at.desc"
                    ),
                    "limit": "1",
                },
            )
        )

        messages_response = (
            await client.get(
                (
                    f"{SUPABASE_URL}/rest/v1/"
                    "decision_messages"
                ),
                headers=_headers(),
                params={
                    "select": (
                        "role,content,"
                        "created_at,provider,"
                        "model,"
                        "knowledge_version"
                    ),
                    "run_id": (
                        f"eq.{run_id}"
                    ),
                    "order": (
                        "created_at.asc"
                    ),
                    "limit": "50",
                },
            )
        )

        explanation_response.raise_for_status()
        messages_response.raise_for_status()

    explanations = (
        explanation_response.json()
    )

    return {
        "run_id": run_id,
        "explanation": (
            explanations[0]
            if explanations
            else None
        ),
        "messages": (
            messages_response.json()
        ),
    }


def interpreter_status() -> dict:
    settings = llm_settings()
    knowledge = (
        load_logistics_knowledge()
    )

    return {
        "configured": (
            settings["configured"]
        ),
        "provider": settings["provider"],
        "model": settings["model"],
        "knowledge_version": (
            knowledge["version"]
        ),
        "knowledge_files": (
            knowledge["files"]
        ),
        "prompt_version": PROMPT_VERSION,
    }
