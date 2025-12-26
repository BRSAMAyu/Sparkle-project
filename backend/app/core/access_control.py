"""
Access Control Middleware
Ensures that only authorized users can access certain endpoints
"""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
import secrets

security = HTTPBearer()

async def verify_token(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifies the provided token against the secret key using timing-safe comparison
    """
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    
    token = credentials.credentials
    # Use timing-safe comparison to prevent timing attacks
    if not secrets.compare_digest(token, settings.SECRET_KEY):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token
