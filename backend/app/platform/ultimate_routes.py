"""Versioned Model/Case setup routes. Cohort creation is checked in SQL and closed by default."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.auth import require_upload_access
from app.platform.entitlements import require_dda
from app.models.ultimate_foundation import ModelCreate,ModelUpdate,ModelPublish,ModelContractPreview,UltimateCaseCreate,UltimateCaseUpdate
from app.services import logistics_model_service as service

router=APIRouter()

def logistics(ctx):require_dda(ctx,'logistics');return ctx

@router.get('/ultimate-foundation/capabilities')
async def capabilities(ctx=Depends(require_upload_access)):
    return await service.capabilities(ctx)

@router.get('/logistics-models')
async def models(q:str=Query('',max_length=120),include_archived:bool=False,limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await service.list_models(logistics(ctx),search_text=q,include_archived=include_archived,limit=limit,offset=offset)

@router.post('/logistics-models')
async def create_model(payload:ModelCreate,ctx=Depends(require_upload_access)):
    return await service.create_model(logistics(ctx),payload)

@router.post('/logistics-models/contract-preview')
async def contract_preview(payload:ModelContractPreview,ctx=Depends(require_upload_access)):
    provisional,contracts=await service.preview_contracts(logistics(ctx),payload)
    return {'provisional':provisional,'contracts':{entity:contract.model_dump(mode='json',exclude={'model_version_id','contract_hash'} if provisional else set()) for entity,contract in contracts.items()}}

@router.post('/logistics-models/contract-preview/templates/{entity}')
async def preview_template(entity:str,payload:ModelContractPreview,ctx=Depends(require_upload_access)):
    from fastapi import HTTPException
    from fastapi.responses import Response
    from app.domain.logistics.data_contracts import ENTITIES,template_csv
    if entity not in ENTITIES:raise HTTPException(404,'Template no disponible.')
    _,contracts=await service.preview_contracts(logistics(ctx),payload)
    return Response(template_csv(contracts[entity]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{entity}.csv"'})

@router.get('/logistics-models/{model_id}')
async def model(model_id:UUID,ctx=Depends(require_upload_access)):
    return await service.get_model(logistics(ctx),model_id)

@router.put('/logistics-models/{model_id}')
async def update_model(model_id:UUID,payload:ModelUpdate,ctx=Depends(require_upload_access)):
    return await service.update_model(logistics(ctx),model_id,payload)

@router.post('/logistics-models/{model_id}/versions')
async def publish_model(model_id:UUID,payload:ModelPublish,ctx=Depends(require_upload_access)):
    return await service.publish_model(logistics(ctx),model_id,payload)

@router.post('/logistics-cases')
async def create_case(payload:UltimateCaseCreate,ctx=Depends(require_upload_access)):
    return await service.create_case(logistics(ctx),payload)

@router.get('/logistics-cases/{case_id}/context')
async def context(case_id:UUID,ctx=Depends(require_upload_access)):
    from app.services import decision_graph_service
    return await decision_graph_service.case_context(logistics(ctx),case_id)

@router.patch('/logistics-cases/{case_id}/context')
async def update_context(case_id:UUID,payload:UltimateCaseUpdate,ctx=Depends(require_upload_access)):
    return await service.update_case_context(logistics(ctx),case_id,payload)
