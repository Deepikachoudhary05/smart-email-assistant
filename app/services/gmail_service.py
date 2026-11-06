"""Gmail access with encrypted database tokens and no local browser or files."""
import json
import base64
from email.mime.text import MIMEText
from fastapi import HTTPException
from sqlalchemy import select
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.database.db import get_engine, tokens
from app.security import cipher

SCOPES = ['https://www.googleapis.com/auth/gmail.compose', 'https://www.googleapis.com/auth/gmail.readonly']

def save_credentials(creds):
    encrypted = cipher().encrypt(creds.to_json().encode()).decode()
    with get_engine().begin() as conn:
        # Serialize replacement across PostgreSQL workers.
        if conn.dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import insert
            stmt = insert(tokens).values(id=1, encrypted=encrypted)
            conn.execute(stmt.on_conflict_do_update(index_elements=['id'], set_={'encrypted': encrypted}))
        else:
            conn.execute(tokens.delete().where(tokens.c.id == 1))
            conn.execute(tokens.insert().values(id=1, encrypted=encrypted))

def load_credentials():
    with get_engine().connect() as conn:
        encrypted = conn.execute(select(tokens.c.encrypted).where(tokens.c.id == 1)).scalar_one_or_none()
    if not encrypted:
        raise HTTPException(409, 'Connect Gmail using /auth/google/start first')
    try:
        info = json.loads(cipher().decrypt(encrypted.encode()))
        creds = Credentials.from_authorized_user_info(info, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_credentials(creds)
        if not creds.valid:
            raise ValueError('Invalid credentials')
        return creds
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(409, 'Gmail authorization expired; reconnect Gmail') from None

class GmailService:
    def service(self):
        return build('gmail', 'v1', credentials=load_credentials(), cache_discovery=False)

    def get_emails(self, query='is:unread', max_results=10):
        service = self.service()
        messages = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute().get('messages', [])
        result = []
        for item in messages:
            message = service.users().messages().get(userId='me', id=item['id'], format='full').execute()
            payload = message.get('payload', {})
            headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
            result.append(dict(id=item['id'], sender=headers.get('from', 'Unknown'), subject=headers.get('subject', 'No Subject'), body=self.get_body(payload)))
        return result

    def get_body(self, payload):
        if payload.get('mimeType') == 'text/plain' or not payload.get('parts'):
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4)).decode('utf-8', errors='replace')
        for part in payload.get('parts', []):
            body = self.get_body(part)
            if body:
                return body
        return ''

    def create_draft(self, to, subject, body):
        message = MIMEText(body)
        message['to'], message['subject'] = to, subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return self.service().users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()

gmail_service = GmailService()
