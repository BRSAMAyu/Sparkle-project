"""
Access Control Middleware
Ensures that only authorized users can access certain endpoints
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token

security = HTTPBearer()

async def verify_token(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifies the provided token using JWT validation
    """
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    
    token = credentials.credentials
    try:
        decode_token(token, expected_type="access")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token
