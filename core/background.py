from __future__ import annotations

import logging
import threading
import time
from typing import Callable

try:
    import pyperclip
except Exception:  # pragma: no cover - optional dependency at runtime
    pyperclip = None


logger = logging.getLogger("SPARK_BACKGROUND")

_watcher_thread: threading.Thread | None = None
_watcher_stop = threading.Event()


def _looks_like_trigger(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith(("http://", "https://")):
        return True
    if len(stripped) > 120 and "\n" in stripped:
        return True
    return False


def _watch_clipboard(llm_query_fn: Callable[[str], str] | None, interval: float) -> None:
    last_clipboard = ""
    while not _watcher_stop.is_set():
        if pyperclip is None:
            time.sleep(interval)
            continue
        try:
            current = pyperclip.paste() or ""
        except Exception:
            current = ""

        if current and current != last_clipboard:
            last_clipboard = current
            logger.info("Clipboard changed (%s chars).", len(current))
            if llm_query_fn and _looks_like_trigger(current):
                try:
                    llm_query_fn(f"Clipboard context: {current[:800]}")
                except Exception as exc:
                    logger.debug("Clipboard trigger failed: %s", exc)

        time.sleep(interval)


def start_watcher(voice=None, llm_query_fn: Callable[[str], str] | None = None, interval: float = 1.0):
    global _watcher_thread
    if _watcher_thread and _watcher_thread.is_alive():
        return _watcher_thread

    _watcher_stop.clear()
    _watcher_thread = threading.Thread(
        target=_watch_clipboard,
        args=(llm_query_fn, interval),
        daemon=True,
        name="spark-clipboard-watcher",
    )
    _watcher_thread.start()
    logger.info("Clipboard watcher started.")
    return _watcher_thread


def stop_watcher():
    _watcher_stop.set()
    logger.info("Clipboard watcher stopped.")