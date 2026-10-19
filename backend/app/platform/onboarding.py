"""First-run progress is derived from real resources; only exploration is recorded."""
from fastapi import HTTPException
from app.platform.identity import platform_call

async def snapshot(ctx):
    return await platform_call('platform_onboarding', {'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id})

async def home_progress(ctx):
    try:return await snapshot(ctx)
    except HTTPException as error:
        if error.status_code!=503:raise
        return {'available':False,'error':'No se pudo cargar la guía inicial.'}
