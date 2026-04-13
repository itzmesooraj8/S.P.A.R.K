"""
Local TTS service for SPARK.

Primary engine: Piper (offline, low-latency).
Fallback engine: edge-tts when Piper is unavailable.
"""

from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple

import edge_tts


class LocalTTS:
    def __init__(self):
        self.preferred_engine = (os.getenv("SPARK_TTS_ENGINE", "piper") or "piper").strip().lower()
        self.piper_binary = (os.getenv("SPARK_PIPER_BINARY", "piper") or "piper").strip()
        self.piper_model_path = (os.getenv("SPARK_PIPER_MODEL_PATH", "") or "").strip()
        self.piper_config_path = (os.getenv("SPARK_PIPER_CONFIG_PATH", "") or "").strip()

        self.default_voice = (os.getenv("SPARK_TTS_VOICE", "en-US-GuyNeural") or "en-US-GuyNeural").strip()
        self.default_rate = (os.getenv("SPARK_TTS_RATE", "+0%") or "+0%").strip()
        self.default_pitch = (os.getenv("SPARK_TTS_PITCH", "+0Hz") or "+0Hz").strip()

    def _piper_ready(self) -> bool:
        if self.preferred_engine == "edge-tts":
            return False
        if not self.piper_model_path:
            return False
        if not os.path.exists(self.piper_model_path):
            return False
        return shutil.which(self.piper_binary) is not None

    def _synthesize_piper_sync(self, text: str) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = tmp.name

        cmd = [
            self.piper_binary,
            "--model",
            self.piper_model_path,
            "--output_file",
            out_path,
        ]

        if self.piper_config_path and os.path.exists(self.piper_config_path):
            cmd.extend(["--config", self.piper_config_path])

        try:
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=45,
                check=False,
            )
            if proc.returncode != 0:
                stderr = proc.stderr.decode("utf-8", errors="ignore").strip()
                stdout = proc.stdout.decode("utf-8", errors="ignore").strip()
                msg = stderr or stdout or "piper synthesis failed"
                raise RuntimeError(msg)

            with open(out_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(out_path):
                try:
                    os.unlink(out_path)
                except Exception:
                    pass

    async def _synthesize_edge(self, text: str, voice: str, rate: str, pitch: str) -> bytes:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
    ) -> Tuple[bytes, str, str]:
        content = (text or "").strip()
        if not content:
            raise ValueError("Text is empty")

        if self._piper_ready():
            try:
                data = await asyncio.to_thread(self._synthesize_piper_sync, content)
                return data, "audio/wav", "piper"
            except Exception as exc:
                print(f"[TTS] Piper failed, falling back to edge-tts: {exc}")

        edge_voice = (voice or self.default_voice).strip() or self.default_voice
        edge_rate = (rate or self.default_rate).strip() or self.default_rate
        edge_pitch = (pitch or self.default_pitch).strip() or self.default_pitch

        data = await self._synthesize_edge(content, edge_voice, edge_rate, edge_pitch)
        return data, "audio/mpeg", "edge-tts"

    def get_engine_status(self) -> dict:
        active = "piper" if self._piper_ready() else "edge-tts"
        return {
            "preferred": self.preferred_engine,
            "active": active,
            "piper_ready": self._piper_ready(),
            "piper_model_configured": bool(self.piper_model_path),
            "default_voice": self.default_voice,
        }


local_tts = LocalTTS()
