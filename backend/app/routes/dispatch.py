from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.auth import require_upload_access
from app.models.assignment_config import (
    AssignmentConfig,
    AssignmentOptions,
    AssignmentResourceMode,
    AssignmentScopeFilter,
)
from app.models.dispatch_config import DispatchConfig, DispatchOptions
from app.models.scheduling_config import SchedulingConfig, SchedulingOptions
from app.services import decision_case_service as case_service
from app.services import dispatch_service as service
from app.services.assignment_config_service import preview_assignment_configuration
from app.validators.contracts import public_contracts, template_csv


router = APIRouter(
    dependencies=[Depends(require_upload_access)]
)


class Inputs(BaseModel):
    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    allow_third_party: bool = True


class AssignmentPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    filters: list[AssignmentScopeFilter] = Field(default_factory=list, max_length=12)
    resource_mode: AssignmentResourceMode = "mixed"


class DecisionCaseRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    node_id: Literal["logistics_assignment", "logistics_scheduling"]


class DecisionCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    state: dict | None = None


class DecisionCaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "completed", "archived"] | None = None
    state: dict | None = None

    @model_validator(mode="after")
    def non_empty(self):
        if self.status is None and self.state is None:
            raise ValueError("Indicá un estado o un snapshot para actualizar el caso.")
        return self


class RunRequest(BaseModel):
    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    configuration: dict = Field(default_factory=dict)
    options: dict = Field(default_factory=dict)
    decision_case: DecisionCaseRef | None = None
    source_run_id: UUID | None = None

    @model_validator(mode="after")
    def canonical(self):
        node_id = (
            self.decision_case.node_id
            if self.decision_case
            else None
        )
        if node_id == "logistics_assignment":
            self.configuration = (
                AssignmentConfig.model_validate(
                    self.configuration
                ).model_dump()
            )
            self.options = (
                AssignmentOptions.model_validate(
                    self.options
                ).model_dump()
            )
        elif node_id == "logistics_scheduling":
            if not self.source_run_id:
                raise ValueError(
                    "Scheduling requiere source_run_id de Assignment."
                )
            self.configuration = (
                SchedulingConfig.model_validate(
                    self.configuration
                ).model_dump()
            )
            self.options = (
                SchedulingOptions.model_validate(
                    self.options
                ).model_dump()
            )
        else:
            self.configuration = (
                DispatchConfig.model_validate(
                    self.configuration
                ).model_dump()
            )
            self.options = (
                DispatchOptions.model_validate(
                    self.options
                ).model_dump()
            )
        return self


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: UUID
    node_id: Literal[
        "logistics_assignment",
        "logistics_scheduling",
    ]


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


@router.get("/api/decision-cases")
async def list_decision_cases(
    status: Literal["active", "completed", "archived"] | None = Query("active"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    cases = await guarded(
        case_service.list_cases(
            status=status,
            limit=limit,
            offset=offset,
        )
    )
    return {"cases": cases}


@router.post("/api/decision-cases")
async def create_decision_case(payload: DecisionCaseCreate):
    case = await guarded(
        case_service.ensure_case(
            str(payload.id),
            str(payload.orders_dataset_id),
            str(payload.fleet_dataset_id),
            state=payload.state,
        )
    )
    return {"case": case}


@router.get("/api/decision-cases/{case_id}")
async def get_decision_case(case_id: UUID):
    return await guarded(case_service.get_case(str(case_id)))


@router.patch("/api/decision-cases/{case_id}")
async def update_decision_case(case_id: UUID, payload: DecisionCaseUpdate):
    case = await guarded(
        case_service.update_case(
            str(case_id),
            state=payload.state,
            status=payload.status,
        )
    )
    return {"case": case}


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
    filename = Path(
        dataset.get("original_filename") or "datos.csv"
    ).name
    filename = (
        filename
        .replace("\r", "")
        .replace("\n", "")
        .replace('"', "")
    )
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


@router.post("/api/runs/assignment-preview")
async def assignment_preview(payload: AssignmentPreviewRequest):
    return await guarded(
        preview_assignment_configuration(
            str(payload.orders_dataset_id),
            str(payload.fleet_dataset_id),
            filters=[item.model_dump() for item in payload.filters],
            resource_mode=payload.resource_mode,
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

    effective_run_id = str(run_id or uuid4())
    case_ref = (
        payload.decision_case.model_dump(mode="json")
        if payload.decision_case
        else None
    )

    async def operation():
        if case_ref:
            await case_service.ensure_case(
                case_ref["case_id"],
                str(payload.orders_dataset_id),
                str(payload.fleet_dataset_id),
            )
            await case_service.record_node_state(
                case_ref["case_id"],
                case_ref["node_id"],
                run_id=effective_run_id,
                status="running",
            )
        try:
            result = await service.execute(
                str(payload.orders_dataset_id),
                str(payload.fleet_dataset_id),
                payload.configuration,
                payload.options,
                effective_run_id,
                case_ref,
                (
                    str(payload.source_run_id)
                    if payload.source_run_id
                    else None
                ),
            )
        except Exception as exc:
            if case_ref:
                try:
                    await case_service.record_node_state(
                        case_ref["case_id"],
                        case_ref["node_id"],
                        run_id=effective_run_id,
                        status="error",
                        error=str(exc)[:1500],
                    )
                except Exception:
                    pass
            raise
        if case_ref:
            await case_service.record_node_state(
                case_ref["case_id"],
                case_ref["node_id"],
                run_id=effective_run_id,
                status="review",
            )
        return result

    return await guarded(operation())


@router.post("/api/runs/{run_id}/approve")
async def approve_run(
    run_id: UUID,
    payload: ApprovalRequest,
):
    async def operation():
        run = await service.approve_decision_run(
            str(run_id),
            case_id=str(payload.case_id),
            node_id=payload.node_id,
        )
        decision_case = (run.get("result_json") or {}).get("decision_case") or {}
        await case_service.record_node_state(
            str(payload.case_id),
            payload.node_id,
            run_id=str(run_id),
            status="approved",
            approved_at=decision_case.get("approved_at"),
        )
        return run

    return await guarded(operation())


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
