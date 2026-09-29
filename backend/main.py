from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.auth import require_upload_access
from app.config import supabase_configured
from app.services.dataset_service import upload_dataset
from app.services.supabase_service import check_supabase_connection
from app.validators.logistics_schema import (
    LogisticsValidationError,
    validate_logistics_csv,
)

app = FastAPI(
    title="Dation Core API",
    version="0.3.0",
    description="Backend core for the Dation Decision Data Asset MVP.",
)

UPLOAD_PAGE = (
    Path(__file__).resolve().parent / "app" / "templates" / "upload.html"
)


@app.get("/")
def root():
    return {
        "service": "Dation Core",
        "version": "0.3.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/api/system/supabase-check")
async def supabase_check():
    return await check_supabase_connection()


@app.get("/upload", response_class=HTMLResponse)
def upload_page(_: str = Depends(require_upload_access)):
    return UPLOAD_PAGE.read_text(encoding="utf-8")


@app.post("/api/datasets/upload")
async def upload_logistics_dataset(
    file: UploadFile = File(...),
    _: str = Depends(require_upload_access),
):
    if not supabase_configured():
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )

    filename = file.filename or "input.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only .csv files are accepted.",
        )

    contents = await file.read()
    max_bytes = 10 * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail="The file exceeds the current 10 MB limit.",
        )

    try:
        validation = validate_logistics_csv(contents)
    except LogisticsValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        stored = await upload_dataset(
            filename=filename,
            contents=contents,
            mime_type=file.content_type or "text/csv",
            row_count=validation["rows"],
            column_count=validation["columns"],
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise HTTPException(
            status_code=502,
            detail=f"Supabase rejected the upload: {detail}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach Supabase: {exc}",
        ) from exc

    return {
        **stored,
        "validation": validation,
    }
