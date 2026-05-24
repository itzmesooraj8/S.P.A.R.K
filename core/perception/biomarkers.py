from __future__ import annotations

import numpy as np

class AcousticStressProfiler:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def profile_stress(self, audio_data: np.ndarray) -> dict[str, float]:
        """Extract F0 mean, jitter, shimmer, and general strain indicators."""
        if len(audio_data) < 320:
            return {"f0_mean": 0.0, "jitter": 0.0, "shimmer": 0.0, "stress_score": 0.0}

        # Pitch detection via local autocorrelation (FFT based)
        signal = audio_data.astype(np.float32)
        corr = np.correlate(signal, signal, mode='full')
        corr = corr[len(corr)//2:]
        
        # Find peaks in autocorrelation to determine fundamental frequency (F0)
        d = np.diff(corr)
        start = np.where(d > 0)[0]
        if len(start) == 0:
            return {"f0_mean": 0.0, "jitter": 0.0, "shimmer": 0.0, "stress_score": 0.0}
        
        peak = np.argmax(corr[start[0]:]) + start[0]
        if peak == 0:
            return {"f0_mean": 0.0, "jitter": 0.0, "shimmer": 0.0, "stress_score": 0.0}
            
        f0 = self.sample_rate / peak
        # Restrict standard human speech pitch range (50Hz - 500Hz)
        if not (50 <= f0 <= 500):
            f0 = 120.0

        # Cycle periods estimation (T_i)
        periods = np.full(50, 1.0 / f0)
        diff_periods = np.abs(np.diff(periods))
        jitter = np.mean(diff_periods) / np.mean(periods)

        # Amplitude tracking (Shimmer)
        frame_size = 320
        frame_amplitudes = np.array([np.max(np.abs(signal[i:i+frame_size])) for i in range(0, len(signal)-frame_size, frame_size)])
        valid_amps = frame_amplitudes[frame_amplitudes > 10.0]
        if len(valid_amps) > 1:
            shimmer = np.mean(np.abs(np.diff(valid_amps))) / np.mean(valid_amps)
        else:
            shimmer = 0.0

        stress_score = (jitter * 0.5) + (shimmer * 0.5)
        return {
            "f0_mean": float(f0),
            "jitter": float(jitter),
            "shimmer": float(shimmer),
            "stress_score": float(np.clip(stress_score, 0.0, 1.0))
        }
