"""
S.P.A.R.K Contactless Biometrics & Human Telemetry Core
Implements face-mesh rPPG (Butterworth bandpass filter + FFT heart rate calculations),
FLIR thermal affine transformations, and landmark-based expression profiling.
"""

import numpy as np
import scipy.signal
import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger("SPARK_TELEMETRY")

# Optional OpenCV/MediaPipe imports
cv2 = None
try:
    import cv2 as cv
    cv2 = cv
except ImportError:
    pass

class rPPGEngine:
    """Extracts biological heart rate contactless-ly using face-mesh green channel color modulation."""
    
    def __init__(self, sample_rate_fs: float = 30.0):
        self.fs = sample_rate_fs

    def extract_roi_intensity(self, frame: np.ndarray, roi_corners: np.ndarray) -> float:
        """Aggregates green channel pixel intensities inside facial region of interest mask."""
        # Check if OpenCV is available
        if cv2 is not None and len(frame.shape) == 3:
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            cv2.fillPoly(mask, [roi_corners.astype(np.int32)], 255)
            # Calculate average intensity in the green channel (Channel 1 in BGR)
            mean_val = cv2.mean(frame, mask=mask)
            return float(mean_val[1]) # Green channel
        else:
            # Simulated aggregation return (average of green coordinates if 3D)
            if len(frame.shape) == 3:
                return float(np.mean(frame[:, :, 1]))
            return float(np.mean(frame))

    def butterworth_bandpass(self, data: np.ndarray, lowcut: float = 0.75, highcut: float = 3.3, order: int = 4) -> np.ndarray:
        """Apples a 4th-order Butterworth bandpass filter to timeseries data."""
        nyq = 0.5 * self.fs
        low = lowcut / nyq
        high = highcut / nyq
        
        # Design Butterworth filter
        b, a = scipy.signal.butter(order, [low, high], btype='band')
        # Apply forward-backward zero-phase digital filtering
        filtered = scipy.signal.filtfilt(b, a, data)
        return filtered

    def calculate_heart_rate(self, filtered_signal: np.ndarray) -> float:
        """Executes FFT and isolates the frequency peak to determine Heart Rate in BPM."""
        n = len(filtered_signal)
        if n < 10:
            return 0.0
            
        # Compute Fast Fourier Transform
        fft_out = np.fft.rfft(filtered_signal)
        freqs = np.fft.rfftfreq(n, d=1.0/self.fs)
        
        amplitudes = np.abs(fft_out)
        
        # Limit search to the bandpass window (45 - 198 BPM)
        valid_indices = np.where((freqs >= 0.75) & (freqs <= 3.3))[0]
        if len(valid_indices) == 0:
            return 0.0
            
        peak_idx = valid_indices[np.argmax(amplitudes[valid_indices])]
        peak_freq = freqs[peak_idx]
        
        # Convert Hz frequency to Beats Per Minute (BPM)
        bpm = peak_freq * 60.0
        logger.info(f"rPPG: Isolated peak frequency: {peak_freq:.2f}Hz -> Heart Rate: {bpm:.1f} BPM")
        return float(bpm)

class ThermalAffineMapper:
    """Applies affine transforms to map thermal matrices onto visible camera coordinate spaces."""
    
    @staticmethod
    def warp_thermal_overlay(thermal_image: np.ndarray, affine_matrix: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """Warps thermal array frames using an affine transformation matrix."""
        if cv2 is not None:
            # OpenCV warpAffine
            return cv2.warpAffine(thermal_image, affine_matrix[:2], target_size)
        else:
            # NumPy matrix transformation fallback
            logger.info("Telemetry: Executing fallback affine overlay projection.")
            h, w = target_size
            warped = np.zeros((h, w), dtype=thermal_image.dtype)
            
            # Simple affine warping implementation via mapping matrix inverse
            try:
                inv_aff = np.linalg.inv(affine_matrix)
                for y in range(h):
                    for x in range(w):
                        src = inv_aff @ np.array([x, y, 1])
                        sx, sy = int(src[0]), int(src[1])
                        if 0 <= sx < thermal_image.shape[1] and 0 <= sy < thermal_image.shape[0]:
                            warped[y, x] = thermal_image[sy, sx]
            except np.linalg.LinAlgError:
                pass
            return warped

class ExpressionProfiler:
    """Evaluates facial expression fatigue signatures using coordinate landmark vectors."""
    
    def __init__(self, base_distance: float = 1.0):
        self.base_distance = base_distance

    def classify_expression(self, eyebrow_distance: float, mouth_height: float) -> str:
        """Classifies expression based on landmark spacing metrics."""
        # High eye-mouth distance ratio indicators
        focused_ratio = eyebrow_distance / (mouth_height + 1e-6)
        
        if mouth_height > eyebrow_distance * 1.5:
            return "Fatigued (Yawning)"
        elif focused_ratio > 2.0:
            return "Focused"
        return "Neutral"
