"""T4 typed input routes. Model/contracts/paths always come from checked state."""
from uuid import UUID
from fastapi import APIRouter,Depends,File,HTTPException,Query,UploadFile
from fastapi.responses import Response
from app.auth import require_upload_access
from app.platform.entitlements import require_dda
from app.models.ultimate_data_pack import Entity,PackPublication
from app.services import case_data_pack_service as service
from app.domain.logistics.data_contracts import template_csv,MAX_BYTES

router=APIRouter(prefix='/logistics-cases')

def access(ctx=Depends(require_upload_access)):require_dda(ctx,'logistics');return ctx

async def contents(file):
    if not (file.filename or '').lower().endswith('.csv') or file.content_type not in ('text/csv','application/csv','application/octet-stream'):
        raise HTTPException(415,'Usá el template CSV UTF-8 de esta Model Version.')
    body=await file.read(MAX_BYTES+1)
    if len(body)>MAX_BYTES:raise HTTPException(413,'El CSV supera 10 MB.')
    return body

@router.get('/{case_id}/data')
async def data(case_id:UUID,offset:int=Query(0,ge=0,le=1000000),ctx=Depends(access)):return await service.context(ctx,case_id,offset)

@router.get('/{case_id}/data/contracts/{entity}')
async def contract(case_id:UUID,entity:Entity,ctx=Depends(access)):return (await service.contract_for(ctx,case_id,entity)).model_dump(mode='json')

@router.get('/{case_id}/data/templates/{entity}')
async def template(case_id:UUID,entity:Entity,ctx=Depends(access)):
    contract=await service.contract_for(ctx,case_id,entity)
    return Response(template_csv(contract),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{entity}.csv"','X-Dation-Contract-Hash':contract.contract_hash})

@router.post('/{case_id}/data/validate/{entity}')
async def validate(case_id:UUID,entity:Entity,contract_hash:str=Query(...,pattern=r'^[0-9a-f]{64}$'),file:UploadFile=File(...),ctx=Depends(access)):
    return await service.validate(ctx,case_id,entity,await contents(file),contract_hash)

@router.post('/{case_id}/data/uploads/{entity}')
async def upload(case_id:UUID,entity:Entity,upload_id:UUID,contract_hash:str=Query(...,pattern=r'^[0-9a-f]{64}$'),file:UploadFile=File(...),ctx=Depends(access)):
    return await service.upload(ctx,case_id,entity,await contents(file),file.filename,upload_id,contract_hash)

@router.post('/{case_id}/data/uploads/{upload_id}/recover')
async def recover(case_id:UUID,upload_id:UUID,ctx=Depends(access)):return await service.recover(ctx,case_id,upload_id)

@router.post('/{case_id}/data/uploads/{upload_id}/discard')
async def discard(case_id:UUID,upload_id:UUID,ctx=Depends(access)):return await service.discard(ctx,case_id,upload_id)

@router.get('/{case_id}/data/reuse/{entity}')
async def reuse(case_id:UUID,entity:Entity,offset:int=Query(0,ge=0,le=1000000),ctx=Depends(access)):return await service.compatible(ctx,case_id,entity,offset)

@router.post('/{case_id}/data/publish')
async def publish(case_id:UUID,payload:PackPublication,ctx=Depends(access)):return await service.publication(ctx,case_id,payload)

@router.get('/{case_id}/data/versions/{version_id}')
async def history(case_id:UUID,version_id:UUID,ctx=Depends(access)):return await service.version(ctx,case_id,version_id)

@router.get('/{case_id}/data/preview/{dataset_id}')
async def preview(case_id:UUID,dataset_id:UUID,ctx=Depends(access)):
    # Case membership/binding before a workspace-wide normalized dataset read.
    state=await service.state(ctx,case_id)
    if str(dataset_id) not in {e['dataset_id'] for e in state['entries']}|{j.get('dataset_id') for j in state['uploads']}:
        raise HTTPException(404,'El input no está vinculado a este Case.')
    return await service.normalized_preview(ctx,dataset_id,10)
