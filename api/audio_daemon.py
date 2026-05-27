"""Integrated Wakeword & Voice Isolation Runner daemon for Phase 3."""

from __future__ import annotations

import asyncio
import logging
import time
import threading
from typing import Any, Dict, Optional

import numpy as np

try:
    import pyaudio
except ImportError:
    pyaudio = None

from biometrics.audio_isolation import SomaticAudioIsolator, SpeakerDiarizationWrapper
from security.intent_validator import validate_intent_text

logger = logging.getLogger("SPARK_AUDIO_DAEMON")


class AudioDaemon:
    """Non-blocking streaming background task executing FastICA and NLMS voice isolation."""

    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 100) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.chunk_size = int((self.sample_rate * self.frame_duration_ms) / 1000)
        self.isolator = SomaticAudioIsolator(sample_rate=self.sample_rate)
        self.diarizer = SpeakerDiarizationWrapper()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Audio input devices parameters
        self.channels = 2  # mic channel + reference channel

    def start(self) -> None:
        """Start the background audio stream daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="spark-audio-daemon")
        self._thread.start()
        logger.info("Audio isolation daemon thread started.")

    def stop(self) -> None:
        """Stop the background audio stream daemon thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Audio isolation daemon thread stopped.")

    def _run_loop(self) -> None:
        """Background thread stream reader and isolator loop."""
        p_audio = None
        stream = None

        if pyaudio is not None:
            try:
                p_audio = pyaudio.PyAudio()
                stream = p_audio.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
                logger.info("Hardware microphone stream successfully opened.")
            except Exception as exc:
                logger.warning("Microphone hardware stream unavailable, using simulated loop: %s", exc)
                stream = None

        # Warm-up delay
        time.sleep(0.5)

        # Buffer to accumulate isolated audio for Whisper transcription or sub-vocal analysis
        audio_buffer = []

        while self._running:
            try:
                if stream is not None:
                    # Read hardware frames
                    try:
                        raw_data = stream.read(self.chunk_size, exception_on_overflow=False)
                        # Interleaved stereo data: shape (2, chunk_size)
                        data_int16 = np.frombuffer(raw_data, dtype=np.int16)
                        if data_int16.size >= self.chunk_size * self.channels:
                            reshaped = data_int16.reshape(-1, self.channels).T
                            mic_channels = reshaped.astype(np.float64) / 32768.0
                        else:
                            # Padding if chunk was short
                            mic_channels = np.zeros((self.channels, self.chunk_size), dtype=np.float64)
                    except Exception as stream_err:
                        logger.debug("Hardware stream read error: %s", stream_err)
                        mic_channels = np.zeros((self.channels, self.chunk_size), dtype=np.float64)
                else:
                    # Simulate non-blocking sleep matching chunk duration
                    time.sleep(self.frame_duration_ms / 1000.0)
                    
                    # Generate simulated noise and signals
                    t = np.linspace(0, self.frame_duration_ms / 1000.0, self.chunk_size, endpoint=False)
                    # Simulated mic signal + background speaker echo (reference)
                    des = 0.01 * np.random.randn(self.chunk_size)
                    ref = 0.005 * np.random.randn(self.chunk_size)
                    
                    # Occasionally inject a simulated sub-vocal frequency pattern (e.g. 5% chance)
                    if time.time() % 10 < 0.1:
                        # Heavy sub-vocal activity peak
                        des += 0.1 * np.sin(2 * np.pi * 80 * t)
                        
                    mic_channels = np.vstack([des, ref])

                # Apply NLMS echo cancellation and FastICA blind source separation
                iso_result = self.isolator.isolate(mic_channels)
                target_stream = iso_result.target_stream

                # Check sub-vocal commands (e.g. via diarization activity thresholds)
                subvocal_cmd = self.diarizer.parse_subvocal_activity(target_stream)
                if subvocal_cmd:
                    logger.info("Detected subvocal command: %s", subvocal_cmd)
                    self._dispatch_command(subvocal_cmd, is_subvocal=True)

                # Process buffer for voice commands
                rms = np.sqrt(np.mean(target_stream ** 2))
                if rms > 0.05:
                    audio_buffer.append(target_stream)
                else:
                    if audio_buffer:
                        # Process full utterance
                        full_utterance = np.concatenate(audio_buffer)
                        audio_buffer = []
                        
                        # Try transcribing via Whisper if available
                        try:
                            from tools.voice import load_whisper
                            whisper_model = load_whisper()
                            # Transcribe on background thread safely
                            res = whisper_model.transcribe(full_utterance.astype(np.float32), fp16=False)
                            text = res.get("text", "").strip()
                            if text:
                                logger.info("Isolated voice transcription: %s", text)
                                self._dispatch_command(text, is_subvocal=False)
                        except Exception as whisper_err:
                            logger.debug("Whisper transcription skipped: %s", whisper_err)

            except Exception as loop_err:
                logger.error("Error in audio isolation loop: %s", loop_err)
                time.sleep(0.1)

        # Cleanup
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        if p_audio is not None:
            try:
                p_audio.terminate()
            except Exception:
                pass

    def _dispatch_command(self, text: str, is_subvocal: bool = False) -> None:
        """Sanitizes text through the intent matrix and forwards to active handlers."""
        # Clean filler words and check safety metrics
        scan = validate_intent_text(text)

        payload = {
            "source": "somatic_audio_isolation",
            "type": "sub_vocal_telemetry" if is_subvocal else "voice_telemetry",
            "raw_text": text,
            "scan": {
                "allowed": bool(scan.allowed),
                "score": float(scan.score),
                "reasons": list(scan.reasons),
                "cleaned_text": scan.cleaned_text or ""
            },
            "timestamp": time.time()
        }

        logger.info("Constructed Intent Payload: %s", payload)

        # Broadcast the payload packet to HUD WebSocket clients
        try:
            from api.server import manager
            # Use running event loop or schedule thread-safely
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.broadcast({
                    "type": "audio_intent_event",
                    "payload": payload
                }))
            else:
                asyncio.run(manager.broadcast({
                    "type": "audio_intent_event",
                    "payload": payload
                }))
        except Exception as ws_exc:
            logger.debug("Could not broadcast intent payload to websocket: %s", ws_exc)

        # If allowed and intent exists, execute command asynchronously in the brain
        if scan.allowed and scan.cleaned_text:
            try:
                from core.brain_entry import ask_spark_brain
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(ask_spark_brain(scan.cleaned_text, session_history=[]))
                else:
                    asyncio.run(ask_spark_brain(scan.cleaned_text, session_history=[]))
            except Exception as brain_exc:
                logger.error("Could not deliver intent to spark brain: %s", brain_exc)


# Shared background instance
audio_daemon_instance = AudioDaemon()
