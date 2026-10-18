"""Supabase asymmetric JWT verification with bounded JWKS caching and rotation."""
import asyncio
from time import monotonic
from uuid import UUID

import httpx
import jwt
from fastapi import HTTPException

from app.config import SUPABASE_URL
from app.services.http_service import http_client

_keys = {}
_expires = 0.0
_last_refresh = 0.0
_lock = asyncio.Lock()
ISSUER = SUPABASE_URL + "/auth/v1"


async def verify(token: str) -> dict:
    global _keys, _expires, _last_refresh
    unauthorized = HTTPException(401, "La sesión no es válida. Ingresá nuevamente.",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        if not SUPABASE_URL or len(token) > 16384:
            raise unauthorized
        header = jwt.get_unverified_header(token)
        kid, algorithm = header.get("kid"), header.get("alg")
        if not isinstance(kid, str) or not kid or algorithm not in {"ES256", "RS256"}:
            raise unauthorized
        now = monotonic()
        if now >= _expires or kid not in _keys:
            async with _lock:
                now = monotonic()
                if now >= _expires or (kid not in _keys and now - _last_refresh >= 5):
                    async with http_client() as client:
                        response = await client.get(ISSUER + "/.well-known/jwks.json", timeout=8)
                    response.raise_for_status()
                    keys = response.json().get("keys", [])
                    if not isinstance(keys, list) or not 1 <= len(keys) <= 20:
                        raise ValueError("Invalid JWKS")
                    replacement = {}
                    for key in keys:
                        if key.get("alg") in {"ES256", "RS256"} and key.get("use", "sig") == "sig":
                            replacement[key["kid"]] = jwt.PyJWK.from_dict(key)
                    _keys, _expires, _last_refresh = replacement, now + 300, now
        key = _keys.get(kid)
        if key is None or key.algorithm_name != algorithm:
            raise unauthorized
        claims = jwt.decode(token, key.key, algorithms=[algorithm], audience="authenticated",
                            issuer=ISSUER, options={"require": ["exp", "iat", "sub", "iss", "aud"]}, leeway=5)
        UUID(claims["sub"])
        if claims.get("role") != "authenticated":
            raise unauthorized
        return claims
    except HTTPException:
        raise
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise unauthorized from None
    except httpx.HTTPError:
        # Never accept a stale or unverifiable signing key on an outage.
        raise HTTPException(503, "No se pudo verificar la sesión. Reintentá en unos instantes.") from None
