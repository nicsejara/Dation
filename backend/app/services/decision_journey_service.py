"""Private pre-Case saga. Reuses canonical compiler, normalizer and Pack service."""
import os,json
from pathlib import PurePosixPath
from uuid import UUID,uuid5
from fastapi import HTTPException
from app.platform.identity import platform_call,headers
from app.services import case_data_pack_service as packs,logistics_model_service as models,decision_graph_service as graphs
from app.domain.logistics.data_contracts import compile_contract,ENTITIES,entities_for,MAX_BYTES
from app.domain.logistics.normalizers import normalize_input,InputValidationError
from app.models.ultimate_foundation import UltimateCaseCreate
from app.models.ultimate_data_pack import PackPublication
from app.services.http_service import http_client
from app.config import SUPABASE_INPUT_BUCKET


def enabled():return os.getenv('DATION_UNIFIED_JOURNEY_ENABLED','false').lower()=='true'

async def call(ctx,operation,**arguments):
    if not enabled():raise HTTPException(404,'Unified Decision Journey todavía no está activado.')
    return await platform_call('platform_decision_journey',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,'operation':operation,'arguments':arguments})

async def capabilities(ctx):return bool(enabled() and (await call(ctx,'capabilities')).get('enabled'))

async def state(ctx,pid):return await call(ctx,'get',preparation_id=str(pid))

def contracts(data):return {e:compile_contract(data['model_version'],e) for e in entities_for(data['model_version'])}

def contract_of(data,entity):
    if entity not in entities_for(data['model_version']):raise HTTPException(404,'El modelo no utiliza ese archivo.')
    return compile_contract(data['model_version'],entity)

def public(data):
    s=data['session'];uploads=[];catalog='order_lines' in entities_for(data['model_version'])
    for u in data['uploads']:
        m=u['metadata'];uploads.append({k:u[k] for k in ('id','entity','ready','selected')}|{'filename':m['filename'],'raw_sha256':m['raw_sha256'],'contract_hash':m['contract_hash'],'report':m['report']}|({'canonical_sha256':m['canonical_sha256']} if catalog else {}))
    result = {'session':{**{k:s[k] for k in ('id','revision','status','model_version_id','parent_case_id','case_id','expires_at','data_owner_user_id')},'creation_intent':s['creation_body']},'uploads':uploads,'contracts':{e:c.model_dump(mode='json') for e,c in contracts(data).items()}}
    if 'order_lines' in result['contracts']:result['bundle_validation_required']=True
    return result

async def create(ctx,payload):return public(await call(ctx,'create',**payload.model_dump(mode='json')))

async def validate(ctx,pid,entity,raw,expected):
    data=await state(ctx,pid);contract=contract_of(data,entity);packs.checked_hash(contract,expected)
    if data['session']['status'] not in ('DRAFT','VALIDATED'):raise HTTPException(409,'La preparación ya tiene una intención de creación congelada.')
    try:return normalize_input(raw,contract)['report']
    except InputValidationError as error:raise HTTPException(422,error.report) from None


def paths(data,u):
    base=f"{data['session']['workspace_id']}/preparations/{data['session']['id']}/{u['id']}"
    return base+'/input.csv',base+'/normalized/snapshot.json'

async def upload(ctx,pid,entity,raw,filename,uid,expected,revision,*,source_dataset_id=None):
    data=await state(ctx,pid);contract=contract_of(data,entity);packs.checked_hash(contract,expected)
    try:n=normalize_input(raw,contract)
    except InputValidationError as error:raise HTTPException(422,error.report) from None
    metadata={'filename':PurePosixPath((filename or entity+'.csv').replace('\\','/')).name[:120],
      'raw_sha256':n['raw_sha256'],'raw_size':len(raw),'canonical_sha256':n['canonical_sha256'],'normalized_size':n['normalized_size'],
      'bucket':SUPABASE_INPUT_BUCKET,'contract_hash':contract.contract_hash,'report':n['report']}
    if source_dataset_id:metadata['source_dataset_id']=str(source_dataset_id)
    intent=models.snapshot_hash('journey_upload_v1',{'actor':ctx.user_id,'entity':entity,'metadata':metadata})
    data=await call(ctx,'upload_prepare',preparation_id=str(pid),upload_id=str(uid),entity=entity,metadata=metadata,intent_hash=intent,expected_revision=revision)
    u=data['upload'];a,b=paths(data,u)
    await packs.private_bucket(metadata['bucket']);await packs.put_object(metadata['bucket'],a,raw,'text/csv',n['raw_sha256'])
    return await recover(ctx,pid,uid)

