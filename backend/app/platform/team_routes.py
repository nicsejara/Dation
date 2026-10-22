"""Workspace collaboration. SQL rechecks membership, role and optimistic versions."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from app.auth import require_upload_access
from app.platform.auth_routes import Email
from app.platform.identity import platform_call

Role = Literal['admin', 'operator', 'viewer']
Responsibility = Literal['data_owner', 'decision_owner']
Node = Literal['logistics_assignment', 'logistics_scheduling', 'logistics_final_assignment']
router = APIRouter()

@router.get('/team')
async def team(q: str = Query('', max_length=120), limit: int = Query(25, ge=1, le=50),
               offset: int = Query(0, ge=0, le=1000000), candidates: bool = False,
               responsibility: Literal['data','data_owner','data_steward','decision_owner','approver'] | None = None,
               ctx=Depends(require_upload_access)):
    if responsibility and not candidates:
        from fastapi import HTTPException
        raise HTTPException(422,'El filtro de responsabilidad requiere candidates=true.')
    return await platform_call('platform_team_foundation', {'target_workspace_id': ctx.workspace_id,
        'actor_user_id': ctx.user_id, 'search_text': q.strip(), 'page_limit': limit,
        'page_offset': offset, 'candidates_only': candidates,'responsibility_group':responsibility})

class Invitation(Email):
    access_role: Role
    business_role: Responsibility | None = None

@router.post('/team/invitations', status_code=201)
async def invite(payload: Invitation, ctx=Depends(require_upload_access)):
    return await platform_call('platform_invite_member', {'target_workspace_id': ctx.workspace_id,
        'actor_user_id': ctx.user_id, 'invite_email': payload.email, 'invite_role': payload.access_role,
        'invite_business_role': payload.business_role})

class Version(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_updated_at: AwareDatetime

class Responsibilities(Version):
    business_roles: list[Responsibility] = Field(max_length=4)

@router.patch('/team/members/{user_id}/responsibilities')
async def responsibilities(user_id: UUID,payload: Responsibilities,ctx=Depends(require_upload_access)):
    from fastapi import HTTPException
    if len(payload.business_roles)>4 or len(set(payload.business_roles))!=len(payload.business_roles):
        raise HTTPException(422,'Elegí responsabilidades distintas y válidas.')
    return await platform_call('platform_set_member_responsibilities',{'target_workspace_id':ctx.workspace_id,
        'actor_user_id':ctx.user_id,'member_user_id':str(user_id),'expected_updated_at':payload.expected_updated_at.isoformat(),
        'new_responsibilities':payload.business_roles})

@router.post('/team/invitations/{invitation_id}/revoke')
async def revoke(invitation_id: UUID, payload: Version, ctx=Depends(require_upload_access)):
    return await platform_call('platform_revoke_invitation', {'target_workspace_id': ctx.workspace_id,
        'actor_user_id': ctx.user_id, 'invitation_id': str(invitation_id),
        'expected_updated_at': payload.expected_updated_at.isoformat()})

class MemberUpdate(Version):
    access_role: Role
    business_role: Responsibility | None = None
    business_roles: list[Responsibility] | None = Field(None,max_length=4)
    status: Literal['active', 'disabled']
    @model_validator(mode='after')
    def responsibility_contract(self):
        if self.business_roles is None:
            if 'business_role' not in self.model_fields_set:
                raise ValueError('Indicá las responsabilidades que querés conservar o modificar.')
        elif 'business_role' in self.model_fields_set or len(set(self.business_roles))!=len(self.business_roles):
            raise ValueError('Usá una única lista de responsabilidades distintas.')
        return self

@router.patch('/team/members/{user_id}')
async def update_member(user_id: UUID, payload: MemberUpdate, ctx=Depends(require_upload_access)):
    if payload.business_roles is not None:
        return await platform_call('platform_update_member_foundation', {'target_workspace_id':ctx.workspace_id,
            'actor_user_id':ctx.user_id,'member_user_id':str(user_id),'expected_updated_at':payload.expected_updated_at.isoformat(),
            'new_role':payload.access_role,'new_status':payload.status,'new_business_roles':payload.business_roles})
    return await platform_call('platform_update_member', {'target_workspace_id': ctx.workspace_id,
        'actor_user_id': ctx.user_id, 'member_user_id': str(user_id),
        'expected_updated_at': payload.expected_updated_at.isoformat(), 'new_role': payload.access_role,
        'new_business_role': payload.business_role, 'new_status': payload.status})

class AssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_updated_at: AwareDatetime | None
    owner_user_id: UUID | None
    approver_user_id: UUID | None

@router.put('/decisions/{case_id}/assignments/{node_id}')
async def assign(case_id: UUID, node_id: Node, payload: AssignmentUpdate, ctx=Depends(require_upload_access)):
    return await platform_call('platform_assign_decision', {'target_workspace_id': ctx.workspace_id,
        'actor_user_id': ctx.user_id, 'target_case_id': str(case_id), 'target_node_id': node_id,
        'expected_updated_at': payload.expected_updated_at.isoformat() if payload.expected_updated_at else None,
        'new_owner_user_id': str(payload.owner_user_id) if payload.owner_user_id else None,
        'new_approver_user_id': str(payload.approver_user_id) if payload.approver_user_id else None})
