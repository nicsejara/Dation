"""Authenticated platform profile endpoints. Workspace authority is resolved server-side."""
from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.auth import require_upload_access
from app.platform.identity import platform_call
from app.platform.home import home_snapshot
from app.platform.data_routes import router as data_router
from app.platform.decision_routes import router as decision_router
from app.platform.team_routes import router as team_router
from app.platform.settings_routes import router as settings_router
from app.platform.activity_routes import router as activity_router
from app.platform.onboarding_routes import router as onboarding_router
from app.platform.ultimate_routes import router as ultimate_router
from app.platform.ultimate_data_routes import router as ultimate_data_router

router=APIRouter(prefix='/api/platform')
router.include_router(data_router)
router.include_router(decision_router)
router.include_router(team_router)
router.include_router(settings_router)
router.include_router(activity_router)
router.include_router(onboarding_router)
router.include_router(ultimate_router)
router.include_router(ultimate_data_router)

@router.get('/home')
async def get_home(ctx=Depends(require_upload_access)):
    return await home_snapshot(ctx)

class ProfileUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    first_name:str=Field(min_length=1,max_length=100)
    last_name:str=Field(min_length=1,max_length=100)

    @field_validator('first_name','last_name')
    @classmethod
    def trim_name(cls,value):
        if not value.strip():raise ValueError('Completá el nombre y apellido.')
        return value.strip()

@router.patch('/profile')
async def update_profile(payload:ProfileUpdate,ctx=Depends(require_upload_access)):
    return await platform_call('platform_update_profile',{'actor_user_id':ctx.user_id,**payload.model_dump()})
