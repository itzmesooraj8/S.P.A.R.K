"""Voice utilities for TTS and optional Whisper-based microphone capture with VAD and barge-in support."""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import logging
import time

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    np = None

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency
    sd = None

try:
    import scipy.io.wavfile as wavfile
except Exception:  # pragma: no cover - optional dependency
    wavfile = None

try:
    import whisper
except Exception:  # pragma: no cover - optional dependency
    whisper = None

try:
    from silero_vad import load_silero_vad
except Exception:  # pragma: no cover - optional dependency
    load_silero_vad = None

logger = logging.getLogger("SPARK_VOICE")
whisper_model = None

# Global barge-in state: set to True when user starts speaking to interrupt current speech
_barge_in_flag = False
_speak_lock = threading.Lock()


def _load_vad_model():
    """
    Load Silero VAD model for fast, accurate speech boundary detection.
    Falls back gracefully if unavailable.
    """
    try:
        if load_silero_vad is None:
            logger.debug("Silero VAD not available; install with: pip install silero-vad")
            return None
        model = load_silero_vad(onnx_model=None, device="cpu")
        logger.info("Silero VAD model loaded successfully")
        return model
    except Exception as e:
        logger.warning(f"Failed to load Silero VAD: {e}")
        return None


def detect_speech_activity(audio_chunk: np.ndarray, vad_model, sample_rate: int = 16000) -> bool:
    """
    Detect if audio chunk contains speech using Silero VAD.
    Returns True if speech is detected.
    """
    if vad_model is None or audio_chunk is None:
        return False
    
    try:
        # Silero VAD expects audio as a 1D numpy array of float32
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32) / 32768.0
        
        # Get speech probability (0.0-1.0)
        confidence = vad_model(audio_chunk, sample_rate).item()
        return confidence > 0.5
    except Exception as e:
        logger.debug(f"VAD detection error: {e}")
        return False


def detect_emotional_tone(audio_chunk: np.ndarray, sample_rate: int = 16000) -> dict[str, float]:
    """
    Basic emotional tone detection based on pause length and pitch variance.
    Returns dict with tone indicators: {'energy': 0-1, 'patience': 0-1}
    """
    try:
        if audio_chunk is None or len(audio_chunk) == 0:
            return {"energy": 0.5, "patience": 0.5}
        
        # Normalize to float
        if audio_chunk.dtype != np.float32:
            audio_float = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_float = audio_chunk
        
        # Energy: RMS amplitude
        rms = np.sqrt(np.mean(audio_float**2))
        energy = min(rms * 2.0, 1.0)  # Scale to 0-1
        
        # Patience: inverse of silence ratio
        silence_threshold = 0.02
        silent_ratio = np.sum(np.abs(audio_float) < silence_threshold) / len(audio_float)
        patience = max(1.0 - silent_ratio, 0.0)
        
        return {"energy": energy, "patience": patience}
    except Exception as e:
        logger.debug(f"Tone detection error: {e}")
        return {"energy": 0.5, "patience": 0.5}


import asyncio, re, threading

def _speak_sync(text: str, check_barge_in: bool = True) -> None:
    """
    Synchronous TTS. Runs in a thread so it never blocks.
    If check_barge_in is True, will stop if _barge_in_flag is set.
    """
    global _barge_in_flag
    
    if not text or not text.strip():
        return
    
    # Strip markdown
    clean = re.sub(r'[*_`#\[\]()\-]+', ' ', text)
    clean = re.sub(r'https?://\S+', 'link', clean)
    clean = ' '.join(clean.split())[:400]
    if not clean:
        return
    
    # Try pyttsx3 first (offline, instant, no audio device issues)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 0.9)
        
        # Use a natural voice if available
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'zira' in voice.name.lower() or 'david' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        # Check for barge-in before speaking
        if check_barge_in and _barge_in_flag:
            logger.debug("Barge-in detected; interrupting speech")
            return
        
        engine.say(clean)
        engine.runAndWait()
        engine.stop()
        return
    except Exception as e1:
        pass
    
    # Fallback: EdgeTTS
    try:
        import edge_tts, tempfile, os
        import pygame
        
        async def _edge():
            if check_barge_in and _barge_in_flag:
                return None
            communicate = edge_tts.Communicate(clean, voice="en-US-AriaNeural")
            # Use secure NamedTemporaryFile instead of deprecated mktemp to prevent race conditions
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp = tmp_file.name
            await communicate.save(tmp)
            return tmp
        
        tmp = asyncio.run(_edge())
        if tmp is None:
            return
        
        pygame.mixer.init()
        pygame.mixer.music.load(tmp)
        
        # Check barge-in during playback
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not _barge_in_flag:
            time.sleep(0.1)
        
        # Stop playback if barge-in detected
        if _barge_in_flag:
            pygame.mixer.music.stop()
            logger.debug("Barge-in: stopping playback")
        
        pygame.mixer.music.unload()
        os.unlink(tmp)
    except Exception as e2:
        logger.debug(f"[SPARK TTS] Both engines failed: pyttsx3={e1}, edge={e2}")

async def speak(text: str, check_barge_in: bool = True) -> None:
    """
    Non-blocking async wrapper with optional barge-in support.
    Fire and forget.
    """
    with _speak_lock:
        thread = threading.Thread(target=_speak_sync, args=(text, check_barge_in), daemon=True)
        thread.start()


