from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,field_validator,model_validator
from app.auth import require_upload_access
from app.platform import decision_center as center
from app.platform.identity import platform_call
from app.platform.foundation import REGISTRY
from app.models.case_identity import CaseIdentity

router=APIRouter(prefix='/decisions')
Node=Literal['logistics_assignment','logistics_scheduling','logistics_final_assignment']
Stage=Literal['data_preparation','data_owner','data_steward','logistics_assignment','logistics_scheduling']

@router.get('/{case_id}/workflow-readiness')
async def workflow_readiness(case_id:UUID,ctx=Depends(require_upload_access)):
    from fastapi import HTTPException
    from app.platform.entitlements import require_dda
    from app.services import decision_case_service,dispatch_service
    from app.routes.dispatch import guarded
    require_dda(ctx,'logistics')
    case=await guarded(decision_case_service.get_case(str(case_id)))
    inputs=await guarded(dispatch_service.check_inputs(case['orders']['id'],case['fleet']['id'],True))
    if not inputs.get('valid'):
        raise HTTPException(409,'Validá y corregí el Data Pack antes de continuar.')
    return await platform_call('platform_validate_data_stage',{'target_workspace_id':ctx.workspace_id,
        'actor_user_id':ctx.user_id,'target_case_id':str(case_id)})

@router.get('/{case_id}/responsibilities')
async def responsibilities(case_id:UUID,ctx=Depends(require_upload_access)):
    return await platform_call('platform_workflow_responsibilities',{'target_workspace_id':ctx.workspace_id,
        'actor_user_id':ctx.user_id,'target_case_id':str(case_id)})

class StageAssignment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_updated_at:AwareDatetime|None
    owner_user_id:UUID|None
    approver_user_id:UUID|None=None

@router.put('/{case_id}/responsibilities/{stage_key}')
async def assign_responsibility(case_id:UUID,stage_key:Stage,payload:StageAssignment,ctx=Depends(require_upload_access)):
    return await platform_call('platform_workflow_responsibilities',{'target_workspace_id':ctx.workspace_id,
        'actor_user_id':ctx.user_id,'target_case_id':str(case_id),'operation':'write','target_stage_key':stage_key,
        'expected_updated_at':payload.expected_updated_at.isoformat() if payload.expected_updated_at else None,
        'new_owner_user_id':str(payload.owner_user_id) if payload.owner_user_id else None,
        'new_approver_user_id':str(payload.approver_user_id) if payload.approver_user_id else None})

@router.get('')
async def cases(filter:Literal['all','in_progress','review','pending_approval','approved','completed','archived']='all',q:str=Query('',max_length=120),
 dda:str=Query('all',max_length=48),owner:UUID|Literal['all','me','unassigned']='all',limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    if dda not in {'all',*(d['id'] for d in REGISTRY['ddas'])}:
        from fastapi import HTTPException
        raise HTTPException(422,'El DDA del filtro no es válido.')
    return await center.listing(ctx,filter_name=filter,search_text=q.strip(),dda=dda,owner_filter=str(owner),page_limit=limit,page_offset=offset)

@router.get('/{case_id}')
async def detail(case_id:UUID,ctx=Depends(require_upload_access)):return await center.detail(ctx,case_id)

@router.get('/{case_id}/runs')
async def history(case_id:UUID,node_id:Node,limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),run_id:UUID|None=None,ctx=Depends(require_upload_access)):
    return await center.history(ctx,case_id,node_id,limit,offset,run_id)

class CaseUpdate(CaseIdentity):
    model_config=ConfigDict(extra='forbid')
    expected_updated_at:AwareDatetime
    archived:bool|None=None
    @field_validator('label')
    @classmethod
    def trim(cls,value):
        if value is not None and not value.strip():raise ValueError('Ingresá un nombre o quitá la etiqueta.')
        return value.strip() if value is not None else None
    @model_validator(mode='after')
    def action(self):
        if not self.model_fields_set.intersection({'label','category','description'}) and self.archived is None:raise ValueError('Elegí un cambio para el caso.')
        return self

@router.patch('/{case_id}')
async def update(case_id:UUID,payload:CaseUpdate,ctx=Depends(require_upload_access)):
    if payload.model_fields_set.intersection({'category','description'}):
        if payload.archived is not None:
            from fastapi import HTTPException
            raise HTTPException(422,'Guardá la identidad y el archivo como acciones separadas.')
        return await platform_call('platform_update_case_identity',{'actor_user_id':ctx.user_id,'target_workspace_id':ctx.workspace_id,
            'target_case_id':str(case_id),'expected_updated_at':payload.expected_updated_at.isoformat(),
            'identity_changes':payload.model_dump(mode='json',include={'label','category','description'},exclude_unset=True)})
    return await platform_call('platform_update_case',{'actor_user_id':ctx.user_id,'target_workspace_id':ctx.workspace_id,
        'target_case_id':str(case_id),'expected_updated_at':payload.expected_updated_at.isoformat(),
        'change_label':'label' in payload.model_fields_set,'new_label':payload.label,'archive':payload.archived})

class CaseDataPack(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_updated_at:AwareDatetime
    orders_dataset_id:UUID
    fleet_dataset_id:UUID

@router.put('/{case_id}/data-pack')
async def replace_data_pack(case_id:UUID,payload:CaseDataPack,ctx=Depends(require_upload_access)):
    from app.services import decision_case_service
    from app.routes.dispatch import guarded
    await guarded(decision_case_service._validate_data_pack(str(payload.orders_dataset_id),str(payload.fleet_dataset_id)))
    return await platform_call('platform_replace_case_data_pack',{'actor_user_id':ctx.user_id,'target_workspace_id':ctx.workspace_id,
        'target_case_id':str(case_id),'expected_updated_at':payload.expected_updated_at.isoformat(),
        'orders_id':str(payload.orders_dataset_id),'fleet_id':str(payload.fleet_dataset_id)})
