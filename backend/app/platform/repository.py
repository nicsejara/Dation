"""The service-key data boundary. Every tenant REST operation is explicitly scoped.

RPCs go through a SQL allowlist that revalidates membership and object ownership
in the same transaction. Infrastructure operations exist only in the worker.
"""
from contextlib import asynccontextmanager
from urllib.parse import unquote, urlsplit

import httpx
from fastapi import HTTPException

from app.config import SUPABASE_URL
from app.platform.context import current, is_infrastructure
from app.services.http_service import http_client as raw_client

TABLES = frozenset({"datasets", "decision_cases", "decision_runs", "dispatch_run_jobs",
    "decision_case_reconciliations", "decision_approval_events", "decision_comparative_analyses",
    "decision_explanations", "decision_messages", "decision_chat_turns", "decision_interpretation_sources"})
INFRA_RPC = frozenset({"claim_dispatch_job", "claim_comparative_analysis", "report_dispatch_worker"})
WORKER_RPC = frozenset({"heartbeat_dispatch_job", "finish_dispatch_job", "heartbeat_comparative_analysis",
    "finish_comparative_analysis", "ack_case_reconciliation", "decision_case_history"})
READ_RPC = frozenset({"list_decision_cases", "decision_case_history", "read_decision_chat_turn",
    "read_decision_chat_turn_with_evidence", "current_decision_explanation", "dispatch_operational_snapshot", "comparative_operational_snapshot"})
WRITE_RPC = frozenset({"enqueue_dispatch_run", "cancel_dispatch_job", "approve_decision_run_version",
    "set_default_fleet", "request_case_reconciliation", "enqueue_comparative_analysis",
    "record_decision_chat_turn", "record_decision_chat_turn_with_evidence", "record_decision_explanation_with_evidence"})


class TenantClient:
    def __init__(self, client):
        self.client = client

    async def request(self, method, url, **options):
        method = method.upper()
        parsed, origin = urlsplit(str(url)), urlsplit(SUPABASE_URL)
        if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc):
            raise RuntimeError("Tenant repository destination is not Supabase.")
        path = unquote(parsed.path)
        if path.startswith("/rest/v1/rpc/"):
            operation = path.rsplit("/", 1)[1]
            if is_infrastructure() and operation in INFRA_RPC:
                return await self.client.request(method, url, **options)
            ctx = current()
            allowed = WORKER_RPC if ctx.worker else READ_RPC | WRITE_RPC
            if operation not in allowed:
                raise HTTPException(403, "La operación no está disponible para este acceso.")
            if operation in WRITE_RPC and ctx.access_role == "viewer":
                raise HTTPException(403, "Tu rol permite consultar, pero no modificar decisiones.")
            options["json"] = {"target_workspace_id": ctx.workspace_id, "actor_user_id": ctx.user_id,
                "operation": operation, "arguments": options.get("json") or dict(options.get("params") or {}), "worker_call": ctx.worker}
            options.pop("params", None)
            response = await self.client.request("POST", SUPABASE_URL + "/rest/v1/rpc/platform_rpc", **options)
            if response.status_code >= 400:
                try: code = response.json().get("code")
                except ValueError: code = None
                if code == "P0002":
                    raise HTTPException(404, "No se encontró el recurso solicitado.")
                if code == "42501":
                    raise HTTPException(403, "No tenés permiso para realizar esta operación.")
            return response
        if path.startswith("/rest/v1/"):
            table = path.removeprefix("/rest/v1/")
            if not table:  # Authorized catalog inspection; it contains no business rows.
                return await self.client.request(method, url, **options)
            if is_infrastructure() and table == "decision_case_reconciliations" and method == "GET":
                return await self.client.request(method, url, **options)
            ctx = current()
            if table not in TABLES:
                raise RuntimeError("Unregistered tenant relation")
            params = httpx.QueryParams(options.get("params") or {})
            if "workspace_id" in params and params["workspace_id"] != "eq." + ctx.workspace_id:
                raise RuntimeError("Conflicting workspace filter")
            options["params"] = params.set("workspace_id", "eq." + ctx.workspace_id)
            if method not in {"GET", "HEAD"}:
                if ctx.access_role == "viewer":
                    raise HTTPException(403, "Tu rol no permite modificar datos.")
                if method in {"POST", "PUT", "PATCH"}:
                    body = options.get("json")
                    rows = body if isinstance(body, list) else [body]
                    for row in rows:
                        if not isinstance(row, dict) or row.get("workspace_id", ctx.workspace_id) != ctx.workspace_id:
                            raise RuntimeError("Invalid tenant payload")
                    options["json"] = ([{**row, "workspace_id": ctx.workspace_id} for row in rows]
                                       if isinstance(body, list) else {**body, "workspace_id": ctx.workspace_id})
            response = await self.client.request(method, url, **options)
            if response.status_code >= 400:
                try: code = response.json().get("code")
                except ValueError: code = None
                if code == "P0002":
                    raise HTTPException(404, "No se encontró el recurso solicitado.")
                if code == "22P02":
                    raise HTTPException(422, "El estado contiene un identificador inválido.")
            if response.status_code == 409:
                # A guessed globally unique ID must not reveal another tenant's resource.
                try:
                    if response.json().get("code") in {"23505", "23503"} and "datasets_dispatch_hash_key" not in response.text:
                        raise HTTPException(404, "No se encontró el recurso solicitado.")
                except ValueError:
                    pass
            return response
        if path.startswith("/storage/v1/bucket/"):
            current()
            return await self.client.request(method, url, **options)
        if path.startswith("/storage/v1/object/"):
            ctx = current()
            relative = path.removeprefix("/storage/v1/object/").removeprefix("authenticated/")
            bucket, _, key = relative.partition("/")
            parts = key.split("/")
            if any(part in {"", ".", ".."} for part in parts):
                raise RuntimeError("Invalid object path")
            if method in {"POST", "DELETE"}:
                if ctx.access_role == "viewer" or len(parts) != 3 or parts[0] != ctx.workspace_id:
                    raise HTTPException(403, "No se puede modificar ese archivo.")
            elif method == "GET":
                # Legacy and new paths require an owned database row BEFORE reading bytes.
                check = await self.request("GET", SUPABASE_URL + "/rest/v1/datasets",
                    headers=options.get("headers"), params={"select": "id", "storage_bucket": "eq." + bucket,
                        "storage_path": "eq." + key, "limit": "1"}, timeout=15)
                check.raise_for_status()
                if not check.json():
                    raise HTTPException(404, "No se encontró el archivo solicitado.")
            else:
                raise RuntimeError("Unsupported Storage operation")
            return await self.client.request(method, url, **options)
        raise RuntimeError("Unsupported tenant repository path")

    async def get(self, url, **options): return await self.request("GET", url, **options)
    async def post(self, url, **options): return await self.request("POST", url, **options)
    async def patch(self, url, **options): return await self.request("PATCH", url, **options)
    async def delete(self, url, **options): return await self.request("DELETE", url, **options)


@asynccontextmanager
async def http_client():
    async with raw_client() as client:
        yield TenantClient(client)
