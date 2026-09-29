import os


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_INPUT_BUCKET = os.getenv(
    "SUPABASE_INPUT_BUCKET",
    "dda-inputs",
)
DATION_ACCESS_PASSWORD = os.getenv(
    "DATION_ACCESS_PASSWORD",
    "",
)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")


def supabase_configured() -> bool:
    return bool(
        SUPABASE_URL
        and SUPABASE_SECRET_KEY
        and SUPABASE_INPUT_BUCKET
    )
