import os
import pickle
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.api_core.exceptions import GoogleAPIError
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.readonly'
]

CREDENTIALS_FILE = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'token.pickle')


class GmailService:
    def __init__(self):
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None

        # Load existing token if available
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(f"❌ {CREDENTIALS_FILE} not found! Download it from Google Cloud Console.")

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail API authenticated!")

    def get_emails(self, query='is:unread', max_results=10):
        """
        Fetch emails from Gmail

        Args:
            query: Gmail search query (default: unread emails)
            max_results: Maximum number of emails to fetch

        Returns:
            List of email dictionaries with id, sender, subject, body
        """
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results).execute()

            messages = results.get('messages', [])
            emails = []

            for message in messages:
                email_data = self.get_message(message['id'])
                if email_data:
                    emails.append(email_data)

            print(f"✅ Fetched {len(emails)} emails")
            return emails
        except GoogleAPIError as e:
            print(f"❌ Error fetching emails: {e}")
            return []

    def get_message(self, message_id):
        """
        Get full message details

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary with id, sender, subject, body
        """
        try:
            message = self.service.users().messages().get(
                userId='me', id=message_id, format='full').execute()

            headers = message['payload']['headers']

            email_data = {
                'id': message_id,
                'sender': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                'body': self.get_body(message['payload'])
            }

            return email_data
        except GoogleAPIError as e:
            print(f"❌ Error getting message {message_id}: {e}")
            return None

    def get_body(self, payload):
        """
        Extract email body from payload

        Args:
            payload: Message payload from Gmail API

        Returns:
            Email body as string
        """
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                data = payload['body'].get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
            return ''
        except Exception as e:
            print(f"❌ Error extracting body: {e}")
            return ''

    def create_draft(self, to, subject, body):
        """
        Create a draft email in Gmail (NOT sent)

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body

        Returns:
            Draft object with id
        """
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            draft = self.service.users().drafts().create(
                userId='me', body={'message': {'raw': raw}}).execute()

            print(f"✅ Draft created for {to}")
            return draft
        except GoogleAPIError as e:
            print(f"❌ Error creating draft: {e}")
            return None

    def get_drafts(self):
        """Get all drafts from Gmail"""
        try:
            results = self.service.users().drafts().list(userId='me').execute()
            drafts = results.get('drafts', [])
            print(f"✅ Fetched {len(drafts)} drafts from Gmail")
            return drafts
        except GoogleAPIError as e:
            print(f"❌ Error fetching drafts: {e}")
            return []


# Global instance
gmail_service = GmailService()