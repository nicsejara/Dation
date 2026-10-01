from uuid import UUID
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
from app.auth import require_upload_access
from app.models.dispatch_config import DispatchConfig, DispatchOptions
from app.services import dispatch_service as service

router=APIRouter(dependencies=[Depends(require_upload_access)])


class Inputs(BaseModel):
    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    allow_third_party: bool=True


class RunRequest(BaseModel):
    orders_dataset_id: UUID
    fleet_dataset_id: UUID
    configuration: DispatchConfig=DispatchConfig()
    options: DispatchOptions=DispatchOptions()


async def guarded(call):
    try:return await call
    except TimeoutError as exc:raise HTTPException(408,str(exc)) from exc
    except LookupError as exc:raise HTTPException(404,str(exc)) from exc
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    except httpx.HTTPError as exc:raise HTTPException(502,'No se pudo guardar o recuperar la información de despacho.') from exc


@router.get('/api/dispatch/status')
async def status():
    ready=await service.available()
    return {'available':ready,'engine_version':'1.0.0','message':None if ready else 'El nuevo DDA requiere aplicar la migración de despacho en Supabase.'}


@router.post('/api/runs/preflight')
async def preflight(payload: Inputs):
    return await guarded(service.check_inputs(str(payload.orders_dataset_id),str(payload.fleet_dataset_id),payload.allow_third_party))


@router.post('/api/runs')
async def run(payload: RunRequest, run_id: UUID | None=Query(None)):
    if not await service.available():raise HTTPException(503,'La migración de despacho todavía no está disponible.')
    return await guarded(service.execute(str(payload.orders_dataset_id),str(payload.fleet_dataset_id),
        payload.configuration.model_dump(),payload.options.model_dump(),str(run_id) if run_id else None))


@router.post('/api/datasets/{dataset_id}/default')
async def default(dataset_id: UUID):
    await guarded(service.db('POST','rpc/set_default_fleet',body={'target_id':str(dataset_id)}))
    return {'ok':True}


@router.get('/api/dispatch/templates/{kind}')
async def template(kind: str):
    if kind not in ('orders','fleet'):raise HTTPException(404,'Plantilla no disponible.')
    return FileResponse(Path(__file__).resolve().parents[1]/'static'/'templates'/f'{kind}.csv',media_type='text/csv',filename=f'{kind}.csv')
