import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import DATION_ACCESS_PASSWORD

security = HTTPBasic()


def require_upload_access(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    if not DATION_ACCESS_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload access is not configured.",
        )

    username_ok = secrets.compare_digest(credentials.username, "dation")
    password_ok = secrets.compare_digest(
        credentials.password,
        DATION_ACCESS_PASSWORD,
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
