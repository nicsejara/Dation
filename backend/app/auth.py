"""Supabase Bearer authentication and per-request workspace authority."""
from fastapi import HTTPException, Request
from app.platform.context import bind
from app.platform.identity import resolve
from app.platform.jwt import verify

READ_POSTS = {"/api/runs/preflight", "/api/runs/assignment-preview", "/api/datasets/validate"}
ADMIN_PATHS = {"/ready", "/metrics", "/api/system/operations", "/api/system/supabase-check"}


async def require_upload_access(request: Request):
    """Existing dependency name; HTTP Basic is retired."""
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Ingresá para continuar.", headers={"WWW-Authenticate": "Bearer"})
    ctx = await resolve(await verify(token))
    if request.url.path in ADMIN_PATHS and ctx.access_role != "admin":
        raise HTTPException(403, "Esta consulta requiere acceso de administrador.")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path not in READ_POSTS and request.url.path != "/api/platform/profile":
        if ctx.access_role == "viewer":
            raise HTTPException(403, "Tu rol permite consultar, pero no modificar datos o decisiones.")
    if request.headers.get("x-dation-workspace-id") not in {None, ctx.workspace_id}:
        raise HTTPException(403, "El workspace solicitado no coincide con tu acceso activo.")
    with bind(ctx):
        yield ctx
