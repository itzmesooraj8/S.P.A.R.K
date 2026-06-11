"""Authentication helpers and DTOs for the S.P.A.R.K. API with Database-Backed Auth."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from security.user_db import user_db_manager

logger = logging.getLogger("SPARK_AUTH")

DEFAULT_OPERATOR_USERNAME = "operator"
TOKEN_VERSION = "spk1"


class AuthLoginRequest(BaseModel):
    username: str = DEFAULT_OPERATOR_USERNAME
    password: str | None = None
    bootstrap_token: str | None = Field(default=None, description="Existing operator token for local bootstrap.")
    mfa_code: str | None = Field(default=None, description="TOTP MFA verification code.")


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class AuthenticatedUser(BaseModel):
    username: str
    role: str
    permissions: list[str] = Field(default_factory=list)


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: AuthenticatedUser


@dataclass(frozen=True, slots=True)
class AuthTokenPayload:
    subject: str
    role: str
    permissions: tuple[str, ...]
    token_type: Literal["access", "refresh"]
    expires_at: int
    issued_at: int
    jwt_id: str


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def get_static_operator_token() -> str:
    return os.getenv("SPARK_ACCESS_TOKEN") or os.getenv("SPARK_TOKEN", "change-this-token")


def get_signing_secret() -> str:
    return os.getenv("SPARK_AUTH_SECRET") or get_static_operator_token()


def get_access_token_ttl_seconds() -> int:
    try:
        return max(60, int(os.getenv("SPARK_ACCESS_TOKEN_TTL_SECONDS", "3600")))
    except Exception:
        return 3600


def get_refresh_token_ttl_seconds() -> int:
    try:
        return max(300, int(os.getenv("SPARK_REFRESH_TOKEN_TTL_SECONDS", "86400")))
    except Exception:
        return 86400


def get_operator_username() -> str:
    return os.getenv("SPARK_OPERATOR_USERNAME", DEFAULT_OPERATOR_USERNAME).strip() or DEFAULT_OPERATOR_USERNAME


def _get_operator_role() -> str:
    return os.getenv("SPARK_OPERATOR_ROLE", "operator").strip() or "operator"


def _get_operator_permissions() -> list[str]:
    raw = os.getenv("SPARK_OPERATOR_PERMISSIONS", "chat,status,tools,admin")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _bootstrap_token_matches(candidate: str | None) -> bool:
    configured = get_static_operator_token()
    if not candidate or not configured or configured == "change-this-token":
        return False
    return secrets.compare_digest(candidate, configured)


def credentials_are_valid(login: AuthLoginRequest) -> bool:
    """Check credentials using user database, falling back to bootstrap token if configured."""
    # 1. Check user database first
    user = user_db_manager.authenticate_user(login.username, login.password)
    if user:
        # If user has MFA enabled, check MFA code
        if user.get("mfa_enabled") == 1:
            if not login.mfa_code:
                logger.warning("MFA required for user: %s", login.username)
                return False
            import pyotp
            totp = pyotp.TOTP(user.get("mfa_secret") or "")
            if not totp.verify(login.mfa_code):
                logger.warning("Invalid MFA code for user: %s", login.username)
                return False
        return True

    # 2. Bootstrap fallback for initial install / CLI bootstrap
    if login.username == get_operator_username():
        # Auto-seed the operator user in SQLite if it does not exist yet
        db_user = user_db_manager.get_user(login.username)
        if not db_user:
            default_pw = os.getenv("SPARK_OPERATOR_PASSWORD") or os.getenv("SPARK_TOKEN") or "change-this-password"
            user_db_manager.create_user(
                login.username, default_pw, role=_get_operator_role(), permissions=_get_operator_permissions()
            )
            # Recheck
            if user_db_manager.authenticate_user(login.username, login.password):
                return True

        # Check bootstrap token directly if provided
        return _bootstrap_token_matches(login.bootstrap_token)

    return False


def _sign(payload: str) -> str:
    digest = hmac.new(get_signing_secret().encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _encode_token(payload: dict[str, Any]) -> str:
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _sign(encoded_payload)
    return f"{TOKEN_VERSION}.{encoded_payload}.{signature}"


def issue_token_pair(user: AuthenticatedUser | None = None) -> AuthTokenResponse:
    """Generate access and refresh tokens, assigning correct roles and permissions."""
    if user is None:
        # Default to operator if none specified
        user = AuthenticatedUser(
            username=get_operator_username(),
            role=_get_operator_role(),
            permissions=_get_operator_permissions(),
        )

    now = int(time.time())
    access_ttl = get_access_token_ttl_seconds()
    refresh_ttl = get_refresh_token_ttl_seconds()

    common = {
        "sub": user.username,
        "role": user.role,
        "permissions": user.permissions,
        "iat": now,
    }
    access_token = _encode_token({**common, "typ": "access", "exp": now + access_ttl, "jti": uuid.uuid4().hex})
    refresh_token = _encode_token({**common, "typ": "refresh", "exp": now + refresh_ttl, "jti": uuid.uuid4().hex})
    return AuthTokenResponse(access_token=access_token, refresh_token=refresh_token, expires_in=access_ttl, user=user)


def validate_signed_token(token: str, expected_type: Literal["access", "refresh"] = "access") -> AuthTokenPayload | None:
    """Parse and cryptographically verify a signed token, checking expiration and blacklist status."""
    try:
        version, encoded_payload, signature = token.split(".", 2)
    except ValueError:
        return None

    if version != TOKEN_VERSION or not secrets.compare_digest(signature, _sign(encoded_payload)):
        return None

    try:
        payload = json.loads(_b64url_decode(encoded_payload))
    except Exception:
        return None

    if payload.get("typ") != expected_type:
        return None

    expires_at = int(payload.get("exp") or 0)
    if expires_at <= int(time.time()):
        return None

    jti = str(payload.get("jti") or "")
    if user_db_manager.is_token_blacklisted(jti):
        logger.warning("Rejected blacklisted token JTI: %s", jti)
        return None

    return AuthTokenPayload(
        subject=str(payload.get("sub") or ""),
        role=str(payload.get("role") or ""),
        permissions=tuple(str(item) for item in payload.get("permissions") or ()),
        token_type=expected_type,
        expires_at=expires_at,
        issued_at=int(payload.get("iat") or 0),
        jwt_id=jti,
    )


def validate_access_token(token: str) -> AuthTokenPayload | None:
    return validate_signed_token(token, expected_type="access")


def static_operator_token_matches(token: str) -> bool:
    """Matches the bootstrap/static token. Allowed only for backward-compatible developer console/CLI."""
    static_token = get_static_operator_token()
    if not token or not static_token:
        return False
    return secrets.compare_digest(token, static_token)


def validate_access_token_or_static(token: str) -> bool:
    """Verify access token via database/blacklist first, falling back to static developer token."""
    if validate_access_token(token):
        return True
    return static_operator_token_matches(token)


def token_has_permission(token: str, permission: str) -> bool:
    """Enforces fine-grained permission mapping for RBAC access control."""
    if static_operator_token_matches(token):
        return True

    payload = validate_access_token(token)
    if not payload:
        return False

    permissions = set(payload.permissions)
    return "admin" in permissions or permission in permissions


from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


async def verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """FastAPI dependency to verify bearer token or static operator token."""
    if not credentials or credentials.scheme.lower() != "bearer" or not validate_access_token_or_static(credentials.credentials):
        raise HTTPException(status_code=401, detail="unauthorized")

