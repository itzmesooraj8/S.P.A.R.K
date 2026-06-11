"""Remote photoplethysmography telemetry for somatic biometrics."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

import numpy as np

try:
    import scipy.signal as sps
except Exception:  # pragma: no cover - optional dependency fallback
    sps = None

logger = logging.getLogger("SPARK_BIOMETRIC_TELEMETRY")


@dataclass(slots=True)
class VitalsSample:
    timestamp: str
    heart_rate_bpm: float
    filtered_trace: np.ndarray
    green_trace: np.ndarray
    thermal_overlay: Optional[np.ndarray] = None


class BiometricTelemetryDaemon:
    """Face-mesh rPPG controller with affine thermal overlays and alert hooks."""

    def __init__(self, sample_rate: float = 30.0, trace_window: int = 300, sample_rate_fs: Optional[float] = None) -> None:
        if sample_rate_fs is not None:
            sample_rate = sample_rate_fs
        self.sample_rate = float(sample_rate)
        self.trace_window = int(trace_window)
        self.green_trace: list[float] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_sample: Optional[VitalsSample] = None

    def extract_green_trace(self, frame: np.ndarray, face_mesh_indices: Optional[np.ndarray] = None) -> float:
        frame = np.asarray(frame)
        if frame.ndim == 3 and frame.shape[-1] >= 3:
            if face_mesh_indices is not None and len(face_mesh_indices) > 0:
                points = np.asarray(face_mesh_indices, dtype=np.int64)
                points = points[(points[:, 0] >= 0) & (points[:, 1] >= 0)]
                points = points[(points[:, 0] < frame.shape[1]) & (points[:, 1] < frame.shape[0])]
                if points.size:
                    return float(np.mean(frame[points[:, 1], points[:, 0], 1]))
            return float(np.mean(frame[:, :, 1]))
        return float(np.mean(frame))

    def _butterworth_bandpass(self, data: np.ndarray, lowcut: float = 0.75, highcut: float = 4.0, order: int = 4) -> np.ndarray:
        data = np.asarray(data, dtype=np.float64).reshape(-1)
        if data.size < 8:
            return data.copy()
        if sps is None:
            spectrum = np.fft.rfft(data)
            freqs = np.fft.rfftfreq(data.size, d=1.0 / self.sample_rate)
            mask = (freqs >= lowcut) & (freqs <= highcut)
            spectrum[~mask] = 0.0
            return np.fft.irfft(spectrum, n=data.size)
        nyquist = 0.5 * self.sample_rate
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = sps.butter(order, [low, high], btype="band")
        return sps.filtfilt(b, a, data)

    def butterworth_bandpass(self, data: np.ndarray, lowcut: float = 0.75, highcut: float = 4.0, order: int = 4) -> np.ndarray:
        return self._butterworth_bandpass(data, lowcut, highcut, order)

    def extract_roi_intensity(self, frame: np.ndarray, face_mesh_indices: Optional[np.ndarray] = None) -> float:
        return self.extract_green_trace(frame, face_mesh_indices)

    def calculate_heart_rate(self, filtered_trace: np.ndarray) -> float:
        signal = np.asarray(filtered_trace, dtype=np.float64).reshape(-1)
        if signal.size < 10:
            return 0.0
        fft_out = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(signal.size, d=1.0 / self.sample_rate)
        valid = np.where((freqs >= 0.75) & (freqs <= 4.0))[0]
        if valid.size == 0:
            return 0.0
        peak = valid[int(np.argmax(np.abs(fft_out)[valid]))]
        bpm = float(freqs[peak] * 60.0)
        return bpm

    def superimpose_thermal(self, thermal_grid: np.ndarray, affine_matrix: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
        thermal_grid = np.asarray(thermal_grid)
        affine_matrix = np.asarray(affine_matrix, dtype=np.float64)
        if thermal_grid.size == 0:
            return np.zeros(target_size, dtype=np.float64)
        try:
            import cv2  # type: ignore

            return cv2.warpAffine(thermal_grid, affine_matrix[:2], target_size)
        except Exception:
            output = np.zeros(target_size, dtype=thermal_grid.dtype)
            inv = np.linalg.pinv(affine_matrix)
            height, width = target_size
            for row in range(height):
                for col in range(width):
                    src = inv @ np.array([col, row, 1.0])
                    sx, sy = int(src[0]), int(src[1])
                    if 0 <= sy < thermal_grid.shape[0] and 0 <= sx < thermal_grid.shape[1]:
                        output[row, col] = thermal_grid[sy, sx]
            return output

    def update_frame(self, frame: np.ndarray, face_mesh_indices: Optional[np.ndarray] = None, thermal_grid: Optional[np.ndarray] = None, affine_matrix: Optional[np.ndarray] = None) -> VitalsSample:
        green_value = self.extract_green_trace(frame, face_mesh_indices)
        self.green_trace.append(green_value)
        if len(self.green_trace) > self.trace_window:
            self.green_trace.pop(0)
        trace = np.asarray(self.green_trace, dtype=np.float64)
        filtered = self._butterworth_bandpass(trace)
        heart_rate = self.calculate_heart_rate(filtered)
        thermal_overlay = None
        if thermal_grid is not None and affine_matrix is not None:
            thermal_overlay = self.superimpose_thermal(thermal_grid, affine_matrix, (thermal_grid.shape[1], thermal_grid.shape[0]))
        sample = VitalsSample(
            timestamp=datetime.utcnow().isoformat(timespec="seconds"),
            heart_rate_bpm=heart_rate,
            filtered_trace=filtered,
            green_trace=trace,
            thermal_overlay=thermal_overlay,
        )
        self._latest_sample = sample
        return sample

    def record_trace(self, green_trace: np.ndarray, heart_rate_bpm: float) -> VitalsSample:
        trace = np.asarray(green_trace, dtype=np.float64).reshape(-1)
        filtered = self._butterworth_bandpass(trace)
        sample = VitalsSample(
            timestamp=datetime.utcnow().isoformat(timespec="seconds"),
            heart_rate_bpm=float(heart_rate_bpm),
            filtered_trace=filtered,
            green_trace=trace,
            thermal_overlay=None,
        )
        self._latest_sample = sample
        return sample

    def get_latest_sample(self) -> Optional[VitalsSample]:
        return self._latest_sample

    def start(self, frame_source: Callable[[], np.ndarray], on_sample: Optional[Callable[[VitalsSample], None]] = None, poll_interval_seconds: float = 1.0 / 30.0) -> None:
        if self._running:
            return
        self._running = True

        def _loop() -> None:
            while self._running:
                try:
                    sample = self.update_frame(frame_source())
                    if on_sample:
                        on_sample(sample)
                except Exception as exc:
                    logger.error("Biometric telemetry monitor fault: %s", exc)
                    try:
                        from api.server import broadcast_system_alert

                        broadcast_system_alert({"source": "biometric_telemetry", "type": "telemetry_error", "message": str(exc), "severity": "warning"})
                    except Exception:
                        pass
                time.sleep(max(0.01, float(poll_interval_seconds)))

        self._thread = threading.Thread(target=_loop, daemon=True, name="spark-biometric-telemetry")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


rPPGEngine = BiometricTelemetryDaemon
telemetry_daemon = BiometricTelemetryDaemon()


class ThermalAffineMapper:
    @staticmethod
    def warp_thermal_overlay(thermal_image: np.ndarray, affine_matrix: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
        return telemetry_daemon.superimpose_thermal(thermal_image, affine_matrix, target_size)


class ExpressionProfiler:
    def __init__(self, base_distance: float = 1.0):
        self.base_distance = base_distance

    def classify_expression(self, eyebrow_distance: float, mouth_height: float) -> str:
        focused_ratio = eyebrow_distance / (mouth_height + 1e-6)
        if mouth_height > eyebrow_distance * 1.5:
            return "Fatigued (Yawning)"
        if focused_ratio > 2.0:
            return "Focused"
        return "Neutral"
