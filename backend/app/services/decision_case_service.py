"""Persistent Decision Case storage, run history and lineage synchronization."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.config import SUPABASE_URL
from app.services.run_service import _headers, get_dataset, get_run


CASE_SCHEMA_VERSION = "decision_case_v2"
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
UPSTREAM_NODE = {
    "logistics_scheduling": "logistics_assignment",
    "logistics_final_assignment": "logistics_scheduling",
}
RUN_SCHEMA_BY_NODE = {
    "logistics_assignment": "assignment_v1",
    "logistics_scheduling": "scheduling_v1",
}
RUN_HISTORY_SELECT = (
    "id,decision_case_id,node_id,upstream_run_id,created_at,started_at,"
    "finished_at,engine_name,engine_version,configuration_json,status,"
    "error_message,duration_ms,schema_version,input_fingerprint,"
    "result_fingerprint,summary_json,progress_json,approved_at,"
    "superseded_at,superseded_by_run_id"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def input_signature(orders_dataset_id: str, fleet_dataset_id: str) -> str:
    return f"{orders_dataset_id}:{fleet_dataset_id}"


def _node_state(status: str) -> dict:
    return {
        "status": status,
        "run_id": None,
        "latest_run_id": None,
        "approved_run_id": None,
        "run_count": 0,
        "latest_execution_status": None,
        "approved_at": None,
        "error": None,
    }


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
            "logistics_assignment": _node_state("available"),
            "logistics_scheduling": _node_state("locked"),
            "logistics_final_assignment": _node_state("locked"),
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
        try:
            node["run_count"] = max(0, int(node.get("run_count") or 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Conteo de corridas inválido para {node_id}.") from exc
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
        "schema_version": CASE_SCHEMA_VERSION,
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


async def list_case_runs(
    case_id: str,
    *,
    node_id: str | None = None,
    limit: int = 1000,
    offset: int = 0,
) -> list[dict]:
    if node_id is not None and node_id not in NODE_IDS:
        raise ValueError("Nodo de Decision Case inválido.")
    params = {
        "select": RUN_HISTORY_SELECT,
        "decision_case_id": f"eq.{case_id}",
        "order": "created_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    if node_id is not None:
        params["node_id"] = f"eq.{node_id}"
    return await _db("GET", "decision_runs", params=params) or []


def _execution_node_status(run: dict) -> str:
    status = run.get("status")
    if status in {"queued", "running"}:
        return "running"
    if status == "error":
        return "error"
    return "review"


def _state_with_history(
    state: dict,
    runs: list[dict],
    *,
    case_id: str,
    orders_dataset_id: str,
    fleet_dataset_id: str,
) -> dict:
    canonical = _validate_state(
        state,
        case_id=case_id,
        orders_dataset_id=orders_dataset_id,
        fleet_dataset_id=fleet_dataset_id,
    )
    grouped = {node_id: [] for node_id in NODE_IDS}
    for run in runs:
        node_id = run.get("node_id")
        if node_id in grouped:
            grouped[node_id].append(run)

    current_approved: dict[str, dict | None] = {}
    for node_id in NODE_IDS:
        entries = grouped[node_id]
        node = canonical["nodes"][node_id]
        latest = entries[0] if entries else None
        approved = next(
            (
                run
                for run in entries
                if run.get("approved_at") and not run.get("superseded_at")
            ),
            None,
        )
        current_approved[node_id] = approved
        node["run_count"] = len(entries)
        node["latest_run_id"] = latest.get("id") if latest else None
        node["latest_execution_status"] = (
            latest.get("status") if latest else None
        )
        node["approved_run_id"] = approved.get("id") if approved else None
        node["approved_at"] = approved.get("approved_at") if approved else None

        if approved:
            node["run_id"] = approved["id"]
            node["status"] = "approved"
            node["error"] = None
        elif latest:
            node["run_id"] = latest["id"]
            node["status"] = _execution_node_status(latest)
            node["error"] = (
                latest.get("error_message")
                if latest.get("status") == "error"
                else None
            )
        else:
            node["run_id"] = None
            node["approved_at"] = None
            node["error"] = None
            if node["status"] in {"running", "review", "approved", "error", "stale"}:
                node["status"] = (
                    "available"
                    if node_id == "logistics_assignment"
                    else "locked"
                )

    assignment = current_approved["logistics_assignment"]
    scheduling = current_approved["logistics_scheduling"]
    final_assignment = current_approved["logistics_final_assignment"]

    scheduling_node = canonical["nodes"]["logistics_scheduling"]
    if scheduling:
        if (
            not assignment
            or str(scheduling.get("upstream_run_id")) != str(assignment.get("id"))
        ):
            scheduling_node["status"] = "stale"
        else:
            scheduling_node["status"] = "approved"
    elif not grouped["logistics_scheduling"]:
        if assignment:
            if scheduling_node["status"] != "needs_data":
                scheduling_node["status"] = "available"
        elif scheduling_node["status"] != "needs_data":
            scheduling_node["status"] = "locked"

    final_node = canonical["nodes"]["logistics_final_assignment"]
    if final_assignment:
        if (
            scheduling_node["status"] != "approved"
            or not scheduling
            or str(final_assignment.get("upstream_run_id")) != str(scheduling.get("id"))
        ):
            final_node["status"] = "stale"
        else:
            final_node["status"] = "approved"
    elif not grouped["logistics_final_assignment"]:
        if scheduling and scheduling_node["status"] == "approved":
            if final_node["status"] != "needs_data":
                final_node["status"] = "available"
        elif final_node["status"] != "needs_data":
            final_node["status"] = "locked"

    return canonical


async def sync_case_history(case_id: str) -> dict:
    row = await get_case_row(case_id)
    if not row:
        raise LookupError("No se encontró el Decision Case.")
    runs = await list_case_runs(case_id)
    state = _state_with_history(
        row.get("state_json") or {},
        runs,
        case_id=case_id,
        orders_dataset_id=str(row["orders_dataset_id"]),
        fleet_dataset_id=str(row["fleet_dataset_id"]),
    )
    return await update_case(case_id, state=state)


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

    if status == "approved":
        node.update(
            {
                "status": "approved",
                "run_id": run_id,
                "latest_run_id": run_id,
                "approved_run_id": run_id,
                "latest_execution_status": "completed",
                "approved_at": approved_at,
                "error": None,
            }
        )
    else:
        if run_id:
            node["latest_run_id"] = run_id
        node["latest_execution_status"] = {
            "running": "running",
            "review": "completed",
            "error": "error",
        }.get(status, node.get("latest_execution_status"))
        if node.get("approved_run_id"):
            node["run_id"] = node["approved_run_id"]
            if node.get("status") != "stale":
                node["status"] = "approved"
            node["error"] = None
        else:
            node["status"] = status
            node["run_id"] = run_id
            node["approved_at"] = None
            node["error"] = error if status == "error" else None

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


async def validate_upstream_run(
    case_id: str,
    node_id: str,
    source_run_id: str,
) -> dict:
    expected_node = UPSTREAM_NODE.get(node_id)
    if not expected_node:
        raise ValueError("La decisión no admite una corrida upstream.")
    source = await get_run(source_run_id)
    if (
        not source
        or str(source.get("decision_case_id")) != str(case_id)
        or source.get("node_id") != expected_node
        or source.get("status") != "completed"
        or not source.get("approved_at")
        or source.get("superseded_at") is not None
    ):
        raise ValueError(
            "La corrida upstream ya no es la decisión aprobada vigente del caso."
        )
    return source


async def approve_run_version(
    run_id: str,
    *,
    case_id: str,
    node_id: str,
) -> dict:
    expected_schema = RUN_SCHEMA_BY_NODE.get(node_id)
    if not expected_schema:
        raise ValueError("Ese nodo todavía no admite aprobación persistida.")
    run = await get_run(run_id)
    if (
        not run
        or run.get("status") != "completed"
        or run.get("schema_version") != expected_schema
        or str(run.get("decision_case_id")) != str(case_id)
        or run.get("node_id") != node_id
    ):
        raise ValueError("La corrida no puede aprobarse para ese Decision Case.")
    if run.get("upstream_run_id"):
        await validate_upstream_run(
            case_id,
            node_id,
            str(run["upstream_run_id"]),
        )
    rows = await _db(
        "POST",
        "rpc/approve_decision_run_version",
        body={
            "target_run_id": run_id,
            "target_case_id": case_id,
            "target_node_id": node_id,
        },
    )
    if not rows:
        raise ValueError("No se pudo persistir la aprobación de la corrida.")
    return rows[0]


def _history_item(run: dict, state: dict) -> dict:
    node = state["nodes"].get(run.get("node_id"), {})
    if run.get("superseded_at"):
        decision_state = "superseded"
    elif run.get("approved_at"):
        decision_state = "approved"
    elif run.get("status") == "completed":
        decision_state = "candidate"
    elif run.get("status") in {"queued", "running"}:
        decision_state = "running"
    else:
        decision_state = "error"
    return {
        **run,
        "decision_state": decision_state,
        "is_latest": str(node.get("latest_run_id")) == str(run.get("id")),
        "is_current_approved": (
            str(node.get("approved_run_id")) == str(run.get("id"))
        ),
    }


async def get_run_history(
    case_id: str,
    *,
    node_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    row = await get_case_row(case_id)
    if not row:
        raise LookupError("No se encontró el Decision Case.")
    all_runs = await list_case_runs(case_id, node_id=node_id)
    state = _state_with_history(
        row.get("state_json") or {},
        all_runs,
        case_id=case_id,
        orders_dataset_id=str(row["orders_dataset_id"]),
        fleet_dataset_id=str(row["fleet_dataset_id"]),
    )
    page = all_runs[offset : offset + limit]
    if node_id:
        node = state["nodes"][node_id]
        summary = {
            "run_count": node["run_count"],
            "latest_run_id": node["latest_run_id"],
            "approved_run_id": node["approved_run_id"],
            "status": node["status"],
        }
        total = node["run_count"]
    else:
        summary = {
            key: {
                "run_count": value["run_count"],
                "latest_run_id": value["latest_run_id"],
                "approved_run_id": value["approved_run_id"],
                "status": value["status"],
            }
            for key, value in state["nodes"].items()
        }
        total = sum(value["run_count"] for value in state["nodes"].values())
    return {
        "case_id": case_id,
        "node_id": node_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "summary": summary,
        "runs": [_history_item(run, state) for run in page],
    }


async def get_case(case_id: str) -> dict:
    row = await get_case_row(case_id)
    if not row:
        raise LookupError("No se encontró el Decision Case.")
    orders, fleet, runs = await asyncio.gather(
        get_dataset(str(row["orders_dataset_id"])),
        get_dataset(str(row["fleet_dataset_id"])),
        list_case_runs(case_id),
    )
    if not orders or not fleet:
        raise LookupError("No se encontró el Data Pack del Decision Case.")
    if orders.get("dataset_type") != "orders" or fleet.get("dataset_type") != "fleet":
        raise ValueError("El Data Pack del Decision Case no conserva sus tipos.")
    state = _state_with_history(
        row.get("state_json") or {},
        runs,
        case_id=case_id,
        orders_dataset_id=str(row["orders_dataset_id"]),
        fleet_dataset_id=str(row["fleet_dataset_id"]),
    )
    return {
        "case": row,
        "decision_case": state,
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
        state = _validate_state(
            row.get("state_json") or {},
            case_id=str(row["id"]),
            orders_dataset_id=str(row["orders_dataset_id"]),
            fleet_dataset_id=str(row["fleet_dataset_id"]),
        )
        return {
            "case": row,
            "decision_case": state,
            "orders": orders,
            "fleet": fleet,
        }

    return await asyncio.gather(*(hydrate(row) for row in rows))
