"""Conversation Manager — Multi-turn state, confirmations, human-friendly responses."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

logger = logging.getLogger("spark.conversation.manager")


class ConversationState:
    IDLE = "idle"
    WAITING_CONFIRMATION = "waiting_confirmation"
    WAITING_INPUT = "waiting_input"


class ConversationManager:
    """
    Manages multi-turn conversations with state.

    Handles:
    - Confirmation flows (yes/no)
    - Follow-up questions
    - Human-friendly response formatting
    - Context preservation across turns
    """

    def __init__(self) -> None:
        self._state = ConversationState.IDLE
        self._pending_action: dict[str, Any] | None = None
        self._context: dict[str, Any] = {}
        self._history: list[dict[str, Any]] = []
        self._on_confirm: Callable | None = None
        self._on_cancel: Callable | None = None

    def format_response(self, result: dict[str, Any], user_input: str = "") -> str:
        """Convert internal result dict to human-friendly response."""
        action = result.get("action", "")
        reply = result.get("reply", "")

        if action == "confirm_needed":
            return self._format_confirmation(result)

        if action == "open":
            return self._format_action_result(result, "Opened")

        if action == "search":
            return self._format_search_result(result)

        if action == "memory":
            return self._format_memory_result(result)

        if action == "plan":
            return self._format_plan_result(result)

        if action == "dashboard":
            return reply

        if action == "conversation":
            return reply

        if action == "error":
            return f"I encountered an issue: {reply}"

        if reply:
            return reply

        return f"I received your message. How can I help?"

    def _format_confirmation(self, result: dict[str, Any]) -> str:
        action = result.get("pending_action", "this action")
        reason = result.get("reason", "")
        self._state = ConversationState.WAITING_CONFIRMATION
        self._pending_action = result
        return f"{action} requires permission. Would you like me to proceed? (yes/no)"

    def _format_action_result(self, result: dict[str, Any], verb: str) -> str:
        data = result.get("result", {})
        if isinstance(data, dict):
            if data.get("success"):
                return f"Done. {verb} successfully."
            else:
                error = data.get("error", "unknown error")
                return f"I couldn't complete that: {error}"
        return f"{verb} completed."

    def _format_search_result(self, result: dict[str, Any]) -> str:
        data = result.get("result", {})
        if isinstance(data, dict) and data.get("success"):
            return f"Here's what I found: {data.get('result', 'No results')}"
        return "I searched but couldn't find results."

    def _format_memory_result(self, result: dict[str, Any]) -> str:
        data = result.get("result", {})
        if isinstance(data, dict):
            results = data.get("results", [])
            if results:
                return f"I remember: {results[0]}"
        return "I don't have that in my memory yet."

    def _format_plan_result(self, result: dict[str, Any]) -> str:
        steps = result.get("steps", 0)
        goal_id = result.get("goal_id", "")
        return f"Goal created with {steps} steps. I'll work on this."

    def handle_confirmation(self, user_input: str) -> dict[str, Any] | None:
        """Handle yes/no confirmation responses."""
        if self._state != ConversationState.WAITING_CONFIRMATION:
            return None

        lower = user_input.lower().strip()
        if lower in ("yes", "y", "yeah", "sure", "go ahead", "proceed", "do it"):
            self._state = ConversationState.IDLE
            action = self._pending_action
            self._pending_action = None
            return {"confirmed": True, "action": action}

        if lower in ("no", "n", "nah", "cancel", "stop", "nevermind"):
            self._state = ConversationState.IDLE
            self._pending_action = None
            return {"confirmed": False, "action": None}

        return None

    def is_waiting_confirmation(self) -> bool:
        return self._state == ConversationState.WAITING_CONFIRMATION

    def cancel_pending(self) -> None:
        self._state = ConversationState.IDLE
        self._pending_action = None

    def record_turn(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {},
        })
        if len(self._history) > 50:
            self._history = self._history[-50:]

    def get_context(self) -> dict[str, Any]:
        return dict(self._context)

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def state(self) -> str:
        return self._state
