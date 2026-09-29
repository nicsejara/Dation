import os


SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_INPUT_BUCKET = os.getenv("SUPABASE_INPUT_BUCKET", "dda-inputs")
DATION_ACCESS_PASSWORD = os.getenv("DATION_ACCESS_PASSWORD", "")


def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY and SUPABASE_INPUT_BUCKET)
