"""T8 versioned/schema-aware retrieval. No public dashboard or LLM producer."""
from uuid import UUID
from typing import Annotated,Literal
from fastapi import APIRouter,Depends,Query,HTTPException,Response
from app.auth import require_upload_access
from app.services import result_package_service as service
from app.services.ultimate_run_service import configuration
from app.domain.logistics.base import EntityType
from app.results import contracts as c
from app.results.canonical import canonical_tree
from app.services import result_consumer_service as consumers,ultimate_decision_context as copilot

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
    return await consumers.entity(ctx,run_id,expected_result_fingerprint,entity_type.value,entity_id)

@router.get('/api/runs/{run_id}/artifacts/{artifact_id}')
async def artifact(run_id:UUID,artifact_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await service.artifact(ctx,run_id,expected_result_fingerprint,artifact_id)

@router.get('/api/runs/{run_id}/approval-review')
async def review(run_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await service.review(ctx,run_id,expected_result_fingerprint)

@router.get('/api/runs/{run_id}/primary-visual')
async def primary_visual(run_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await consumers.primary_visual(ctx,run_id,expected_result_fingerprint)

@router.get('/api/runs/{run_id}/visual-entities/{graph_node_id}')
async def visual_entity(run_id:UUID,graph_node_id:str,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await consumers.visual_entity(ctx,run_id,expected_result_fingerprint,graph_node_id)

@router.get('/api/runs/{run_id}/resource-capacities')
async def resource_capacities(run_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await consumers.resource_capacities(ctx,run_id,expected_result_fingerprint)

@router.get('/api/runs/{run_id}/analysis-status')
async def analysis_status(run_id:UUID,expected_result_fingerprint:Fingerprint,ctx=Depends(require_upload_access)):
    return await consumers.analysis_status(ctx,run_id,expected_result_fingerprint)

@router.get('/api/runs/{run_id}/decision-export')
async def decision_export(run_id:UUID,expected_result_fingerprint:Fingerprint,format:Literal['csv','json']='csv',ctx=Depends(require_upload_access)):
    name,body,media=await consumers.export(ctx,run_id,expected_result_fingerprint,format)
    return Response(body,media_type=media,headers={'Content-Disposition':f'attachment; filename="{name}"','X-Run-Id':str(run_id),'X-Result-Fingerprint':expected_result_fingerprint})

@router.get('/api/runs/{run_id}/decision-context')
async def decision_context(run_id:UUID,expected_result_fingerprint:Fingerprint,mode:Literal['EXPLAIN','EXPLORE','COMPARE','REVIEW']='EXPLAIN',
    entity_type:EntityType|None=None,entity_id:str|None=Query(None,pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$'),
    alternative_ids:list[str]=Query(default=[]),ctx=Depends(require_upload_access)):
    if (entity_type is None)!=(entity_id is None):raise HTTPException(422,'Entity type and ID are required together')
    selected=c.EntityRef(type=entity_type.value,id=entity_id) if entity_type else None
    package,data,context,material=await copilot.context(ctx,run_id,expected_result_fingerprint,mode,selected,alternative_ids)
    return {'context':canonical_tree(context),'selected_evidence':material,'approval_overlay':data['overlay'],
        'approval_state':'APPROVED' if data['run'].get('approved_at') else 'RECOMMENDATION'}

@router.post('/api/runs/{run_id}/copilot')
async def copilot_turn(run_id:UUID,expected_result_fingerprint:Fingerprint,body:copilot.CopilotRequest,ctx=Depends(require_upload_access)):
    return await copilot.turn(ctx,run_id,expected_result_fingerprint,body)

@router.get('/api/runs/{run_id}/copilot-history')
async def copilot_history(run_id:UUID,expected_result_fingerprint:Fingerprint,offset:int=Query(0,ge=0,le=1000000),ctx=Depends(require_upload_access)):
    return await copilot.history(ctx,run_id,expected_result_fingerprint,offset)
