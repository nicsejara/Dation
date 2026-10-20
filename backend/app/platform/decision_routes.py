from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,field_validator,model_validator
from app.auth import require_upload_access
from app.platform import decision_center as center
from app.platform.identity import platform_call

router=APIRouter(prefix='/decisions')
Node=Literal['logistics_assignment','logistics_scheduling','logistics_final_assignment']
Stage=Literal['data_preparation','logistics_assignment','logistics_scheduling']

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
async def cases(filter:Literal['all','in_progress','review','completed','archived']='all',q:str=Query('',max_length=120),
 dda:Literal['all','logistics']='all',limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await center.listing(ctx,filter_name=filter,search_text=q.strip(),dda=dda,page_limit=limit,page_offset=offset)

@router.get('/{case_id}')
async def detail(case_id:UUID,ctx=Depends(require_upload_access)):return await center.detail(ctx,case_id)

@router.get('/{case_id}/runs')
async def history(case_id:UUID,node_id:Node,limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await center.history(ctx,case_id,node_id,limit,offset)

class CaseUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_updated_at:AwareDatetime
    label:str|None=Field(None,max_length=120)
    archived:bool|None=None
    @field_validator('label')
    @classmethod
    def trim(cls,value):
        if value is not None and not value.strip():raise ValueError('Ingresá un nombre o quitá la etiqueta.')
        return value.strip() if value is not None else None
    @model_validator(mode='after')
    def action(self):
        if 'label' not in self.model_fields_set and self.archived is None:raise ValueError('Elegí un cambio para el caso.')
        return self

@router.patch('/{case_id}')
async def update(case_id:UUID,payload:CaseUpdate,ctx=Depends(require_upload_access)):
    return await platform_call('platform_update_case',{'actor_user_id':ctx.user_id,'target_workspace_id':ctx.workspace_id,
        'target_case_id':str(case_id),'expected_updated_at':payload.expected_updated_at.isoformat(),
        'change_label':'label' in payload.model_fields_set,'new_label':payload.label,'archive':payload.archived})
