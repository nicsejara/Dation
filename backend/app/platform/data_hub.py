"""Workspace library projection; only explicit reuse crosses into a DDA."""
import csv
import io
import json
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from app.platform.identity import platform_call,headers
from app.platform.entitlements import require_dda
from app.services import dispatch_service as dispatch
from app.services.run_service import get_dataset,download_dataset
from app.services.http_service import http_client as storage_client
from app.config import SUPABASE_URL


async def snapshot(ctx,**options):
    return await platform_call('platform_data_hub',{'actor_user_id':ctx.user_id,
        'target_workspace_id':ctx.workspace_id,**options})


async def library(ctx,**options):
    return await platform_call('platform_dataset_library',{'actor_user_id':ctx.user_id,
        'target_workspace_id':ctx.workspace_id,**options})


async def dataset_detail(ctx,dataset_id,limit=25,offset=0):
    data=await library(ctx,target_dataset_id=str(dataset_id),page_limit=limit,page_offset=offset)
    raw=data.pop('validation_report') or {}
    if not isinstance(raw,dict):raw={}
    data['validation_report']={key:raw.get(key) for key in ('valid','schema','counts')}
    for key in ('errors','warnings'):
        values=raw.get(key) or []
        if not isinstance(values,list):values=[]
        data['validation_report'][key]=values[:50]
        data['validation_report'][key+'_total']=len(values)
    return data


async def active_dataset(ctx,dataset_id):
    row=await get_dataset(str(dataset_id))
    # TenantClient already scopes this lookup and excludes pending deletions.
    # Check the projection again before passing a service-backed object to Storage.
    if not row or str(row.get('workspace_id'))!=str(ctx.workspace_id):
        raise HTTPException(404,'No se encontró el dataset.')
    return row


async def preview(ctx,dataset_id,limit=25,offset=0):
    row=await active_dataset(ctx,dataset_id)
    if row.get('dataset_type') in {'transport_demand','transport_resources'}:
        from app.services.case_data_pack_service import normalized_preview
        data=await normalized_preview(ctx,dataset_id,limit,offset)
        # Data Hub keeps its existing table contract; the source is the verified
        # normalized DTO rather than a second delimiter/schema inference.
        columns=list(data['records'][0]) if data['records'] else []
        return {'columns':columns,'rows':[[json.dumps(r[k],ensure_ascii=False) if isinstance(r[k],(dict,list)) else str(r[k]) if r[k] is not None else '—' for k in columns] for r in data['records']],
            'limit':limit,'offset':offset,'has_more':offset+limit<data['total'],'cell_limit':500,'canonical_sha256':data['canonical_sha256'],'normalizer_version':data['normalizer_version']}
    contents=await download_dataset(row)
    if len(contents)>10*1024*1024:raise HTTPException(413,'La vista previa admite archivos de hasta 10 MB.')
    try:
        text=contents.decode('utf-8-sig')
        first=text.partition('\n')[0]
        try:delimiter=csv.Sniffer().sniff(text[:8192],delimiters=',;\t|').delimiter
        except csv.Error:delimiter=max((',',';','\t','|'),key=first.count)
        reader=csv.reader(io.StringIO(text),delimiter=delimiter)
        columns=next(reader)
        if len(columns)>100:raise ValueError('Too many columns')
        rows=[]
        for index,values in enumerate(reader):
            if index<offset:continue
            if len(rows)>limit:break
            rows.append([value[:500] for value in values[:100]])
    except (UnicodeError,csv.Error,StopIteration,IndexError,ValueError):
        raise HTTPException(422,'No se pudo generar la vista previa de este CSV.') from None
    return {'columns':[value[:120] for value in columns],'rows':rows[:limit],
        'limit':limit,'offset':offset,'has_more':len(rows)>limit,'cell_limit':500}


