"""Versioned input persistence; solver executes in a worker thread while request stays open."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from time import perf_counter
from uuid import uuid4
from urllib.parse import quote
import httpx
from app.config import SUPABASE_URL, SUPABASE_INPUT_BUCKET
from app.services.run_service import _headers, get_dataset, download_dataset, _insert_run
from app.validators.orders_schema import validate_orders_csv
from app.validators.fleet_schema import validate_fleet_csv
from app.engines.dispatch import ENGINE_NAME, ENGINE_VERSION, run_dispatch_engine
from app.engines.dispatch.normalization import preflight

VALIDATORS={'orders':validate_orders_csv,'fleet':validate_fleet_csv}


async def db(method, path, *, params=None, body=None):
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.request(method,f'{SUPABASE_URL}/rest/v1/{path}',headers={**_headers(),'Prefer':'return=representation'},params=params,json=body)
        r.raise_for_status()
        return r.json() if r.content else None


async def available():
    try:
        await db('GET','datasets',params={'select':'id,dataset_type,profile_json,is_default','limit':'0'})
        await db('GET','decision_runs',params={'select':'id,orders_dataset_id,fleet_dataset_id,progress_json','limit':'0'})
        return True
    except httpx.HTTPError:return False


async def list_typed(kind, limit=100):
    return await db('GET','datasets',params={'select':'*','dataset_type':f'eq.{kind}','order':'created_at.desc','limit':str(limit)})


async def store_input(filename, contents, kind, label=None, parent=None):
    if kind not in VALIDATORS:raise ValueError('Tipo de dataset inválido.')
    validation=VALIDATORS[kind](contents)
    filehash=hashlib.sha256(contents).hexdigest()
    if parent:
        previous=await get_dataset(parent)
        if kind!='fleet' or not previous or previous.get('dataset_type')!='fleet':
            raise ValueError('La versión anterior debe ser una flota existente.')
    existing=await db('GET','datasets',params={'select':'*','dataset_type':f'eq.{kind}','sha256':f'eq.{filehash}','limit':'1'})
    public={k:v for k,v in validation.items() if k!='records'}
    if existing:return {'duplicate':True,'existing_dataset':existing[0],'validation':public}
    id=str(uuid4());path=f'{id}/{kind}.csv';url=f'{SUPABASE_URL}/storage/v1/object/{SUPABASE_INPUT_BUCKET}/{quote(path,safe="/")}'
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(url,headers={**_headers(),'Content-Type':'text/csv','x-upsert':'false'},content=contents);r.raise_for_status()
        try:
            result=await db('POST','datasets',body={'id':id,'original_filename':filename,'storage_bucket':SUPABASE_INPUT_BUCKET,
                'storage_path':path,'mime_type':'text/csv','size_bytes':len(contents),'sha256':filehash,'status':'uploaded',
                'row_count':validation['rows'],'column_count':validation['columns'],'dataset_type':kind,
                'schema_version':validation['schema'],'label':label or filename,'parent_dataset_id':parent,'profile_json':public})
        except Exception as exc:
            await c.delete(url,headers=_headers())
            if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code==409:
                existing=await db('GET','datasets',params={'select':'*','dataset_type':f'eq.{kind}','sha256':f'eq.{filehash}','limit':'1'})
                if existing:return {'duplicate':True,'existing_dataset':existing[0],'validation':public}
            raise
    return {'duplicate':False,'dataset':result[0],'validation':public}


async def load_inputs(orders_id,fleet_id):
    o,f=await asyncio.gather(get_dataset(orders_id),get_dataset(fleet_id))
    if not o or not f:raise LookupError('No se encontraron ambos datasets.')
    if o.get('dataset_type')!='orders' or f.get('dataset_type')!='fleet':raise ValueError('Seleccioná un dataset de órdenes y uno de flota.')
    ob,fb=await asyncio.gather(download_dataset(o),download_dataset(f))
    return o,f,ob,fb


async def check_inputs(orders_id,fleet_id,allow_third_party=True):
    o,f,ob,fb=await load_inputs(orders_id,fleet_id)
    orders=validate_orders_csv(ob);fleet=validate_fleet_csv(fb)
    vehicles=[v for v in fleet['records'] if allow_third_party or v['ownership']=='own']
    if not vehicles:raise ValueError('No hay flota habilitada.')
    return {**preflight(orders['records'],vehicles,fleet['records']),'orders_profile':orders['profile'],'fleet_profile':fleet['profile']}


async def execute(orders_id,fleet_id,configuration,options,run_id=None):
    o,f,ob,fb=await load_inputs(orders_id,fleet_id)
    id=run_id or str(uuid4());start=perf_counter();now=datetime.now(timezone.utc).isoformat()
    await _insert_run({'id':id,'dataset_id':orders_id,'orders_dataset_id':orders_id,'fleet_dataset_id':fleet_id,
        'schema_version':'dispatch_v1','engine_name':ENGINE_NAME,'engine_version':ENGINE_VERSION,
        'configuration_json':{**configuration,'options':options},'status':'running','started_at':now,
        'input_fingerprint':hashlib.sha256(ob+b'\0'+fb+json.dumps(configuration,sort_keys=True).encode()+json.dumps(options,sort_keys=True).encode()).hexdigest(),
        'progress_json':{'stage':'validating'}})
    async def update(values):
        return await db('PATCH','decision_runs',params={'id':f'eq.{id}','status':'eq.running'},body=values)
    loop=asyncio.get_running_loop()
    def progress(stage):
        # Await actual persisted stage changes, not fabricated percentages.
        future=asyncio.run_coroutine_threadsafe(update({'progress_json':{'stage':stage}}),loop)
        future.result(timeout=35)
    metadata={k:{'dataset_id':v['id'],'filename':v['original_filename'],'label':v.get('label'),'created_at':v['created_at']} for k,v in [('orders',o),('fleet',f)]}
    try:
        result=await asyncio.to_thread(run_dispatch_engine,ob,fb,configuration,options,metadata,progress)
        rows=await update({'status':'completed','finished_at':datetime.now(timezone.utc).isoformat(),
            'duration_ms':int((perf_counter()-start)*1000),'result_json':result,'result_fingerprint':result['result_fingerprint'],
            'summary_json':result['scenarios']['selected']['metrics'],'progress_json':{'stage':'completed'},'error_message':None})
        if not rows:raise ValueError('La corrida venció antes de guardar el resultado; ejecutala nuevamente.')
        return rows[0]
    except Exception as exc:
        await update({'status':'error','finished_at':datetime.now(timezone.utc).isoformat(),
                      'duration_ms':int((perf_counter()-start)*1000),'error_message':str(exc)[:1500],'progress_json':{'stage':'error'}})
        raise
