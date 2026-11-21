"""Checked J1.02 reads/writes; production activation remains independently gated."""
from fastapi import HTTPException
from app.platform.identity import platform_call
from app.models.decision_case_v2 import DecisionCaseDefinitionV2
from app.results.canonical import canonical_tree, canonical_bytes, content_sha256, policy_hash


async def call(ctx,operation,**arguments):
    return await platform_call('platform_decision_case_v2',{'target_workspace_id':ctx.workspace_id,
        'actor_user_id':ctx.user_id,'operation':operation,'arguments':canonical_tree(arguments)})


async def require_writes(ctx):
    from app.services.logistics_model_service import capabilities
    if not (await capabilities(ctx)).get('decision_case_v2_enabled',False):
        raise HTTPException(409,'Decision Case V2 permanece cerrado para este acceso.')


def checked_revision(row):
    definition=DecisionCaseDefinitionV2.model_validate(row['snapshot'])
    if content_sha256(canonical_bytes(definition))!=row['definition_hash']:
        raise HTTPException(409,'El snapshot de definición no coincide con su huella canónica.')
    return row


async def validate(ctx,definition):
    await require_writes(ctx)
    result=await call(ctx,'validate',definition_v2=definition)
    if result.get('definition_hash')!=content_sha256(canonical_bytes(definition)):
        raise HTTPException(409,'La confirmación no corresponde a esta definición.')
    return result


async def update(ctx,case_id,payload):
    await require_writes(ctx)
    from app.services.logistics_model_service import enrich_context
    result=await call(ctx,'update',case_id=str(case_id),**payload.model_dump(mode='python'),
        case_policy_hash=policy_hash(payload.definition_v2.case_policy))
    return enrich_context(result)


async def enrich_listing(ctx,items):
    if not items:return items
    data=await call(ctx,'projection',case_ids=[item['id'] for item in items])
    return [{**item,'case_definition_context':data.get(item['id'])} for item in items]


async def from_run(ctx,case_id,run_id):
    run=await call(ctx,'run_context',case_id=str(case_id),run_id=str(run_id))
    binding=run.get('definition_binding')
    if not binding:return {'legacy':True,'run_id':str(run_id),'revision':None}
    row=checked_revision(await call(ctx,'revision',case_id=str(case_id),revision_id=binding['definition_revision_id']))
    if row['definition_hash']!=binding['definition_hash']:
        raise HTTPException(409,'La definición de la corrida no coincide con el snapshot.')
    return {'legacy':False,'run_id':str(run_id),'revision':row}


async def acceptance(ctx,case_id,run_id=None):
    from app.services import decision_graph_service as graphs, ultimate_run_service as runs
    referenced_by=None
    if run_id:
        requested=await call(ctx,'run_context',case_id=str(case_id),run_id=str(run_id))
        if requested['node_id']=='logistics_scheduling':
            referenced_by=str(run_id);run_id=requested.get('upstream_run_id')
            if not run_id:return {'status':'NOT_EVALUABLE','reason':'D2 no identifica su D1 aprobado.'}
    raw=await graphs.snapshot(ctx,case_id,node_id='logistics_assignment',run_id=run_id)
    if not raw.get('case_definition'):
        return {'status':'NOT_CONFIGURED','reason':'Case histórico sin criterio J1.02.'}
    candidates=[r for r in raw.get('runs',[]) if r.get('node_id')=='logistics_assignment']
    run=raw.get('selected_run') if run_id else next((r for r in candidates if r.get('id')==raw['case'].get('assignment_run_id')),None)
    if run is None and not run_id:
        run=max(candidates,key=lambda r:(r.get('created_at',''),r['id']),default=None)
    if run is None:return {'status':'PENDING','reason':'Todavía no hay una corrida D1 para evaluar.'}
    run=await call(ctx,'run_context',case_id=str(case_id),run_id=run['id'])
    if not run.get('result_fingerprint') or run.get('status')!='completed':
        return {'status':'NOT_EVALUABLE','run_id':run['id'],'reason':'La corrida aún no tiene un resultado certificado.'}
    from app.services import result_package_service as packages
    # The existing delivery path checks current tenant access and immutable
    # artifact indexes before any result can be evaluated.
    package,data=await packages.snapshot(ctx,run['id'],run['result_fingerprint'])
    core,evidence,_=await runs.source_facts(package,data['artifacts'])
    from app.domain.logistics.case_acceptance import evaluate_acceptance
    from app.results.contracts import EngineOutput
    evaluated=evaluate_acceptance(EngineOutput(core=core,evidence=evidence),expected_case_id=case_id,expected_run_id=run['id'],
        expected_pack_id=run['data_pack_version_id'],expected_model_version_id=run['logistics_model_version_id'],
        expected_definition_id=(run.get('definition_binding') or {}).get('definition_revision_id'))
    return {**evaluated,**({'referenced_by_d2_run_id':referenced_by} if referenced_by else {})}
