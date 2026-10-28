"""T8 versioned/schema-aware retrieval. No public dashboard or LLM producer."""
from uuid import UUID
from typing import Annotated,Literal
from fastapi import APIRouter,Depends,Query
from app.auth import require_upload_access
from app.services import result_package_service as service
from app.services.ultimate_run_service import configuration
from app.domain.logistics.base import EntityType

router=APIRouter()
Fingerprint=Annotated[str,Query(pattern=r'^[0-9a-f]{64}$')]

@router.get('/api/platform/logistics-cases/{case_id}/run-context')
async def run_context(case_id:UUID,node_id:Literal['logistics_assignment','logistics_scheduling']='logistics_assignment',ctx=Depends(require_upload_access)):return await configuration(ctx,case_id,node_id)

@router.get('/api/runs/{run_id}/result')
async def result(run_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await service.result(ctx,run_id,expected_result_fingerprint)

@router.get('/api/runs/{run_id}/details/{dataset_id}')
async def details(run_id:UUID,dataset_id:str,expected_result_fingerprint:Fingerprint,offset:int=Query(0,ge=0,le=1000000),limit:int=Query(25,ge=1,le=100),ctx=Depends(require_upload_access)):
    return await service.details(ctx,run_id,expected_result_fingerprint,dataset_id,offset,limit)

@router.get('/api/runs/{run_id}/entities/{entity_type}/{entity_id}')
async def entity(run_id:UUID,entity_type:EntityType,entity_id:str,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await service.entity(ctx,run_id,expected_result_fingerprint,entity_type.value,entity_id)

@router.get('/api/runs/{run_id}/artifacts/{artifact_id}')
async def artifact(run_id:UUID,artifact_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await service.artifact(ctx,run_id,expected_result_fingerprint,artifact_id)

@router.get('/api/runs/{run_id}/approval-review')
async def review(run_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await service.review(ctx,run_id,expected_result_fingerprint)
