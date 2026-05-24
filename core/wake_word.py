"""Wake word detection for S.P.A.R.K."""

from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger("SPARK_WAKE")

try:
    import keyboard
except Exception:  # pragma: no cover - optional dependency at runtime
    keyboard = None

try:
    from openwakeword.model import Model as OpenWakeWordModel
    OPENWAKEWORD_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency at runtime
    OpenWakeWordModel = None
    OPENWAKEWORD_AVAILABLE = False

FORMAT = None
CHANNELS = 1
RATE = 16000
CHUNK = 1280
THRESHOLD = 0.5

_listener_started = False
_hotkey_handle = None
oww_model = None


def _load_wake_model():
    """Load the openWakeWord model once if the optional dependencies exist."""
    global oww_model, FORMAT
    if oww_model is not None:
        return oww_model
    if not OPENWAKEWORD_AVAILABLE:
        raise ImportError("openwakeword is not installed")
    import numpy as np  # noqa: F401
    import pyaudio

    FORMAT = pyaudio.paInt16
    oww_model = OpenWakeWordModel(wakeword_models=["hey_jarvis"])
    return oww_model


def listen_for_wake_word(callback: Callable[[], None]) -> None:
    """Blocking mic loop that invokes a callback when the wake score crosses the threshold."""
    try:
        import numpy as np
        import pyaudio
    except Exception as exc:
        logger.warning("Wake word dependencies unavailable: %s", exc)
        return

    try:
        model = _load_wake_model()
    except Exception as exc:
        logger.info("openWakeWord unavailable; falling back to keyboard mode: %s", exc)
        return

    audio = pyaudio.PyAudio()
    mic = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    logger.info("[SPARK] Wake word listener active. Say 'Hey SPARK'...")

    while True:
        pcm = mic.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(pcm, dtype=np.int16)
        prediction = model.predict(audio_data)
        for _, score in prediction.items():
            if score > THRESHOLD:
                logger.info("[SPARK] Wake word! Score: %.2f", score)
                try:
                    callback()
                except Exception as exc:
                    logger.exception("Wake callback failed: %s", exc)
                break


def start_wake_engine(on_wake_callback=None, use_hotword: bool = True, transcribe_on_wake: bool = False, transcribe_duration: int = 5):
    """Start wake-word monitoring in a daemon thread or fall back to F9 hotkey.

    If `transcribe_on_wake` is True, a background transcription loop will run on wake
    using `audio.stt.SparkEars.listen()` and the result will be passed to
    `core.brain_entry.ask_spark_brain_sync` in a background thread to avoid encoding
    issues and keep the hotword handle responsive.
    """
    global _listener_started, _hotkey_handle
    if _listener_started:
        return

    if on_wake_callback is None:
        logger.info("Wake engine unavailable; no callback provided.")
        _listener_started = True
        return

    def _invoke_callback():
        try:
            # Invoke original callback (legacy behavior)
            on_wake_callback()
        except Exception as exc:
            logger.exception("Wake callback failed: %s", exc)

        # If transcription-on-wake is enabled, perform a pre-warmed transcription
        # synchronously in a background thread and dispatch to the core brain.
        if transcribe_on_wake:
            def _transcribe_and_dispatch():
                try:
                    from audio.stt import SparkEars
                    from core.brain_entry import ask_spark_brain_sync

                    ears = SparkEars()
                    text = ears.listen(transcribe_duration)
                    if not text:
                        logger.debug("Wake transcription returned empty.")
                        return

                    # Deliver to the brain synchronously (thread-safe wrapper)
                    try:
                        ask_spark_brain_sync(text, session_history=[], timeout=120)
                        logger.info("Wake transcription dispatched to brain: %s", text[:80])
                    except Exception as exc:
                        logger.exception("Dispatching wake transcription failed: %s", exc)
                except Exception as exc:
                    logger.exception("Transcription on wake failed: %s", exc)

            t = threading.Thread(target=_transcribe_and_dispatch, daemon=True)
            t.start()

    if not OPENWAKEWORD_AVAILABLE:
        logger.info("openwakeword not installed; wake word disabled.")
        use_hotword = False

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
    """Stop any hotkey registration created by the wake engine."""
    global _listener_started, _hotkey_handle
    if keyboard is not None and _hotkey_handle is not None:
        try:
            keyboard.remove_hotkey(_hotkey_handle)
        except Exception:
            pass
    _hotkey_handle = None
    _listener_started = False
    logger.info("Wake engine stopped.")
