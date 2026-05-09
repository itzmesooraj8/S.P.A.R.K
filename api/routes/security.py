from __future__ import annotations

from fastapi import APIRouter

from security.audit import get_recent_audit
from security.policy_engine import get_policy_engine
from security.trust_levels import get_security_mode


router = APIRouter()


@router.get("/api/security/status")
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


@router.get("/api/security/audit/recent")
async def security_audit_recent(limit: int = 25):
    return {"items": get_recent_audit(limit=limit)}
