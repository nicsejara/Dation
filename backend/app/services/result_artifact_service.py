"""Scoped immutable bytes. All locators are reserved by checked SQL, not clients."""
import json
from uuid import UUID
from urllib.parse import quote
import httpx
from fastapi import HTTPException
from app.config import SUPABASE_URL
from app.platform.identity import headers
from app.services.http_service import http_client
from app.results.contracts import DecisionResultPackageV1,ResultArtifactReference,EVIDENCE_CHUNK_MAX_BYTES
from app.results.canonical import content_sha256,canonical_bytes,artifact_bytes


def locator(row):
    expected=f"{row['workspace_id']}/runs/{row['run_id']}/{row['kind'].lower()}/{row['part_key']}/{row['content_sha256']}.json"
    if row['storage_bucket']!='dda-inputs' or row['storage_path']!=expected or '..' in expected.split('/') or row['size_bytes']>EVIDENCE_CHUNK_MAX_BYTES:raise HTTPException(409,'ARTIFACT_BINDING_ERROR')
    return SUPABASE_URL+'/storage/v1/object/dda-inputs/'+quote(expected,safe='/')


def indexes(bundle):
    """Index already assembled bytes; never derive or change engine results."""
    offsets={};result={}
    for part in bundle.artifacts:
        body=json.loads(part.content);dataset=body['dataset_id'];rows=body['rows'];offset=offsets.get(dataset,0)
        result[str(part.reference.artifact_id)]={'version':1,'row_offset':offset,'row_count':len(rows),
            'entities':[[r['entity_type'],r['entity_id']] for r in rows if isinstance(r,dict) and 'entity_type' in r and 'entity_id' in r]}
        offsets[dataset]=offset+len(rows)
    return result


async def read(row,*,missing=False):
    url=locator(row)
    try:
        async with http_client() as client:
            async with client.stream('GET',url,headers=headers(),timeout=30) as response:
                if response.status_code==404:
                    if missing:return None
                    raise HTTPException(409,'ARTIFACT_MISSING')
                response.raise_for_status();chunks=[];size=0
                async for chunk in response.aiter_bytes():
                    size+=len(chunk)
                    if size>row['size_bytes']:raise HTTPException(409,'ARTIFACT_INTEGRITY_ERROR')
                    chunks.append(chunk)
        blob=b''.join(chunks)
    except httpx.HTTPError:raise HTTPException(503,'ARTIFACT_UNAVAILABLE') from None
    if len(blob)!=row['size_bytes'] or content_sha256(blob)!=row['content_sha256']:raise HTTPException(409,'ARTIFACT_INTEGRITY_ERROR')
    try:
        body=json.loads(blob)
        if artifact_bytes(body)!=blob:raise ValueError('Noncanonical bytes')
    except (ValueError,TypeError):raise HTTPException(409,'ARTIFACT_INTEGRITY_ERROR') from None
    return blob


async def upload(row,blob):
    if len(blob)!=row['size_bytes'] or content_sha256(blob)!=row['content_sha256']:raise HTTPException(409,'ARTIFACT_INTEGRITY_ERROR')
    url=locator(row)
    try:
        async with http_client() as client:
            bucket=await client.get(SUPABASE_URL+'/storage/v1/bucket/dda-inputs',headers=headers(),timeout=15)
            bucket.raise_for_status()
            if bucket.json().get('public') is not False:raise HTTPException(503,'Private artifact bucket required')
            response=await client.post(url,headers={**headers(),'Content-Type':'application/json','x-upsert':'false'},content=blob,timeout=30)
        if response.status_code not in (400,409):response.raise_for_status()
    except httpx.HTTPError:raise HTTPException(503,'ARTIFACT_UPLOAD_UNAVAILABLE') from None
    await read(row)


def bound_rows(package,rows):
    package=DecisionResultPackageV1.model_validate(package)
    indexed={row['id']:row for row in rows};manifest=package.artifact_manifest.artifacts
    if len(indexed)!=len(rows) or set(indexed)!={str(r.artifact_id) for r in manifest}:raise HTTPException(409,'ARTIFACT_MANIFEST_MISMATCH')
    for ref in manifest:
        row=indexed[str(ref.artifact_id)]
        if row.get('publication_state')=='READY' and row.get('result_fingerprint')!=package.fingerprints.result_fingerprint:raise HTTPException(409,'ARTIFACT_BINDING_ERROR')
        data={'artifact_id':row['id'],**{k:row[k] for k in ResultArtifactReference.model_fields if k!='artifact_id'}}
        if ResultArtifactReference.model_validate(data)!=ref or row['workspace_id']!=str(package.context.workspace_id) or row['run_id']!=str(package.decision.run_id):raise HTTPException(409,'ARTIFACT_BINDING_ERROR')
        locator(row)
    return package,indexed


async def verify_all(package,rows,*,missing=False):
    package,indexed=bound_rows(package,rows)
    complete=True
    for row in indexed.values():
        blob=await read(row,missing=missing)
        if blob is None:complete=False
    return complete


async def dataset(delivery,rows,*,offset=0,limit=None,entity=None):
    if delivery.mode=='INLINE':return list(delivery.rows)[offset:None if limit is None else offset+limit]
    indexed={row['id']:row for row in rows};result=[];cursor=0
    metadata=[((indexed.get(str(r.artifact_id)) or {}).get('producer_metadata') or {}).get('retrieval_index') or {} for r in delivery.artifacts]
    has_index=all(m.get('version')==1 for m in metadata)
    if has_index:
        for m in metadata:
            if m.get('row_offset')!=cursor or not isinstance(m.get('row_count'),int) or not 0<=m['row_count']<=100:raise HTTPException(409,'ARTIFACT_INDEX_MISMATCH')
            cursor+=m['row_count']
        if cursor!=delivery.row_count:raise HTTPException(409,'ARTIFACT_INDEX_MISMATCH')
    for index,ref in enumerate(delivery.artifacts):
        row=indexed.get(str(ref.artifact_id))
        if row is None:raise HTTPException(409,'ARTIFACT_MISSING')
        m=metadata[index]
        if has_index:
            if entity is not None and '/'.join(entity) not in row.get('lookup_keys',[]):continue
            if entity is None and limit is not None and (m['row_offset']+m['row_count']<=offset or m['row_offset']>=offset+limit):continue
        body=json.loads(await read(row))
        if body['dataset_id']!=delivery.dataset_id or body['row_schema']!=delivery.row_schema or body['scope']!='FULL' or body['chunk_index']!=index or body['chunk_count']!=len(delivery.artifacts) or body['total_rows']!=delivery.row_count:raise HTTPException(409,'ARTIFACT_DATASET_MISMATCH')
        if body['core_binding']!={'run_id':row['run_id'],'core_result_fingerprint':row['core_fingerprint']}:raise HTTPException(409,'ARTIFACT_BINDING_ERROR')
        values=body['rows']
        if has_index and len(values)!=m['row_count']:raise HTTPException(409,'ARTIFACT_INDEX_MISMATCH')
        if has_index and entity is None and limit is not None:values=values[max(0,offset-m['row_offset']):max(0,offset+limit-m['row_offset'])]
        result.extend(values)
    if entity is not None:return [r for r in result if (r.get('entity_type'),r.get('entity_id'))==entity]
    if not has_index:
        if len(result)!=delivery.row_count:raise HTTPException(409,'ARTIFACT_DATASET_INCOMPLETE')
        return result[offset:None if limit is None else offset+limit]
    if limit is None and len(result)!=delivery.row_count:raise HTTPException(409,'ARTIFACT_DATASET_INCOMPLETE')
    return result
