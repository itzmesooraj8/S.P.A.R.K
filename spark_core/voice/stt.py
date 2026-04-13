"""
Local STT service for SPARK.

Uses faster-whisper for offline transcription and exposes helpers for:
- audio file paths
- raw audio bytes
- short microphone captures
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import wave
from typing import Optional

from faster_whisper import WhisperModel

try:
    import numpy as np
except Exception:
    np = None

try:
    import sounddevice as sd
except Exception:
    sd = None


class WhisperSTT:
    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        self.model_size = (model_size or os.getenv("SPARK_WHISPER_MODEL", "small")).strip() or "small"
        self.device = (device or os.getenv("SPARK_WHISPER_DEVICE", "auto")).strip().lower()
        self.compute_type = (compute_type or os.getenv("SPARK_WHISPER_COMPUTE_TYPE", "auto")).strip().lower()
        self.default_language = (os.getenv("SPARK_STT_LANGUAGE", "en") or "en").strip() or "en"

        self._model: Optional[WhisperModel] = None
        self._model_lock = threading.Lock()

    def _resolve_device(self) -> str:
        if self.device in {"cpu", "cuda"}:
            return self.device

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _resolve_compute_type(self, resolved_device: str) -> str:
        if self.compute_type != "auto":
            return self.compute_type
        return "float16" if resolved_device == "cuda" else "int8"

    def _ensure_model(self) -> WhisperModel:
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model

            resolved_device = self._resolve_device()
            resolved_compute = self._resolve_compute_type(resolved_device)
            print(
                f"[STT] Loading faster-whisper model={self.model_size} "
                f"device={resolved_device} compute_type={resolved_compute}"
            )
            self._model = WhisperModel(
                self.model_size,
                device=resolved_device,
                compute_type=resolved_compute,
            )
            print("[STT] Model ready")
            return self._model

    def _transcribe_sync(self, audio_path: str, language: Optional[str] = None) -> str:
        model = self._ensure_model()

        kwargs = {
            "beam_size": 5,
            "vad_filter": True,
        }
        lang = (language or self.default_language or "").strip()
        if lang:
            kwargs["language"] = lang

        segments, _ = model.transcribe(audio_path, **kwargs)
        text_parts = []
        for segment in segments:
            part = (segment.text or "").strip()
            if part:
                text_parts.append(part)
        return " ".join(text_parts).strip()

    async def transcribe_file(self, audio_path: str, language: Optional[str] = None) -> str:
        return await asyncio.to_thread(self._transcribe_sync, audio_path, language)

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        suffix: str = ".wav",
        language: Optional[str] = None,
    ) -> str:
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            return await self.transcribe_file(tmp_path, language=language)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def _record_microphone_sync(self, duration_sec: float, sample_rate: int) -> str:
        if sd is None or np is None:
            raise RuntimeError("sounddevice and numpy are required for microphone STT")

        frames = max(1, int(duration_sec * sample_rate))
        recording = sd.rec(
            frames,
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        clipped = np.clip(recording.squeeze(), -1.0, 1.0)
        pcm16 = (clipped * 32767).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = tmp.name

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm16.tobytes())

        return path

    async def transcribe_microphone(
        self,
        duration_sec: float = 4.0,
        language: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> str:
        path = await asyncio.to_thread(self._record_microphone_sync, duration_sec, sample_rate)
        try:
            return await self.transcribe_file(path, language=language)
        finally:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass


whisper_stt = WhisperSTT()
