import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv('DATABASE_PATH', 'app/database/email_automation.db')


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with schema"""
    conn = get_db_connection()
    c = conn.cursor()

    # Emails table
    c.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_id TEXT UNIQUE NOT NULL,
            sender TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            analyzed BOOLEAN DEFAULT 0
        )
    ''')

    # Drafts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER NOT NULL,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(email_id) REFERENCES emails(id)
        )
    ''')

    # Company data table
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized!")


if __name__ == '__main__':
    init_db()