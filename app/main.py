from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routes import email_routes, auth_routes

app = FastAPI(title='Smart Email Assistant', version='2.0.0', description='Single-owner backend. Authorize with your private APP_API_KEY. Never share the owner key.')
app.include_router(email_routes.router)
app.include_router(auth_routes.router)

@app.middleware('http')
async def privacy_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    # Do not expose SQL parameters, connection strings, or OAuth responses.
    return JSONResponse(status_code=500, content={'detail': 'Operation failed; check server configuration'})

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/')
def root():
    return {'message': 'Smart Email Assistant API', 'docs': '/docs'}

from fastapi import Depends
from app.security import require_owner
from app.database.db import init_db

@app.post('/admin/database/initialize', dependencies=[Depends(require_owner)], tags=['Administration'])
def initialize_database():
    """Create missing tables after setting DATABASE_URL. Does not import local email data."""
    init_db()
    return {'status': 'initialized'}
