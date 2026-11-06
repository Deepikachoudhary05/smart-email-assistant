"""Single-owner API access. The owner key must never be put in a URL."""
import os
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cryptography.fernet import Fernet

bearer = HTTPBearer(auto_error=False)

def require_owner(auth: HTTPAuthorizationCredentials | None = Depends(bearer)):
    expected = os.getenv('APP_API_KEY', '')
    if len(expected) < 32:
        raise HTTPException(503, 'Owner authentication is not configured')
    if not auth or auth.scheme.lower() != 'bearer' or not secrets.compare_digest(auth.credentials, expected):
        raise HTTPException(401, 'Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    return 'owner'

def cipher():
    key = os.getenv('TOKEN_ENCRYPTION_KEY', '')
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        raise HTTPException(503, 'Token encryption is not configured') from None
