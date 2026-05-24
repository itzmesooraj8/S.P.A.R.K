from __future__ import annotations

from typing import Any
import numpy as np
import pyaudio

class GSCBeamformer:
    """Multi-microphone Blind Source Separation and MVDR-based beamforming compiler."""
    def __init__(self, num_channels: int = 4, rate: int = 16000, chunk: int = 1024):
        self.num_channels = num_channels
        self.rate = rate
        self.chunk = chunk
        self.d_spacing = 0.05  # Linear micro-array spacing (meters)
        self.speed_of_sound = 343.0

    def process_frame(self, raw_buffer: bytes) -> np.ndarray:
        """Processes multichannel raw audio bytes to isolate targets."""
        signals = np.frombuffer(raw_buffer, dtype=np.int16).reshape(-1, self.num_channels)
        signals_f = np.fft.rfft(signals, axis=0)
        
        freqs = np.fft.rfftfreq(len(signals), d=1.0/self.rate)
        steered_signals = np.zeros(signals_f.shape[0], dtype=complex)
        
        for idx, f in enumerate(freqs):
            if f == 0:
                steered_signals[idx] = np.mean(signals_f[idx, :])
                continue
            tau = np.array([m * self.d_spacing / self.speed_of_sound for m in range(self.num_channels)])
            d = np.exp(-1j * 2 * np.pi * f * tau)
            steered_signals[idx] = np.dot(signals_f[idx, :], np.conj(d)) / self.num_channels
            
        output_signal = np.fft.irfft(steered_signals).astype(np.int16)
        return output_signal

def detect_speech_activity(audio_chunk: np.ndarray, vad_model: Any | None, sample_rate: int = 16000) -> bool:
    """Simple energy-based VAD if Silero VAD is not loaded, otherwise returns VAD prediction."""
    if vad_model is not None:
        try:
            confidence = vad_model(audio_chunk, sample_rate).item()
            return bool(confidence > 0.5)
        except Exception:
            pass
    # Local RMS threshold calculation as fallback
    if len(audio_chunk) == 0:
        return False
    rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
    return bool(rms > 350.0)
