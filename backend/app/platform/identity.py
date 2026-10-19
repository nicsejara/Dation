"""Service-side membership resolution; client tenant/role claims are not authority."""
import httpx
from fastapi import HTTPException
from app.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.platform.context import RequestContext
from app.services.http_service import http_client
from app.platform.entitlements import enabled_ddas


def headers():
    return {"apikey": SUPABASE_SECRET_KEY, "Authorization": "Bearer " + SUPABASE_SECRET_KEY,
            "Prefer": "return=representation"}


async def platform_call(name, body):
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise HTTPException(503, "El acceso a la plataforma todavía no está configurado.")
    try:
        async with http_client() as client:
            response = await client.post(SUPABASE_URL + "/rest/v1/rpc/" + name,
                                         headers=headers(), json=body, timeout=15)
        if response.status_code >= 400:
            code = response.json().get("code")
            if code == "42501":
                raise HTTPException(403, "No tenés acceso activo a este workspace.")
            if code == "22023":
                collaboration_errors = {
                    'platform_invite_member': 'Ya existe una membresía o invitación pendiente para ese email. Revisá el equipo antes de reintentar.',
                    'platform_update_member': 'Revisá los roles y conservá al menos un administrador activo en el workspace.',
                    'platform_assign_decision': 'Elegí miembros activos con rol Admin u Operator para este workspace.',
                    'platform_received_invitations': 'La invitación venció, fue revocada o ya existe una membresía. Consultá al administrador.',
                }
                if name in collaboration_errors:
                    raise HTTPException(409, collaboration_errors[name])
                raise HTTPException(409, "Ya existe una membresía o la configuración es inválida.")
            if code == "P0002":
                raise HTTPException(404, "No se encontró el recurso solicitado.")
            if code in {"55006", "55P03"}:
                raise HTTPException(409, "El recurso cambió o hay otra operación en curso. Actualizá antes de reintentar.",
                                    headers={"X-Dation-Retryable":"true"})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        raise HTTPException(503, "No se pudo comprobar el acceso al workspace. Reintentá.") from None


async def bootstrap(claims):
    metadata = claims.get("user_metadata") or {}
    names = {field: str(metadata.get(field) or "")[:100] for field in ("first_name", "last_name")}
    return await platform_call("platform_identity", {"actor_user_id": claims["sub"], **names})


async def resolve(claims) -> RequestContext:
    data = await bootstrap(claims)
    membership = data.get("membership")
    if not membership:
        raise HTTPException(409, "Creá tu workspace para continuar.", headers={"X-Dation-Setup": "required"})
    return RequestContext(claims["sub"], membership["workspace_id"], membership["access_role"],
                          membership.get("business_role"),
                          enabled_ddas=enabled_ddas(data, membership["workspace_id"]))
