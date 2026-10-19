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
    failure=ROOT/'fail-next-dataset-insert'
    if path=='datasets' and request.method=='POST' and failure.exists():
        failure.unlink()
        return JSONResponse({'error':'Synthetic metadata outage'},status_code=503)
    headers = {k:v for k,v in request.headers.items() if k.lower() not in
               {'host','content-length','connection','accept-encoding'}}
    response = await request.app.state.rest.request(request.method, '/'+path,
        params=request.query_params.multi_items(), headers=headers, content=await request.body())
    uncertain=ROOT/'fail-next-dataset-response'
    if path=='datasets' and request.method=='POST' and response.is_success and uncertain.exists():
        uncertain.unlink()
        return JSONResponse({'error':'Synthetic lost committed response'},status_code=503)
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
    failure=ROOT/'fail-next-delete'
    if failure.exists():
        failure.unlink()
        return JSONResponse({'error':'Synthetic storage outage'},status_code=503)
    target.unlink(missing_ok=True)
    return {'deleted':True}


@app.get('/auth/v1/.well-known/jwks.json')
async def jwks():
    import json
    return json.loads((Path(os.environ['DATION_E2E_AUTH'])/'auth-fixture-jwks.json').read_text())

@app.post('/auth/v1/token')
async def auth_token(request: Request):
    from auth_fixture import token, USER_A, USER_B
    if not authorized(request):return JSONResponse({'error':'Unauthorized'},status_code=401)
    body=await request.json()
    if request.query_params.get('grant_type')=='password':
        user={'user-1@example.test':USER_A,'user-2@example.test':USER_B}.get(body.get('email'))
        if user is None or body.get('password')!='dispatch-e2e-private':return JSONResponse({'error':'Invalid credentials'},status_code=400)
    elif request.query_params.get('grant_type')=='refresh_token':
        user={'fixture-refresh-a':USER_A,'fixture-refresh-b':USER_B}.get(body.get('refresh_token'))
        if not user:return JSONResponse({'error':'Invalid refresh'},status_code=400)
    else:return JSONResponse({'error':'Unsupported grant'},status_code=400)
    access=token((Path(os.environ['DATION_E2E_AUTH'])/'auth-fixture-key.pem').read_bytes(),os.environ['SUPABASE_URL'],user)
    return {'access_token':access,'refresh_token':'fixture-refresh-'+('a' if user==USER_A else 'b'),'expires_in':3600,'token_type':'bearer'}

@app.post('/auth/v1/logout')
async def auth_logout():
    return Response(status_code=204)
