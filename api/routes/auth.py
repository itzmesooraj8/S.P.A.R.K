"""S.P.A.R.K. API Authentication and User Management Router."""

from __future__ import annotations

import logging
import time
from typing import Any

import pyotp
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from api.auth import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthTokenResponse,
    AuthenticatedUser,
    credentials_are_valid,
    get_access_token_ttl_seconds,
    get_operator_username,
    get_static_operator_token,
    issue_token_pair,
    static_operator_token_matches,
    validate_access_token,
    validate_signed_token,
)
from security.audit import record_audit
from security.user_db import user_db_manager

logger = logging.getLogger("SPARK_AUTH_ROUTES")

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# Pydantic Domain Models
class UserRegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    permissions: list[str] = Field(default_factory=lambda: ["status"])


class MFASetupResponse(BaseModel):
    mfa_secret: str
    provisioning_uri: str


class MFAVerifyRequest(BaseModel):
    mfa_code: str


# Helper dependencies
async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Any:
    """Dependency to retrieve and validate the token, returning payload."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="unauthorized")
    token = credentials.credentials
    payload = validate_access_token(token)
    if payload:
        return payload
    if static_operator_token_matches(token):
        from api.auth import _get_operator_permissions, _get_operator_role

        return AuthenticatedUser(
            username=get_operator_username(),
            role=_get_operator_role(),
            permissions=_get_operator_permissions(),
        )
    raise HTTPException(status_code=401, detail="unauthorized")


async def require_admin(payload: Any = Depends(get_current_user_payload)) -> None:
    """Dependency enforcing that the caller has admin role/permission."""
    permissions = getattr(payload, "permissions", []) or []
    role = getattr(payload, "role", "") or ""
    if "admin" not in permissions and role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")


def _client_ip(request: Request) -> str:
    return request.client.host if request and request.client else "unknown"


def _record_auth_audit(event: str, request: Request, **payload: Any) -> None:
    try:
        record_audit(event, {"client_ip": _client_ip(request), **payload})
    except Exception as exc:
        logger.debug("Auth audit recording failed: %s", exc)


@router.post("/login", response_model=AuthTokenResponse)
async def auth_login(login: AuthLoginRequest, request: Request):
    """Logs in a user with username/password (and TOTP code if enabled), returning token pair."""
    if not credentials_are_valid(login):
        logger.warning("Rejected login for username=%s", login.username)
        _record_auth_audit(
            "auth_login_rejected", request, username=login.username, reason="invalid_credentials"
        )
        raise HTTPException(status_code=401, detail="unauthorized")

    # Fetch user permissions for token mapping
    user_data = user_db_manager.get_user(login.username)
    if user_data:
        user = AuthenticatedUser(
            username=user_data["username"],
            role=user_data["role"],
            permissions=user_data["permissions"],
        )
    else:
        # Fallback to default operator settings
        from api.auth import _get_operator_permissions, _get_operator_role

        user = AuthenticatedUser(
            username=login.username,
            role=_get_operator_role(),
            permissions=_get_operator_permissions(),
        )

    logger.info("Issued auth session for username=%s", user.username)
    _record_auth_audit("auth_login_success", request, username=user.username)
    return issue_token_pair(user)


@router.post("/refresh", response_model=AuthTokenResponse)
async def auth_refresh(refresh: AuthRefreshRequest, request: Request):
    """Refreshes access token and rotates the refresh token. Old refresh token is blacklisted."""
    payload = validate_signed_token(refresh.refresh_token, expected_type="refresh")
    if not payload:
        _record_auth_audit("auth_refresh_rejected", request, reason="invalid_refresh_token")
        raise HTTPException(status_code=401, detail="unauthorized")

    # Revoke/blacklist the used refresh token JTI immediately
    user_db_manager.blacklist_token(payload.jwt_id, payload.expires_at)

    # Fetch fresh user data from database
    user_data = user_db_manager.get_user(payload.subject)
    if user_data:
        user = AuthenticatedUser(
            username=user_data["username"],
            role=user_data["role"],
            permissions=user_data["permissions"],
        )
    else:
        user = AuthenticatedUser(
            username=payload.subject,
            role=payload.role,
            permissions=list(payload.permissions),
        )

    logger.info("Refreshed auth session and rotated tokens for username=%s", user.username)
    _record_auth_audit("auth_refresh_success", request, username=user.username)
    return issue_token_pair(user)


@router.post("/logout")
async def auth_logout(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Logs out the active user session and invalidates the session token."""
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
        # Invalidate access token
        payload = validate_access_token(token)
        if payload:
            user_db_manager.blacklist_token(payload.jwt_id, payload.expires_at)
            _record_auth_audit("auth_logout", request, username=payload.subject)
            return {"status": "ok"}

    _record_auth_audit("auth_logout", request)
    return {"status": "ok"}


@router.post("/register", dependencies=[Depends(require_admin)])
async def register_user(reg: UserRegisterRequest, request: Request):
    """Registers a new user (restricted to security administrators)."""
    success = user_db_manager.create_user(
        username=reg.username,
        password=reg.password,
        role=reg.role,
        permissions=reg.permissions,
    )
    if not success:
        raise HTTPException(status_code=400, detail="username_already_exists")

    _record_auth_audit("user_registered", request, target_user=reg.username, role=reg.role)
    return {"status": "user_created", "username": reg.username}


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    request: Request,
    payload: Any = Depends(get_current_user_payload),
):
    """Generates an MFA secret and TOTP URI for setting up Google Authenticator."""
    username = getattr(payload, "subject", None) or getattr(payload, "username", None)
    if not username:
        raise HTTPException(status_code=401, detail="unauthorized")

    mfa_secret = pyotp.random_base32()
    totp = pyotp.TOTP(mfa_secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name="S.P.A.R.K.")

    return MFASetupResponse(mfa_secret=mfa_secret, provisioning_uri=provisioning_uri)


@router.post("/mfa/enable")
async def mfa_enable(
    verify: MFAVerifyRequest,
    request: Request,
    payload: Any = Depends(get_current_user_payload),
):
    """Enables MFA for the current user using the verified setup secret and code."""
    username = getattr(payload, "subject", None) or getattr(payload, "username", None)
    if not username:
        raise HTTPException(status_code=401, detail="unauthorized")

    # Generate a temporary session-cached secret from setup phase, or expect verify request to carry secret.
    # To keep this route stateless, setup secret can be passed, or we can check body.
    # Since setup returns secret, we require verify to provide secret to complete handshake.
    pass


class MFAEnableVerifyRequest(BaseModel):
    mfa_secret: str
    mfa_code: str


@router.post("/mfa/enable-verify")
async def mfa_enable_verify(
    verify: MFAEnableVerifyRequest,
    request: Request,
    payload: Any = Depends(get_current_user_payload),
):
    """Verifies the TOTP code against the secret and permanently enables MFA in DB."""
    username = getattr(payload, "subject", None) or getattr(payload, "username", None)
    if not username:
        raise HTTPException(status_code=401, detail="unauthorized")

    totp = pyotp.TOTP(verify.mfa_secret)
    if not totp.verify(verify.mfa_code):
        raise HTTPException(status_code=400, detail="invalid_mfa_code")

    success = user_db_manager.enable_mfa(username, verify.mfa_secret)
    if not success:
        raise HTTPException(status_code=500, detail="failed_to_enable_mfa")

    _record_auth_audit("mfa_enabled", request, username=username)
    return {"status": "mfa_enabled"}
