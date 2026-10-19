"""Supabase Auth BFF. Refresh tokens stay HttpOnly; business calls use Bearer.

PKCE binds email callbacks to the initiating browser. Cookie mutations require
same-origin requests. Passwords are forwarded to GoTrue and never persisted.
"""
import base64
import hashlib
import secrets
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import SUPABASE_URL
from app.platform.identity import bootstrap, headers, platform_call
from app.platform.jwt import verify
from app.services.http_service import http_client

router = APIRouter()
TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'
ACCESS, REFRESH, PKCE, RECOVERY = 'dation_access', 'dation_refresh', 'dation_pkce', 'dation_recovery'


class Email(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(min_length=3, max_length=254)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if value.count('@') != 1 or any(c.isspace() for c in value) or '.' not in value.rsplit('@', 1)[1]:
            raise ValueError('Revisá el email.')
        return value


class Login(Email):
    password: str = Field(min_length=1, max_length=128)


class Signup(Login):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    confirm_password: str = Field(min_length=10, max_length=128)

    @model_validator(mode='after')
    def passwords(self):
        if len(self.password) < 10 or self.password != self.confirm_password:
            raise ValueError('Usá al menos 10 caracteres y confirmá la misma contraseña.')
        if not self.first_name.strip() or not self.last_name.strip():
            raise ValueError('Completá tu nombre y apellido.')
        return self


class Password(BaseModel):
    model_config = ConfigDict(extra='forbid')
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str = Field(min_length=10, max_length=128)

    @model_validator(mode='after')
    def passwords(self):
        if self.password != self.confirm_password:
            raise ValueError('Las contraseñas no coinciden.')
        return self


class Workspace(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=2, max_length=120)
    country: str = Field(pattern=r'^[A-Z]{2}$')
    timezone: str = Field(min_length=1, max_length=80)
    currency: str = Field(pattern=r'^[A-Z]{3}$')

    @field_validator('name')
    @classmethod
    def valid_name(cls, value):
        if len(value.strip()) < 2:
            raise ValueError('Completá el nombre del workspace.')
        return value.strip()

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Elegí una zona horaria válida.') from None
        return value


def origin(request):
    # Cloud Run terminates TLS ahead of Uvicorn. Public product origins use HTTPS;
    # only loopback development may use HTTP. Never trust a caller-supplied redirect.
    parsed=request.url
    scheme=parsed.scheme if parsed.hostname in {'127.0.0.1','localhost','::1'} else 'https'
    return scheme+'://'+parsed.netloc


def csrf(request):
    if request.headers.get('origin') != origin(request) or request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'La solicitud debe iniciarse desde Dation.')


def cookie(response, request, name, value, age, path='/'):
    response.set_cookie(name, value, max_age=age, httponly=True,
                        secure=origin(request).startswith('https://'), samesite='lax', path=path)


def session_cookies(response, request, session):
    cookie(response, request, ACCESS, session['access_token'], min(int(session.get('expires_in', 3600)), 3600))
    cookie(response, request, REFRESH, session['refresh_token'], 60 * 60 * 24 * 30, '/auth')
    response.headers['Cache-Control'] = 'no-store'


def clear_cookies(response):
    for name, path in ((ACCESS, '/'), (REFRESH, '/auth'), (PKCE, '/auth'), (RECOVERY, '/auth')):
        response.delete_cookie(name, path=path, httponly=True, samesite='lax')
    response.headers['Cache-Control'] = 'no-store'


async def gotrue(path, body=None, *, token=None, method='POST', redirect=None):
    outgoing = headers()
    outgoing.pop('Prefer', None)
    if token:
        outgoing['Authorization'] = 'Bearer ' + token
    try:
        async with http_client() as client:
            response = await client.request(method, SUPABASE_URL + '/auth/v1/' + path,
                headers=outgoing, params={'redirect_to': redirect} if redirect else None, json=body, timeout=15)
        if response.status_code >= 400:
            if response.status_code == 429:
                raise HTTPException(429, 'Demasiados intentos. Esperá unos minutos antes de reintentar.')
            if response.status_code >= 500:
                raise HTTPException(503, 'El servicio de acceso no está disponible. Reintentá.')
            raise HTTPException(401, 'No se pudo completar el acceso. Revisá los datos o solicitá un nuevo enlace.')
        return response.json() if response.content else {}
    except httpx.HTTPError:
        raise HTTPException(503, 'No se pudo conectar con el servicio de acceso.') from None


def pkce(response, request):
    verifier = secrets.token_urlsafe(48)
    cookie(response, request, PKCE, verifier, 1800, '/auth')
    return {'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode(),
            'code_challenge_method': 's256'}


@router.get('/login', response_class=HTMLResponse)
@router.get('/register', response_class=HTMLResponse)
@router.get('/recover', response_class=HTMLResponse)
@router.get('/workspace-setup', response_class=HTMLResponse)
def auth_page():
    return HTMLResponse((TEMPLATES / 'auth.html').read_text(), headers={'Cache-Control': 'no-store',
        'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff'})


