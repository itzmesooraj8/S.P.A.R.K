"""Wake word detection for S.P.A.R.K."""

from __future__ import annotations

import logging
import threading

try:
    import keyboard
except Exception:  # pragma: no cover - optional dependency at runtime
    keyboard = None

logger = logging.getLogger("SPARK_WAKE")

_listener_started = False
_hotkey_handle = None


def listen_for_wake_word(callback):
    """Best-effort wake listener with openWakeWord fallback to hotkey mode."""
    try:
        import numpy as np
        import pyaudio
        from openwakeword.model import Model
    except Exception:
        logger.info("openWakeWord unavailable; falling back to hotkey mode.")
        callback()
        return

    model = Model(wakeword_models=["hey_jarvis"])
    format_ = pyaudio.paInt16
    channels = 1
    rate = 16000
    chunk = 1280

    audio = pyaudio.PyAudio()
    mic = audio.open(format=format_, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
    logger.info("[SPARK] Listening for wake word...")

    while True:
        pcm = mic.read(chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(pcm, dtype=np.int16)
        prediction = model.predict(audio_data)
        for _, score in prediction.items():
            if score > 0.5:
                logger.info("[SPARK] Wake word detected!")
                callback()
                break


def start_wake_engine(on_wake_callback=None, use_hotword: bool = True):
    global _listener_started, _hotkey_handle
    if _listener_started:
        return

    if on_wake_callback is None:
        logger.info("Wake engine unavailable; no callback provided.")
        _listener_started = True
        return

    def _invoke_callback():
        try:
            on_wake_callback()
        except Exception as exc:
            logger.exception("Wake callback failed: %s", exc)

    if use_hotword:
        try:
            thread = threading.Thread(target=listen_for_wake_word, args=(_invoke_callback,), daemon=True)
            thread.start()
            _listener_started = True
            logger.info("Wake engine started.")
            return
        except Exception as exc:
            logger.warning("Wake engine could not start: %s", exc)

    if keyboard is not None:
        try:
            _hotkey_handle = keyboard.add_hotkey("f9", _invoke_callback)
            _listener_started = True
            logger.info("Wake engine started with F9 hotkey trigger.")
            return
        except Exception as exc:
            logger.warning("Wake engine hotkey fallback failed: %s", exc)

    _listener_started = True
    logger.info("Wake engine unavailable; running without hotword listener.")


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