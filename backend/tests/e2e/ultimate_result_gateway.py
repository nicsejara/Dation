"""Owned T8 private JSON artifact fixture and deterministic outage markers."""
import asyncio,json
from fastapi import Request
from fastapi.responses import JSONResponse,Response
from ultimate_storage_gateway import app,ROOT,authorized
from storage_gateway import storage

@app.middleware('http')
async def publication_faults(request:Request,call_next):
    path=request.url.path;operation=None
    if path=='/rest/v1/rpc/platform_ultimate_execution' and request.method=='POST':
        operation=(await request.json()).get('operation')
        while (ROOT/('block-t8-'+str(operation))).exists():await asyncio.sleep(.05)
    if '/storage/v1/object/' in path and '/runs/' in path:
        if not authorized(request):return JSONResponse({'error':'Unauthorized'},status_code=401)
        if request.method=='POST':
            if request.headers.get('content-type')!='application/json' or request.headers.get('x-upsert')!='false':return JSONResponse({'error':'Unsafe artifact upload'},status_code=415)
            fail=ROOT/'fail-t8-upload'
            if fail.exists():fail.unlink();return JSONResponse({'error':'Synthetic artifact outage'},status_code=503)
            while (ROOT/'block-t8-upload').exists():await asyncio.sleep(.05)
        response=await storage(path.split('/storage/v1/object/',1)[1],request)
        if isinstance(response,dict):response=JSONResponse(response)
        if request.method=='POST' and response is not None:
            marker=ROOT/'fail-t8-after-first-upload'
            if marker.exists():marker.unlink();(ROOT/'fail-t8-upload').touch()
        return response
    response=await call_next(request)
    if operation and response.status_code>=400:
        content=b''.join([chunk async for chunk in response.body_iterator])
        with (ROOT/'t8-rpc-errors.jsonl').open('a') as log:log.write(json.dumps({'operation':operation,'status':response.status_code,'body':content.decode()})+'\n')
        response=Response(content,status_code=response.status_code,headers=dict(response.headers))
    if operation:
        marker=ROOT/('lose-t8-'+operation+'-response')
        if marker.exists() and response.status_code<300:marker.unlink();return JSONResponse({'error':'Synthetic lost committed response'},status_code=503)
    return response