async def reuse(ctx,dataset_id=None,orders_id=None,fleet_id=None):
    require_dda(ctx,'logistics')
    rows=[await active_dataset(ctx,dataset_id)] if dataset_id else [await active_dataset(ctx,orders_id),await active_dataset(ctx,fleet_id)]
    if any(row.get('archived_at') or row.get('dataset_type') not in {'orders','fleet'} for row in rows):
        raise HTTPException(409,'Elegí datos activos de Órdenes o Flota para reutilizar.')
    # Revalidate older profiles in memory, without rewriting historical metadata.
    rows=[await dispatch._ensure_profile(row if isinstance(row.get('profile_json'),dict) else {**row,'profile_json':{}}) for row in rows]
    if any(not (row.get('profile_json') or {}).get('valid') for row in rows):
        raise HTTPException(409,'Revisá la validación del dataset antes de reutilizarlo.')
    if not dataset_id and [row['dataset_type'] for row in rows]!=['orders','fleet']:
        raise HTTPException(409,'El Data Pack debe reunir Órdenes y Flota.')
    return {'datasets':rows}


async def delete_authorized_object(ctx,dataset_id,permit):
    # Authorization and the immutable object identity come from the locked DB
    # operation, never a browser path. Keep its durable intent until both steps
    # finish; failures are recoverable by repeating this same DELETE.
    key=permit['storage_path'];parts=key.split('/')
    if any(part in {'','.','..'} for part in parts):raise HTTPException(409,'La ruta del archivo requiere revisión.')
    if not ((len(parts)==3 and parts[:2]==[ctx.workspace_id,str(dataset_id)]) or (len(parts)==2 and parts[0]==str(dataset_id))):
        raise HTTPException(409,'La identidad del archivo requiere revisión.')
    url=SUPABASE_URL+'/storage/v1/object/'+quote(permit['storage_bucket'],safe='')+'/'+quote(key,safe='/')
    try:
        async with storage_client() as client:
            response=await client.delete(url,headers=headers(),timeout=30)
        if response.status_code not in (200,204,404):response.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(503,'La eliminación quedó pendiente. Reintentá para completarla; el archivo no se puede reutilizar mientras tanto.') from None


async def discard_upload(ctx,operation_id):
    body={'actor_user_id':ctx.user_id,'target_workspace_id':ctx.workspace_id,'operation_id':str(operation_id)}
    permit=await platform_call('platform_dataset_upload',{**body,'operation':'discard'})
    if permit.get('cleared'):return permit
    await delete_authorized_object(ctx,permit['dataset_id'],permit)
    return await platform_call('platform_dataset_upload',{**body,'operation':'finish'})


async def archive_input(ctx,dataset_id,archived):
    row=await active_dataset(ctx,dataset_id)
    if row.get('dataset_type') in {'transport_demand','transport_resources'}:
        from app.services.case_data_pack_service import call
        return await call(ctx,'dataset_archive',dataset_id=str(dataset_id),archived=archived)
    await dispatch.archive_dataset(str(dataset_id),archived)
    return {'archived':archived}


async def delete_dataset(ctx,dataset_id):
    body={'actor_user_id':ctx.user_id,'target_workspace_id':ctx.workspace_id,'target_dataset_id':str(dataset_id)}
    try:permit=await platform_call('platform_dataset_delete',body)
    except HTTPException as error:
        if error.status_code==409 and not (error.headers or {}).get('X-Dation-Retryable'):raise HTTPException(409,'Primero archivá el dataset. Si tiene referencias o es la flota vigente, debe conservarse.') from None
        raise
    if permit.get('deleted'):return permit
    await delete_authorized_object(ctx,dataset_id,permit)
    try:
        return await platform_call('platform_dataset_delete',{**body,'operation':'finish','operation_id':permit['operation_id']})
    except HTTPException as error:
        if error.status_code==503:raise HTTPException(503,'El archivo fue retirado de Storage. Reintentá para completar su eliminación de la biblioteca.') from None
        raise
