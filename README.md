# Smart Email Assistant

A single-owner FastAPI backend for reading Gmail messages and creating drafts, with hosted PostgreSQL storage, web OAuth, and authenticated API access. A responsive web dashboard is served by the same FastAPI app at `/`. Creating a draft never sends it.

## Dashboard

Open the production root URL for the web interface. The initial preview contains clearly labeled sample emails, local sample reply templates, and preview drafts held only in memory. Preview mode does not call Gmail or Gemini and does not access private data.

Choose **Use my inbox** and enter the owner key to unlock real data. The key and loaded private content remain in tab memory only; locking, refreshing, or leaving the page clears them. The generated Vercel secret is not readable afterward: if you do not have the owner key, replace `APP_API_KEY` with your own random key (at least 32 characters) in Vercel and redeploy.

- **Inbox:** search messages, sync unread Gmail messages, select an email, and edit a reply.
- **AI reply:** choose a tone and optional context; requires `GEMINI_API_KEY`. All suggestions must be reviewed.
- **Drafts:** copy a reply or save it as a Gmail draft. Nothing is sent automatically.
- **Connections:** authorize Gmail, see setup status, and disconnect Gmail with confirmation.

Authorize Gmail from the Connections page and follow the returned authorization link in the same browser. Return to the dashboard after approval; its connection status refreshes on focus. The existing Google Web OAuth setup requirement still applies.

## Hosting changes

- SQLAlchemy + psycopg use a hosted PostgreSQL `DATABASE_URL`, TLS, and no process-local connection pool. SQLite is accepted only with `APP_ENV=test` outside Vercel.
- Gmail uses Google's Web application OAuth flow with PKCE. A short-lived HttpOnly browser cookie binds the callback to the browser that started authorization. One-time state is consumed atomically in the database.
- Gmail credentials are encrypted using Fernet before being stored in PostgreSQL. Refreshes are persisted. No pickle, token file, local browser listener, or import-time authentication is used.
- All email, draft, connection-management, and initialization endpoints require `Authorization: Bearer <APP_API_KEY>`. Missing authentication configuration fails closed. The dashboard at `/`, static assets, `/health`, `/docs`, and the OAuth callback remain public; the callback requires valid state and a matching browser cookie.
- No permissive CORS policy is enabled. Use the dashboard or `/docs` on the same origin, or a trusted backend client. This is an owner API key, not a multi-user login system. Everyone with this key has access to the same mailbox and data.

## Deployment configuration

Connect this GitHub repository to the Vercel project using the FastAPI framework preset. `index.py` exports the ASGI app. Python 3.12 is selected by `.python-version`.

1. Provision a hosted PostgreSQL database, such as Neon, through Vercel Marketplace. Prefer the provider's pooled URL. Set `DATABASE_URL` in the target Vercel environment. Existing SQLite data is not automatically copied; this creates a new schema.
2. In Google Cloud, enable Gmail API and configure OAuth consent. If the app is in testing, add the Gmail account as a test user. Create an OAuth client of type **Web application**, not Desktop.
3. Register the exact callback `https://YOUR-DEPLOYMENT/auth/google/callback` as an authorized redirect URI. Use a stable production hostname, not a rotating preview hostname.
4. Configure these Vercel environment variables securely:

| Variable | Meaning |
| --- | --- |
| `DATABASE_URL` | Hosted PostgreSQL connection URL |
| `APP_API_KEY` | Random owner bearer key, at least 32 characters |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for encrypting stored Gmail tokens |
| `GOOGLE_CLIENT_ID` | Web OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Web OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Exact authorized callback URL |
| `GEMINI_API_KEY` | Optional: used only by Gemini service helpers |
| `GEMINI_MODEL` | Optional: defaults to `gemini-2.5-flash` |

Generate the owner key with `secrets.token_urlsafe(48)` and the encryption key with `Fernet.generate_key()` in your own trusted environment; save them directly to your password manager and Vercel. Keep the encryption key stable and backed up: losing or changing it makes existing tokens unreadable and requires reconnecting Gmail. Never put secrets in Git, URLs, or chat. `.env.example` lists names only.

