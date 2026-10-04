"""Versioned input persistence and Dispatch execution services."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
from time import perf_counter
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.config import (
    SUPABASE_INPUT_BUCKET,
    SUPABASE_SECRET_KEY,
    SUPABASE_URL,
    supabase_configured,
)
from app.engines.assignment import (
    ENGINE_NAME as ASSIGNMENT_ENGINE_NAME,
    ENGINE_VERSION as ASSIGNMENT_ENGINE_VERSION,
    SCHEMA_VERSION as ASSIGNMENT_SCHEMA_VERSION,
    run_assignment_engine,
)
from app.engines.assignment.preflight import assignment_preflight
from app.engines.dispatch import (
    ENGINE_NAME,
    ENGINE_VERSION,
    SCHEMA_VERSION,
    run_dispatch_engine,
)
from app.engines.scheduling import (
    ENGINE_NAME as SCHEDULING_ENGINE_NAME,
    ENGINE_VERSION as SCHEDULING_ENGINE_VERSION,
    SCHEMA_VERSION as SCHEDULING_SCHEMA_VERSION,
    run_scheduling_engine,
)
from app.services.run_service import (
    _headers,
    _insert_run,
    download_dataset,
    get_dataset,
    get_run,
)
from app.services.decision_readiness import build_decision_readiness
from app.validators.fleet_schema import (
    validate_fleet_csv,
    validate_fleet_report,
)
from app.validators.orders_schema import (
    validate_orders_csv,
    validate_orders_report,
)


VALIDATORS = {
    "orders": validate_orders_csv,
    "fleet": validate_fleet_csv,
}
REPORT_VALIDATORS = {
    "orders": validate_orders_report,
    "fleet": validate_fleet_report,
}

CANONICAL_TIMEZONE = ZoneInfo("America/Argentina/Cordoba")
CANONICAL_PREFIXES = {
    "orders": "Orders",
    "fleet": "Fleet",
}


def canonical_filename(
    kind: str,
    *,
    now: datetime | None = None,
) -> str:
    if kind not in CANONICAL_PREFIXES:
        raise ValueError("Tipo de dataset inválido.")

    instant = now or datetime.now(CANONICAL_TIMEZONE)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=CANONICAL_TIMEZONE)
    else:
        instant = instant.astimezone(CANONICAL_TIMEZONE)

    timestamp = instant.strftime("%Y%m%d_%H%M%S")
    return f"{CANONICAL_PREFIXES[kind]}_{timestamp}.csv"


async def db(method, path, *, params=None, body=None):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method,
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers={
                **_headers(),
                "Prefer": "return=representation",
            },
            params=params,
            json=body,
        )
        response.raise_for_status()
        return response.json() if response.content else None


def validate_input(filename: str, contents: bytes, kind: str) -> dict:
    if kind not in REPORT_VALIDATORS:
        raise ValueError("Tipo de dataset inválido.")
    report = REPORT_VALIDATORS[kind](contents)
    public = {
        key: value
        for key, value in report.items()
        if key != "records"
    }
    public["file"] = {
        "name": filename,
        "size_bytes": len(contents),
        "sha256": hashlib.sha256(contents).hexdigest(),
    }
    return public


async def _probe_rest(path, params):
    try:
        await db("GET", path, params=params)
        return True, None
    except httpx.HTTPStatusError as exc:
        return False, f"HTTP {exc.response.status_code}"
    except httpx.HTTPError:
        return False, "No se pudo conectar con Supabase."


async def _probe_default_rpc():
    if not supabase_configured():
        return False, "Supabase no está configurado."
    url = f"{SUPABASE_URL}/rest/v1/rpc/set_default_fleet"
    body = {"target_id": "00000000-0000-0000-0000-000000000000"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                headers={
                    **_headers(),
                    "Content-Type": "application/json",
                },
                json=body,
            )
        if response.status_code == 404:
            return False, "La función set_default_fleet no está expuesta."
        if response.status_code < 500:
            return True, "La función está disponible."
        return False, f"Supabase respondió HTTP {response.status_code}."
    except httpx.HTTPError:
        return False, "No se pudo comprobar la función."


async def _probe_bucket():
    if not supabase_configured():
        return False, "Supabase no está configurado."
    url = f"{SUPABASE_URL}/storage/v1/bucket/{quote(SUPABASE_INPUT_BUCKET)}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers={
                    "apikey": SUPABASE_SECRET_KEY,
                    "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
                },
            )
        if response.status_code == 200:
            data = response.json()
            if data.get("public"):
                return False, "El bucket existe pero está configurado como público."
            return True, "Bucket privado disponible."
        return False, f"Bucket no disponible (HTTP {response.status_code})."
    except httpx.HTTPError:
        return False, "No se pudo comprobar el almacenamiento."


async def system_status():
    if not supabase_configured():
        checks = [
            {
                "id": "supabase",
                "label": "Conexión a Supabase",
                "ok": False,
                "detail": "Faltan variables de conexión en el backend.",
                "fix": "Configurá SUPABASE_URL, SUPABASE_SECRET_KEY y SUPABASE_INPUT_BUCKET.",
            },
        ]
        return {
            "available": False,
            "engine_version": ENGINE_VERSION,
            "checks": checks,
            "message": "Activación pendiente: Supabase no está configurado.",
        }

    connection_ok, connection_detail = await _probe_rest(
        "datasets",
        {"select": "id", "limit": "0"},
    )
    datasets_ok, datasets_detail = await _probe_rest(
        "datasets",
        {
            "select": (
                "id,dataset_type,schema_version,label,canonical_filename,is_default,"
                "parent_dataset_id,profile_json,archived_at,is_sample"
            ),
            "limit": "0",
        },
    )
    runs_ok, runs_detail = await _probe_rest(
        "decision_runs",
        {
            "select": (
                "id,schema_version,orders_dataset_id,fleet_dataset_id,"
                "input_fingerprint,result_fingerprint,summary_json,progress_json"
            ),
            "limit": "0",
        },
    )
    rpc_ok, rpc_detail = await _probe_default_rpc()
    bucket_ok, bucket_detail = await _probe_bucket()
    schema_ok = datasets_ok and runs_ok

    checks = [
        {
            "id": "supabase",
            "label": "Conexión a Supabase",
            "ok": connection_ok,
            "detail": (
                "Conexión disponible."
                if connection_ok
                else connection_detail
            ),
            "fix": "Revisá URL, clave secreta y disponibilidad del proyecto.",
        },
        {
            "id": "datasets_schema",
            "label": "Esquema de datasets",
            "ok": datasets_ok,
            "detail": (
                "Columnas de Dispatch y biblioteca visibles."
                if datasets_ok
                else f"Columnas nuevas no visibles ({datasets_detail})."
            ),
            "fix": (
                "Aplicá las migraciones pendientes y ejecutá "
                "NOTIFY pgrst, 'reload schema';"
            ),
        },
        {
            "id": "runs_schema",
            "label": "Esquema de corridas",
            "ok": runs_ok,
            "detail": (
                "Columnas Dispatch visibles."
                if runs_ok
                else f"Columnas nuevas no visibles ({runs_detail})."
            ),
            "fix": (
                "Aplicá las migraciones Dispatch pendientes y recargá el esquema."
            ),
        },
        {
            "id": "set_default_fleet",
            "label": "Cambio de flota vigente",
            "ok": rpc_ok,
            "detail": rpc_detail,
            "fix": "Verificá la función set_default_fleet de la migración Dispatch.",
        },
        {
            "id": "postgrest_schema",
            "label": "Esquema visible para la API",
            "ok": schema_ok,
            "detail": (
                "PostgREST ve las columnas requeridas."
                if schema_ok
                else (
                    "Las columnas no están visibles para la API. "
                    "Puede faltar la migración o la recarga del esquema."
                )
            ),
            "fix": (
                "Verificá las columnas en SQL Editor y luego ejecutá "
                "NOTIFY pgrst, 'reload schema';"
            ),
        },
        {
            "id": "validate_dispatch_run",
            "label": "Control de integridad de corridas",
            "ok": None,
            "detail": (
                "La función trigger no puede verificarse de forma fiable "
                "a través de PostgREST."
            ),
            "fix": (
                "Confirmala en SQL Editor con pg_proc; no bloquea este diagnóstico API."
            ),
        },
        {
            "id": "storage",
            "label": "Almacenamiento privado",
            "ok": bucket_ok,
            "detail": bucket_detail,
            "fix": f"Verificá el bucket privado '{SUPABASE_INPUT_BUCKET}'.",
        },
    ]
    available_now = all(
        check["ok"] is True
        for check in checks
        if check["id"] != "validate_dispatch_run"
    )
    return {
        "available": available_now,
        "engine_version": ENGINE_VERSION,
        "checks": checks,
        "message": (
            None
            if available_now
            else (
                "Activación pendiente: la validación local funciona, "
                "pero todavía no se pueden guardar todos los datos."
            )
        ),
    }


async def available():
    return bool((await system_status())["available"])


async def _ensure_profile(dataset):
    kind = dataset.get("dataset_type")
    if kind not in REPORT_VALIDATORS:
        return dataset

    stored = dataset.get("profile_json") or {}
    profile = stored.get("profile") or {}
    expected_profile_version = {
        "orders": 3,
        "fleet": 4,
    }[kind]
    if profile.get("profile_version") == expected_profile_version:
        return dataset

    try:
        contents = await download_dataset(dataset)
        report = REPORT_VALIDATORS[kind](contents)
        if not report["valid"]:
            return dataset

        public = {
            key: value
            for key, value in report.items()
            if key != "records"
        }
        values = {
            "profile_json": public,
            "row_count": report["rows"],
            "column_count": report["columns"],
        }
        if not dataset.get("label"):
            values["label"] = (
                report.get("suggested_label")
                or dataset.get("original_filename")
            )
        rows = await db(
            "PATCH",
            "datasets",
            params={"id": f"eq.{dataset['id']}"},
            body=values,
        )
        return rows[0] if rows else {**dataset, **values}
    except (httpx.HTTPError, ValueError):
        return dataset


async def list_typed(kind, limit=100, offset=0, q=None, include_archived=False):
    params = {
        "select": "*",
        "dataset_type": f"eq.{kind}",
        "order": "created_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    if not include_archived:
        params["archived_at"] = "is.null"
    if q:
        safe = q.replace("*", "").replace(",", " ").strip()
        if safe:
            params["or"] = (
                (
                f"(canonical_filename.ilike.*{safe}*,"
                f"label.ilike.*{safe}*,original_filename.ilike.*{safe}*)"
            )
            )

    rows = await db("GET", "datasets", params=params)
    return await asyncio.gather(
        *(_ensure_profile(dataset) for dataset in rows)
    )


async def archive_dataset(dataset_id: str, archived: bool):
    dataset = await get_dataset(dataset_id)
    if not dataset:
        raise LookupError("No se encontró el dataset.")
    if dataset.get("dataset_type") not in ("orders", "fleet"):
        raise ValueError("Sólo se pueden archivar datasets de Dispatch.")
    if archived and dataset.get("dataset_type") == "fleet" and dataset.get("is_default"):
        raise ValueError(
            "No podés archivar la flota vigente. Elegí otra versión como vigente primero."
        )
    archived_at = datetime.now(timezone.utc).isoformat() if archived else None
    rows = await db(
        "PATCH",
        "datasets",
        params={"id": f"eq.{dataset_id}"},
        body={"archived_at": archived_at},
    )
    if not rows:
        raise LookupError("No se encontró el dataset.")
    return rows[0]


async def store_input(
    filename,
    contents,
    kind,
    label=None,
    parent=None,
    *,
    is_sample=False,
):
    if kind not in VALIDATORS:
        raise ValueError("Tipo de dataset inválido.")
    validation = VALIDATORS[kind](contents)
    filehash = hashlib.sha256(contents).hexdigest()

    if parent:
        previous = await get_dataset(parent)
        if (
            kind != "fleet"
            or not previous
            or previous.get("dataset_type") != "fleet"
        ):
            raise ValueError("La versión anterior debe ser una flota existente.")

    existing = await db(
        "GET",
        "datasets",
        params={
            "select": "*",
            "dataset_type": f"eq.{kind}",
            "sha256": f"eq.{filehash}",
            "limit": "1",
        },
    )
    public = {
        key: value
        for key, value in validation.items()
        if key != "records"
    }
    public["valid"] = True
    public["counts"] = {
        "errors": 0,
        "warnings": len(validation.get("warnings") or []),
    }
    if existing:
        return {
            "duplicate": True,
            "existing_dataset": existing[0],
            "validation": public,
        }

    dataset_id = str(uuid4())
    canonical_name = canonical_filename(kind)
    storage_path = f"{dataset_id}/{canonical_name}"
    url = (
        f"{SUPABASE_URL}/storage/v1/object/"
        f"{SUPABASE_INPUT_BUCKET}/{quote(storage_path, safe='/')}"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={
                **_headers(),
                "Content-Type": "text/csv",
                "x-upsert": "false",
            },
            content=contents,
        )
        response.raise_for_status()
        try:
            result = await db(
                "POST",
                "datasets",
                body={
                    "id": dataset_id,
                    "original_filename": filename,
                    "canonical_filename": canonical_name,
                    "storage_bucket": SUPABASE_INPUT_BUCKET,
                    "storage_path": storage_path,
                    "mime_type": "text/csv",
                    "size_bytes": len(contents),
                    "sha256": filehash,
                    "status": "uploaded",
                    "row_count": validation["rows"],
                    "column_count": validation["columns"],
                    "dataset_type": kind,
                    "schema_version": validation["schema"],
                    "label": (
                        label
                        or validation.get("suggested_label")
                        or filename
                    ),
                    "parent_dataset_id": parent,
                    "profile_json": public,
                    "is_sample": bool(is_sample),
                },
            )
        except Exception as exc:
            await client.delete(url, headers=_headers())
            if (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code == 409
            ):
                existing = await db(
                    "GET",
                    "datasets",
                    params={
                        "select": "*",
                        "dataset_type": f"eq.{kind}",
                        "sha256": f"eq.{filehash}",
                        "limit": "1",
                    },
                )
                if existing:
                    return {
                        "duplicate": True,
                        "existing_dataset": existing[0],
                        "validation": public,
                    }
            raise

    return {
        "duplicate": False,
        "dataset": result[0],
        "validation": public,
    }


async def update_dataset_label(dataset_id: str, label: str):
    clean = label.strip()
    if not clean:
        raise ValueError("El nombre no puede quedar vacío.")
    if len(clean) > 120:
        raise ValueError("El nombre no puede superar 120 caracteres.")
    rows = await db(
        "PATCH",
        "datasets",
        params={"id": f"eq.{dataset_id}"},
        body={"label": clean},
    )
    if not rows:
        raise LookupError("No se encontró el dataset.")
    return rows[0]


async def download_input(dataset_id: str):
    dataset = await get_dataset(dataset_id)
    if not dataset:
        raise LookupError("No se encontró el dataset.")
    if dataset.get("dataset_type") not in ("orders", "fleet"):
        raise ValueError("La descarga sólo está disponible para Dispatch.")
    return dataset, await download_dataset(dataset)


async def load_sample_inputs():
    root = Path(__file__).resolve().parents[3]
    sample_dir = root / "sample_data" / "v3"

    orders_bytes = (sample_dir / "orders.csv").read_bytes()
    fleet_bytes = (sample_dir / "fleet.csv").read_bytes()

    orders_report = validate_orders_report(orders_bytes)
    fleet_report = validate_fleet_report(fleet_bytes)

    orders_result = await store_input(
        "orders.csv",
        orders_bytes,
        "orders",
        orders_report.get("suggested_label"),
        is_sample=True,
    )
    fleet_result = await store_input(
        "fleet.csv",
        fleet_bytes,
        "fleet",
        fleet_report.get("suggested_label"),
        is_sample=True,
    )

    orders_dataset = (
        orders_result.get("dataset")
        or orders_result["existing_dataset"]
    )
    fleet_dataset = (
        fleet_result.get("dataset")
        or fleet_result["existing_dataset"]
    )

    await db(
        "PATCH",
        "datasets",
        params={
            "id": (
                f"in.({orders_dataset['id']},{fleet_dataset['id']})"
            )
        },
        body={"is_sample": True},
    )
    await db(
        "POST",
        "rpc/set_default_fleet",
        body={"target_id": fleet_dataset["id"]},
    )

    fleet_dataset = {
        **fleet_dataset,
        "is_default": True,
        "is_sample": True,
    }
    orders_dataset = {
        **orders_dataset,
        "is_sample": True,
    }

    return {
        "orders": orders_dataset,
        "fleet": fleet_dataset,
        "orders_validation": {
            key: value
            for key, value in orders_report.items()
            if key != "records"
        },
        "fleet_validation": {
            key: value
            for key, value in fleet_report.items()
            if key != "records"
        },
        "duplicate": {
            "orders": bool(orders_result.get("duplicate")),
            "fleet": bool(fleet_result.get("duplicate")),
        },
    }


async def load_inputs(orders_id, fleet_id):
    orders_dataset, fleet_dataset = await asyncio.gather(
        get_dataset(orders_id),
        get_dataset(fleet_id),
    )
    if not orders_dataset or not fleet_dataset:
        raise LookupError("No se encontraron ambos datasets.")
    if (
        orders_dataset.get("dataset_type") != "orders"
        or fleet_dataset.get("dataset_type") != "fleet"
    ):
        raise ValueError("Seleccioná un dataset de órdenes y uno de flota.")
    orders_bytes, fleet_bytes = await asyncio.gather(
        download_dataset(orders_dataset),
        download_dataset(fleet_dataset),
    )
    return orders_dataset, fleet_dataset, orders_bytes, fleet_bytes


async def check_inputs(orders_id, fleet_id, allow_third_party=True):
    orders_dataset, fleet_dataset, orders_bytes, fleet_bytes = await load_inputs(
        orders_id,
        fleet_id,
    )
    orders = validate_orders_csv(orders_bytes)
    fleet = validate_fleet_csv(fleet_bytes)
    vehicles = [
        vehicle
        for vehicle in fleet["records"]
        if allow_third_party or vehicle["ownership"] == "own"
    ]
    if not vehicles:
        raise ValueError("No hay flota habilitada.")

    compatibility_preflight = assignment_preflight(
        orders["records"],
        vehicles,
        fleet["records"],
    )
    decision_readiness = build_decision_readiness(
        orders,
        fleet,
        compatibility_preflight,
    )
    return {
        **compatibility_preflight,
        "decision_readiness": decision_readiness,
        "orders_profile": orders["profile"],
        "fleet_profile": fleet["profile"],
        "orders_dataset": orders_dataset,
        "fleet_dataset": fleet_dataset,
    }


async def approve_decision_run(
    run_id,
    *,
    case_id,
    node_id,
):
    run = await get_run(run_id)
    if (
        not run
        or run.get("status")
        != "completed"
        or not run.get("result_json")
    ):
        raise ValueError(
            "Sólo se puede aprobar una corrida completada."
        )

    expected_schema = {
        "logistics_assignment": (
            ASSIGNMENT_SCHEMA_VERSION
        ),
        "logistics_scheduling": (
            SCHEDULING_SCHEMA_VERSION
        ),
    }.get(node_id)
    if not expected_schema:
        raise ValueError(
            "Ese nodo todavía no admite aprobación persistida."
        )

    result = {
        **run["result_json"]
    }
    if (
        result.get("schema_version")
        != expected_schema
    ):
        raise ValueError(
            "La corrida no corresponde al nodo que intentás aprobar."
        )

    current_case = (
        result.get("decision_case")
        or {}
    )
    if (
        current_case.get("case_id")
        != case_id
        or current_case.get("node_id")
        != node_id
    ):
        raise ValueError(
            "La corrida pertenece a otro Decision Case."
        )

    approved_at = (
        current_case.get(
            "approved_at"
        )
        or datetime.now(
            timezone.utc
        ).isoformat()
    )
    approved_case = {
        **current_case,
        "status": "approved",
        "approved_at": approved_at,
    }
    result[
        "decision_case"
    ] = approved_case

    configuration = {
        **(
            run.get(
                "configuration_json"
            )
            or {}
        ),
        "decision_case": (
            approved_case
        ),
    }

    rows = await db(
        "PATCH",
        "decision_runs",
        params={
            "id": f"eq.{run_id}",
            "status": "eq.completed",
        },
        body={
            "result_json": result,
            "configuration_json": (
                configuration
            ),
        },
    )
    if not rows:
        raise ValueError(
            "No se pudo persistir la aprobación."
        )
    return rows[0]


async def execute(
    orders_id,
    fleet_id,
    configuration,
    options,
    run_id=None,
    decision_case=None,
    source_run_id=None,
):
    orders_dataset, fleet_dataset, orders_bytes, fleet_bytes = await load_inputs(
        orders_id,
        fleet_id,
    )
    run_id = run_id or str(uuid4())
    node_id = (
        decision_case.get("node_id")
        if decision_case
        else None
    )
    is_assignment = (
        node_id
        == "logistics_assignment"
    )
    is_scheduling = (
        node_id
        == "logistics_scheduling"
    )

    source_run = None
    if is_scheduling:
        if not source_run_id:
            raise ValueError(
                "Scheduling requiere la corrida aprobada de Assignment."
            )
        source_run = await get_run(
            source_run_id
        )
        if (
            not source_run
            or source_run.get("status")
            != "completed"
            or not source_run.get(
                "result_json"
            )
        ):
            raise ValueError(
                "La corrida fuente de Assignment no está completada."
            )

        source_result = source_run[
            "result_json"
        ]
        source_case = source_result.get(
            "decision_case"
        ) or {}
        if (
            source_result.get(
                "schema_version"
            )
            != ASSIGNMENT_SCHEMA_VERSION
            or source_case.get(
                "node_id"
            )
            != "logistics_assignment"
            or source_case.get(
                "case_id"
            )
            != decision_case.get(
                "case_id"
            )
        ):
            raise ValueError(
                "Scheduling requiere Assignment V1 del mismo Decision Case."
            )
        if (
            source_case.get("status")
            != "approved"
            or not source_case.get(
                "approved_at"
            )
        ):
            raise ValueError(
                "Primero aprobá Assignment antes de ejecutar Scheduling."
            )
        if (
            str(
                source_run.get(
                    "orders_dataset_id"
                )
            )
            != str(orders_id)
            or str(
                source_run.get(
                    "fleet_dataset_id"
                )
            )
            != str(fleet_id)
        ):
            raise ValueError(
                "La corrida fuente usa un Data Pack distinto."
            )

    if is_assignment:
        engine_name = (
            ASSIGNMENT_ENGINE_NAME
        )
        engine_version = (
            ASSIGNMENT_ENGINE_VERSION
        )
        schema_version = (
            ASSIGNMENT_SCHEMA_VERSION
        )
        runner = run_assignment_engine
    elif is_scheduling:
        engine_name = (
            SCHEDULING_ENGINE_NAME
        )
        engine_version = (
            SCHEDULING_ENGINE_VERSION
        )
        schema_version = (
            SCHEDULING_SCHEMA_VERSION
        )
        runner = run_scheduling_engine
    else:
        engine_name = ENGINE_NAME
        engine_version = (
            ENGINE_VERSION
        )
        schema_version = (
            SCHEMA_VERSION
        )
        runner = run_dispatch_engine

    start = perf_counter()
    now = datetime.now(timezone.utc).isoformat()
    await _insert_run(
        {
            "id": run_id,
            "dataset_id": orders_id,
            "orders_dataset_id": orders_id,
            "fleet_dataset_id": fleet_id,
            "schema_version": schema_version,
            "engine_name": engine_name,
            "engine_version": engine_version,
            "configuration_json": {
                **configuration,
                "options": options,
                **(
                    {"decision_case": decision_case}
                    if decision_case
                    else {}
                ),
                **(
                    {
                        "source_assignment_run_id": (
                            source_run_id
                        )
                    }
                    if is_scheduling
                    else {}
                ),
            },
            "status": "running",
            "started_at": now,
            "input_fingerprint": hashlib.sha256(
                engine_name.encode()
                + b"\0"
                + orders_bytes
                + b"\0"
                + fleet_bytes
                + json.dumps(configuration, sort_keys=True).encode()
                + json.dumps(options, sort_keys=True).encode()
                + (
                    (
                        source_run["result_json"][
                            "handoff"
                        ][
                            "assignment_fingerprint"
                        ]
                    ).encode()
                    if is_scheduling
                    else b""
                )
            ).hexdigest(),
            "progress_json": {"stage": "validating"},
        }
    )

    async def update(values):
        return await db(
            "PATCH",
            "decision_runs",
            params={
                "id": f"eq.{run_id}",
                "status": "eq.running",
            },
            body=values,
        )

    loop = asyncio.get_running_loop()

    def progress(stage):
        future = asyncio.run_coroutine_threadsafe(
            update({"progress_json": {"stage": stage}}),
            loop,
        )
        future.result(timeout=35)

    metadata = {
        key: {
            "dataset_id": value["id"],
            "filename": value["original_filename"],
            "label": value.get("label"),
            "created_at": value["created_at"],
            "schema_version": value.get("schema_version"),
        }
        for key, value in (
            ("orders", orders_dataset),
            ("fleet", fleet_dataset),
        )
    }
    if is_scheduling:
        metadata["assignment"] = {
            "run_id": (
                source_run["id"]
            ),
            "result_fingerprint": (
                source_run.get(
                    "result_fingerprint"
                )
            ),
            "approved_at": (
                source_run[
                    "result_json"
                ].get(
                    "decision_case",
                    {},
                ).get(
                    "approved_at"
                )
            ),
        }
    try:
        if is_scheduling:
            result = await asyncio.to_thread(
                runner,
                orders_bytes,
                fleet_bytes,
                source_run[
                    "result_json"
                ],
                configuration,
                options,
                metadata,
                progress,
            )
        else:
            result = await asyncio.to_thread(
                runner,
                orders_bytes,
                fleet_bytes,
                configuration,
                options,
                metadata,
                progress,
            )
        if decision_case:
            result["decision_case"] = decision_case

        rows = await update(
            {
                "status": "completed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": int((perf_counter() - start) * 1000),
                "result_json": result,
                "result_fingerprint": result["result_fingerprint"],
                "summary_json": result["scenarios"]["selected"]["metrics"],
                "progress_json": {"stage": "completed"},
                "error_message": None,
            }
        )
        if not rows:
            raise ValueError(
                "La corrida venció antes de guardar el resultado; ejecutala nuevamente."
            )
        return rows[0]
    except Exception as exc:
        await update(
            {
                "status": "error",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": int((perf_counter() - start) * 1000),
                "error_message": str(exc)[:1500],
                "progress_json": {"stage": "error"},
            }
        )
        raise
