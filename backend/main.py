from fastapi import FastAPI

from app.services.supabase_service import check_supabase_connection

app = FastAPI(
    title="Dation Core API",
    version="0.2.0",
    description="Backend core for the Dation Decision Data Asset MVP.",
)


@app.get("/")
def root():
    return {
        "service": "Dation Core",
        "version": "0.2.0",
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