async def recover(ctx,pid,uid):
    data=await call(ctx,'upload_get',preparation_id=str(pid),upload_id=str(uid));u=data['upload'];m=u['metadata']
    if u['ready']:return public(data)
    a,b=paths(data,u);await packs.private_bucket(m['bucket'])
    raw=await packs.read_object(m['bucket'],a,m['raw_sha256'],m['raw_size'])
    contract=contracts(data)[u['entity']];packs.checked_hash(contract,m['contract_hash'])
    try:n=normalize_input(raw,contract)
    except InputValidationError:raise HTTPException(409,'El snapshot no cumple el contrato publicado.') from None
    if n['canonical_sha256']!=m['canonical_sha256'] or n['normalized_size']!=m['normalized_size']:raise HTTPException(409,'La interpretación del snapshot cambió.')
    await packs.put_object(m['bucket'],b,n['bytes'],'application/json',m['canonical_sha256'])
    await packs.read_object(m['bucket'],b,m['canonical_sha256'],m['normalized_size'])
    return public(await call(ctx,'upload_ready',preparation_id=str(pid),upload_id=str(uid),expected_revision=data['session']['revision']))

async def cleanup(ctx,pid):
    # Stage objects are never Pack objects. Only expired/consumed sessions qualify.
    data=await call(ctx,'cleanup',preparation_id=str(pid));removed=0
    for u in data['uploads']:
        shell={'session':{'workspace_id':ctx.workspace_id,'id':str(pid)}};a,b=paths(shell,u)
        async with http_client() as client:
            for path in (a,b):
                r=await client.delete(packs.object_url(u['metadata']['bucket'],path),headers=headers(),timeout=30)
                if r.status_code not in (200,204,404):raise HTTPException(503,'La limpieza privada sigue pendiente; no se tocaron snapshots publicados.')
        await call(ctx,'cleanup_done',preparation_id=str(pid),upload_id=u['id']);removed+=1
    return {'removed_uploads':removed}

