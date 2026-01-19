#!/usr/bin/env python3
import jwt
import time
import os
import uuid
from typing import Optional

# This script generates a development JWT for testing the Sparkle Gateway.
# It uses the JWT_SECRET from the .env file if available.

def get_jwt_secret() -> str:
    # Try to find .env file
    env_paths = ['.env', 'backend/gateway/.env', 'backend/.env']
    for path in env_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                for line in f:
                    if line.startswith('JWT_SECRET='):
                        return line.split('=', 1)[1].strip()
    
    # Fallback to a common dev secret if not found
    return "dev-secret-key"

def generate_token(user_id: Optional[str] = None, secret: Optional[str] = None):
    if not user_id:
        user_id = str(uuid.uuid4())
    
    if not secret:
        secret = get_jwt_secret()
        
    print(f"Using JWT_SECRET: {secret[:4]}...{secret[-4:] if len(secret) > 8 else ''}")
    
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + 3600,  # 1 hour
        "iat": int(time.time()),
        "type": "access",
        "is_admin": False
    }
    
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, user_id

if __name__ == "__main__":
    # Check if pyjwt is installed
    try:
        import jwt
    except ImportError:
        print("Error: PyJWT not installed. Run 'pip install pyjwt'")
        exit(1)

    token, uid = generate_token()
    print("\n--- TEST TOKEN GENERATED ---")
    print(f"User ID: {uid}")
    print(f"Token: {token}")
    print("\nRun the test script with:")
    print(f"export TEST_JWT_TOKEN={token}")
    print("python3 scripts/test_ws_ticket.py")
    print("----------------------------\n")