def load_whisper():
    """Load the Whisper base model once and reuse it."""
    global whisper_model
    if whisper is None:
        raise RuntimeError("openai-whisper is not installed")
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
    return whisper_model


def load_whisper():
    """Load the Whisper base model once and reuse it."""
    global whisper_model
    if whisper is None:
        raise RuntimeError("openai-whisper is not installed")
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
    return whisper_model


def record_audio(duration: int = 5, sample_rate: int = 16000, vad_enabled: bool = True) -> str:
    """
    Record from mic for `duration` seconds, optionally with VAD-based endpoint detection.
    Returns temp wav path.
    If vad_enabled and VAD is available, will stop recording early if silence is detected.
    """
    if sd is None or np is None or wavfile is None:
        raise RuntimeError("audio recording dependencies are not installed")

    vad_model = _load_vad_model() if vad_enabled else None
    chunk_size = sample_rate // 10  # 100ms chunks
    chunks = []
    silence_counter = 0
    max_silence_frames = 10  # ~1 second of silence
    
    try:
        for _ in range(int(duration * sample_rate / chunk_size)):
            # Check for barge-in signal
            if _barge_in_flag:
                logger.debug("Barge-in flag set during recording; stopping early")
                break
            
            chunk = sd.rec(chunk_size, samplerate=sample_rate, channels=1, dtype="int16", blocking=True)
            chunks.append(chunk)
            
            # Early exit on silence if VAD available
            if vad_model and len(chunk) > 0:
                is_speech = detect_speech_activity(chunk.flatten(), vad_model, sample_rate)
                if is_speech:
                    silence_counter = 0
                else:
                    silence_counter += 1
                    if silence_counter >= max_silence_frames:
                        logger.debug("VAD: silence detected; ending recording early")
                        break
    except Exception as e:
        logger.error(f"Recording error: {e}")
    
    # Concatenate and save
    if not chunks:
        raise RuntimeError("No audio recorded")
    
    audio = np.vstack(chunks)
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wavfile.write(tmp, sample_rate, audio)
    return tmp


def listen_and_transcribe(duration: int = 5, vad_enabled: bool = True) -> str:
    """
    Record audio and return transcribed text.
    With VAD enabled, will auto-detect end of speech.
    """
    wav_path = ""
    try:
        wav_path = record_audio(duration, vad_enabled=vad_enabled)
        model = load_whisper()
        result = model.transcribe(wav_path, fp16=False)
        text = result.get("text", "").strip()
        
        # Extract emotional tone from the recording
        if np and wavfile:
            sample_rate, audio_data = wavfile.read(wav_path)
            tone = detect_emotional_tone(audio_data.flatten(), sample_rate)
            logger.debug(f"Detected tone: energy={tone['energy']:.2f}, patience={tone['patience']:.2f}")
        
        return text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return ""
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception:
                pass


class AlwaysOnListener:
    """
    Continuously listens in background for wake words or speech activity.
    Feeds detected speech into a callback without blocking main thread.
    Supports barge-in to interrupt current speech.
    """
    def __init__(self, callback=None, sample_rate: int = 16000):
        self.callback = callback
        self.sample_rate = sample_rate
        self.running = False
        self._thread = None
        self.vad_model = _load_vad_model()
        logger.info("AlwaysOnListener initialized")
    
    def start(self):
        """Start listening thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("AlwaysOnListener started")
    
    def stop(self):
        """Stop listening thread."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("AlwaysOnListener stopped")
    
    def _listen_loop(self):
        """Main listening loop — continuous VAD-based speech detection."""
        global _barge_in_flag
        
        if sd is None or np is None:
            logger.error("Audio dependencies unavailable")
            return
        
        chunk_size = self.sample_rate // 10  # 100ms chunks
        speech_buffer = []
        speech_start_time = None
        min_speech_duration = 0.5  # Seconds
        
        try:
            while self.running:
                try:
                    chunk = sd.rec(chunk_size, samplerate=self.sample_rate, channels=1, dtype="int16", blocking=True)
                    
                    if not self.running:
                        break
                    
                    is_speech = (
                        self.vad_model and detect_speech_activity(chunk.flatten(), self.vad_model, self.sample_rate)
                    ) or (not self.vad_model)  # If no VAD, assume speech
                    
                    if is_speech:
                        if speech_start_time is None:
                            speech_start_time = time.time()
                            _barge_in_flag = True  # Signal that user is speaking
                            logger.debug("Speech detected; setting barge-in flag")
                        speech_buffer.append(chunk)
                    else:
                        # Silence detected
                        if speech_start_time is not None:
                            elapsed = time.time() - speech_start_time
                            if elapsed >= min_speech_duration and self.callback and speech_buffer:
                                # Accumulate and process
                                audio_data = np.vstack(speech_buffer)
                                logger.debug(f"Speech segment complete ({elapsed:.1f}s); calling callback")
                                self.callback(audio_data, self.sample_rate)
                            speech_buffer = []
                            speech_start_time = None
                            _barge_in_flag = False  # Clear barge-in flag
                
                except Exception as e:
                    logger.debug(f"Listen loop error: {e}")
                    continue
        except KeyboardInterrupt:
            logger.info("AlwaysOnListener interrupted")
        finally:
            _barge_in_flag = False


def set_barge_in_flag():
    """Explicitly set barge-in flag to interrupt current speech."""
    global _barge_in_flag
    _barge_in_flag = True
    logger.info("Barge-in flag set")


if __name__ == "__main__":
    _speak_sync("S.P.A.R.K voice system online. Audio confirmed.")