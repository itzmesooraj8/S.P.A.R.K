from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import token_has_permission, validate_access_token_or_static
from security.audit import get_recent_audit
from security.policy_engine import get_policy_engine
from security.trust_levels import get_security_mode


router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


async def require_security_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> None:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="unauthorized")

    token = credentials.credentials
    if not validate_access_token_or_static(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    if not token_has_permission(token, "admin"):
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/api/security/status", dependencies=[Depends(require_security_admin)])
async def security_status():
    engine = get_policy_engine()
    recent = get_recent_audit(limit=12)
    blocked = [item for item in recent if item.get("event") in {"policy_denied", "action_blocked", "action_confirmation_required"}]
    return {
        "mode": get_security_mode().value,
        "policy": engine.describe(),
        "recent_audit_count": len(recent),
        "blocked_count": len(blocked),
        "recent_events": [item.get("event") for item in recent[-8:]],
    }


@router.get("/api/security/audit/recent", dependencies=[Depends(require_security_admin)])
async def security_audit_recent(limit: int = 25):
    return {"items": get_recent_audit(limit=limit)}
