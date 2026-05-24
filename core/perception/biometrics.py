from __future__ import annotations

import base64
import numpy as np
import scipy.signal

class BiometricVoiceVerifier:
    def __init__(self, anchor_template: np.ndarray | None = None, threshold: float = 0.72):
        self.threshold = threshold
        self.anchor_embedding = anchor_template if anchor_template is not None else np.ones(192)

    def verify_vocal_path(self, speaker_embedding: np.ndarray) -> bool:
        """Compares target speaker embedding vector against registered anchor using cosine similarity."""
        dot_product = np.dot(speaker_embedding, self.anchor_embedding)
        norm_a = np.linalg.norm(speaker_embedding)
        norm_b = np.linalg.norm(self.anchor_embedding)
        if norm_a == 0 or norm_b == 0:
            return False
        similarity = dot_product / (norm_a * norm_b)
        return bool(similarity >= self.threshold)

def process_semg_signal(raw_emg: np.ndarray, fs: int = 500) -> np.ndarray:
    """Applies Butter bandpass (20-245Hz) and a notch filter (50Hz) to clean sEMG signals."""
    if len(raw_emg) < 15:
        return raw_emg
    nyq = 0.5 * fs
    low = 20 / nyq
    high = 245 / nyq
    b, a = scipy.signal.butter(4, [low, high], btype='band')
    filtered = scipy.signal.filtfilt(b, a, raw_emg)
    
    w0 = 50.0 / nyq
    Q = 30.0
    b_notch, a_notch = scipy.signal.iirnotch(w0, Q)
    clean_emg = scipy.signal.filtfilt(b_notch, a_notch, filtered)
    return clean_emg

class SubVocalDecoder:
    """Mock/Heuristics translation engine mapping sEMG signals into string prompts."""
    def decode_signals(self, clean_emg: np.ndarray) -> str:
        # RMS energy heuristic mapping
        rms = np.sqrt(np.mean(clean_emg**2))
        if rms > 150.0:
            return "emergency abort"
        if rms > 80.0:
            return "status query"
        return ""
