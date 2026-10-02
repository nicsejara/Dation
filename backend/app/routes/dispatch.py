from pathlib import Path
from uuid import UUID

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.auth import require_upload_access
from app.models.dispatch_config import DispatchConfig, DispatchOptions
from app.services import dispatch_service as service
from app.validators.contracts import public_contracts, template_csv


router = APIRouter(
    dependencies=[Depends(require_upload_access)]
)


class Inputs(BaseModel):
    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    allow_third_party: bool = True


class RunRequest(BaseModel):
    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    configuration: DispatchConfig = DispatchConfig()
    options: DispatchOptions = DispatchOptions()


class LabelUpdate(BaseModel):
    label: str


async def guarded(call):
    try:
        return await call
    except TimeoutError as exc:
        raise HTTPException(408, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            502,
            "No se pudo guardar o recuperar la información de despacho.",
        ) from exc


@router.get("/api/dispatch/status")
async def status():
    return await service.system_status()


@router.get("/api/dispatch/contracts")
async def contracts():
    return {
        "formats": public_contracts(),
        "file_rules": {
            "extension": ".csv",
            "max_bytes": 10 * 1024 * 1024,
            "encoding": "UTF-8",
            "delimiters": [",", ";"],
            "date_formats": ["AAAA-MM-DD", "d/m/AAAA"],
            "decimal_rule": (
                "Usá punto decimal; con separador punto y coma también se admite coma."
            ),
        },
    }


@router.post("/api/datasets/validate")
async def validate_dataset(
    dataset_type: str = Query(...),
    file: UploadFile = File(...),
):
    if dataset_type not in ("orders", "fleet"):
        raise HTTPException(422, "Tipo de dataset inválido.")
    filename = file.filename or "input.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            400,
            "Sólo se admiten archivos con extensión .csv.",
        )
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            413,
            "El archivo supera el límite actual de 10 MB.",
        )
    return service.validate_input(
        filename,
        contents,
        dataset_type,
    )


@router.post("/api/datasets/load-sample")
async def load_sample():
    if not await service.available():
        raise HTTPException(
            503,
            "Falta activar el almacenamiento de datos.",
        )
    return await guarded(service.load_sample_inputs())


@router.patch("/api/datasets/{dataset_id}")
async def update_dataset(dataset_id: UUID, payload: LabelUpdate):
    dataset = await guarded(
        service.update_dataset_label(
            str(dataset_id),
            payload.label,
        )
    )
    return {"dataset": dataset}


@router.get("/api/datasets/{dataset_id}/download")
async def download_dataset(dataset_id: UUID):
    dataset, contents = await guarded(
        service.download_input(str(dataset_id))
    )
    filename = dataset.get("original_filename") or "datos.csv"
    return Response(
        content=contents,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/api/runs/preflight")
async def preflight(payload: Inputs):
    return await guarded(
        service.check_inputs(
            str(payload.orders_dataset_id),
            str(payload.fleet_dataset_id),
            payload.allow_third_party,
        )
    )


@router.post("/api/runs")
async def run(
    payload: RunRequest,
    run_id: UUID | None = Query(None),
):
    if not await service.available():
        raise HTTPException(
            503,
            "El almacenamiento de Dispatch todavía no está activado.",
        )
    return await guarded(
        service.execute(
            str(payload.orders_dataset_id),
            str(payload.fleet_dataset_id),
            payload.configuration.model_dump(),
            payload.options.model_dump(),
            str(run_id) if run_id else None,
        )
    )


@router.post("/api/datasets/{dataset_id}/default")
async def default(dataset_id: UUID):
    await guarded(
        service.db(
            "POST",
            "rpc/set_default_fleet",
            body={"target_id": str(dataset_id)},
        )
    )
    return {"ok": True}


@router.post("/api/datasets/{dataset_id}/archive")
async def archive(dataset_id: UUID):
    dataset = await guarded(
        service.archive_dataset(
            str(dataset_id),
            True,
        )
    )
    return {"dataset": dataset}


@router.post("/api/datasets/{dataset_id}/unarchive")
async def unarchive(dataset_id: UUID):
    dataset = await guarded(
        service.archive_dataset(
            str(dataset_id),
            False,
        )
    )
    return {"dataset": dataset}


@router.get("/api/dispatch/templates/{kind}")
async def template(kind: str):
    if kind not in ("orders", "fleet"):
        raise HTTPException(404, "Plantilla no disponible.")
    return Response(
        content=template_csv(kind),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{kind}.csv"',
        },
    )


@router.get("/api/dispatch/examples/{kind}")
async def example(kind: str):
    if kind not in ("orders", "fleet"):
        raise HTTPException(404, "Ejemplo no disponible.")
    root = Path(__file__).resolve().parents[3]
    path = root / "sample_data" / "v1" / f"{kind}.csv"
    return FileResponse(
        path,
        media_type="text/csv",
        filename=f"{kind}_ejemplo.csv",
    )
