from __future__ import annotations

import numpy as np
import scipy.signal

class ContactlessRPPG:
    """Estimates blood volume pulse (BVP) heart rate from face video masks using CHROM."""
    def __init__(self, buffer_size: int = 150, fps: float = 30.0):
        self.buffer_size = buffer_size
        self.fps = fps
        self.raw_rgb = []

    def process_frame(self, roi_mask: np.ndarray) -> float:
        if roi_mask.size == 0 or np.sum(roi_mask) == 0:
            return 0.0

        # Average colors across channels
        mean_rgb = np.mean(roi_mask, axis=(0, 1))
        self.raw_rgb.append(mean_rgb)
        
        if len(self.raw_rgb) > self.buffer_size:
            self.raw_rgb.pop(0)

        if len(self.raw_rgb) < self.buffer_size:
            return 0.0

        signal = np.array(self.raw_rgb)
        R = signal[:, 0]
        G = signal[:, 1]
        B = signal[:, 2]

        # CHROM mathematical projection
        X = 3 * R - 2 * G
        Y = 1.5 * R + G - 1.5 * B
        
        std_x = np.std(X)
        std_y = np.std(Y)
        if std_y == 0:
            return 0.0
            
        bvp = X - (std_x / std_y) * Y
        
        # Bandpass filter boundaries 0.75Hz (45 BPM) to 3.0Hz (180 BPM)
        nyq = 0.5 * self.fps
        low = 0.75 / nyq
        high = 3.0 / nyq
        b, a = scipy.signal.butter(4, [low, high], btype='band')
        filtered_bvp = scipy.signal.filtfilt(b, a, bvp)

        # Power Spectral Density peak extraction
        freqs = np.fft.rfftfreq(self.buffer_size, d=1.0/self.fps)
        fft_values = np.abs(np.fft.rfft(filtered_bvp))
        
        valid_indices = np.where((freqs >= 0.75) & (freqs <= 3.0))[0]
        if len(valid_indices) == 0:
            return 0.0
            
        peak_idx = valid_indices[np.argmax(fft_values[valid_indices])]
        bpm = freqs[peak_idx] * 60.0
        return float(bpm)
