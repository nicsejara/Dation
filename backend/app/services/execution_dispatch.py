"""Durable activation adapter. No loop, solver or detached task in the API.

The DB owns intent identity/capacity/fencing. The provider only wakes finite
processes. A failed post-commit nudge never revokes an accepted intention.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from time import perf_counter
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import HTTPException
from app.config import SUPABASE_URL
from app.cloud_identity import PROJECT, REGION, JOBS, validate_environment
from app.platform.context import current, is_infrastructure
from app.platform.identity import headers
from app.services.http_service import http_client
from app.observability import event, metrics

_override = ContextVar('execution_dispatch_transport', default=None)


class DispatchConfigurationError(RuntimeError):
    pass


def jobs_mode():
    mode=os.getenv('DATION_EXECUTION_MODE','jobs')
    if mode not in {'jobs','legacy'}:raise DispatchConfigurationError('Unknown execution mode')
    return mode=='jobs'


@contextmanager
def use_transport(transport):
    """Task-local injection for owned tests; never selected by request data."""
    token=_override.set(transport)
    try:yield transport
    finally:_override.reset(token)


async def runtime_rpc(operation, arguments=None, *, infrastructure=False):
    body={'operation':operation,'arguments':arguments or {}}
    if infrastructure:
        if not is_infrastructure():
            if not current().worker:raise RuntimeError('Worker authority required')
    else:
        ctx=current()
        body.update(target_workspace_id=ctx.workspace_id,actor_user_id=ctx.user_id)
    async with http_client() as client:
        response=await client.post(SUPABASE_URL+'/rest/v1/rpc/execution_runtime',
                                   headers=headers(),json=body,timeout=8)
    if response.status_code>=400:
        try:code=response.json().get('code')
        except ValueError:code=None
        if code=='42501':raise HTTPException(403,'No tenés acceso a esta operación.')
        if code=='P0002':raise HTTPException(404,'No se encontró la intención.')
    response.raise_for_status()
    return response.json()


class GoogleJobsTransport:
    def __init__(self):
        if os.getenv('DATION_CLOUD_EXECUTION_ENABLED','false')!='true':
            raise DispatchConfigurationError('Cloud execution is disabled')
        try:
            validate_environment(os.environ)
        except ValueError as exc:
            raise DispatchConfigurationError(str(exc)) from exc
        self.resources=dict(JOBS)

    async def _token(self,client):
        # Managed service identity only; no forwarded user token/static data key.
        response=await client.get('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',
                                  headers={'Metadata-Flavor':'Google'},timeout=2)
        response.raise_for_status()
        value=response.json().get('access_token')
        if not isinstance(value,str) or not value:raise DispatchConfigurationError('Managed token unavailable')
        return value

    async def dispatch(self,intent):
        identifier=str(UUID(intent['id']));token=str(UUID(intent['delivery_token']))
        resource=self.resources['control' if intent['kind']=='reconciliation' else 'compute']
        body={'overrides':{'taskCount':1,'containerOverrides':[{
            'name':'runtime','args':['--intent-id',identifier,'--delivery-token',token]}]}}
        async with http_client() as client:
            access=await self._token(client)
            response=await client.post('https://run.googleapis.com/v2/'+resource+':run',
                headers={'Authorization':'Bearer '+access},json=body,timeout=5)
        response.raise_for_status()
        operation=response.json().get('name','')
        prefix=f'projects/{PROJECT}/locations/{REGION}/operations/'
        if not operation.startswith(prefix) or len(operation)>512:
            raise DispatchConfigurationError('Unexpected provider operation reference')
        return operation

    async def healthy(self):
        async with http_client() as client:
            access=await self._token(client)
            for resource in self.resources.values():
                response=await client.get('https://run.googleapis.com/v2/'+resource,
                    headers={'Authorization':'Bearer '+access},timeout=3)
                response.raise_for_status()
                if response.json().get('name')!=resource:return False
                permissions=['run.jobs.run','run.jobs.runWithOverrides']
                probe=await client.post('https://run.googleapis.com/v2/'+resource+':testIamPermissions',
                    headers={'Authorization':'Bearer '+access},json={'permissions':permissions},timeout=3)
                probe.raise_for_status()
                if not set(permissions).issubset(probe.json().get('permissions',[])):return False
        # Read-only IAM/resource verification; no Job execution is started.
        return True


class LoopbackJobsTransport:
    """Real HTTP fake for isolated integration; unavailable in Cloud Run."""
    def __init__(self,url):
        parsed=urlsplit(url)
        if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.username or parsed.password or parsed.path not in {'','/'}:
            raise DispatchConfigurationError('Fake dispatch must use an owned loopback origin')
        if os.getenv('K_SERVICE') or os.getenv('CLOUD_RUN_JOB'):
            raise DispatchConfigurationError('Fake transport is forbidden in Cloud Run')
        self.url=url.rstrip('/')

    async def dispatch(self,intent):
        async with http_client() as client:
            response=await client.post(self.url+'/execute',json={
                'intent_id':str(UUID(intent['id'])),'delivery_token':str(UUID(intent['delivery_token'])),
                'kind':intent['kind']},timeout=5)
        response.raise_for_status()
        return response.json()['name']

    async def healthy(self):
        async with http_client() as client:
            response=await client.get(self.url+'/health',timeout=2)
        return response.status_code==200 and response.json().get('ready') is True


def transport():
    injected=_override.get()
    if injected is not None:return injected
    if os.getenv('DATION_TEST_RUNTIME')=='1':
        return LoopbackJobsTransport(os.getenv('DATION_DISPATCH_FAKE_URL',''))
    return GoogleJobsTransport()


async def ensure_admission():
    if not jobs_mode():return
    try:
        policy=await runtime_rpc('policy')
        available=all(policy.get(k) for k in ('enabled','admissions_open','recovery_fresh','dispatch_budget_available'))
        if not available or not await transport().healthy():raise DispatchConfigurationError('Activation is not ready')
    except (DispatchConfigurationError,httpx.HTTPError,TimeoutError,ValueError) as exc:
        raise HTTPException(503,'La ejecución bajo demanda no está disponible. Reintentá con el mismo ID.',
                            headers={'Retry-After':'15'}) from exc


async def publish_pending(*, kind=None, entity_id=None, limit=1, infrastructure=False):
    provider=transport()  # Fail before reserving/consuming attempts if disabled.
    arguments={'limit':limit}
    if kind is not None:arguments['kind']=kind
    if entity_id is not None:arguments['entity_id']=str(UUID(str(entity_id)))
    rows=await runtime_rpc('reserve',arguments,infrastructure=infrastructure)
    outcomes=[]
    for row in rows:
        started=perf_counter();outcome='submitted'
        identity={'intent_id':row['id'],'delivery_token':row['delivery_token']}
        try:
            operation=await provider.dispatch(row)
            accepted=await runtime_rpc('submitted',{**identity,'provider_operation':operation},infrastructure=infrastructure)
            outcome='submitted' if accepted else 'superseded'
        except (httpx.HTTPError,DispatchConfigurationError,HTTPException,ValueError) as exc:
            outcome='pending_recovery'
            code='provider_timeout' if isinstance(exc,httpx.TimeoutException) else 'provider_unavailable'
            if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code<500:code='provider_rejected'
            try:await runtime_rpc('defer',{**identity,'code':code},infrastructure=infrastructure)
            except (httpx.HTTPError,HTTPException):pass
        duration=perf_counter()-started
        metrics.observe('dation_dispatch_provider_seconds',duration,(('kind',row['kind']),))
        event('execution_dispatch',intent_id=row['id'],kind=row['kind'],generation=row['generation'],
              retry_count=row['delivery_attempts']-1,outcome=outcome,provider_wall_ms=duration*1000)
        outcomes.append(outcome)
    return outcomes


async def nudge(kind,entity_id):
    """Best effort after commit; recovery owns the cross-provider failure gap."""
    try:
        if not jobs_mode():return
        await publish_pending(kind=kind,entity_id=entity_id)
    except (httpx.HTTPError,HTTPException,DispatchConfigurationError,ValueError) as exc:
        event('execution_activation_pending',kind=kind,error_type=type(exc).__name__)
