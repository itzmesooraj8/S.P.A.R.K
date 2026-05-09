from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from .audit import record_audit
from .permissions import ActionRequest
from .policy_engine import get_policy_engine
from .content_sanitizer import sanitize_for_llm


def guard_action(action: str, *, source: str = "voice", risk: str = "low", requires_confirmation: bool = False, args: Any = None, payload: dict[str, Any] | None = None) -> tuple[bool, str, Any]:
    request = ActionRequest(
        action=action,
        source=source,
        risk=risk,
        requires_confirmation=requires_confirmation,
        args=args,
        payload=payload or {},
    )
    decision = get_policy_engine().evaluate(request)

    if not decision.allowed:
        message = f"Security policy blocked {action}: {decision.reason}."
        record_audit("action_blocked", {"request": asdict(request), "decision": asdict(decision)})
        return False, message, None

    if decision.requires_confirmation:
        message = f"Confirmation required before {action}."
        record_audit("action_confirmation_required", {"request": asdict(request), "decision": asdict(decision)})
        return False, message, None

    record_audit("action_allowed", {"request": asdict(request), "decision": asdict(decision)})
    return True, "allowed", request


def guard_tool_function(action: str, fn: Callable[[Any], Any], *, source: str = "task", risk: str | None = None, requires_confirmation: bool = False) -> Callable[[Any], Any]:
    def _wrapped(arg: Any = None) -> Any:
        ok, message, _request = guard_action(
            action,
            source=source,
            risk=risk or "low",
            requires_confirmation=requires_confirmation,
            args=arg,
            payload={"source": source},
        )
        if not ok:
            return message
        if isinstance(arg, str):
            arg = sanitize_for_llm(arg, max_length=1200)
        return fn(arg)

    return _wrapped
