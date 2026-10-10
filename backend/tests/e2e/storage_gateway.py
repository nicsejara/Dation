"""Local Storage contract fixture; SQL/REST are handled by real PostgREST.

Only loopback services use this fixture. No production hosts or credentials.
"""
from contextlib import asynccontextmanager
import asyncio
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

ROOT = Path(os.environ['DATION_E2E_STORAGE']).resolve()
REST = os.environ['DATION_E2E_REST']
TOKEN = os.environ['SUPABASE_SECRET_KEY']


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(base_url=REST, trust_env=False, timeout=30) as client:
        app.state.rest = client
        yield


app = FastAPI(lifespan=lifespan)


@app.api_route('/rest/v1/{path:path}', methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'])
async def rest(path: str, request: Request):
    headers = {k:v for k,v in request.headers.items() if k.lower() not in
               {'host','content-length','connection','accept-encoding'}}
    response = await request.app.state.rest.request(request.method, '/'+path,
        params=request.query_params.multi_items(), headers=headers, content=await request.body())
    return Response(response.content, status_code=response.status_code,
        headers={k:v for k,v in response.headers.items() if k.lower() not in
                 {'content-length','connection','transfer-encoding','content-encoding'}})


def authorized(request):
    return request.headers.get('authorization') == 'Bearer '+TOKEN and request.headers.get('apikey') == TOKEN


@app.get('/storage/v1/bucket/{bucket}')
async def bucket_info(bucket: str, request: Request):
    if not authorized(request):return JSONResponse({'error':'Unauthorized'},status_code=401)
    if bucket != 'dda-inputs':return JSONResponse({'error':'Not found'},status_code=404)
    return {'id':bucket,'name':bucket,'public':False}


@app.api_route('/storage/v1/object/{path:path}', methods=['GET','POST','DELETE'])
async def storage(path: str, request: Request):
    if not authorized(request):return JSONResponse({'error':'Unauthorized'},status_code=401)
    relative = path.removeprefix('authenticated/')
    target = (ROOT/relative).resolve()
    if not target.is_relative_to(ROOT) or not relative.startswith('dda-inputs/'):
        return JSONResponse({'error':'Invalid path'},status_code=400)
    if request.method == 'GET':
        # The owner can block a real worker download to exercise process death deterministically.
        while (ROOT/'block-downloads').exists():await asyncio.sleep(.05)
        if not target.is_file():return JSONResponse({'error':'Not found'},status_code=404)
        return Response(target.read_bytes(),media_type='text/csv')
    if request.method == 'POST':
        if target.exists():return JSONResponse({'error':'Already exists'},status_code=409)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(await request.body())
        return {'Key':relative}
    target.unlink(missing_ok=True)
    return {'deleted':True}
