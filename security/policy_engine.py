from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .audit import record_audit
from .permissions import ALLOWED_ACTIONS, ActionRequest, PermissionDecision, RESTRICTED_ACTIONS
from .trust_levels import MODE_CAPABILITIES, TrustLevel, get_security_mode


class PolicyEngine:
    def evaluate(self, request: ActionRequest) -> PermissionDecision:
        mode = get_security_mode()
        action = (request.action or "").strip().lower()

        if not action:
            decision = PermissionDecision(False, False, mode.value, "missing action", mode.value)
            record_audit("policy_denied", {"request": asdict(request), "decision": asdict(decision)})
            return decision

        if mode == TrustLevel.LOCKED:
            decision = PermissionDecision(False, False, mode.value, "runtime locked", mode.value)
            record_audit("policy_denied", {"request": asdict(request), "decision": asdict(decision)})
            return decision

        if action in RESTRICTED_ACTIONS:
            decision = PermissionDecision(False, False, mode.value, "restricted action", mode.value)
            record_audit("policy_denied", {"request": asdict(request), "decision": asdict(decision)})
            return decision

        profile = ALLOWED_ACTIONS.get(action)
        if not profile:
            decision = PermissionDecision(False, False, mode.value, "action not allowlisted", mode.value)
            record_audit("policy_denied", {"request": asdict(request), "decision": asdict(decision)})
            return decision

        capability = profile.get("capability", "read")
        if capability not in MODE_CAPABILITIES[mode]:
            decision = PermissionDecision(False, False, mode.value, f"{mode.value} mode lacks {capability}", mode.value)
            record_audit("policy_denied", {"request": asdict(request), "decision": asdict(decision)})
            return decision

        risk = (request.risk or profile.get("risk", "low")).lower()
        requires_confirmation = bool(request.requires_confirmation or risk in {"medium", "high", "critical"} or action in {"type_text", "open_application", "open_website", "take_screenshot"})
        allowed = True
        reason = "allowed"
        if request.source in {"screen", "web", "clipboard"} and risk in {"medium", "high", "critical"}:
            requires_confirmation = True
            reason = "confirmation required for untrusted source"

        decision = PermissionDecision(allowed, requires_confirmation, mode.value, reason, mode.value)
        record_audit("policy_approved", {"request": asdict(request), "decision": asdict(decision)})
        return decision

    def describe(self) -> dict[str, Any]:
        mode = get_security_mode()
        return {
            "mode": mode.value,
            "capabilities": sorted(MODE_CAPABILITIES[mode]),
            "allowlisted_actions": sorted(ALLOWED_ACTIONS.keys()),
            "restricted_actions": sorted(RESTRICTED_ACTIONS),
        }


_ENGINE = PolicyEngine()


def get_policy_engine() -> PolicyEngine:
    return _ENGINE
