"""Security regressions for authority, scoped transport, JWKS rotation and Auth."""
import asyncio,json
from contextlib import asynccontextmanager
from time import time,monotonic
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock,patch
import httpx,jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from app.platform import jwt as verifier,auth_routes
from app.platform.context import RequestContext,bind,current
from app.platform.repository import TenantClient
A='00000000-0000-4000-8000-000000000001'
B='00000000-0000-4000-8000-000000000002'
U='10000000-0000-4000-8000-000000000001'

class RepositorySecurityTests(IsolatedAsyncioTestCase):
 async def test_missing_context_viewer_write_and_worker_rpc_never_reach_provider(self):
  calls=[]
  async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:calls.append(r) or httpx.Response(200,json=[]))) as raw:
   with patch('app.platform.repository.SUPABASE_URL','https://qa.invalid'):
    repo=TenantClient(raw)
    with self.assertRaises(RuntimeError):await repo.get('https://qa.invalid/rest/v1/datasets')
    with bind(RequestContext(U,A,'viewer')):
     for url in ['datasets','rpc/claim_dispatch_job','rpc/enqueue_dispatch_run']:
      with self.assertRaises(HTTPException) as error:await repo.post('https://qa.invalid/rest/v1/'+url,json={})
      self.assertEqual(error.exception.status_code,403)
  self.assertEqual(calls,[])

 async def test_concurrent_requests_keep_independent_workspace_filters(self):
  seen=[]
  async def respond(request):
   await asyncio.sleep(0);seen.append(request);return httpx.Response(200,json=[])
  async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as raw:
   with patch('app.platform.repository.SUPABASE_URL','https://qa.invalid'):
    async def call(wid):
     with bind(RequestContext(U,wid,'operator')):
      await TenantClient(raw).get('https://qa.invalid/rest/v1/datasets',params={'id':'eq.'+wid})
    await asyncio.gather(call(A),call(B))
  self.assertEqual(len(seen),2)
  for request in seen:self.assertEqual(request.url.params['workspace_id'],request.url.params['id'])
  with self.assertRaises(RuntimeError):current()

 async def test_rpc_binds_verified_authority_and_legacy_storage_checks_database_first(self):
  seen=[]
  async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:seen.append(r) or httpx.Response(200,json=[]))) as raw:
   with patch('app.platform.repository.SUPABASE_URL','https://qa.invalid'),bind(RequestContext(U,A,'viewer')):
    repo=TenantClient(raw)
    await repo.get('https://qa.invalid/rest/v1/rpc/decision_case_history',params={'target_case_id':B})
    with self.assertRaises(HTTPException) as error:await repo.get('https://qa.invalid/storage/v1/object/authenticated/dda-inputs/'+B+'/input.csv')
    self.assertEqual(error.exception.status_code,404)
  body=json.loads(seen[0].content);self.assertEqual((body['actor_user_id'],body['target_workspace_id'],body['worker_call']),(U,A,False))
  self.assertEqual(seen[0].method,'POST');self.assertEqual(seen[1].url.path,'/rest/v1/datasets');self.assertEqual(len(seen),2)

class JWTTests(IsolatedAsyncioTestCase):
 def key(self,kid):
  key=ec.generate_private_key(ec.SECP256R1());jwk=json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()));jwk.update(kid=kid,alg='ES256',use='sig');return key,jwk
 async def test_signature_claims_caching_and_rotation(self):
  key,jwk=self.key('a');other,otherjwk=self.key('b');calls=[];keys=[jwk]
  @asynccontextmanager
  async def client():
   async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:calls.append(r) or httpx.Response(200,json={'keys':keys}))) as c:yield c
  claims={'sub':U,'iss':'https://qa.invalid/auth/v1','aud':'authenticated','iat':int(time()),'exp':int(time())+600,'role':'authenticated'}
  def signed(values=claims,private=key,kid='a'):return jwt.encode(values,private,algorithm='ES256',headers={'kid':kid})
  with patch.object(verifier,'SUPABASE_URL','https://qa.invalid'),patch.object(verifier,'ISSUER',claims['iss']),patch.object(verifier,'http_client',client),patch.object(verifier,'_keys',{}),patch.object(verifier,'_expires',0),patch.object(verifier,'_last_refresh',0):
   self.assertEqual((await verifier.verify(signed()))['sub'],U);await verifier.verify(signed());self.assertEqual(len(calls),1)
   for bad in [signed({**claims,'aud':'other'}),signed({**claims,'iss':'https://evil.invalid'}),signed({**claims,'exp':int(time())-60}),signed(private=other),signed({**claims,'sub':'invalid'}),jwt.encode(claims,'f'*32,algorithm='HS256',headers={'kid':'a'})]:
    with self.assertRaises(HTTPException) as error:await verifier.verify(bad)
    self.assertEqual(error.exception.status_code,401)
   keys.append(otherjwk);verifier._last_refresh=monotonic()-6
   await verifier.verify(signed(private=other,kid='b'));self.assertEqual(len(calls),2)

