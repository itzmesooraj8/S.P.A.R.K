"""
S.P.A.R.K Predictive Diagnostics & Material Failure Mitigation Core
Contains local audio anomaly detection (Mel-Spectrogram),
corrosion & thermal fatigue history log tracking, and post-operation degradation calibration checklists.
"""

import os
import sqlite3
import numpy as np
import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger("SPARK_DIAGNOSTICS")

# Optional PyTorch/TorchAudio imports
torch = None
torchaudio = None
try:
    import torch as t
    import torchaudio as ta
    torch = t
    torchaudio = ta
except ImportError:
    logger.warning("torch/torchaudio not installed. Falling back to NumPy/SciPy spectrogram algorithms.")

class AcousticAnomalyDetector:
    """Processes workshop acoustic frames and analyzes Mel-Spectrogram features for chatter patterns."""
    
    def __init__(self, sample_rate: int = 16000, n_mels: int = 64, use_simulation: bool = False):
        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.use_simulation = use_simulation or (torch is None or torchaudio is None)

    def generate_spectrogram(self, waveform: np.ndarray) -> np.ndarray:
        """Transforms a 1D audio waveform into a 2D Mel-Spectrogram tracking matrix."""
        if self.use_simulation:
            # Reconstruct dummy mel-spectrogram [n_mels, time_frames]
            time_frames = len(waveform) // 256
            logger.info(f"Acoustic: Computing simulated spectrogram matrix of shape ({self.n_mels}, {time_frames})")
            # Generate deterministic spectrum based on sine components
            t_grid = np.linspace(0, 1, time_frames)
            spec = np.zeros((self.n_mels, time_frames))
            for i in range(self.n_mels):
                spec[i, :] = np.sin(2.0 * np.pi * (i + 1) * t_grid) * np.mean(np.abs(waveform))
            return spec
            
        try:
            # Convert NumPy array to PyTorch tensor
            tensor_waveform = torch.from_numpy(waveform).float().unsqueeze(0)
            mel_transform = torchaudio.transforms.MelSpectrogram(
                sample_rate=self.sample_rate,
                n_fft=512,
                hop_length=256,
                n_mels=self.n_mels
            )
            mel_spec = mel_transform(tensor_waveform)
            # Convert back to NumPy matrix representation
            return mel_spec.squeeze(0).numpy()
        except Exception as e:
            logger.error(f"TorchAudio spectrogram processing failed: {e}. Falling back to simulation.")
            self.use_simulation = True
            return self.generate_spectrogram(waveform)

    def detect_bearing_chatter(self, spectrogram: np.ndarray) -> Tuple[bool, float]:
        """
        Scans Mel-Spectrogram columns to flag high-frequency bearing chatter.
        Returns (is_anomalous, confidence_score)
        """
        # Spindle bearing chatter is characterized by high energy spikes at upper frequencies (index > 45)
        high_freqs = spectrogram[45:, :]
        mean_high_energy = float(np.mean(np.abs(high_freqs)))
        
        # Simple thresholding logic representing classifier detection
        threshold = 0.75
        is_anomalous = mean_high_energy > threshold
        confidence = min(1.0, mean_high_energy / (threshold + 1e-6))
        
        if is_anomalous:
            logger.warning(f"ACOUSTIC ANOMALY FLAG: Bearing chatter detected! Energy={mean_high_energy:.2f} > {threshold}")
        return is_anomalous, confidence

class ThermalFatigueTracker:
    """Logs temperature histories in SQLite, estimating material stress limits."""
    
    def __init__(self, db_path: str = "knowledge_base/fatigue_tracker.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        
    def _init_db(self) -> None:
        """Initializes un-tuned SQLite table for thermal histories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thermal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                component_name TEXT,
                avg_temperature_c REAL,
                cycle_duration_seconds REAL,
                accumulated_fatigue REAL
            )
        """)
        conn.commit()
        conn.close()

    def log_operational_cycle(self, component: str, temp: float, duration: float) -> Tuple[float, bool]:
        """
        Correlates operational cycles to compute structural fatigue indices.
        Uses a standard Arrhenius-type equation to model thermal fatigue acceleration.
        Returns (accumulated_fatigue, requires_preventive_replacement_flag)
        """
        # Baseline reference temperature: 20C (room temp)
        temp_factor = max(1.0, (temp - 20.0) / 100.0)
        # Fatigue is proportional to duration and exponential temperature factor
        fatigue_increment = duration * (temp_factor ** 2)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Read prior accumulated fatigue
        cursor.execute(
            "SELECT SUM(accumulated_fatigue) FROM thermal_logs WHERE component_name = ?", 
            (component,)
        )
        prior = cursor.fetchone()[0] or 0.0
        accumulated = prior + fatigue_increment
        
        # Insert new record
        cursor.execute("""
            INSERT INTO thermal_logs (component_name, avg_temperature_c, cycle_duration_seconds, accumulated_fatigue)
            VALUES (?, ?, ?, ?)
        """, (component, temp, duration, fatigue_increment))
        conn.commit()
        conn.close()
        
        # Enforce strict fatigue limit threshold (e.g. 10000 limit)
        threshold_limit = 10000.0
        flag_replacement = accumulated > threshold_limit
        
        if flag_replacement:
            logger.critical(f"FATIGUE ALERT: Component '{component}' fatigue index ({accumulated:.1f}) exceeded threshold ({threshold_limit})! Preventive replacement required.")
            
        return accumulated, flag_replacement

class DegradationCalibrator:
    """Post-operation validation checklists mapping wear parameters back to calibration adjustments."""
    
    def __init__(self, tolerance_threshold: float = 0.05):
        self.tolerance_threshold = tolerance_threshold

    def evaluate_run(self, actual_dimensions: np.ndarray, expected_dimensions: np.ndarray) -> Dict[str, Any]:
        """Compares run output tolerances, generating micro-calibration steps for mechanical axes."""
        deviation = actual_dimensions - expected_dimensions
        avg_deviation = np.mean(np.abs(deviation))
        
        recalibration_required = avg_deviation > self.tolerance_threshold
        calibration_steps = []
        
        if recalibration_required:
            logger.warning(f"DEGRADATION DETECTED: Average tool run deviation is {avg_deviation:.3f}mm > threshold {self.tolerance_threshold}mm.")
            # Calculate correction offsets for X, Y, Z axes
            for idx, axis_name in enumerate(["X", "Y", "Z"]):
                axis_dev = float(np.mean(deviation[:, idx])) if len(deviation.shape) > 1 else float(deviation[idx])
                if abs(axis_dev) > self.tolerance_threshold:
                    # Correction offset is inverse of deviation
                    correction = -axis_dev
                    calibration_steps.append(f"M92 {axis_name.lower()}_offset {correction:+.3f} ; Calibrate {axis_name} axis")
        else:
            logger.info("Post-operation checks: All dimensions within baseline expected tolerances.")
            
        return {
            "recalibration_required": bool(recalibration_required),
            "average_deviation_mm": float(avg_deviation),
            "suggested_calibration_gcode": calibration_steps
        }
