"""Pure Decision Case state and authoritative Run-history projection.

No HTTP, tenant context or database access belongs in this module.
"""
from __future__ import annotations

from datetime import datetime, timezone


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def input_signature(orders_dataset_id: str, fleet_dataset_id: str) -> str:
    return f"{orders_dataset_id}:{fleet_dataset_id}"


def create_node_state(status: str) -> dict:
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


def create_case_state(
    case_id: str,
    orders_dataset_id: str,
    fleet_dataset_id: str,
    *,
    created_at: str | None = None,
) -> dict:
    now = created_at or utc_now()
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
            "logistics_assignment": create_node_state("available"),
            "logistics_scheduling": create_node_state("locked"),
            "logistics_final_assignment": create_node_state("locked"),
        },
    }


def validate_case_state(
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
        **create_case_state(
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
    base_nodes = create_case_state(
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


def execution_node_status(run: dict) -> str:
    status = run.get("status")
    if status in {"queued", "running"}:
        return "running"
    if status == "error":
        return "error"
    return "review"


def project_case_history(
    state: dict,
    runs: list[dict],
    *,
    case_id: str,
    orders_dataset_id: str,
    fleet_dataset_id: str,
    summaries: dict | None = None,
) -> dict:
    canonical = validate_case_state(
        state,
        case_id=case_id,
        orders_dataset_id=orders_dataset_id,
        fleet_dataset_id=fleet_dataset_id,
    )
    grouped = {node_id: [] for node_id in NODE_IDS}
    if summaries is not None:
        # At most two rows per node. Current approval may be thousands of runs old.
        runs = []
        for node_id in NODE_IDS:
            summary = summaries[node_id]
            latest, approved = summary.get("latest"), summary.get("approved")
            if latest:
                runs.append(latest)
            if approved and (not latest or approved["id"] != latest["id"]):
                runs.append(approved)
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
        node["run_count"] = summaries[node_id]["run_count"] if summaries is not None else len(entries)
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
            node["status"] = "stale" if latest.get("superseded_at") else execution_node_status(latest)
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
    if grouped["logistics_scheduling"] and (
        not assignment or str(grouped["logistics_scheduling"][0].get("upstream_run_id")) != str(assignment.get("id"))
    ):
        scheduling_node["status"] = "stale"
    elif scheduling:
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


def run_history_item(run: dict, state: dict) -> dict:
    node = state["nodes"].get(run.get("node_id"), {})
    if run.get("superseded_at"):
        decision_state = "superseded"
    elif run.get("approved_at"):
        decision_state = "stale" if node.get("status") == "stale" else "approved"
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
            node.get("status") == "approved" and str(node.get("approved_run_id")) == str(run.get("id"))
        ),
    }
