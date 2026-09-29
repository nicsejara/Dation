from fastapi import FastAPI

app = FastAPI(
    title="Dation Core API",
    version="0.1.0",
    description="Backend core for the Dation Decision Data Asset MVP.",
)


@app.get("/")
def root():
    return {
        "service": "Dation Core",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }
