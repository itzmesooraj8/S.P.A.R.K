from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Callable
from threading import Event
from typing import Any

from core.spark_brain import handle as spark_brain_handle


async def ask_spark_brain(
    user_input: str,
    session_history: list[dict[str, Any]] | None = None,
    stream_sink: Callable[[str, dict[str, Any]], None] | None = None,
    cancel_event: Event | None = None,
) -> dict[str, Any]:
    """Single async entry path for all interactive SPARK turns."""
    return await spark_brain_handle(
        user_input,
        session_history or [],
        stream_sink=stream_sink,
        cancel_event=cancel_event,
    )


def ask_spark_brain_sync(
    user_input: str,
    session_history: list[dict[str, Any]] | None = None,
    stream_sink: Callable[[str, dict[str, Any]], None] | None = None,
    cancel_event: Event | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Thread-safe sync wrapper for callers that cannot await directly."""

    def _run() -> dict[str, Any]:
        return asyncio.run(
            ask_spark_brain(
                user_input,
                session_history=session_history,
                stream_sink=stream_sink,
                cancel_event=cancel_event,
            )
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"Spark brain timed out after {timeout}s") from exc
