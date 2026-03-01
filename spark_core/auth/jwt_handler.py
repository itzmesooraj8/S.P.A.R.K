"""
SPARK Auth — JWT Access + Refresh Tokens, bcrypt, RBAC
"""
import os
import time
import secrets
import hashlib
from typing import Dict, Any, Optional

import jwt
import bcrypt

# ── Secret resolution ─────────────────────────────────────────────────────────
# Loaded at import time; override via environment variable SPARK_JWT_SECRET
_SECRET_KEY: str = os.getenv(
    "SPARK_JWT_SECRET",
    "SPARK_SOVEREIGN_CORE_SECRET_DO_NOT_SHARE_IN_PRODUCTION"
)
ALGORITHM = "HS256"

ACCESS_TOKEN_TTL  = int(os.getenv("SPARK_ACCESS_TTL",  "3600"))    # 1 hour
REFRESH_TOKEN_TTL = int(os.getenv("SPARK_REFRESH_TTL", "604800"))  # 7 days

# ── In-memory refresh token store (replace with Redis in prod) ────────────────
_refresh_store: Dict[str, Dict[str, Any]] = {}  # token_hash → {sub, role, exp}

# ── Role hierarchy ────────────────────────────────────────────────────────────
ROLE_LEVELS = {
    "VIEWER":    10,
    "OPERATOR":  20,
    "ADMIN":     30,
    "ROOT":      40,
}

# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta_secs: int = ACCESS_TOKEN_TTL) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": time.time() + expires_delta_secs, "type": "access"})
    return jwt.encode(to_encode, _SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(sub: str, role: str) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    exp = time.time() + REFRESH_TOKEN_TTL
    _refresh_store[token_hash] = {"sub": sub, "role": role, "exp": exp}
    return raw  # return raw; store only the hash


def create_token_pair(sub: str, role: str) -> Dict[str, str]:
    """Create both access + refresh tokens in one call."""
    access = create_access_token({"sub": sub, "role": role})
    refresh = create_refresh_token(sub, role)
    return {"access_token": access, "refresh_token": refresh, "type": "bearer"}


# ── Token verification ────────────────────────────────────────────────────────

def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}


def refresh_access_token(refresh_raw: str) -> Optional[Dict[str, str]]:
    """Exchange a valid refresh token for a new access token."""
    token_hash = hashlib.sha256(refresh_raw.encode()).hexdigest()
    entry = _refresh_store.get(token_hash)
    if not entry or entry["exp"] < time.time():
        _refresh_store.pop(token_hash, None)
        return None
    # Rotate: issue new access token
    access = create_access_token({"sub": entry["sub"], "role": entry["role"]})
    return {"access_token": access, "type": "bearer"}


def revoke_refresh_token(refresh_raw: str) -> bool:
    token_hash = hashlib.sha256(refresh_raw.encode()).hexdigest()
    return _refresh_store.pop(token_hash, None) is not None


# ── RBAC helpers ─────────────────────────────────────────────────────────────

def verify_role(payload: dict, required_role: str) -> bool:
    """True if the token holder's role is >= required_role in hierarchy."""
    user_level = ROLE_LEVELS.get(payload.get("role", ""), 0)
    req_level  = ROLE_LEVELS.get(required_role, 99)
    return user_level >= req_level

def verify_root(payload: dict) -> bool:
    return verify_role(payload, "ROOT")

def verify_admin(payload: dict) -> bool:
    return verify_role(payload, "ADMIN")

def verify_operator(payload: dict) -> bool:
    return verify_role(payload, "OPERATOR")


# ── FastAPI dependency ────────────────────────────────────────────────────────

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer_scheme = HTTPBearer(auto_error=False)

def require_auth(min_role: str = "OPERATOR"):
    """Returns a FastAPI dependency that validates the bearer token."""
    def _dep(credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme)):
        if not credentials:
            raise HTTPException(status_code=401, detail="Missing Authorization header")
        payload = decode_token(credentials.credentials)
        if "error" in payload:
            raise HTTPException(status_code=401, detail=payload["error"])
        if not verify_role(payload, min_role):
            raise HTTPException(status_code=403, detail=f"Requires {min_role} role or higher")
        return payload
    return _dep
