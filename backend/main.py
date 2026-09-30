from pathlib import Path

import httpx
from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.exceptions import (
    RequestValidationError,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
)

from app.auth import require_upload_access
from app.config import supabase_configured
from app.models.decision_config import (
    DecisionRunConfig,
)
from app.services.dataset_profile_service import (
    get_dataset_profile,
)
from app.services.dataset_service import (
    upload_dataset,
)
from app.services.decision_interpreter_service import (
    answer_question,
    generate_explanation,
    get_saved_interpretation,
    interpreter_status,
)
from app.services.run_service import (
    execute_logistics_run,
    get_run,
)
from app.services.supabase_service import (
    check_supabase_connection,
)
from app.services.workspace_service import (
    list_datasets,
    list_runs,
    workspace_summary,
)
from app.validators.logistics_schema import (
    LogisticsValidationError,
    validate_logistics_csv,
)


BASE_DIR = Path(__file__).resolve().parent
APP_PAGE = (
    BASE_DIR
    / "app"
    / "templates"
    / "app.html"
)
STATIC_DIR = (
    BASE_DIR
    / "app"
    / "static"
)


app = FastAPI(
    title="Dation Core API",
    version="0.7.0",
    description=(
        "Backend para Dation Decision "
        "Intelligence Workspace."
    ),
)

app.mount(
    "/static",
    StaticFiles(
        directory=STATIC_DIR
    ),
    name="static",
)


class DecisionQuestion(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=2000,
    )


@app.exception_handler(
    RequestValidationError
)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "detail": (
                "La solicitud contiene datos "
                "inválidos. Revisá la "
                "configuración enviada."
            ),
            "errors": [
                {
                    "field": ".".join(
                        str(value)
                        for value in error.get(
                            "loc",
                            [],
                        )
                    ),
                    "message": error.get(
                        "msg",
                        "Valor inválido.",
                    ),
                }
                for error in exc.errors()
            ],
        },
    )


@app.get("/")
def root():
    return {
        "service": "Dation Core",
        "version": "0.7.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get(
    "/app",
    response_class=HTMLResponse,
)
def decision_workspace(
    _: str = Depends(
        require_upload_access
    ),
):
    return APP_PAGE.read_text(
        encoding="utf-8"
    )


@app.get(
    "/upload",
    response_class=HTMLResponse,
)
def upload_compatibility(
    _: str = Depends(
        require_upload_access
    ),
):
    return APP_PAGE.read_text(
        encoding="utf-8"
    )


@app.get(
    "/api/system/supabase-check"
)
async def supabase_check():
    return await (
        check_supabase_connection()
    )


@app.get("/api/system/llm-status")
def llm_status(
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return interpreter_status()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.get("/api/workspace/summary")
async def get_workspace_summary(
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return await workspace_summary()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo cargar el "
                "resumen del workspace."
            ),
        ) from exc


@app.get("/api/datasets")
async def get_datasets(
    limit: int = Query(
        default=25,
        ge=1,
        le=100,
    ),
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return {
            "items": await list_datasets(
                limit=limit
            ),
        }
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudieron cargar "
                "los datasets."
            ),
        ) from exc


@app.get(
    "/api/datasets/{dataset_id}/profile"
)
async def dataset_profile(
    dataset_id: str,
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return await get_dataset_profile(
            dataset_id
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except LogisticsValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo recuperar el "
                "dataset desde Supabase."
            ),
        ) from exc


@app.get("/api/runs")
async def get_runs(
    limit: int = Query(
        default=40,
        ge=1,
        le=100,
    ),
    dataset_id: str | None = None,
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return {
            "items": await list_runs(
                limit=limit,
                dataset_id=dataset_id,
            ),
        }
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo cargar el "
                "historial de decisiones."
            ),
        ) from exc


