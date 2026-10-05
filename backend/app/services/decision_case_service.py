"""Persistent Decision Case storage and state synchronization."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.config import SUPABASE_URL
from app.services.run_service import _headers, get_dataset


CASE_SCHEMA_VERSION = "decision_case_v1"
CASE_DOMAIN = "logistics"
CASE_STATUSES = {"active", "completed", "archived"}
NODE_IDS = (
    "logistics_assignment",
    "logistics_scheduling",
    "logistics_final_assignment",
)
NODE_STATUS = {
    "available",
    "running",
    "review",
    "approved",
    "locked",
    "needs_data",
    "error",
    "stale",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def input_signature(orders_dataset_id: str, fleet_dataset_id: str) -> str:
    return f"{orders_dataset_id}:{fleet_dataset_id}"


def _base_state(
    case_id: str,
    orders_dataset_id: str,
    fleet_dataset_id: str,
    *,
    created_at: str | None = None,
) -> dict:
    now = created_at or _now()
    return {
        "schema_version": CASE_SCHEMA_VERSION,
        "id": case_id,
        "domain": CASE_DOMAIN,
        "signature": input_signature(orders_dataset_id, fleet_dataset_id),
        "created_at": now,
        "updated_at": now,
        "inputs": {
            "orders_dataset_id": orders_dataset_id,
            "fleet_dataset_id": fleet_dataset_id,
        },
        "stale_predecessor": None,
        "nodes": {
            "logistics_assignment": {
                "status": "available",
                "run_id": None,
                "approved_at": None,
                "error": None,
            },
            "logistics_scheduling": {
                "status": "locked",
                "run_id": None,
                "approved_at": None,
                "error": None,
            },
            "logistics_final_assignment": {
                "status": "locked",
                "run_id": None,
                "approved_at": None,
                "error": None,
            },
        },
    }


async def _db(method: str, path: str, *, params=None, body=None):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers={
                **_headers(),
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            params=params,
            json=body,
        )
        response.raise_for_status()
        return response.json() if response.content else None


async def _validate_data_pack(orders_dataset_id: str, fleet_dataset_id: str):
    orders, fleet = await asyncio.gather(
        get_dataset(orders_dataset_id),
        get_dataset(fleet_dataset_id),
    )
    if not orders or not fleet:
        raise LookupError("No se encontró el Data Pack del Decision Case.")
    if orders.get("dataset_type") != "orders":
        raise ValueError("El Decision Case requiere un dataset de Órdenes.")
    if fleet.get("dataset_type") != "fleet":
        raise ValueError("El Decision Case requiere un dataset de Flota.")
    return orders, fleet


def _validate_state(
    state: dict,
    *,
    case_id: str,
    orders_dataset_id: str,
    fleet_dataset_id: str,
) -> dict:
    if not isinstance(state, dict):
        raise ValueError("El estado del Decision Case debe ser un objeto.")
    if state.get("id") not in (None, case_id):
        raise ValueError("El estado corresponde a otro Decision Case.")
    inputs = state.get("inputs") or {}
    if inputs.get("orders_dataset_id") not in (None, orders_dataset_id):
        raise ValueError("El estado referencia otro dataset de Órdenes.")
    if inputs.get("fleet_dataset_id") not in (None, fleet_dataset_id):
        raise ValueError("El estado referencia otro dataset de Flota.")

    canonical = {
        **_base_state(
            case_id,
            orders_dataset_id,
            fleet_dataset_id,
            created_at=state.get("created_at"),
        ),
        **state,
        "schema_version": CASE_SCHEMA_VERSION,
        "id": case_id,
        "domain": CASE_DOMAIN,
        "signature": input_signature(orders_dataset_id, fleet_dataset_id),
        "inputs": {
            "orders_dataset_id": orders_dataset_id,
            "fleet_dataset_id": fleet_dataset_id,
        },
    }
    nodes = canonical.get("nodes") or {}
    base_nodes = _base_state(
        case_id,
        orders_dataset_id,
        fleet_dataset_id,
    )["nodes"]
    canonical["nodes"] = {
        node_id: {
            **base_nodes[node_id],
            **(nodes.get(node_id) or {}),
        }
        for node_id in NODE_IDS
    }
    for node_id, node in canonical["nodes"].items():
        if node.get("status") not in NODE_STATUS:
            raise ValueError(f"Estado inválido para {node_id}.")
    return canonical


async def get_case_row(case_id: str) -> dict | None:
    rows = await _db(
        "GET",
        "decision_cases",
        params={
            "select": "*",
            "id": f"eq.{case_id}",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


async def ensure_case(
    case_id: str,
    orders_dataset_id: str,
    fleet_dataset_id: str,
    *,
    state: dict | None = None,
) -> dict:
    existing = await get_case_row(case_id)
    if existing:
        if (
            str(existing["orders_dataset_id"]) != str(orders_dataset_id)
            or str(existing["fleet_dataset_id"]) != str(fleet_dataset_id)
        ):
            raise ValueError(
                "El Decision Case ya existe y pertenece a otro Data Pack."
            )
        if state is not None:
            return await update_case(
                case_id,
                state=state,
            )
        return existing

    await _validate_data_pack(orders_dataset_id, fleet_dataset_id)
    now = _now()
    canonical_state = _validate_state(
        state
        or _base_state(
            case_id,
            orders_dataset_id,
            fleet_dataset_id,
            created_at=now,
        ),
        case_id=case_id,
        orders_dataset_id=orders_dataset_id,
        fleet_dataset_id=fleet_dataset_id,
    )
    canonical_state["created_at"] = canonical_state.get("created_at") or now
    canonical_state["updated_at"] = now

    rows = await _db(
        "POST",
        "decision_cases",
        body={
            "id": case_id,
            "schema_version": CASE_SCHEMA_VERSION,
            "domain": CASE_DOMAIN,
            "status": "active",
            "orders_dataset_id": orders_dataset_id,
            "fleet_dataset_id": fleet_dataset_id,
            "input_signature": input_signature(
                orders_dataset_id,
                fleet_dataset_id,
            ),
            "state_json": canonical_state,
            "created_at": canonical_state["created_at"],
            "updated_at": now,
            "last_activity_at": now,
        },
    )
    return rows[0]


async def update_case(
    case_id: str,
    *,
    state: dict | None = None,
    status: str | None = None,
) -> dict:
    row = await get_case_row(case_id)
    if not row:
        raise LookupError("No se encontró el Decision Case.")
    if status is not None and status not in CASE_STATUSES:
        raise ValueError("Estado de Decision Case inválido.")

    now = _now()
    values: dict = {
        "updated_at": now,
        "last_activity_at": now,
    }
    if status is not None:
        values["status"] = status
        values["archived_at"] = now if status == "archived" else None
    if state is not None:
        canonical_state = _validate_state(
            state,
            case_id=case_id,
            orders_dataset_id=str(row["orders_dataset_id"]),
            fleet_dataset_id=str(row["fleet_dataset_id"]),
        )
        canonical_state["created_at"] = (
            canonical_state.get("created_at")
            or row["created_at"]
        )
        canonical_state["updated_at"] = now
        values["state_json"] = canonical_state

    rows = await _db(
        "PATCH",
        "decision_cases",
        params={"id": f"eq.{case_id}"},
        body=values,
    )
    if not rows:
        raise LookupError("No se encontró el Decision Case.")
    return rows[0]


async def record_node_state(
    case_id: str,
    node_id: str,
    *,
    run_id: str | None,
    status: str,
    approved_at: str | None = None,
    error: str | None = None,
) -> dict:
    if node_id not in NODE_IDS:
        raise ValueError("Nodo de Decision Case inválido.")
    if status not in NODE_STATUS:
        raise ValueError("Estado de nodo inválido.")

    row = await get_case_row(case_id)
    if not row:
        raise LookupError("No se encontró el Decision Case.")
    state = _validate_state(
        row.get("state_json") or {},
        case_id=case_id,
        orders_dataset_id=str(row["orders_dataset_id"]),
        fleet_dataset_id=str(row["fleet_dataset_id"]),
    )
    node = state["nodes"][node_id]
    node.update(
        {
            "status": status,
            "run_id": run_id,
            "approved_at": approved_at if status == "approved" else None,
            "error": error if status == "error" else None,
        }
    )

    if status == "approved":
        next_node = {
            "logistics_assignment": "logistics_scheduling",
            "logistics_scheduling": "logistics_final_assignment",
        }.get(node_id)
        if next_node and state["nodes"][next_node]["status"] in {
            "locked",
            "needs_data",
        }:
            state["nodes"][next_node]["status"] = "available"
            state["nodes"][next_node]["error"] = None

    return await update_case(case_id, state=state)


async def get_case(case_id: str) -> dict:
    row = await get_case_row(case_id)
    if not row:
        raise LookupError("No se encontró el Decision Case.")
    orders, fleet = await _validate_data_pack(
        str(row["orders_dataset_id"]),
        str(row["fleet_dataset_id"]),
    )
    return {
        "case": row,
        "decision_case": row.get("state_json") or {},
        "orders": orders,
        "fleet": fleet,
    }


async def list_cases(
    *,
    status: str | None = "active",
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    if status is not None and status not in CASE_STATUSES:
        raise ValueError("Estado de Decision Case inválido.")
    params = {
        "select": "*",
        "order": "last_activity_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    if status is not None:
        params["status"] = f"eq.{status}"
    rows = await _db("GET", "decision_cases", params=params) or []

    async def hydrate(row: dict) -> dict:
        orders, fleet = await _validate_data_pack(
            str(row["orders_dataset_id"]),
            str(row["fleet_dataset_id"]),
        )
        return {
            "case": row,
            "decision_case": row.get("state_json") or {},
            "orders": orders,
            "fleet": fleet,
        }

    return await asyncio.gather(*(hydrate(row) for row in rows))
