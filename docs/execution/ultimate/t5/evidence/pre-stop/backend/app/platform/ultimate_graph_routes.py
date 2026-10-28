"""T5 read/config-context only. No admission or graph supplied by the browser."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from app.auth import require_upload_access
from app.platform.entitlements import require_dda
from app.services import decision_graph_service as service

router=APIRouter(prefix='/logistics-cases')
Node=Literal['logistics_assignment','logistics_scheduling']
def access(ctx=Depends(require_upload_access)):require_dda(ctx,'logistics');return ctx

@router.get('/{case_id}/graph')
async def graph(case_id:UUID,node_id:Node|None=None,run_id:UUID|None=None,ctx=Depends(access)):
    return await service.read(ctx,case_id,node_id,run_id)

@router.get('/{case_id}/graph/config/{node_id}')
async def config(case_id:UUID,node_id:Node,ctx=Depends(access)):return await service.configure(ctx,case_id,node_id)

@router.get('/{case_id}/graph/history/{node_id}')
async def history(case_id:UUID,node_id:Node,limit:int=Query(25,ge=1,le=50),offset:int=Query(0,ge=0,le=1000000),ctx=Depends(access)):
    return await service.history(ctx,case_id,node_id,limit,offset)