class AuthFlowTests(IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  from main import app
  self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://qa.invalid');self.addAsyncCleanup(self.client.aclose)
 async def test_signup_uses_pkce_confirmation_redirect_and_http_only_secure_cookie(self):
  with patch.object(auth_routes,'gotrue',AsyncMock(return_value={'user':{'id':U}})) as provider:
   result=await self.client.post('/auth/register',headers={'Origin':'https://qa.invalid'},json={'email':'user@example.test','password':'sufficient-password','confirm_password':'sufficient-password','first_name':'Test','last_name':'User'})
  self.assertEqual(result.status_code,200);self.assertNotIn('sufficient-password',result.text)
  call=provider.await_args;self.assertEqual(call.kwargs['redirect'],'https://qa.invalid/auth/callback');self.assertEqual(call.args[1]['code_challenge_method'],'s256');self.assertNotIn('code_verifier',call.args[1]);self.assertIn('Secure',result.headers['set-cookie']);self.assertIn('HttpOnly',result.headers['set-cookie'])
 async def test_recovery_link_requires_initiating_browser(self):
  with patch.object(auth_routes,'gotrue',AsyncMock(return_value={})) as provider:
   response=await self.client.post('/auth/recover',headers={'Origin':'https://qa.invalid'},json={'email':'user@example.test'})
   self.assertEqual(response.status_code,200);self.assertIn('/auth/callback/recovery',provider.await_args.kwargs['redirect']);self.client.cookies.clear()
   self.assertEqual((await self.client.get('/auth/callback/recovery?code=unbound')).status_code,303);self.assertEqual(provider.await_count,1)
 async def test_revoked_refresh_clears_session_and_csrf_blocks_logout(self):
  self.client.cookies.set('dation_refresh','revoked')
  with patch.object(auth_routes,'gotrue',AsyncMock(side_effect=HTTPException(401,'Invalid refresh'))):response=await self.client.post('/auth/session',headers={'Origin':'https://qa.invalid'})
  self.assertEqual(response.status_code,401);self.assertIn('Max-Age=0',response.headers['set-cookie']);self.assertEqual((await self.client.post('/auth/logout',headers={'Origin':'https://evil.invalid'})).status_code,403)

 async def test_recovery_does_not_expose_provider_account_existence_errors(self):
  responses=[]
  for result in ({},HTTPException(401,'Account missing')):
   with patch.object(auth_routes,'gotrue',AsyncMock(side_effect=result if isinstance(result,Exception) else None,return_value={} )):
    responses.append(await self.client.post('/auth/recover',headers={'Origin':'https://qa.invalid'},json={'email':'unknown@example.test'}))
  self.assertTrue(all(r.status_code==200 for r in responses));self.assertEqual(responses[0].json(),responses[1].json())
  self.assertNotIn('Account missing',responses[1].text)

 async def test_password_change_clears_recovery_session_and_requests_fresh_login(self):
  for logout_error in (None,HTTPException(503,'Provider unavailable')):
   self.client.cookies.set(auth_routes.RECOVERY,'1',domain='qa.invalid',path='/auth')
   with patch.object(auth_routes,'cookie_session',AsyncMock(return_value=('synthetic-recovery-token',{'sub':U}))),patch.object(auth_routes,'gotrue',AsyncMock(side_effect=[{},logout_error] if logout_error else [{},{}])) as provider:
    result=await self.client.post('/auth/password',headers={'Origin':'https://qa.invalid'},json={'password':'synthetic-new-password','confirm_password':'synthetic-new-password'})
   self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['redirect'],'/login?password=updated')
   self.assertEqual(provider.await_args_list[0].args[0],'user');self.assertEqual(provider.await_args_list[1].args[0],'logout?scope=local')
   self.assertNotIn('synthetic-new-password',result.text)
   cookies=';'.join(result.headers.get_list('set-cookie'))
   for name in (auth_routes.ACCESS,auth_routes.REFRESH,auth_routes.RECOVERY):self.assertIn(name+'=""',cookies)
   self.assertNotIn(auth_routes.RECOVERY,self.client.cookies)
