"""Hosted PostgreSQL storage; SQLite is permitted only in explicit local tests."""
import os
from functools import lru_cache
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()
metadata = MetaData()
emails = Table('emails', metadata,
    Column('id', Integer, primary_key=True), Column('gmail_id', String, nullable=False, unique=True),
    Column('sender', Text, nullable=False), Column('subject', Text, nullable=False), Column('body', Text))
drafts = Table('drafts', metadata,
    Column('id', Integer, primary_key=True), Column('email_id', Integer, ForeignKey('emails.id'), nullable=False),
    Column('recipient_email', Text, nullable=False), Column('subject', Text, nullable=False),
    Column('body', Text, nullable=False), Column('analysis', Text))
tokens = Table('gmail_tokens', metadata, Column('id', Integer, primary_key=True), Column('encrypted', Text, nullable=False))
oauth_states = Table('oauth_states', metadata,
    Column('state_hash', String(64), primary_key=True), Column('verifier', Text, nullable=False),
    Column('expires_at', Integer, nullable=False))

@lru_cache
def get_engine():
    url = os.getenv('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = 'postgresql+psycopg://' + url[len('postgres://'):]
    elif url.startswith('postgresql://'):
        url = 'postgresql+psycopg://' + url[len('postgresql://'):]
    if url.startswith('sqlite:') and os.getenv('APP_ENV') == 'test' and not os.getenv('VERCEL'):
        return create_engine(url, connect_args={'check_same_thread': False})
    if not url.startswith('postgresql+psycopg://'):
        raise RuntimeError('Configure a hosted PostgreSQL DATABASE_URL')
    return create_engine(url, poolclass=NullPool, connect_args={'sslmode': 'require', 'connect_timeout': 10})

def init_db():
    """Run explicitly once after provisioning; never during build/import."""
    metadata.create_all(get_engine())

if __name__ == '__main__':
    init_db()
