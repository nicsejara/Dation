"""Data Hub is workspace-wide; executing/reusing a DDA still requires its grant."""
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import quote
from uuid import UUID
import httpx
from fastapi import APIRouter,Depends,File,HTTPException,Query,UploadFile
from fastapi.responses import Response
from pydantic import BaseModel,ConfigDict
from app.auth import require_upload_access
from app.platform import data_hub as hub
from app.services import dispatch_service as dispatch
from app.services.run_service import download_dataset
from app.validators.contracts import public_contracts,template_csv

router=APIRouter(prefix='/data',dependencies=[Depends(require_upload_access)])
Kind=Literal['orders','fleet']

async def guarded(call):
    try:return await call
    except LookupError:raise HTTPException(404,'No se encontró el dataset.') from None
    except ValueError as error:raise HTTPException(422,str(error)) from None
    except httpx.HTTPError:raise HTTPException(503,'No se pudo completar la operación de datos. Reintentá.') from None

async def csv_contents(file):
    if not (file.filename or '').lower().endswith('.csv'):raise HTTPException(400,'Sólo se admiten archivos CSV.')
    contents=await file.read(10*1024*1024+1)
    if len(contents)>10*1024*1024:raise HTTPException(413,'El archivo supera el límite de 10 MB.')
    return contents

@router.get('/datasets')
async def datasets(filter:Literal['all','orders','fleet','validated','issues','archived']='all',
 type:Literal['all','orders','fleet','logistics_legacy']='all',
 validation:Literal['all','validated','issues','unknown']='all',state:Literal['active','archived','all']='active',
 q:str=Query('',max_length=120),limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    # Preserve legacy filter callers; explicit dimensions compose in V2.
    if filter in ('orders','fleet') and type=='all':type=filter
    if filter in ('validated','issues') and validation=='all':validation=filter
    if filter=='archived':state='archived'
    return await hub.library(ctx,dataset_type=type,validation_state=validation,lifecycle_state=state,
        search_text=q.strip(),page_limit=limit,page_offset=offset)

@router.get('/contracts')
async def contracts():return {'formats':public_contracts()}

@router.get('/templates/{kind}')
async def template(kind:Kind):
    return Response(template_csv(kind),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{kind}.csv"'})

@router.post('/datasets/validate')
async def validate(kind:Kind=Query(...,alias='dataset_type'),file:UploadFile=File(...)):
    return dispatch.validate_input(file.filename,await csv_contents(file),kind)

@router.post('/datasets/upload')
async def upload(kind:Kind=Query(...,alias='dataset_type'),file:UploadFile=File(...)):
    return await guarded(dispatch.store_input(file.filename,await csv_contents(file),kind,track_upload=True))

@router.get('/datasets/{dataset_id}')
async def dataset(dataset_id:UUID,limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await hub.dataset_detail(ctx,dataset_id,limit,offset)

@router.post('/uploads/{operation_id}/discard')
async def discard_upload(operation_id:UUID,ctx=Depends(require_upload_access)):
    return await hub.discard_upload(ctx,operation_id)

@router.get('/datasets/{dataset_id}/preview')
async def preview(dataset_id:UUID,limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await guarded(hub.preview(ctx,dataset_id,limit,offset))

@router.get('/datasets/{dataset_id}/download')
async def download(dataset_id:UUID,ctx=Depends(require_upload_access)):
    row=await hub.active_dataset(ctx,dataset_id)
    contents=await guarded(download_dataset(row))
    filename=PurePosixPath((row.get('original_filename') or 'datos.csv').replace('\\','/')).name
    return Response(contents,media_type='text/csv; charset=utf-8',headers={
        'Content-Disposition':"attachment; filename=datos.csv; filename*=UTF-8''"+quote(filename,safe='')})

@router.post('/datasets/{dataset_id}/reuse')
async def reuse(dataset_id:UUID,ctx=Depends(require_upload_access)):
    return await guarded(hub.reuse(ctx,dataset_id=dataset_id))

@router.post('/datasets/{dataset_id}/archive')
async def archive(dataset_id:UUID,ctx=Depends(require_upload_access)):
    return await guarded(hub.archive_input(ctx,dataset_id,True))

@router.post('/datasets/{dataset_id}/unarchive')
async def unarchive(dataset_id:UUID,ctx=Depends(require_upload_access)):
    return await guarded(hub.archive_input(ctx,dataset_id,False))

@router.delete('/datasets/{dataset_id}')
async def delete(dataset_id:UUID,ctx=Depends(require_upload_access)):
    return await hub.delete_dataset(ctx,dataset_id)

@router.get('/packs')
async def packs(q:str=Query('',max_length=120),limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await hub.snapshot(ctx,resource='packs',search_text=q.strip(),page_limit=limit,page_offset=offset)

@router.get('/pack')
async def pack(orders_id:UUID,fleet_id:UUID,limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await hub.snapshot(ctx,resource='pack',orders_id=str(orders_id),fleet_id=str(fleet_id),page_limit=limit,page_offset=offset)

class PackRef(BaseModel):
    model_config=ConfigDict(extra='forbid')
    orders_id:UUID
    fleet_id:UUID

@router.post('/pack/reuse')
async def reuse_pack(payload:PackRef,ctx=Depends(require_upload_access)):
    await hub.snapshot(ctx,resource='pack',orders_id=str(payload.orders_id),fleet_id=str(payload.fleet_id))
    return await guarded(hub.reuse(ctx,orders_id=payload.orders_id,fleet_id=payload.fleet_id))
