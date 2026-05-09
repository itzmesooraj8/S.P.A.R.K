from __future__ import annotations

import logging

try:
    import keyboard
except Exception:  # pragma: no cover - optional dependency at runtime
    keyboard = None


logger = logging.getLogger("SPARK_WAKE")

_listener_started = False
_hotkey_handle = None


def start_wake_engine(on_wake_callback=None, use_hotword: bool = True):
    global _listener_started, _hotkey_handle
    if _listener_started:
        return

    if not use_hotword or keyboard is None or on_wake_callback is None:
        logger.info("Wake engine unavailable; running without hotword listener.")
        _listener_started = True
        return

    def _invoke_callback():
        try:
            on_wake_callback()
        except Exception as exc:
            logger.exception("Wake callback failed: %s", exc)

    try:
        _hotkey_handle = keyboard.add_hotkey("f9", _invoke_callback)
        _listener_started = True
        logger.info("Wake engine started with F9 hotkey trigger.")
    except Exception as exc:
        logger.warning("Wake engine could not start: %s", exc)
        _listener_started = True


def stop_wake_engine():
    global _listener_started, _hotkey_handle
    if keyboard is not None and _hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_hotkey_handle)
        except Exception:
            pass
    _hotkey_handle = None
    _listener_started = False
    logger.info("Wake engine stopped.")