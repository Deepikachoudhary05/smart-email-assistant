# Smart Email Assistant

A Python backend built with FastAPI, Gmail API, Gemini, and SQLite for fetching emails and managing drafts.

## Features

- Fetch up to 10 unread Gmail messages and save them in SQLite.
- List stored emails and retrieve individual messages.
- Create Gmail drafts and store draft details locally. Draft creation does not send email.
- Gemini service functions for generating professional email replies and business proposals.

The Gemini functions are included in the service layer but are not connected to HTTP endpoints in this version. This project has no separate frontend.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set your Gemini API key.
4. Enable Gmail API in your Google Cloud project, configure the OAuth consent screen, and create OAuth credentials for a desktop application. Download the client configuration as `credentials.json` in the project root. Add your Gmail account as a test user if the OAuth app is in testing.
5. Start from the project root:

   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 5000
   ```

Gmail authentication runs at application import/startup and opens a browser on the first run. Complete authorization locally; the resulting token is saved in `token.pickle`. SQLite tables are created on startup. Open http://127.0.0.1:5000/docs for interactive API documentation.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/api/emails/fetch` | Fetch unread Gmail messages and save them |
| GET | `/api/emails/list` | List stored emails |
| GET | `/api/emails/{email_id}` | Retrieve a stored email |
| GET | `/api/emails/drafts/list` | List stored drafts |
| GET | `/api/emails/drafts/{email_id}` | List drafts for an email |
| POST | `/api/emails/drafts/create` | Create a Gmail draft and save its details |

Draft request example:

```json
{
  "email_id": 1,
  "recipient_email": "recipient@example.com",
  "subject": "Re: Your enquiry",
  "body": "Thank you for your email."
}
```

## Project structure

- `app/main.py`: FastAPI application
- `app/routes/`: Email and draft endpoints
- `app/services/`: Gmail and Gemini integrations
- `app/models/`: SQLite persistence helpers
- `app/database/`: Connection and schema initialization
- `app/schemas/`: Request schemas

## Configuration and local use

Keep API keys, OAuth credentials, tokens, and email databases out of Git. Only placeholder values are provided in `.env.example`. The API currently has no application-level authentication and uses permissive CORS; run it locally for development.

The supplied dependency versions are preserved, with the missing `google-auth-oauthlib` dependency added. Live Gmail/Gemini integration requires your own credentials and has not been verified as part of the repository upload.
