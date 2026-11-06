import json
import time
from urllib.parse import parse_qs, urlparse
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from app.database.db import get_engine, init_db, oauth_states, tokens
from app.main import app
from app.models.email_model import Email, Draft
from app.routes import auth_routes
from app.services.gmail_service import load_credentials

@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'test.db'))
    monkeypatch.setenv('APP_API_KEY', 'a' * 48)
    monkeypatch.setenv('TOKEN_ENCRYPTION_KEY', Fernet.generate_key().decode())
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
    monkeypatch.setenv('GOOGLE_REDIRECT_URI', 'https://assistant.example/auth/google/callback')
    get_engine.cache_clear()
    init_db()
    test_engine = get_engine()
    with TestClient(app, base_url='https://assistant.example', raise_server_exceptions=False) as c:
        yield c
    test_engine.dispose()
    get_engine.cache_clear()

AUTH = {'Authorization': 'Bearer ' + 'a' * 48}

@pytest.mark.parametrize('method,path', [('get','/api/emails/fetch'), ('get','/api/emails/list'), ('get','/api/emails/1'), ('get','/api/emails/drafts/list'), ('get','/api/emails/drafts/1'), ('post','/api/emails/drafts/create'), ('post','/auth/google/start'), ('get','/auth/google/status'), ('delete','/auth/google/connection'), ('post','/admin/database/initialize'), ('get','/api/workspace'), ('post','/api/emails/1/reply')])
def test_routes_require_owner(client, method, path):
    assert getattr(client, method)(path).status_code == 401
    assert getattr(client, method)(path, headers={'Authorization': 'Bearer wrong'}).status_code == 401

def test_fail_closed_without_key(client, monkeypatch):
    monkeypatch.delenv('APP_API_KEY')
    assert client.get('/api/emails/list', headers=AUTH).status_code == 503
    assert client.get('/health').status_code == 200

def test_storage_and_duplicate(client):
    eid = Email('gmail-1', 'sender@example.com', 'Subject', 'Body').save()
    assert Email('gmail-1', 'sender@example.com', 'Subject', 'Body').save() is None
    Draft(eid, 'recipient@example.com', 'Reply', 'Hello').save()
    assert client.get('/api/emails/list', headers=AUTH).json()['emails'][0]['body'] == 'Body'
    assert len(client.get(f'/api/emails/drafts/{eid}', headers=AUTH).json()['drafts']) == 1
    assert client.get('/api/emails/999', headers=AUTH).status_code == 404
    assert client.get('/api/emails/fetch', headers=AUTH).status_code == 409

def start(client):
    r = client.post('/auth/google/start', headers=AUTH)
    assert r.status_code == 200
    q = parse_qs(urlparse(r.json()['authorization_url']).query)
    assert q['code_challenge_method'] == ['S256']
    assert q['access_type'] == ['offline']
    assert 'HttpOnly' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
    return q['state'][0]

def test_oauth_rejects_missing_mismatched_cookie(client):
    state = start(client)
    assert client.get('/auth/google/callback', params={'state':'wrong', 'code':'x'}).status_code == 400
    client.cookies.clear()
    assert client.get('/auth/google/callback', params={'state':state, 'code':'x'}).status_code == 400

def test_expired_state(client):
    state = start(client)
    with get_engine().begin() as conn:
        conn.execute(update(oauth_states).values(expires_at=int(time.time()) - 1))
    assert client.get('/auth/google/callback', params={'state':state, 'code':'x'}).status_code == 400

def test_success_encryption_replay_and_disconnect(client, monkeypatch):
    state = start(client)
    class Credentials:
        refresh_token = 'private-refresh-token'
        def to_json(self):
            return json.dumps({'token': 'private-access-token', 'refresh_token': self.refresh_token,
                'token_uri': 'https://oauth2.googleapis.com/token', 'client_id': 'test-client', 'client_secret': 'test-secret', 'expiry': '2099-01-01T00:00:00Z'})
    class Flow:
        credentials = Credentials()
        def fetch_token(self, **kwargs):
            assert kwargs['code'] == 'test-code'
    monkeypatch.setattr(auth_routes, 'make_flow', lambda verifier, state: Flow())
    r = client.get('/auth/google/callback', params={'state':state,'code':'test-code'})
    assert r.status_code == 200
    with get_engine().connect() as conn:
        ciphertext = conn.execute(select(tokens.c.encrypted)).scalar_one()
    assert 'private' not in ciphertext
    assert load_credentials().refresh_token == 'private-refresh-token'
    client.cookies.set('gmail_oauth_state', state, domain='assistant.example', path='/auth/google')
    assert client.get('/auth/google/callback', params={'state':state,'code':'test-code'}).status_code == 400
    assert client.delete('/auth/google/connection', headers=AUTH).status_code == 200
    assert client.get('/auth/google/status', headers=AUTH).json() == {'connected': False}

def test_missing_database_does_not_leak(client, monkeypatch):
    monkeypatch.delenv('DATABASE_URL')
    get_engine.cache_clear()
    r = client.get('/api/emails/list', headers=AUTH)
    assert r.status_code == 500
    assert 'postgresql' not in r.text

def test_vercel_refuses_sqlite(client, monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    get_engine.cache_clear()
    with pytest.raises(RuntimeError):
        get_engine()


def test_dashboard_is_public_but_data_is_protected(client):
    r = client.get('/')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
    assert 'Make room for what matters' in r.text
    assert 'Cache-Control' in r.headers
    assert client.get('/assets/app.js').status_code == 200
    assert client.get('/assets/style.css').status_code == 200
    assert client.get('/api/workspace').status_code == 401


def test_status_contains_flags_not_secrets(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'private-test-key')
    r = client.get('/api/workspace', headers=AUTH)
    assert r.json() == {'oauth_configured': True, 'ai_configured': True, 'database_configured': True}
    assert 'private-test-key' not in r.text
    assert 'test-secret' not in r.text


def test_reply_requires_provider_configuration(client, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert client.post('/api/emails/1/reply', headers=AUTH, json={}).status_code == 503


def test_reply_generation_and_validation(client, monkeypatch):
    from app.services import gemini_service
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    eid = Email('test-ai', 'sender@example.com', 'Test', 'Email body').save()
    def generate(body, tone, context):
        assert body == 'Email body'
        assert tone == 'Friendly'
        assert context == 'Thank them'
        return 'Thanks for reaching out.'
    monkeypatch.setattr(gemini_service, 'generate_email_reply', generate)
    r = client.post(f'/api/emails/{eid}/reply', headers=AUTH, json={'tone':'Friendly','context':'Thank them'})
    assert r.status_code == 200
    assert r.json()['reply'] == 'Thanks for reaching out.'
    assert client.post(f'/api/emails/{eid}/reply', headers=AUTH, json={'tone':'bad'}).status_code == 422
    assert client.post(f'/api/emails/{eid}/reply', headers=AUTH, json={'context':'x'*2001}).status_code == 422
    assert client.post('/api/emails/999/reply', headers=AUTH, json={}).status_code == 404


def test_reply_failure_does_not_leak_provider_error(client, monkeypatch):
    from app.services import gemini_service
    monkeypatch.setenv('GEMINI_API_KEY', 'private-test-key')
    eid = Email('test-error', 'sender@example.com', 'Test', 'Body').save()
    def fail(*args, **kwargs):
        raise RuntimeError('private-test-key')
    monkeypatch.setattr(gemini_service, 'generate_email_reply', fail)
    r = client.post(f'/api/emails/{eid}/reply', headers=AUTH, json={})
    assert r.status_code == 502
    assert 'private-test-key' not in r.text
