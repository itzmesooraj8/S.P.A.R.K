import time
import jwt # PyJWT Library
from typing import Dict, Any

# In production this must be loaded from a secure file!
SECRET_KEY = "SPARK_SOVEREIGN_CORE_SECRET_DO_NOT_SHARE"
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta_secs: int = 3600) -> str:
    """Generate a JWT token for the device."""
    to_encode = data.copy()
    expire = time.time() + expires_delta_secs
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Dict[str, Any]:
    """Verify JWT limits."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}

# Example role checker for OS Core
def verify_root(payload: dict) -> bool:
    return payload.get("role") == "ROOT"
