"""T4-only private JSON/CSV Storage contract fixture and deterministic faults."""
import json
from fastapi import Request
from fastapi.responses import JSONResponse
from storage_gateway import app,ROOT,authorized

@app.middleware('http')
async def ultimate_inputs(request:Request,call_next):
    path=request.url.path
    if path=='/storage/v1/bucket/dda-inputs':
        if not authorized(request):return JSONResponse({'error':'Unauthorized'},status_code=401)
        return JSONResponse({'id':'dda-inputs','name':'dda-inputs','public':False,'allowed_mime_types':['text/csv','application/json'],'file_size_limit':10485760})
    operation=None
    if path=='/rest/v1/rpc/platform_ultimate_data_pack' and request.method=='POST':
        operation=(await request.json()).get('operation')
        marker=ROOT/('fail-t4-'+str(operation))
        if marker.exists():marker.unlink();return JSONResponse({'error':'Synthetic T4 RPC outage'},status_code=503)
    if path.startswith('/storage/v1/object/') and request.method=='POST':
        normalized='/normalized/' in path
        if request.headers.get('content-type')!=('application/json' if normalized else 'text/csv'):return JSONResponse({'error':'MIME not allowed'},status_code=415)
        marker=ROOT/('fail-t4-normalized' if normalized else 'fail-t4-raw')
        if marker.exists():marker.unlink();return JSONResponse({'error':'Synthetic T4 Storage outage'},status_code=503)
    response=await call_next(request)
    if operation:
        marker=ROOT/('lose-t4-'+operation+'-response')
        if marker.exists() and response.status_code<300:marker.unlink();return JSONResponse({'error':'Synthetic lost committed T4 response'},status_code=503)
    if '/storage/v1/object/' in path and '/normalized/' in path and response.status_code==200:response.headers['Content-Type']='application/json'
    return response