@router.post('/auth/login')
async def login(request: Request, payload: Login):
    csrf(request)
    session = await gotrue('token?grant_type=password', {'email': payload.email, 'password': payload.password})
    await verify(session['access_token'])
    response = JSONResponse({'ok': True})
    session_cookies(response, request, session)
    response.delete_cookie(RECOVERY, path='/auth', httponly=True)
    return response


@router.post('/auth/register')
async def register(request: Request, payload: Signup):
    csrf(request)
    response = JSONResponse({'message': 'Revisá tu email para confirmar la cuenta y continuar.'})
    session = await gotrue('signup', {'email': payload.email, 'password': payload.password,
        'data': {'first_name': payload.first_name.strip(), 'last_name': payload.last_name.strip()}, **pkce(response, request)},
        redirect=origin(request) + '/auth/callback')
    if session.get('access_token'):
        await verify(session['access_token'])
        session_cookies(response, request, session)
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.post('/auth/recover')
async def recover(request: Request, payload: Email):
    csrf(request)
    response = JSONResponse({'message': 'Si la cuenta existe, recibirás un enlace para cambiar la contraseña.'})
    await gotrue('recover', {'email': payload.email, **pkce(response, request)},
                 redirect=origin(request) + '/auth/callback/recovery')
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.get('/auth/callback')
@router.get('/auth/callback/recovery')
async def callback(request: Request, code: str = ''):
    verifier = request.cookies.get(PKCE)
    if not verifier or not code or len(code) > 2048:
        return RedirectResponse('/login?error=link', status_code=303, headers={'Cache-Control': 'no-store'})
    try:
        session = await gotrue('token?grant_type=pkce', {'auth_code': code, 'code_verifier': verifier})
        await verify(session['access_token'])
    except HTTPException:
        return RedirectResponse('/login?error=link', status_code=303, headers={'Cache-Control': 'no-store'})
    recovery = request.url.path.endswith('/recovery')
    response = RedirectResponse('/recover?step=password' if recovery else '/app', status_code=303)
    session_cookies(response, request, session)
    response.delete_cookie(PKCE, path='/auth', httponly=True)
    if recovery:
        cookie(response, request, RECOVERY, '1', 900, '/auth')
    return response


async def cookie_session(request, response):
    token = request.cookies.get(ACCESS)
    if token:
        try:
            return token, await verify(token)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
    refresh = request.cookies.get(REFRESH)
    if not refresh:
        raise HTTPException(401, 'Ingresá para continuar.')
    session = await gotrue('token?grant_type=refresh_token', {'refresh_token': refresh})
    claims = await verify(session['access_token'])
    session_cookies(response, request, session)
    return session['access_token'], claims


def set_json(response, body):
    response.body = JSONResponse(body).body
    response.headers['content-length'] = str(len(response.body))
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.post('/auth/session')
async def session(request: Request):
    csrf(request)
    response = JSONResponse({})
    try:
        token, claims = await cookie_session(request, response)
        identity = await bootstrap(claims)
    except HTTPException as exc:
        response = JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
        if exc.status_code == 401:
            clear_cookies(response)
        return response
    return set_json(response, {'access_token': token, 'expires_at': claims['exp'], **identity})


@router.post('/auth/logout')
async def logout(request: Request):
    csrf(request)
    token = request.cookies.get(ACCESS)
    response = JSONResponse({'ok': True})
    if token:
        try:
            await gotrue('logout?scope=local', token=token)
        except HTTPException as exc:
            if exc.status_code != 401:
                return JSONResponse({'detail': 'No se pudo cerrar la sesión. Reintentá.'}, status_code=503)
    clear_cookies(response)
    return response


@router.post('/auth/password')
async def password(request: Request, payload: Password):
    csrf(request)
    if request.cookies.get(RECOVERY) != '1':
        raise HTTPException(403, 'Abrí el enlace de recuperación para cambiar tu contraseña.')
    response = JSONResponse({'ok': True})
    token, _ = await cookie_session(request, response)
    await gotrue('user', {'password': payload.password}, token=token, method='PUT')
    response.delete_cookie(RECOVERY, path='/auth', httponly=True)
    return set_json(response, {'ok': True})


@router.post('/auth/workspace')
async def create_workspace(request: Request, payload: Workspace):
    csrf(request)
    response = JSONResponse({})
    _, claims = await cookie_session(request, response)
    result = await platform_call('platform_create_workspace', {'actor_user_id': claims['sub'],
        'workspace_name': payload.name, 'workspace_country': payload.country,
        'workspace_timezone': payload.timezone, 'workspace_currency': payload.currency})
    return set_json(response, result)


@router.post('/auth/invitations')
async def received_invitations(request: Request):
    """Confirmed identity can inspect invitations before it has a workspace."""
    csrf(request)
    response = JSONResponse({})
    _, claims = await cookie_session(request, response)
    return set_json(response, await platform_call('platform_received_invitations',
        {'actor_user_id': claims['sub']}))


@router.post('/auth/invitations/{invitation_id}/accept')
async def accept_invitation(request: Request, invitation_id: UUID):
    csrf(request)
    response = JSONResponse({})
    _, claims = await cookie_session(request, response)
    return set_json(response, await platform_call('platform_received_invitations',
        {'actor_user_id': claims['sub'], 'invitation_id': str(invitation_id)}))
