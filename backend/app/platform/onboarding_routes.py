from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict
from app.auth import require_upload_access
from app.platform import onboarding
from app.platform.identity import platform_call
from app.platform.entitlements import require_dda
from app.platform.data_routes import guarded
from app.services.dispatch_service import load_sample_inputs

router=APIRouter(prefix='/onboarding')
class EmptyRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')

@router.get('')
async def progress(ctx=Depends(require_upload_access)):
    return await onboarding.snapshot(ctx)

@router.post('/explore')
async def explore(payload:EmptyRequest,ctx=Depends(require_upload_access)):
    return await platform_call('platform_onboarding_explore',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id})

@router.post('/demo')
async def demo(payload:EmptyRequest,ctx=Depends(require_upload_access)):
    require_dda(ctx,'logistics')
    return await guarded(load_sample_inputs())
