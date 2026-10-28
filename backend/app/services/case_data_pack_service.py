"""T4 checked Pack API with immutable private bytes and durable upload recovery."""
import json
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID,uuid5

import httpx
from fastapi import HTTPException
from app.config import SUPABASE_URL,SUPABASE_INPUT_BUCKET
from app.platform.identity import platform_call,headers
from app.services.http_service import http_client
from app.services.logistics_model_service import snapshot_hash
from app.domain.logistics.data_contracts import compile_contract,ENTITIES,MAX_BYTES,NORMALIZER_VERSION
from app.domain.logistics.normalizers import normalize_input,InputValidationError
from app.results.canonical import content_sha256


async def call(ctx,operation,**arguments):
    return await platform_call('platform_ultimate_data_pack',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,'operation':operation,'arguments':arguments})


async def state(ctx,case_id,offset=0):return await call(ctx,'state',case_id=str(case_id),offset=offset)


def public_upload(j):
    return {k:j.get(k) for k in ['id','entity','status','dataset_id','filename','created_at','updated_at','cleanup_pending','raw_sha256','canonical_sha256','contract_hash','normalizer_version','record_count']}


def public_entry(entry):
    return {k:entry.get(k) for k in ['slot_key','dataset_id','contract_id','contract_hash','raw_sha256','canonical_sha256','normalizer_version','record_count','summary']}


async def context(ctx,case_id,offset=0):
    value=await state(ctx,case_id,offset);result={k:value[k] for k in ['case','pack','version','history','history_total','enabled','can_edit','runtime_execution_available']}
    contracts={entity:compile_contract(value['model_version'],entity).model_dump(mode='json') for entity in ENTITIES}
    result.update(contracts=contracts,entries=[public_entry(x) for x in value['entries']],uploads=[public_upload(j) for j in value['uploads']],history_offset=offset,
        inputs_available={entity:any(e['slot_key']==entity for e in value['entries']) for entity in ENTITIES},decision_readiness=None)
    return result


async def contract_for(ctx,case_id,entity):
    data=await state(ctx,case_id)
    return compile_contract(data['model_version'],entity)


def checked_hash(contract,expected):
    if contract.contract_hash!=expected:raise HTTPException(409,'El contrato no corresponde a esta Model Version. Descargá su template.')


async def validate(ctx,case_id,entity,contents,expected):
    contract=await contract_for(ctx,case_id,entity);checked_hash(contract,expected)
    try:return normalize_input(contents,contract)['report']
    except InputValidationError as error:raise HTTPException(422,error.report) from None


def object_url(bucket,path):
    if not bucket or any(x in ('','.','..') for x in path.split('/')):raise HTTPException(409,'La referencia privada requiere revisión.')
    return SUPABASE_URL+'/storage/v1/object/'+quote(bucket,safe='')+'/'+quote(path,safe='/')


async def private_bucket(bucket):
    try:
        async with http_client() as client:r=await client.get(SUPABASE_URL+'/storage/v1/bucket/'+quote(bucket,safe=''),headers=headers(),timeout=15)
        r.raise_for_status();data=r.json()
        allowed=data.get('allowed_mime_types')
        if data.get('public') is not False or allowed is not None and not all(x in allowed for x in ['text/csv','application/json']):
            raise HTTPException(503,'El bucket privado debe admitir CSV y JSON normalizado. No se modificó su configuración.')
    except httpx.HTTPError:raise HTTPException(503,'No se pudo verificar Storage privado. El candidato se conserva.') from None


async def read_object(bucket,path,hash_,size,*,missing=False):
    try:
        async with http_client() as client:
            async with client.stream('GET',object_url(bucket,path),headers=headers(),timeout=30) as response:
                if missing and response.status_code==404:return None
                response.raise_for_status();chunks=[];length=0
                async for part in response.aiter_bytes():
                    length+=len(part)
                    if length>MAX_BYTES:raise HTTPException(409,'El objeto privado supera el límite permitido.')
                    chunks.append(part)
        data=b''.join(chunks)
    except httpx.HTTPError:raise HTTPException(503,'No se pudieron verificar los bytes privados. El Pack vigente no cambió.') from None
    if len(data)!=size or content_sha256(data)!=hash_:raise HTTPException(409,'Los bytes privados no coinciden con su snapshot. El Pack vigente no cambió.')
    return data


