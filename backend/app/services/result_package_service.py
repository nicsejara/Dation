"""Schema-aware retrieval and present-tense approval overlay, never reassembly."""
import json
from fastapi import HTTPException
from app.results import contracts as c
from app.results.canonical import canonical_tree,canonical_bytes,content_sha256
from app.services import result_artifact_service as artifacts
from app.services.ultimate_run_service import call


async def snapshot(ctx,run_id,fingerprint):
    data=await call(ctx,'read',run_id=str(run_id),result_fingerprint=fingerprint)
    try:package,_=artifacts.bound_rows(data['run']['result_json'],data['artifacts'])
    except (ValueError,KeyError,TypeError):raise HTTPException(409,'RESULT_SCHEMA_OR_BINDING_ERROR') from None
    if str(package.context.workspace_id)!=ctx.workspace_id or str(package.decision.run_id)!=str(run_id) or package.fingerprints.result_fingerprint!=fingerprint:
        raise HTTPException(409,'RESULT_FINGERPRINT_MISMATCH')
    return package,data


async def result(ctx,run_id,fingerprint):
    package,data=await snapshot(ctx,run_id,fingerprint)
    overlay={**data['overlay'],'approval_allowed':False,'approval_blockers':[*data['overlay']['approval_blockers'],'INTEGRITY_CHECK_REQUIRED']}
    return c.ResultResponse(package=package,provenance=c.ResultBinding(run_id=run_id,result_fingerprint=fingerprint),approval_overlay=c.ApprovalOverlay.model_validate(overlay))


async def details(ctx,run_id,fingerprint,dataset_id,offset=0,limit=25):
    package,data=await snapshot(ctx,run_id,fingerprint)
    descriptor=next((d for d in package.details if d.dataset_id==dataset_id),None)
    if descriptor is None:raise HTTPException(404,'Dataset not found')
    rows=await artifacts.dataset(descriptor.data,data['artifacts'],offset=offset,limit=limit)
    return {'provenance':{'run_id':str(run_id),'result_fingerprint':fingerprint},'dataset_id':dataset_id,'offset':offset,'limit':limit,'total':descriptor.data.row_count,'rows':rows}


async def entity(ctx,run_id,fingerprint,entity_type,entity_id):
    package,data=await snapshot(ctx,run_id,fingerprint)
    descriptor=next(d for d in package.details if d.dataset_id=='evidence')
    rows=await artifacts.dataset(descriptor.data,data['artifacts'],entity=(entity_type,entity_id))
    row=next((r for r in rows if r['entity_type']==entity_type and r['entity_id']==entity_id),None)
    if row is None:raise HTTPException(404,'Entity not found')
    return {'provenance':{'run_id':str(run_id),'result_fingerprint':fingerprint},'entity':row}


async def artifact(ctx,run_id,fingerprint,artifact_id):
    package,data=await snapshot(ctx,run_id,fingerprint)
    row=next((r for r in data['artifacts'] if r['id']==str(artifact_id)),None)
    if row is None:raise HTTPException(404,'Artifact not found')
    return json.loads(await artifacts.read(row))


async def review(ctx,run_id,fingerprint):
    package,data=await snapshot(ctx,run_id,fingerprint)
    await artifacts.verify_all(package,data['artifacts'])
    package,data=await snapshot(ctx,run_id,fingerprint)
    return c.ApprovalReviewResponse(provenance=c.ResultBinding(run_id=run_id,result_fingerprint=fingerprint),approval_review=package.approval_review,
        approval_overlay=c.ApprovalOverlay.model_validate(data['overlay']))


async def approve(ctx,run_id,case_id,node_id,fingerprint):
    package,data=await snapshot(ctx,run_id,fingerprint)
    await artifacts.verify_all(package,data['artifacts'])
    result=await call(ctx,'approve',run_id=str(run_id),case_id=str(case_id),node_id=node_id,result_fingerprint=fingerprint,
        verified_manifest_hash=content_sha256(canonical_bytes(package.artifact_manifest.artifacts)))
    return {'id':str(run_id),'result_fingerprint':fingerprint,'approved_at':result['run']['approved_at'],'approved_by':result['run']['approved_by'],'approved_by_user_id':result['run']['approved_by_user_id']}


async def ai_context(ctx,run_id,fingerprint):
    from app.results.ai_context import DecisionContextBase,bind_context
    package,data=await snapshot(ctx,run_id,fingerprint)
    base=(await artifacts.dataset(package.ai_context.base_context,data['artifacts']))[0]
    return bind_context(DecisionContextBase.model_validate(base),package)