5. Deploy, open `/docs`, select **Authorize**, and enter the owner bearer key. Swagger's HTTP Bearer input expects the key itself, without the `Bearer ` prefix.
6. Execute `POST /admin/database/initialize` once to create missing tables. The operation is authenticated and idempotent. It does not run at import, during build, or on public requests. Future schema changes require explicit migrations; this command only creates missing tables.
7. In that same browser, execute `POST /auth/google/start`. Open the returned `authorization_url` in the same browser, sign into Gmail, and grant access. The callback stores encrypted credentials and displays a confirmation. This connects Gmail; it does not replace owner API authentication.
8. Check `GET /auth/google/status`, then fetch emails. Do not disable Vercel Deployment Protection to work around a sign-in issue.

The cloud database, real OAuth consent, and live deployment must be configured before Gmail works. No placeholder credentials or in-memory database fallback are used in production.

## Local development

```bash
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -r requirements.txt
# Copy .env.example to .env and configure a real hosted PostgreSQL database.
python -m app.database.db
python -m uvicorn app.main:app --host 127.0.0.1 --port 5000
```

For local OAuth, register a localhost callback in Google Cloud and use it as `GOOGLE_REDIRECT_URI`. Production redirects must use HTTPS. Do not load untrusted legacy pickle token files. Google refresh-token lifetime is subject to Google consent-app settings; reconnect if authorization expires or is revoked.

## API

All endpoints below require the owner bearer key unless marked public.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Public dashboard with sample preview; real data requires owner authentication |
| GET | `/health` | Public process health check, not provider readiness |
| GET | `/api/workspace` | Owner-only configuration flags; no secret values |
| POST | `/api/emails/{email_id}/reply` | Owner-only Gemini reply generation with tone and optional context |
| POST | `/admin/database/initialize` | Create missing database tables |
| POST | `/auth/google/start` | Start browser-bound Gmail OAuth; returns authorization URL |
| GET | `/auth/google/callback` | Public OAuth callback, validated by state + browser cookie |
| GET | `/auth/google/status` | Check whether a Gmail token is stored (not a live token-validity check) |
| DELETE | `/auth/google/connection` | Remove stored tokens and pending OAuth states |
| GET | `/api/emails/fetch` | Fetch up to 10 unread Gmail messages and save new ones |
| GET | `/api/emails/list` | List stored emails |
| GET | `/api/emails/{email_id}` | Retrieve stored email |
| GET | `/api/emails/drafts/list` | List stored drafts |
| GET | `/api/emails/drafts/{email_id}` | List drafts for an email |
| POST | `/api/emails/drafts/create` | Create Gmail draft and save its details |

Draft request:

```json
{
  "email_id": 1,
  "recipient_email": "recipient@example.com",
  "subject": "Re: Your enquiry",
  "body": "Thank you for your email."
}
```

`DELETE /auth/google/connection` disconnects this application locally. To revoke the Google grant itself, remove the app in your Google Account's third-party access settings. Stored emails and drafts remain in the database after disconnecting.

The dashboard uses the authenticated `POST /api/emails/{email_id}/reply` endpoint for Gemini reply generation. The proposal helper remains a service-layer function. The original Gmail-fetch GET endpoint is retained for compatibility even though it saves new rows. A Gmail draft and its local database record are separate operations; if the database write fails after Gmail succeeds, check Gmail before retrying to avoid duplicate drafts.

## Verification

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use a disposable SQLite database only in explicit test mode and mock the Google token exchange. They cover route authentication, fail-closed configuration, storage, duplicate messages, OAuth browser binding, PKCE, state expiry/replay, token encryption, disconnect, sanitized errors, and production rejection of SQLite. They do not prove live PostgreSQL connectivity or Google consent. Live verification requires your hosted database and OAuth credentials.
