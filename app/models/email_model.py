from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database.db import get_engine, emails, drafts

class Email:
    def __init__(self, gmail_id, sender, subject, body):
        self.values = dict(gmail_id=gmail_id, sender=sender, subject=subject, body=body)

    def save(self):
        engine = get_engine()
        with engine.begin() as conn:
            if engine.dialect.name == 'postgresql':
                stmt = pg_insert(emails).values(**self.values).on_conflict_do_nothing(index_elements=['gmail_id']).returning(emails.c.id)
                return conn.execute(stmt).scalar_one_or_none()
            if conn.execute(select(emails.c.id).where(emails.c.gmail_id == self.values['gmail_id'])).first():
                return None
            return conn.execute(emails.insert().values(**self.values)).inserted_primary_key[0]

    @staticmethod
    def get_all():
        with get_engine().connect() as conn:
            return [dict(row) for row in conn.execute(select(emails).order_by(emails.c.id)).mappings()]

    @staticmethod
    def get_by_id(email_id):
        with get_engine().connect() as conn:
            row = conn.execute(select(emails).where(emails.c.id == email_id)).mappings().first()
            return dict(row) if row else None

class Draft:
    def __init__(self, email_id, recipient_email, subject, body, analysis=None):
        self.values = dict(email_id=email_id, recipient_email=recipient_email, subject=subject, body=body, analysis=analysis)

    def save(self):
        with get_engine().begin() as conn:
            return conn.execute(drafts.insert().values(**self.values)).inserted_primary_key[0]

    @staticmethod
    def get_all():
        with get_engine().connect() as conn:
            return [dict(row) for row in conn.execute(select(drafts).order_by(drafts.c.id)).mappings()]

    @staticmethod
    def get_by_email_id(email_id):
        with get_engine().connect() as conn:
            return [dict(row) for row in conn.execute(select(drafts).where(drafts.c.email_id == email_id)).mappings()]
