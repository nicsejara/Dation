"""UX04 routes, opt-in in both runtime and SQL. No execution or engine endpoints."""
from uuid import UUID
from fastapi import APIRouter,Depends,File,UploadFile,Query
from app.platform.ultimate_data_routes import access,contents
from app.models.ultimate_data_pack import Entity,PackPublication
from app.models.decision_journey import PreparationCreate,PreparationRevision,PreparationOwner,PreparationFinalize,CaseClose
from app.services import decision_journey_service as service
router=APIRouter()
@router.get('/data-preparations')
async def preparations(ctx=Depends(access)):return await service.call(ctx,'list')
@router.post('/data-preparations')
async def create(payload:PreparationCreate,ctx=Depends(access)):return await service.create(ctx,payload)
@router.get('/data-preparations/{pid}')
async def read(pid:UUID,ctx=Depends(access)):return service.public(await service.state(ctx,pid))
@router.put('/data-preparations/{pid}/owner')
async def owner(pid:UUID,payload:PreparationOwner,ctx=Depends(access)):return service.public(await service.call(ctx,'owner',preparation_id=str(pid),**payload.model_dump(mode='json')))
@router.post('/data-preparations/{pid}/validate/{entity}')
async def validate(pid:UUID,entity:Entity,contract_hash:str=Query(pattern=r'^[0-9a-f]{64}$'),file:UploadFile=File(...),ctx=Depends(access)):return await service.validate(ctx,pid,entity,await contents(file),contract_hash)
@router.post('/data-preparations/{pid}/uploads/{entity}')
async def upload(pid:UUID,entity:Entity,upload_id:UUID,expected_revision:int=Query(ge=1),contract_hash:str=Query(pattern=r'^[0-9a-f]{64}$'),file:UploadFile=File(...),ctx=Depends(access)):return await service.upload(ctx,pid,entity,await contents(file),file.filename,upload_id,contract_hash,expected_revision)
@router.post('/data-preparations/{pid}/uploads/{uid}/recover')
async def recover(pid:UUID,uid:UUID,ctx=Depends(access)):return await service.recover(ctx,pid,uid)
@router.post('/data-preparations/{pid}/unselect/{entity}')
async def unselect(pid:UUID,entity:Entity,payload:PreparationRevision,ctx=Depends(access)):return service.public(await service.call(ctx,'unselect',preparation_id=str(pid),entity=entity,expected_revision=payload.expected_revision))
@router.post('/data-preparations/{pid}/finalize')
async def finalize(pid:UUID,payload:PreparationFinalize,ctx=Depends(access)):return await service.finalize(ctx,pid,payload)
@router.post('/data-preparations/{pid}/cleanup')
async def cleanup(pid:UUID,ctx=Depends(access)):return await service.cleanup(ctx,pid)
@router.get('/logistics-cases/{cid}/journey')
async def case_state(cid:UUID,ctx=Depends(access)):return (await service.case_state(ctx,cid))[1]
@router.post('/logistics-cases/{cid}/close')
async def close(cid:UUID,payload:CaseClose,ctx=Depends(access)):return await service.close(ctx,cid,payload.token)

@router.post('/logistics-cases/{cid}/journey/publish')
async def publish_guarded(cid:UUID,payload:PackPublication,ctx=Depends(access)):
    from app.services.case_data_pack_service import publication
    await service.call(ctx,'case_state',case_id=str(cid))
    return await publication(ctx,cid,payload,guarded=True)
