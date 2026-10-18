"""Entitlements come from the resolved database identity, never JWT metadata."""
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
import httpx
from app.platform.context import RequestContext
from app.platform.identity import resolve
from app.platform.entitlements import enabled_ddas
from app.platform.home import home_snapshot

W='00000000-0000-4000-8000-000000000001'
U='10000000-0000-4000-8000-000000000001'


class EntitlementTests(IsolatedAsyncioTestCase):
 async def test_resolved_identity_is_fail_closed_and_ignores_forged_claims(self):
  data={'membership':{'workspace_id':W,'access_role':'admin'},'ddas':[
   {'workspace_id':W,'dda_id':'production','status':'enabled'},
   {'workspace_id':U,'dda_id':'logistics','status':'enabled'}]}
  self.assertEqual(enabled_ddas(data,W),frozenset())
  with patch('app.platform.identity.bootstrap',AsyncMock(return_value=data)):
   ctx=await resolve({'sub':U,'ddas':['logistics'],'user_metadata':{'logistics':'enabled'}})
  self.assertEqual(ctx.enabled_ddas,frozenset())

 async def test_business_api_blocks_before_provider_while_home_remains_available(self):
  from main import app
  with patch('app.auth.verify',AsyncMock(return_value={'sub':U})),patch('app.auth.resolve',AsyncMock(return_value=RequestContext(U,W,'admin'))),patch('app.platform.home.platform_call',AsyncMock()) as provider:
   async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://qa.invalid',headers={'Authorization':'Bearer verified'}) as client:
    for method,path in [('GET','/api/decision-cases'),('GET','/api/datasets'),('GET','/api/runs'),('POST','/api/runs'),('GET','/api/workspace/summary')]:
     result=await client.request(method,path,json={} if method=='POST' else None)
     self.assertEqual(result.status_code,403,(path,result.text));self.assertEqual(result.headers['X-Dation-Entitlement'],'disabled')
    home=await client.get('/api/platform/home');self.assertEqual(home.status_code,200)
    self.assertEqual(home.json()['recent_cases'],[])
   provider.assert_not_awaited()

 async def test_disabled_home_never_queries_business_data(self):
  with patch('app.platform.home.platform_call',AsyncMock()) as provider:
   result=await home_snapshot(RequestContext(U,W,'viewer'))
  self.assertEqual(result['attention']['total'],0);provider.assert_not_awaited()
