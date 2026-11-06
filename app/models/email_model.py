from app.database.db import get_db_connection
from datetime import datetime


class Email:
    def __init__(self, gmail_id, sender, subject, body):
        self.gmail_id = gmail_id
        self.sender = sender
        self.subject = subject
        self.body = body

    def save(self):
        """Save email to database"""
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO emails (gmail_id, sender, subject, body)
                VALUES (?, ?, ?, ?)
            ''', (self.gmail_id, self.sender, self.subject, self.body))
            conn.commit()
            email_id = c.lastrowid
            return email_id
        except Exception as e:
            print(f"Error saving email: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_all():
        """Get all emails from database"""
        conn = get_db_connection()
        c = conn.cursor()
        emails = c.execute('SELECT * FROM emails').fetchall()
        conn.close()
        return [dict(email) for email in emails]

    @staticmethod
    def get_by_id(email_id):
        """Get email by ID"""
        conn = get_db_connection()
        c = conn.cursor()
        email = c.execute('SELECT * FROM emails WHERE id = ?', (email_id,)).fetchone()
        conn.close()
        return dict(email) if email else None


class Draft:
    def __init__(self, email_id, recipient_email, subject, body, analysis=None):
        self.email_id = email_id
        self.recipient_email = recipient_email
        self.subject = subject
        self.body = body
        self.analysis = analysis

    def save(self):
        """Save draft to database"""
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO drafts (email_id, recipient_email, subject, body, analysis)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.email_id, self.recipient_email, self.subject, self.body, self.analysis))
            conn.commit()
            draft_id = c.lastrowid
            return draft_id
        except Exception as e:
            print(f"Error saving draft: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_all():
        """Get all drafts"""
        conn = get_db_connection()
        c = conn.cursor()
        drafts = c.execute('SELECT * FROM drafts').fetchall()
        conn.close()
        return [dict(draft) for draft in drafts]

    @staticmethod
    def get_by_email_id(email_id):
        """Get drafts for specific email"""
        conn = get_db_connection()
        c = conn.cursor()
        drafts = c.execute('SELECT * FROM drafts WHERE email_id = ?', (email_id,)).fetchall()
        conn.close()
        return [dict(draft) for draft in drafts]