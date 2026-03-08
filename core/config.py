"""
SPARK Core Config
─────────────────────────────────────────────────────────────────────────────
Compatibility shim that provides the Config class used by audio/ modules.
Values are read from config/settings.yaml with sensible fallbacks.
"""
import os
import pathlib

def _load_settings() -> dict:
    try:
        import yaml
        p = pathlib.Path(__file__).parent.parent / "config" / "settings.yaml"
        if p.exists():
            return yaml.safe_load(p.read_text()) or {}
    except Exception:
        pass
    return {}

_s = _load_settings()
_audio = _s.get("audio", {})

class Config:
    # Audio pipeline
    SAMPLE_RATE       = int(os.getenv("SPARK_SAMPLE_RATE", "16000"))
    CHANNELS          = int(os.getenv("SPARK_CHANNELS", "1"))
    FRAME_LENGTH      = int(os.getenv("SPARK_FRAME_LENGTH", "1600"))

    # Whisper STT — default "small" for CPU; set env SPARK_WHISPER_MODEL to override
    WHISPER_MODEL_SIZE = os.getenv("SPARK_WHISPER_MODEL", "small")

    # TTS voice — read from settings.yaml audio.voice
    TTS_VOICE = _audio.get("voice", os.getenv("SPARK_TTS_VOICE", "en-US-ChristopherNeural"))
    TTS_RATE  = _audio.get("rate",  os.getenv("SPARK_TTS_RATE",  "+0%"))