@app.post("/api/datasets/upload")
async def upload_logistics_dataset(
    file: UploadFile = File(...),
    _: str = Depends(
        require_upload_access
    ),
):
    if not supabase_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Supabase no está "
                "configurado."
            ),
        )

    filename = (
        file.filename or "input.csv"
    )

    if not filename.lower().endswith(
        ".csv"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Sólo se admiten archivos "
                "con extensión .csv."
            ),
        )

    contents = await file.read()
    max_bytes = 10 * 1024 * 1024

    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                "El archivo supera el "
                "límite actual de 10 MB."
            ),
        )

    try:
        validation = (
            validate_logistics_csv(
                contents
            )
        )
    except LogisticsValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    try:
        stored = await upload_dataset(
            filename=filename,
            contents=contents,
            mime_type=(
                file.content_type
                or "text/csv"
            ),
            row_count=validation[
                "rows"
            ],
            column_count=validation[
                "columns"
            ],
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Supabase rechazó la "
                "carga del archivo."
            ),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo conectar con "
                "Supabase."
            ),
        ) from exc

    return {
        **stored,
        "validation": validation,
    }


@app.post("/api/runs/{dataset_id}")
async def run_logistics_decision(
    dataset_id: str,
    config: DecisionRunConfig | None = (
        Body(default=None)
    ),
    objective: str | None = Query(
        default=None
    ),
    _: str = Depends(
        require_upload_access
    ),
):
    if config is None:
        if objective not in {
            None,
            "min_cost",
            "min_trips",
        }:
            raise HTTPException(
                status_code=422,
                detail=(
                    "El objetivo legado debe "
                    "ser min_cost o min_trips."
                ),
            )

        config = (
            DecisionRunConfig
            .from_legacy_objective(
                objective
            )
        )

    try:
        configuration = (
            DecisionRunConfig.model_validate(
                config.model_dump()
            ).model_dump()
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "La configuración de la "
                "decisión es inválida."
            ),
        ) from exc

    try:
        return await execute_logistics_run(
            dataset_id=dataset_id,
            configuration=configuration,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Supabase rechazó la "
                "ejecución o persistencia "
                "de la corrida."
            ),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo conectar con "
                "Supabase."
            ),
        ) from exc


@app.get("/api/runs/{run_id}")
async def read_decision_run(
    run_id: str,
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        run = await get_run(
            run_id
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo recuperar "
                "la corrida."
            ),
        ) from exc

    if not run:
        raise HTTPException(
            status_code=404,
            detail=(
                "No se encontró la "
                "corrida solicitada."
            ),
        )

    return run


@app.get(
    "/api/runs/{run_id}/interpretation"
)
async def read_run_interpretation(
    run_id: str,
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return await (
            get_saved_interpretation(
                run_id
            )
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo recuperar la "
                "interpretación guardada."
            ),
        ) from exc


@app.post(
    "/api/runs/{run_id}/explain"
)
async def explain_decision_run(
    run_id: str,
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return await (
            generate_explanation(
                run_id
            )
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        status = (
            503
            if "LLM is not configured"
            in str(exc)
            else 502
        )
        raise HTTPException(
            status_code=status,
            detail=(
                "El intérprete IA no pudo "
                "generar la explicación."
            ),
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "El proveedor de IA o "
                "Supabase rechazó la "
                "solicitud."
            ),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo conectar con "
                "el servicio externo."
            ),
        ) from exc


@app.post(
    "/api/runs/{run_id}/chat"
)
async def chat_about_decision(
    run_id: str,
    payload: DecisionQuestion,
    _: str = Depends(
        require_upload_access
    ),
):
    try:
        return await answer_question(
            run_id=run_id,
            question=(
                payload.question.strip()
            ),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        status = (
            503
            if "LLM is not configured"
            in str(exc)
            else 502
        )
        raise HTTPException(
            status_code=status,
            detail=(
                "El intérprete IA no pudo "
                "responder la pregunta."
            ),
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "El proveedor de IA o "
                "Supabase rechazó la "
                "solicitud."
            ),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo conectar con "
                "el servicio externo."
            ),
        ) from exc
