"""Retry Manager — Intelligent retry with backoff and strategy switching."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger("spark.reliability.retry")


class RetryAttempt:
    def __init__(self, attempt: int, strategy: str, error: str, timestamp: float):
        self.attempt = attempt
        self.strategy = strategy
        self.error = error
        self.timestamp = timestamp


class RetryManager:
    """
    Intelligent retry with backoff and strategy switching.

    Not just:
        retry 3 times

    But:
        Try strategy A
        Fail → wait 1s
        Try strategy B
        Fail → wait 2s
        Try strategy A with different params
        Fail → report to user with explanation
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._attempts: list[RetryAttempt] = []
        self._strategies: dict[str, list[str]] = {}

    async def execute_with_retry(
        self,
        action: Callable[..., Coroutine[Any, Any, Any]],
        strategies: list[str] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute with intelligent retry."""
        strategy_list = strategies or ["default"]
        last_error = None

        for attempt in range(self._max_retries):
            strategy = strategy_list[attempt % len(strategy_list)]
            delay = min(self._base_delay * (2 ** attempt), self._max_delay)

            try:
                result = await action(**kwargs)
                self._record_attempt(attempt, strategy, "", True)
                return {"success": True, "result": result, "attempts": attempt + 1, "strategy": strategy}
            except Exception as exc:
                last_error = str(exc)
                self._record_attempt(attempt, strategy, last_error, False)
                logger.warning("Attempt %d failed (strategy: %s): %s", attempt + 1, strategy, exc)

                if attempt < self._max_retries - 1:
                    logger.info("Retrying in %.1fs with strategy: %s", delay, strategy)
                    await self._async_sleep(delay)

        return {
            "success": False,
            "error": last_error,
            "attempts": self._max_retries,
            "strategies_tried": strategy_list,
            "explanation": self._generate_explanation(strategy_list, last_error),
        }

    def _record_attempt(self, attempt: int, strategy: str, error: str, success: bool) -> None:
        self._attempts.append(RetryAttempt(attempt, strategy, error, time.time()))

    def _generate_explanation(self, strategies: list[str], error: str) -> str:
        return f"Tried {len(strategies)} strategies ({', '.join(strategies)}). Last error: {error}"

    def _async_sleep(self, delay: float) -> Coroutine:
        import asyncio
        return asyncio.sleep(delay)

    def get_history(self) -> list[dict[str, Any]]:
        return [
            {"attempt": a.attempt, "strategy": a.strategy, "error": a.error, "timestamp": a.timestamp}
            for a in self._attempts[-20:]
        ]

    def reset(self) -> None:
        self._attempts.clear()
