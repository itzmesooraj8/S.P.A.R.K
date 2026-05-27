"""Acoustic predictive diagnostics and cycle aging history logging."""

from __future__ import annotations

import logging
import math
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from core.db_partitioner import DatabasePartitioner

logger = logging.getLogger("SPARK_PREDICTIVE_DIAGNOSTICS")


class PredictiveDiagnosticsEngine:
    def __init__(self, sample_rate: int = 16000, n_mels: int = 64, partitioner: Optional[DatabasePartitioner] = None) -> None:
        self.sample_rate = int(sample_rate)
        self.n_mels = int(n_mels)
        self.partitioner = partitioner or DatabasePartitioner()
        self._monitor_running = False
        self._monitor_thread: Optional[threading.Thread] = None

    @staticmethod
    def _hann_window(length: int) -> np.ndarray:
        return np.hanning(length).astype(np.float64)

    def _stft(self, waveform: np.ndarray, fft_size: int = 512, hop_length: int = 256) -> np.ndarray:
        waveform = np.asarray(waveform, dtype=np.float64).reshape(-1)
        if waveform.size < fft_size:
            waveform = np.pad(waveform, (0, fft_size - waveform.size))
        window = self._hann_window(fft_size)
        frames = []
        for start in range(0, waveform.size - fft_size + 1, hop_length):
            frame = waveform[start : start + fft_size] * window
            frames.append(np.fft.rfft(frame))
        if not frames:
            frames.append(np.fft.rfft(waveform[:fft_size] * window))
        return np.stack(frames, axis=1)

    def _mel_filter_bank(self, n_fft_bins: int) -> np.ndarray:
        nyquist = self.sample_rate / 2.0
        mel_min = 2595.0 * math.log10(1.0)
        mel_max = 2595.0 * math.log10(1.0 + nyquist / 700.0)
        mel_points = np.linspace(mel_min, mel_max, self.n_mels + 2)
        hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)
        bin_points = np.floor((n_fft_bins - 1) * hz_points / nyquist).astype(int)
        filters = np.zeros((self.n_mels, n_fft_bins), dtype=np.float64)
        for mel_index in range(1, self.n_mels + 1):
            left, center, right = bin_points[mel_index - 1 : mel_index + 2]
            left = max(0, min(left, n_fft_bins - 1))
            center = max(left + 1, min(center, n_fft_bins - 1))
            right = max(center + 1, min(right, n_fft_bins))
            for bin_index in range(left, center):
                filters[mel_index - 1, bin_index] = (bin_index - left) / max(1, center - left)
            for bin_index in range(center, right):
                filters[mel_index - 1, bin_index] = (right - bin_index) / max(1, right - center)
        return filters

    def mel_spectrogram(self, waveform: np.ndarray, fft_size: int = 512, hop_length: int = 256) -> np.ndarray:
        spectrum = self._stft(waveform, fft_size=fft_size, hop_length=hop_length)
        magnitude = np.abs(spectrum) ** 2
        filters = self._mel_filter_bank(magnitude.shape[0])
        mel_spec = filters @ magnitude
        return np.log1p(np.maximum(mel_spec, 0.0))

    def detect_chatter(self, waveform: np.ndarray) -> Tuple[bool, float, np.ndarray]:
        mel_spec = self.mel_spectrogram(waveform)
        high_band = mel_spec[int(self.n_mels * 0.7) :, :]
        mean_energy = float(np.mean(high_band)) if high_band.size else 0.0
        threshold = 0.75
        chatter = mean_energy > threshold
        confidence = min(1.0, mean_energy / (threshold + 1e-6))
        return chatter, confidence, mel_spec

    def log_cycle(self, component: str, temperature_c: float, duration_seconds: float, signal_quality: float) -> Dict[str, Any]:
        arrhenius_factor = math.exp(max(0.0, (temperature_c - 20.0) / 120.0))
        fatigue_index = float(duration_seconds) * arrhenius_factor * (1.0 + max(0.0, 1.0 - signal_quality))
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "component": component,
            "temperature_c": float(temperature_c),
            "duration_seconds": float(duration_seconds),
            "signal_quality": float(signal_quality),
            "arrhenius_factor": float(arrhenius_factor),
            "fatigue_index": fatigue_index,
        }
        try:
            self.partitioner.log_runtime_event("INFO", "arrhenius_cycle", str(payload))
        except Exception as exc:
            logger.debug("Cycle log persistence skipped: %s", exc)
        return payload

    def start_monitoring(
        self,
        sensor_source: Callable[[], np.ndarray],
        on_alert: Optional[Callable[[Dict[str, Any]], None]] = None,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        if self._monitor_running:
            return
        self._monitor_running = True

        def _loop() -> None:
            while self._monitor_running:
                try:
                    waveform = np.asarray(sensor_source(), dtype=np.float64)
                    chatter, confidence, mel_spec = self.detect_chatter(waveform)
                    if chatter:
                        alert = {
                            "type": "predictive_diagnostics_alert",
                            "confidence": confidence,
                            "mel_shape": list(mel_spec.shape),
                            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
                        }
                        try:
                            from api.server import broadcast_system_alert

                            broadcast_system_alert({"source": "predictive_diagnostics", **alert})
                        except Exception:
                            pass
                        if on_alert:
                            on_alert(alert)
                    self.log_cycle("spindle", 40.0 + confidence * 10.0, poll_interval_seconds, 1.0 - confidence)
                except Exception as exc:
                    logger.error("Predictive diagnostics monitor fault: %s", exc)
                    try:
                        from api.server import broadcast_system_alert

                        broadcast_system_alert(
                            {
                                "source": "predictive_diagnostics",
                                "type": "predictive_diagnostics_error",
                                "message": str(exc),
                                "severity": "warning",
                            }
                        )
                    except Exception:
                        pass
                    if on_alert:
                        try:
                            on_alert({"type": "predictive_diagnostics_error", "message": str(exc)})
                        except Exception:
                            pass
                time.sleep(max(0.01, float(poll_interval_seconds)))

        self._monitor_thread = threading.Thread(target=_loop, daemon=True, name="spark-predictive-diagnostics")
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

    def generate_spectrogram(self, waveform: np.ndarray) -> np.ndarray:
        return self.mel_spectrogram(waveform)

    def detect_bearing_chatter(self, spectrogram: np.ndarray) -> Tuple[bool, float]:
        high_band = spectrogram[int(self.n_mels * 0.7) :, :]
        mean_energy = float(np.mean(high_band)) if high_band.size else 0.0
        threshold = 0.75
        is_anomalous = mean_energy > threshold
        confidence = min(1.0, mean_energy / (threshold + 1e-6))
        return is_anomalous, confidence


class AcousticAnomalyDetector(PredictiveDiagnosticsEngine):
    pass


class ThermalFatigueTracker:
    def __init__(self, db_path: str = "knowledge_base/fatigue_tracker.db"):
        self.db_path = db_path
        self.partitioner = DatabasePartitioner()

    def log_operational_cycle(self, component: str, temp: float, duration: float) -> Tuple[float, bool]:
        payload = PredictiveDiagnosticsEngine(partitioner=self.partitioner).log_cycle(component, temp, duration, 1.0)
        fatigue = float(payload["fatigue_index"])
        return fatigue, fatigue > 10000.0


class DegradationCalibrator:
    def __init__(self, tolerance_threshold: float = 0.05):
        self.tolerance_threshold = float(tolerance_threshold)

    def evaluate_run(self, actual_dimensions: np.ndarray, expected_dimensions: np.ndarray) -> Dict[str, Any]:
        deviation = np.asarray(actual_dimensions, dtype=np.float64) - np.asarray(expected_dimensions, dtype=np.float64)
        avg_deviation = float(np.mean(np.abs(deviation)))
        recalibration_required = avg_deviation > self.tolerance_threshold
        calibration_steps: List[str] = []
        if recalibration_required:
            for idx, axis_name in enumerate(["X", "Y", "Z"]):
                axis_dev = float(np.mean(deviation[:, idx])) if deviation.ndim > 1 else float(deviation[idx])
                if abs(axis_dev) > self.tolerance_threshold:
                    calibration_steps.append(f"M92 {axis_name.lower()}_offset {(-axis_dev):+.3f}")
        return {
            "recalibration_required": bool(recalibration_required),
            "average_deviation_mm": avg_deviation,
            "suggested_calibration_gcode": calibration_steps,
        }