async def finalize(ctx,pid,payload):
    data=await state(ctx,pid);s=data['session'];body=payload.case.model_dump(mode='json')
    if body.get('definition_v2'):
        from app.services.decision_case_v2_service import require_writes
        from app.results.canonical import canonical_tree
        await require_writes(ctx)
        body['definition_v2']=canonical_tree(payload.case.definition_v2)
        if body['definition_v2'].get('provenance',{}):
            if body['definition_v2']['provenance']['parent_case_id']!=s['parent_case_id']:
                raise HTTPException(409,'La preparación no pertenece al origen de la definición.')
        elif s['parent_case_id'] is not None:
            raise HTTPException(409,'La preparación derivada requiere su origen explícito.')
    # Read/validate all selected private snapshots BEFORE freezing/creating a Case.
    selected=[u for u in data['uploads'] if u['selected']];verified=[];records={}
    if body.get('definition_v2') and s['status']!='CONSUMED':
        from app.services.decision_case_v2_service import validate as validate_definition
        if {u['entity'] for u in selected if u['ready']}!=set(contracts(data)):
            raise HTTPException(409,'Guardá y validá todos los archivos de esta versión antes de crear el Case V2.')
        if s['status']!='FINALIZING':await validate_definition(ctx,payload.case.definition_v2)
    if s['status']!='CONSUMED':
        for u in selected:
            if not u['ready']:raise HTTPException(409,'Recuperá los candidatos pendientes antes de finalizar.')
            m=u['metadata'];contract=contracts(data)[u['entity']];packs.checked_hash(contract,m['contract_hash']);a,b=paths(data,u)
            await packs.private_bucket(m['bucket'])
            raw=await packs.read_object(m['bucket'],a,m['raw_sha256'],m['raw_size'])
            await packs.read_object(m['bucket'],b,m['canonical_sha256'],m['normalized_size'])
            try:normalized=normalize_input(raw,contract)
            except InputValidationError:raise HTTPException(409,'El candidato dejó de cumplir su contrato.') from None
            if normalized['canonical_sha256']!=m['canonical_sha256']:raise HTTPException(409,'La interpretación del candidato cambió; no se creó un Case.')
            verified.append((u,raw))
            if 'order_lines' in entities_for(data['model_version']):records[u['entity']]=json.loads(normalized['bytes'])['records']
    if 'order_lines' in contracts(data) and s['status']!='CONSUMED':
        from app.domain.logistics.normalizers_v2 import combine_catalog
        try:combine_catalog(records,contracts(data)['transport_demand'])
        except InputValidationError as error:raise HTTPException(422,error.report) from None
    data=await call(ctx,'begin',preparation_id=str(pid),expected_revision=payload.expected_revision,creation_body=body,creation_hash=models.snapshot_hash('journey_case_creation_v1',body))
    s=data['session'];cid=body['id']
    if s['status']!='CONSUMED':
        from app.models.decision_case_v2 import UltimateCaseCreateV2
        create_type=UltimateCaseCreateV2 if s['creation_body'].get('definition_v2') else UltimateCaseCreate
        await models.create_case(ctx,create_type.model_validate(s['creation_body']))
        selection=[]
        for u,raw in verified:
            j=await packs.upload(ctx,cid,u['entity'],raw,u['metadata']['filename'],uuid5(UUID(u['id']),'case-upload-v1'),u['metadata']['contract_hash'])
            selection.append({'slot_key':u['entity'],'upload_id':j['id']})
        if selection:
            # Initial revision and publication UUID are frozen, never recomputed from mutable state.
            await packs.publication(ctx,cid,PackPublication(publication_id=uuid5(UUID(str(pid)),'publication-v1'),expected_revision=1,selection=selection))
        if s['data_owner_user_id']:
            snap=await models.get_case_context(ctx,cid);stage=snap['responsibilities']['stages'].get('data_owner') or {}
            if stage.get('owner',{} ) and stage['owner']['id']!=s['data_owner_user_id']:raise HTTPException(409,'El Data Owner cambió durante la recuperación.')
            if not stage.get('owner'):
                await platform_call('platform_workflow_responsibilities',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,'target_case_id':cid,'target_stage_key':'data_owner','operation':'write','expected_updated_at':stage.get('updated_at'),'new_owner_user_id':s['data_owner_user_id'],'new_approver_user_id':None})
        await call(ctx,'finish',preparation_id=str(pid))
    result=await graphs.read(ctx,cid);context=await graphs.case_context(ctx,cid)
    return {'context':context,'graph':result['graph'],'preparation':public(await state(ctx,pid))}

async def case_state(ctx,cid):
    data=await call(ctx,'case_state',case_id=str(cid));graph=graphs.project(data['snapshot']);nodes={n['id']:n for n in graph['graph']['nodes']}
    d1=nodes.get('logistics_assignment',{});d2=nodes.get('logistics_scheduling',{})
    eligible=bool(not data['pending_work'] and data['snapshot']['permissions'].get('can_write') and graph['case']['status']!='archived' and d1.get('node_state')=='APPROVED' and d1.get('freshness')=='CURRENT' and d2.get('node_state') in ('APPROVED','NOT_APPLICABLE') and not any(n.get('technical_failure') or n.get('freshness')=='STALE' for n in nodes.values()))
    return data,{'has_runs':data['has_runs'],'can_prepare':bool(data['snapshot']['permissions'].get('can_write')),'can_edit_context':bool(data['snapshot']['permissions'].get('can_edit')),'token':data['token'],'can_close':eligible,'lifecycle':data['lifecycle'],'graph':graph['graph'],'reason':None if eligible else 'El cierre requiere D1 vigente y D2 aprobada o no aplicable, con permiso y sin trabajo pendiente.'}

