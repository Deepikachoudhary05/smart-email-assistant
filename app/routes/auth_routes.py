"""Owner-authorized, browser-bound, one-time OAuth with PKCE."""
import hashlib
import os
import secrets
import time
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select, delete
from app.security import require_owner, cipher
from app.database.db import get_engine, oauth_states, tokens
from app.services.gmail_service import SCOPES, save_credentials

router = APIRouter(prefix='/auth/google', tags=['Gmail connection'])
COOKIE = 'gmail_oauth_state'

def make_flow(verifier, state=None):
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    redirect = os.getenv('GOOGLE_REDIRECT_URI', '')
    parsed = urlparse(redirect)
    local = parsed.hostname in ('localhost', '127.0.0.1') and not os.getenv('VERCEL')
    if not client_id or not client_secret or not parsed.netloc or (parsed.scheme != 'https' and not local):
        raise HTTPException(503, 'Google web OAuth is not configured')
    config = {'web': {'client_id': client_id, 'client_secret': client_secret,
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token', 'redirect_uris': [redirect]}}
    return Flow.from_client_config(config, scopes=SCOPES, redirect_uri=redirect,
        state=state, code_verifier=verifier, autogenerate_code_verifier=False)

@router.post('/start', dependencies=[Depends(require_owner)])
def start(response: Response):
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    flow = make_flow(verifier, state)
    url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    now = int(time.time())
    with get_engine().begin() as conn:
        conn.execute(delete(oauth_states).where(oauth_states.c.expires_at < now))
        conn.execute(oauth_states.insert().values(state_hash=hashlib.sha256(state.encode()).hexdigest(),
            verifier=cipher().encrypt(verifier.encode()).decode(), expires_at=now + 600))
    response.set_cookie(COOKIE, state, httponly=True, secure=not (urlparse(os.getenv('GOOGLE_REDIRECT_URI', '')).hostname in ('localhost', '127.0.0.1') and not os.getenv('VERCEL')),
        samesite='lax', max_age=600, path='/auth/google')
    response.headers['Cache-Control'] = 'no-store'
    return {'authorization_url': url}

@router.get('/callback', include_in_schema=False)
def callback(request: Request, state: str = '', code: str = '', error: str = ''):
    cookie = request.cookies.get(COOKIE, '')
    if not state or not cookie or not secrets.compare_digest(state, cookie):
        raise HTTPException(400, 'Invalid OAuth state; restart Gmail connection')
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    with get_engine().begin() as conn:
        row = conn.execute(delete(oauth_states).where(oauth_states.c.state_hash == state_hash).returning(oauth_states)).mappings().first()
    if not row or row['expires_at'] < int(time.time()):
        raise HTTPException(400, 'OAuth request expired or already used')
    if error or not code:
        raise HTTPException(400, 'Google authorization was not completed')
    try:
        verifier = cipher().decrypt(row['verifier'].encode()).decode()
        flow = make_flow(verifier, state)
        flow.fetch_token(code=code, timeout=20)
        if not flow.credentials.refresh_token:
            raise ValueError('Missing refresh token')
        save_credentials(flow.credentials)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, 'Could not connect Gmail; restart authorization') from None
    response = Response('Gmail connected. You may close this page.', media_type='text/plain', headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})
    response.delete_cookie(COOKIE, path='/auth/google')
    return response

@router.get('/status', dependencies=[Depends(require_owner)])
def status():
    with get_engine().connect() as conn:
        connected = conn.execute(select(tokens.c.id).where(tokens.c.id == 1)).first() is not None
    return {'connected': connected}

@router.delete('/connection', dependencies=[Depends(require_owner)])
def disconnect():
    with get_engine().begin() as conn:
        conn.execute(delete(tokens))
        conn.execute(delete(oauth_states))
    return {'connected': False, 'message': 'Local connection removed; revoke app access in Google Account settings to revoke the Google grant.'}