async def put_object(bucket,path,contents,mime,hash_):
    try:
        async with http_client() as client:r=await client.post(object_url(bucket,path),headers={**headers(),'Content-Type':mime,'x-upsert':'false'},content=contents,timeout=30)
        if r.status_code in (400,409):
            # Never upsert: reconcile a prior completed POST by exact hash/size.
            await read_object(bucket,path,hash_,len(contents));return
        r.raise_for_status()
    except httpx.HTTPError:raise HTTPException(503,'La carga quedó interrumpida. Recuperá el candidato antes de publicar; no se movió el Pack.') from None


async def cleanup(ctx,case_id,upload_id):
    permit=await call(ctx,'cleanup',case_id=str(case_id),upload_id=str(upload_id))
    if not permit.get('may_delete_reserved_objects'):return permit
    # Each reserved UUID belongs to exactly one journal, and is never reused by
    # another upload. SQL proves it has no dataset/Pack consumer before deletion.
    try:
        async with http_client() as client:
            for path in [permit['storage_path'],permit['normalized_path']]:
                r=await client.delete(object_url(permit['storage_bucket'],path),headers=headers(),timeout=30)
                if r.status_code not in (200,204,404):r.raise_for_status()
    except httpx.HTTPError:return permit
    return await call(ctx,'cleanup_finish',case_id=str(case_id),upload_id=str(upload_id))


async def recover(ctx,case_id,upload_id):
    j=await call(ctx,'upload_get',case_id=str(case_id),upload_id=str(upload_id))
    if j['status'] in ('DISCARDED','DISCARDING'):raise HTTPException(409,'El candidato fue descartado; creá una nueva intención de carga.')
    if j['status']=='READY':
        if j['cleanup_pending']:await cleanup(ctx,case_id,upload_id)
        return public_upload(j)
    contract=await contract_for(ctx,case_id,j['entity']);checked_hash(contract,j['contract_hash']);await private_bucket(j['storage_bucket'])
    raw=await read_object(j['storage_bucket'],j['storage_path'],j['raw_sha256'],j['raw_size'],missing=True)
    if raw is None:raise HTTPException(409,'Falta el CSV del candidato. Volvé a subir el mismo archivo con esta intención.')
    try:normalized=normalize_input(raw,contract)
    except InputValidationError:raise HTTPException(409,'El candidato no coincide con su contrato inmutable.') from None
    if normalized['canonical_sha256']!=j['canonical_sha256'] or normalized['normalized_size']!=j['normalized_size']:raise HTTPException(409,'El normalizer no coincide con el snapshot preparado.')
    await put_object(j['storage_bucket'],j['normalized_path'],normalized['bytes'],'application/json',j['canonical_sha256'])
    await read_object(j['storage_bucket'],j['normalized_path'],j['canonical_sha256'],j['normalized_size'])
    result=await call(ctx,'store',case_id=str(case_id),upload_id=str(upload_id),verified_raw_sha256=j['raw_sha256'],verified_canonical_sha256=j['canonical_sha256'])
    if result['cleanup_pending']:
        try:result=await cleanup(ctx,case_id,upload_id)
        except HTTPException:pass  # Durable successful metadata must not become a false failed upload.
    return public_upload(result)


async def upload(ctx,case_id,entity,contents,filename,upload_id,expected):
    contract=await contract_for(ctx,case_id,entity);checked_hash(contract,expected)
    try:normalized=normalize_input(contents,contract)
    except InputValidationError as error:raise HTTPException(422,error.report) from None
    name=PurePosixPath((filename or entity+'.csv').replace('\\','/')).name[:120]
    profile={k:v for k,v in normalized['report'].items() if k not in ('preview','summary')}
    body=dict(case_id=str(case_id),upload_id=str(upload_id),entity=entity,contract_id=contract.contract_id,contract_hash=contract.contract_hash,normalizer_version=NORMALIZER_VERSION,
        raw_sha256=normalized['raw_sha256'],canonical_sha256=normalized['canonical_sha256'],raw_size=len(contents),normalized_size=normalized['normalized_size'],record_count=normalized['record_count'],column_count=len(contract.fields),filename=name,storage_bucket=SUPABASE_INPUT_BUCKET,profile=profile,summary=normalized['report']['summary'])
    intent=snapshot_hash('ultimate_upload_intent_v1',{'actor':ctx.user_id,**body})
    j=await call(ctx,'prepare',**body,intent_hash=intent)
    if j['status']=='READY':return public_upload(j)
    if j['status']!='PREPARED':raise HTTPException(409,'La intención de carga fue descartada.')
    await private_bucket(j['storage_bucket'])
    await put_object(j['storage_bucket'],j['storage_path'],contents,'text/csv',j['raw_sha256'])
    return await recover(ctx,case_id,upload_id)