async def close(ctx,cid,token):
    data,result=await case_state(ctx,cid)
    if data['lifecycle'] and data['lifecycle']['closed_at'] and data['snapshot']['case']['status']=='archived':return result
    if not result['can_close'] or token!=data['token']:raise HTTPException(409,result['reason'] or 'El Case cambió. Actualizá el Graph.')
    await call(ctx,'close',case_id=str(cid),token=token,eligible=True)
    return (await case_state(ctx,cid))[1]


async def compatible(ctx,pid,entity):
    data=await state(ctx,pid);contract=contract_of(data,entity)
    return await call(ctx,'compatible',preparation_id=str(pid),entity=entity,contract_hash=contract.contract_hash)

async def reuse(ctx,pid,entity,payload):
    data=await state(ctx,pid);contract=contract_of(data,entity)
    source=await call(ctx,'reuse_plan',preparation_id=str(pid),entity=entity,dataset_id=str(payload.dataset_id),contract_hash=contract.contract_hash)
    await packs.private_bucket(source['storage_bucket'])
    raw=await packs.read_object(source['storage_bucket'],source['storage_path'],source['raw_sha256'],source['raw_size'])
    await packs.read_object(source['normalized_bucket'],source['normalized_path'],source['canonical_sha256'],source['normalized_size'])
    uid=uuid5(UUID(str(pid)),entity+':'+str(payload.dataset_id))
    return await upload(ctx,pid,entity,raw,'reused-'+entity+'.csv',uid,contract.contract_hash,payload.expected_revision,source_dataset_id=payload.dataset_id)


async def validate_bundle(ctx,pid,payload):
    data=await state(ctx,pid);s=data['session'];compiled=contracts(data)
    if s['revision']!=payload.expected_revision:raise HTTPException(409,'La preparación cambió; volvé a validar sus archivos.')
    records={};hashes={}
    for upload in data['uploads']:
        if not upload['selected']:continue
        if not upload['ready']:raise HTTPException(409,'Recuperá primero los candidatos pendientes.')
        metadata=upload['metadata'];contract=compiled[upload['entity']];packs.checked_hash(contract,metadata['contract_hash']);_,path=paths(data,upload)
        raw=await packs.read_object(metadata['bucket'],path,metadata['canonical_sha256'],metadata['normalized_size'])
        normalized=json.loads(raw)
        if normalized['model_version_id']!=s['model_version_id'] or normalized['contract_hash']!=contract.contract_hash or normalized['normalizer_version']!=contract.normalizer_version:
            raise HTTPException(409,'El candidato no coincide con el snapshot publicado.')
        records[upload['entity']]=normalized['records'];hashes[upload['entity']]=metadata['canonical_sha256']
    if 'order_lines' in compiled:
        from app.domain.logistics.normalizers_v2 import combine_catalog
        try:combine_catalog(records,compiled['transport_demand'])
        except InputValidationError as error:raise HTTPException(422,error.report) from None
    latest=await state(ctx,pid)
    if latest['session']['revision']!=s['revision']:raise HTTPException(409,'La preparación cambió durante la validación.')
    return {'valid':True,'preparation_id':str(pid),'expected_revision':s['revision'],'model_version_id':s['model_version_id'],'normalized_hashes':hashes,
        'order_count':len(records.get('transport_demand',[])),'line_count':len(records.get('order_lines',[])),
        'solver_admission_supported':len(records.get('transport_demand',[]))<=500 and len(records.get('order_lines',[]))<=500}
