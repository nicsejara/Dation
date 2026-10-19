from hashlib import sha256
from typing import Literal
from uuid import UUID
import httpx
from fastapi import APIRouter,Depends,HTTPException,Query
from fastapi.responses import Response
from pydantic import AwareDatetime,BaseModel,ConfigDict
from app.auth import require_upload_access
from app.platform import activity
from app.platform.entitlements import require_dda
from app.platform.exports import generate
from app.platform.identity import platform_call
from app.services.run_service import get_run

router=APIRouter(prefix='/activity')
@router.get('')
async def feed(case_id:UUID|None=None,limit:int=Query(5,ge=1,le=50),before_time:AwareDatetime|None=None,before_id:UUID|None=None,ctx=Depends(require_upload_access)):
 if (before_time is None)!=(before_id is None):raise HTTPException(422,'El cursor de actividad está incompleto.')
 return await activity.snapshot(ctx,case_id,limit,before_time,before_id)
class ExportRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 run_id:UUID
 format:Literal['csv','json']
 operation_id:UUID
@router.post('/exports')
async def export(payload:ExportRequest,ctx=Depends(require_upload_access)):
 require_dda(ctx,'logistics')
 try:run=await get_run(str(payload.run_id))
 except httpx.HTTPError:raise HTTPException(503,'No se pudo preparar la exportación. Reintentá.') from None
 if not run:raise HTTPException(404,'No se encontró la corrida.')
 try:name,content,media=generate(run,payload.format)
 except ValueError as error:raise HTTPException(422,str(error)) from None
 await platform_call('platform_record_export',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,
  'target_run_id':str(payload.run_id),'export_format':payload.format,'operation_id':str(payload.operation_id),
  'content_sha256':sha256(content).hexdigest(),'content_bytes':len(content)})
 return Response(content,media_type=media,headers={'Content-Disposition':'attachment; filename="'+name+'"','Cache-Control':'no-store'})
