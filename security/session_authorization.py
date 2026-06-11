"""Session-based and Role-based authorization for sensitive S.P.A.R.K. tool execution."""

from __future__ import annotations

import asyncio
import contextvars
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("SPARK_SESSION_AUTH")

# ContextVar to hold the active user context across async frames
active_user_var: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("active_user", default=None)

SENSITIVE_TOOLS = {
    "control_device",
    "execute_python",
    "generate_workspace",
    "get_network_connections",
    "get_weather",
    "open_app",
    "open_url",
    "read_region",
    "read_screen",
    "run_swarm_task",
    "run_swarm_workflow",
    "run_swarm_router",
    "verify_sandbox_metrics",
    "scene_leaving",
    "scene_arriving",
    "scene_good_night",
}

# Mapping sensitive tools to their required minimum roles
TOOL_ROLE_REQUIREMENTS = {
    # Admin tools (highest authorization required)
    "execute_python": "admin",
    "generate_workspace": "admin",
    "run_swarm_task": "admin",
    "run_swarm_workflow": "admin",
    "run_swarm_router": "admin",
    "verify_sandbox_metrics": "admin",
    # Operator tools
    "control_device": "operator",
    "scene_leaving": "operator",
    "scene_arriving": "operator",
    "scene_good_night": "operator",
    "open_app": "operator",
    "open_url": "operator",
    "read_screen": "operator",
    "read_region": "operator",
    "get_clipboard": "operator",
    "get_network_connections": "operator",
    # Viewer tools
    "get_time": "viewer",
    "get_weather": "viewer",
    "get_news": "viewer",
    "get_system_stats": "viewer",
    "archive_session_state": "viewer",
}

_ephemeral_approval_until = 0.0


@dataclass(slots=True)
class SessionAuthResult:
    allowed: bool
    reason: str = ""
    session_token: str = ""


def _get_env_token() -> str:
    return (os.getenv("SPARK_SESSION_TOKEN") or os.getenv("SPARK_AUTH_TOKEN") or "").strip()


def _get_session_ttl_seconds() -> int:
    try:
        return max(1, int(os.getenv("SPARK_SESSION_TOKEN_TTL_SECONDS", "300")))
    except Exception:
        return 300


def _get_expiry_epoch() -> float:
    raw = (os.getenv("SPARK_SESSION_TOKEN_EXPIRES_AT") or os.getenv("SPARK_SESSION_EXPIRES_AT") or "").strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except Exception:
        return 0.0


def _token_is_fresh() -> bool:
    token = _get_env_token()
    if not token:
        return False

    expiry = _get_expiry_epoch()
    if expiry and time.time() > expiry:
        return False

    return True


def _session_context_is_valid() -> bool:
    context = (os.getenv("SPARK_SESSION_CONTEXT") or os.getenv("SPARK_AUTH_CONTEXT") or "").strip().lower()
    return context in {"authorized", "trusted", "validated", "confirmed"}


def validate_session_auth() -> SessionAuthResult:
    if _session_context_is_valid():
        return SessionAuthResult(True, reason="session_context", session_token="context")

    token = _get_env_token()
    if token and _token_is_fresh():
        return SessionAuthResult(True, reason="session_token", session_token=token)

    return SessionAuthResult(False, reason="missing_or_expired_session_token")


def _prompt_for_confirmation(tool_name: str) -> bool:
    prompt = f"[y/N]: Execute {tool_name}? "
    try:
        response = input(prompt).strip().lower()
    except EOFError:
        return False
    return response in {"y", "yes"}


def authorize_sensitive_tool(
    tool_name: str, tool_args: dict[str, Any] | None = None, prompt: bool = True
) -> SessionAuthResult:
    tool_name = str(tool_name or "").strip()
    if tool_name not in SENSITIVE_TOOLS:
        return SessionAuthResult(True, reason="not_sensitive")

    # 1. Enforce RBAC context validation if active user is bound
    user = active_user_var.get()
    if user:
        role = user.get("role", "viewer").strip().lower()
        permissions = set(user.get("permissions") or [])
        required_role = TOOL_ROLE_REQUIREMENTS.get(tool_name, "viewer")

        # Admin bypass
        if "admin" in permissions or role == "admin":
            return SessionAuthResult(True, reason="role_authorized_admin")

        # Admin tool validation
        if required_role == "admin":
            logger.warning("RBAC Blocked: user '%s' (role: %s) requested admin-only tool: %s", user.get("username"), role, tool_name)
            return SessionAuthResult(False, reason="admin_role_required")

        # Operator tool validation
        if required_role == "operator":
            if role != "operator" and "operator" not in permissions:
                logger.warning("RBAC Blocked: user '%s' (role: %s) requested operator tool: %s", user.get("username"), role, tool_name)
                return SessionAuthResult(False, reason="operator_role_required")

        return SessionAuthResult(True, reason="role_authorized")

    # 2. Fallback to CLI human-in-loop and legacy environment authorizations
    global _ephemeral_approval_until
    now = time.time()
    if _ephemeral_approval_until > now:
        return SessionAuthResult(True, reason="ephemeral_confirmation")

    auth = validate_session_auth()
    if auth.allowed:
        return auth

    if prompt and os.getenv("SPARK_HITL_AUTH_REQUIRED", "1").strip().lower() in {"1", "true", "yes", "on"}:
        if _prompt_for_confirmation(tool_name):
            _ephemeral_approval_until = now + _get_session_ttl_seconds()
            logger.info("Human-in-loop confirmation granted for %s", tool_name)
            return SessionAuthResult(True, reason="human_confirmed")

    return SessionAuthResult(False, reason=auth.reason or "confirmation_denied")


async def authorize_sensitive_tool_async(
    tool_name: str, tool_args: dict[str, Any] | None = None, prompt: bool = True
) -> SessionAuthResult:
    # Explicitly carry the active context to the execution thread
    ctx = contextvars.copy_context()
    return await asyncio.to_thread(ctx.run, authorize_sensitive_tool, tool_name, tool_args, prompt)
