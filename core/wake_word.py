"""
core/wake_word.py — S.P.A.R.K. Always-On Hotword Engine
Replaces keyboard.wait('f9') with openWakeWord continuous detection.
Sub-10MB model. < 2% CPU. Hardware independence.

Fallback: if openWakeWord is not installed, gracefully falls back
to the F9 keyboard trigger so the system always boots.
"""

import logging
import threading
import time
import requests

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
WAKE_WORD_MODEL = "hey_jarvis"   # openWakeWord built-in model (closest to "Hey SPARK")
# Other available built-ins: "alexa", "hey_mycroft", "timers", "weather", etc.
# For a custom "Hey SPARK" model, train via openWakeWord's custom training guide
# and set WAKE_WORD_MODEL = "path/to/hey_spark.tflite"

CHUNK_DURATION_MS = 80          # ms per audio chunk (openWakeWord default)
SAMPLE_RATE = 16000
CHANNELS = 1
DETECTION_THRESHOLD = 0.5       # 0.0–1.0, higher = less sensitive
COOLDOWN_SECONDS = 2.0          # silence period after trigger to avoid re-firing

_running = False
_on_wake_callback = None        # fn() called when wake word is detected


def _broadcast_hud_state(state: str):
    """Notify HUD of wake/listening state change."""
    def _send():
        try:
            requests.post(
                "http://127.0.0.1:8000/internal/broadcast",
                json={
                    "type": "voice_state",
                    "payload": {"status": state, "isListening": state == "listening"}
                },
                timeout=0.3
            )
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


def _run_openwakeword():
    """
    Core openWakeWord detection loop.
    Streams mic audio in chunks and checks for the wake word each frame.
    """
    global _running

    try:
        import numpy as np
        import pyaudio
        from openwakeword.model import Model

        logger.info(f"[WAKE_WORD] Loading openWakeWord model: '{WAKE_WORD_MODEL}'")
        oww_model = Model(wakeword_models=[WAKE_WORD_MODEL], inference_framework="tflite")

        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=SAMPLE_RATE,
            channels=CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)
        )

        logger.info(f"[WAKE_WORD] ✅ Listening for wake word '{WAKE_WORD_MODEL}'... Say 'Hey SPARK'.")
        last_trigger = 0.0

        while _running:
            try:
                audio_chunk = stream.read(
                    int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000),
                    exception_on_overflow=False
                )
                import numpy as np
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                oww_model.predict(audio_array)

                scores = oww_model.prediction_buffer.get(WAKE_WORD_MODEL, [0])
                score = scores[-1] if scores else 0

                now = time.time()
                if score >= DETECTION_THRESHOLD and (now - last_trigger) > COOLDOWN_SECONDS:
                    last_trigger = now
                    logger.info(f"[WAKE_WORD] 🔊 Wake word detected! Score={score:.3f}")
                    _broadcast_hud_state("listening")
                    if _on_wake_callback:
                        threading.Thread(
                            target=_on_wake_callback,
                            daemon=True,
                            name="spark-wake-handler"
                        ).start()

            except Exception as inner:
                logger.debug(f"[WAKE_WORD] Chunk error (non-fatal): {inner}")
                time.sleep(0.1)

        stream.stop_stream()
        stream.close()
        pa.terminate()

    except ImportError as e:
        logger.warning(
            f"[WAKE_WORD] openWakeWord not installed ({e}). "
            f"Run: pip install openwakeword pyaudio\n"
            f"Falling back to F9 keyboard trigger."
        )
        _run_keyboard_fallback()

    except Exception as e:
        logger.error(f"[WAKE_WORD] Fatal error in wake word engine: {e}")
        logger.info("[WAKE_WORD] Falling back to F9 keyboard trigger.")
        _run_keyboard_fallback()


def _run_keyboard_fallback():
    """
    Graceful fallback: F9 key trigger.
    Used when openWakeWord or PyAudio is not available.
    """
    global _running
    try:
        import keyboard
        logger.info("[WAKE_WORD] Keyboard fallback active. Press F9 to trigger SPARK.")
        while _running:
            keyboard.wait('f9')
            if not _running:
                break
            logger.info("[WAKE_WORD] F9 pressed — triggering wake callback.")
            _broadcast_hud_state("listening")
            if _on_wake_callback:
                threading.Thread(
                    target=_on_wake_callback,
                    daemon=True,
                    name="spark-f9-handler"
                ).start()
            time.sleep(COOLDOWN_SECONDS)
    except ImportError:
        logger.error("[WAKE_WORD] keyboard library not installed. No trigger available!")
    except Exception as e:
        logger.error(f"[WAKE_WORD] Keyboard fallback error: {e}")


def start_wake_engine(on_wake_callback, use_hotword: bool = True):
    """
    Start the wake word / always-on listening engine.
    Call once from main.py during boot.

    on_wake_callback: fn() — called when 'Hey SPARK' is detected.
    use_hotword:      True = try openWakeWord, fall back to F9.
                      False = keyboard F9 only (dev mode).
    """
    global _running, _on_wake_callback

    if _running:
        logger.warning("[WAKE_WORD] Engine already running.")
        return

    _on_wake_callback = on_wake_callback
    _running = True

    if use_hotword:
        t = threading.Thread(
            target=_run_openwakeword,
            daemon=True,
            name="spark-wake-engine"
        )
    else:
        t = threading.Thread(
            target=_run_keyboard_fallback,
            daemon=True,
            name="spark-wake-engine-f9"
        )

    t.start()
    logger.info(f"[WAKE_WORD] Wake engine started (hotword={'enabled' if use_hotword else 'disabled/F9'}).")


def stop_wake_engine():
    """Signal the wake engine to stop."""
    global _running
    _running = False
    logger.info("[WAKE_WORD] Wake engine stop signal sent.")
