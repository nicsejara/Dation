"""Transient SQL contention must not strand an otherwise completed upload."""
from contextlib import asynccontextmanager
from pathlib import Path
import unittest
from unittest.mock import AsyncMock,patch
import httpx
from fastapi import HTTPException
from app.platform.context import RequestContext,bind
from app.services import dispatch_service as service

WID='00000000-0000-4000-8000-000000000001'
UID='00000000-0000-4000-8000-000000000002'

def busy():return HTTPException(409,'Concurrent data operation',headers={'X-Dation-Retryable':'true'})

class UploadJournalConcurrencyTests(unittest.IsolatedAsyncioTestCase):
 async def exercise(self,conflict=False):
  client=AsyncMock()
  client.post.return_value=httpx.Response(200,request=httpx.Request('POST','https://storage.test/object'))
  client.delete.return_value=httpx.Response(200,request=httpx.Request('DELETE','https://storage.test/object'))
  @asynccontextmanager
  async def http():yield client
  existing={'id':'existing','is_sample':False,'original_filename':'mis-pedidos.csv'}
  conflict_error=httpx.HTTPStatusError('Duplicate',request=httpx.Request('POST','https://db.test/datasets'),response=httpx.Response(409))
  db=AsyncMock(side_effect=[[],conflict_error,[existing]] if conflict else [[],[{'id':'new'}]])
  attempts={};operations=[]
  async def journal(name,body):
   operation=body['operation'];operations.append(operation);attempts[operation]=attempts.get(operation,0)+1
   if operation=='prepare':return {'operation_id':'intent'}
   if attempts[operation]==1:raise busy()
   return {'cleared':False,'storage_bucket':service.SUPABASE_INPUT_BUCKET,'storage_path':client.post.call_args.args[0].split('/object/'+service.SUPABASE_INPUT_BUCKET+'/')[1]} if operation=='discard' else {'cleared':True}
  raw=(Path(__file__).resolve().parents[2]/'sample_data/onboarding-v1/orders.csv').read_bytes()
  with bind(RequestContext(UID,WID,'admin')),patch.object(service,'db',db),patch.object(service,'http_client',http),patch.object(service,'platform_call',side_effect=journal),patch.object(service.asyncio,'sleep',AsyncMock()):
   result=await service.store_input('demo.csv',raw,'orders',is_sample=True,track_upload=True)
  client.post.assert_awaited_once()
  self.assertEqual(attempts['prepare'],1,'Never retry intent creation')
  if conflict:
   self.assertTrue(result['duplicate']);self.assertEqual(result['existing_dataset'],existing)
   client.delete.assert_awaited_once();self.assertEqual(operations,['prepare','failed','failed','discard','discard','finish','finish'])
  else:
   self.assertFalse(result['duplicate']);client.delete.assert_not_awaited();self.assertEqual(operations,['prepare','stored','stored'])
 async def test_committed_upload_retries_busy_journal_without_reupload(self):await self.exercise()
 async def test_duplicate_loser_finishes_compensation_and_preserves_original(self):await self.exercise(conflict=True)
 async def test_retries_are_bounded_and_only_for_explicit_sql_contention(self):
  for error,expected in [(busy(),5),(HTTPException(409,'Identity conflict'),1),(HTTPException(403,'Access denied'),1),(HTTPException(503,'Uncertain network outcome'),1)]:
   with self.subTest(status=error.status_code,retryable=bool(error.headers)),patch.object(service,'platform_call',AsyncMock(side_effect=error)) as rpc,patch.object(service.asyncio,'sleep',AsyncMock()):
    with self.assertRaises(HTTPException) as result:await service._upload_journal_call({'operation':'stored'})
    self.assertIs(result.exception,error);self.assertEqual(rpc.await_count,expected)
