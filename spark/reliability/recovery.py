"""Failure Recovery — Diagnoses failures and suggests recovery actions."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.reliability.recovery")


class FailureRecord:
    def __init__(self, action: str, error: str, context: dict[str, Any] | None = None):
        self.action = action
        self.error = error
        self.context = context or {}
        self.timestamp = time.time()
        self.recovery_attempted = False
        self.recovery_succeeded = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "error": self.error,
            "timestamp": self.timestamp,
            "recovery_attempted": self.recovery_attempted,
            "recovery_succeeded": self.recovery_succeeded,
        }


class FailureRecovery:
    """
    Diagnoses failures and suggests recovery actions.

    Can it recover from UI changes?
    Can it explain failures?
    Can it self-correct?
    """

    def __init__(self) -> None:
        self._failures: list[FailureRecord] = []
        self._recovery_strategies: dict[str, list[dict[str, Any]]] = {
            "element_not_found": [
                {"action": "wait_and_retry", "description": "Wait for page to load and retry"},
                {"action": "scroll_to_element", "description": "Scroll to find the element"},
                {"action": "take_screenshot", "description": "Capture screen for analysis"},
                {"action": "try_alternative_selector", "description": "Use different CSS selector"},
            ],
            "timeout": [
                {"action": "increase_timeout", "description": "Increase timeout and retry"},
                {"action": "check_network", "description": "Verify network connectivity"},
                {"action": "reload_page", "description": "Reload and try again"},
            ],
            "permission_denied": [
                {"action": "request_permission", "description": "Ask user for permission"},
                {"action": "try_alternative", "description": "Try a different approach"},
            ],
            "network_error": [
                {"action": "check_connection", "description": "Verify network"},
                {"action": "retry_later", "description": "Wait and retry"},
                {"action": "use_cache", "description": "Use cached data if available"},
            ],
            "ocr_failed": [
                {"action": "try_different_backend", "description": "Switch OCR engine"},
                {"action": "enhance_image", "description": "Pre-process image for better OCR"},
                {"action": "use_vision_model", "description": "Fall back to vision LLM"},
            ],
            "llm_error": [
                {"action": "retry_with_fallback", "description": "Try fallback model"},
                {"action": "simplify_prompt", "description": "Reduce prompt complexity"},
                {"action": "wait_and_retry", "description": "Wait and retry"},
            ],
        }

    def record_failure(self, action: str, error: str, context: dict[str, Any] | None = None) -> FailureRecord:
        record = FailureRecord(action, error, context)
        self._failures.append(record)
        if len(self._failures) > 100:
            self._failures = self._failures[-100:]
        return record

    def diagnose(self, error: str) -> dict[str, Any]:
        error_lower = error.lower()
        category = self._categorize_error(error_lower)
        strategies = self._recovery_strategies.get(category, [])

        pattern = self._detect_pattern(error_lower)

        return {
            "category": category,
            "strategies": strategies,
            "pattern": pattern,
            "occurrence_count": self._count_occurrences(error_lower),
        }

    def _categorize_error(self, error: str) -> str:
        if any(w in error for w in ["element not found", "no element", "selector", "locate"]):
            return "element_not_found"
        if any(w in error for w in ["timeout", "timed out", "slow"]):
            return "timeout"
        if any(w in error for w in ["permission", "denied", "forbidden", "unauthorized"]):
            return "permission_denied"
        if any(w in error for w in ["network", "connection", "dns", "resolve"]):
            return "network_error"
        if any(w in error for w in ["ocr", "text recognition", "no text"]):
            return "ocr_failed"
        if any(w in error for w in ["llm", "model", "inference", "generation"]):
            return "llm_error"
        return "unknown"

    def _detect_pattern(self, error: str) -> str | None:
        recent = self._failures[-10:]
        errors = [f.error.lower() for f in recent]
        if len(errors) >= 3:
            if all(self._categorize_error(e) == self._categorize_error(errors[0]) for e in errors):
                return "recurring_failure"
        return None

    def _count_occurrences(self, error: str) -> int:
        return sum(1 for f in self._failures[-20:] if error in f.error.lower())

    def recent_failures(self, limit: int = 20) -> list[dict[str, Any]]:
        return [f.to_dict() for f in self._failures[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._failures)
        recovered = sum(1 for f in self._failures if f.recovery_succeeded)
        return {
            "total_failures": total,
            "recovered": recovered,
            "recovery_rate": recovered / total if total > 0 else 0.0,
        }