async def publication(ctx,case_id,payload):
    body=payload.model_dump(mode='json',exclude_none=True);body['selection'].sort(key=lambda item:item['slot_key'])
    intent=snapshot_hash('ultimate_pack_publication_intent_v1',{'actor':ctx.user_id,'case_id':str(case_id),**body})
    replay=await call(ctx,'replay',case_id=str(case_id),publication_id=body['publication_id'],intent_hash=intent)
    if replay['replayed']:return replay
    current=await state(ctx,case_id);contracts={e:compile_contract(current['model_version'],e).contract_hash for e in ENTITIES}
    plan=await call(ctx,'plan',case_id=str(case_id),selection=body['selection'],contracts=contracts)
    entries=plan['entries']
    for entry in entries:
        await private_bucket(entry['storage_bucket'])
        await read_object(entry['storage_bucket'],entry['storage_path'],entry['raw_sha256'],entry['raw_size'])
        await read_object(entry['normalized_bucket'],entry['normalized_path'],entry['canonical_sha256'],entry['normalized_size'])
    version_id=uuid5(UUID(body['publication_id']),'pack-version-v1')
    semantic_entries=[{k:e[k] for k in ['slot_key','dataset_id','contract_id','contract_hash','raw_sha256','canonical_sha256','normalizer_version','normalized_bucket','normalized_path','record_count']} for e in entries]
    manifest={'version':plan['next_version'],'workspace_id':ctx.workspace_id,'case_id':str(case_id),'pack_id':plan['pack']['id'],'pack_version_id':str(version_id),'entries':semantic_entries}
    return await call(ctx,'publish',**body,case_id=str(case_id),intent_hash=intent,contracts=contracts,entries=entries,
        expected_current_version_id=plan['pack']['current_version_id'],version_id=str(version_id),
        manifest_hash=snapshot_hash('case_data_pack_manifest_v1',manifest),contract_set_hash=snapshot_hash('case_data_pack_contract_set_v1',[(e['slot_key'],e['contract_hash']) for e in entries]))


async def compatible(ctx,case_id,entity,offset=0):
    contract=await contract_for(ctx,case_id,entity)
    return await call(ctx,'compatible',case_id=str(case_id),entity=entity,contract_hash=contract.contract_hash,offset=offset)


async def version(ctx,case_id,version_id):
    data=await call(ctx,'version_get',case_id=str(case_id),version_id=str(version_id))
    return {'version':data['version'],'entries':[public_entry(e) for e in data['entries']]}


async def normalized_preview(ctx,dataset_id,limit=25,offset=0):
    data=await call(ctx,'dataset_get',dataset_id=str(dataset_id));entry=data['entry']
    if not entry:raise HTTPException(409,'Falta la provenance del snapshot normalizado.')
    await private_bucket(entry['normalized_bucket'])
    raw=await read_object(entry['normalized_bucket'],entry['normalized_path'],entry['canonical_sha256'],entry['normalized_size'])
    normalized=json.loads(raw)
    return {'semantic_entity':entry['slot_key'],'records':normalized['records'][offset:offset+limit],'summary':entry['summary'],
        'total':entry['record_count'],'limit':limit,'offset':offset,'canonical_sha256':entry['canonical_sha256'],'normalizer_version':entry['normalizer_version']}


async def discard(ctx,case_id,upload_id):
    result=await call(ctx,'discard',case_id=str(case_id),upload_id=str(upload_id))
    if result.get('may_delete_reserved_objects'):
        try:result=await cleanup(ctx,case_id,upload_id)
        except HTTPException:pass
    return public_upload(result)
