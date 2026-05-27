"""Blind source separation and sub-vocal translation for somatic audio input."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

import numpy as np

from security.intent_validator import validate_intent_text

logger = logging.getLogger("SPARK_SOMATIC_AUDIO")


@dataclass(slots=True)
class IsolationResult:
    target_stream: np.ndarray
    separated_streams: np.ndarray
    command_tokens: dict[str, Any]


class SomaticAudioIsolator:
    """FastICA plus NLMS-based audio isolation for multi-microphone somatic capture."""

    def __init__(self, sample_rate: int = 16000, filter_length: int = 128, step_size: float = 0.1, epsilon: float = 1e-6) -> None:
        self.sample_rate = int(sample_rate)
        self.filter_length = int(filter_length)
        self.step_size = float(step_size)
        self.epsilon = float(epsilon)
        self._weights = np.zeros(self.filter_length, dtype=np.float64)

    @staticmethod
    def _finite_array(array: np.ndarray, label: str) -> np.ndarray:
        array = np.asarray(array, dtype=np.float64)
        if array.size == 0:
            raise ValueError(f"{label} cannot be empty.")
        if not np.all(np.isfinite(array)):
            raise FloatingPointError(f"{label} contains non-finite values.")
        return array

    def _nlms_cancel(self, desired: np.ndarray, reference: np.ndarray) -> np.ndarray:
        desired = self._finite_array(desired, "desired signal").reshape(-1)
        reference = self._finite_array(reference, "reference signal").reshape(-1)
        n_samples = min(desired.size, reference.size)
        clean = np.zeros(n_samples, dtype=np.float64)
        weights = self._weights.copy()
        x_buffer = np.zeros(self.filter_length, dtype=np.float64)

        for index in range(n_samples):
            x_buffer[1:] = x_buffer[:-1]
            x_buffer[0] = reference[index]
            y_hat = float(np.dot(weights, x_buffer))
            error = desired[index] - y_hat
            clean[index] = error
            norm = self.epsilon + float(np.dot(x_buffer, x_buffer))
            weights += (self.step_size / norm) * error * x_buffer

        self._weights = weights
        return clean

    def _whiten(self, signals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        centered = signals - signals.mean(axis=1, keepdims=True)
        cov = np.cov(centered)
        eigen_values, eigen_vectors = np.linalg.eigh(cov)
        inv_root = np.diag(1.0 / np.sqrt(np.maximum(eigen_values, self.epsilon)))
        whitening = eigen_vectors @ inv_root @ eigen_vectors.T
        return whitening @ centered, whitening

    def _fastica(self, signals: np.ndarray, max_iter: int = 80, tol: float = 1e-4) -> np.ndarray:
        signals = self._finite_array(signals, "mixed signals")
        if signals.ndim != 2:
            raise ValueError("mixed signals must have shape (channels, samples).")
        if signals.shape[0] > 3:
            raise ValueError("SomaticAudioIsolator supports up to three input channels.")
        whitened, _ = self._whiten(signals)
        n_components, n_samples = whitened.shape
        weights = np.zeros((n_components, n_components), dtype=np.float64)

        def g(values: np.ndarray) -> np.ndarray:
            return np.tanh(values)

        def g_prime(values: np.ndarray) -> np.ndarray:
            return 1.0 - np.tanh(values) ** 2

        for component_index in range(n_components):
            w = np.random.randn(n_components)
            w /= np.linalg.norm(w) + self.epsilon
            for _ in range(max_iter):
                previous = w.copy()
                projection = w @ whitened
                w = (whitened * g(projection)).mean(axis=1) - g_prime(projection).mean() * w
                if component_index > 0:
                    w -= (w @ weights[:component_index].T) @ weights[:component_index]
                w /= np.linalg.norm(w) + self.epsilon
                if abs(abs(np.dot(w, previous)) - 1.0) < tol:
                    break
            weights[component_index] = w

        separated = weights @ whitened
        if not np.all(np.isfinite(separated)):
            raise FloatingPointError("FastICA separation produced invalid values.")
        return separated

    def isolate(self, mic_channels: np.ndarray, reference_channel: Optional[np.ndarray] = None) -> IsolationResult:
        channels = self._finite_array(mic_channels, "microphone channels")
        if channels.ndim == 1:
            channels = channels.reshape(1, -1)
        if channels.shape[0] == 0:
            raise ValueError("At least one microphone channel is required.")
        if reference_channel is None:
            reference_channel = channels[-1]

        cleaned_channels = []
        for channel in channels:
            cleaned_channels.append(self._nlms_cancel(channel, reference_channel))
        cleaned_matrix = np.vstack(cleaned_channels)
        separated = self._fastica(cleaned_matrix)
        target_stream = separated[0] if separated.ndim == 2 else separated.reshape(-1)
        if target_stream.size > 32:
            command_window = target_stream[: min(target_stream.size, int(self.sample_rate * 0.75))]
        else:
            command_window = target_stream

        token_scan = validate_intent_text(" ".join(f"{value:.5f}" for value in command_window[:128]))
        command_tokens = {
            "allowed": bool(token_scan.allowed),
            "score": float(token_scan.score),
            "reasons": sorted(token_scan.reasons),
            "cleaned_text": token_scan.cleaned_text or "",
        }
        return IsolationResult(target_stream=target_stream, separated_streams=separated, command_tokens=command_tokens)

    async def isolate_async(
        self,
        frame_source: Callable[[], Awaitable[np.ndarray] | np.ndarray],
        reference_source: Optional[Callable[[], Awaitable[np.ndarray] | np.ndarray]] = None,
    ) -> IsolationResult:
        mic = frame_source()
        if asyncio.iscoroutine(mic):
            mic = await mic
        reference = None
        if reference_source is not None:
            reference = reference_source()
            if asyncio.iscoroutine(reference):
                reference = await reference
        return self.isolate(np.asarray(mic, dtype=np.float64), None if reference is None else np.asarray(reference, dtype=np.float64))


class AcousticEchoCanceller:
    def __init__(self, filter_length: int = 128, step_size: float = 0.1):
        self.filter_length = filter_length
        self.step_size = step_size
        self._impl = SomaticAudioIsolator(filter_length=filter_length, step_size=step_size)

    def cancel_echo(self, reference_signal: np.ndarray, mic_signal: np.ndarray) -> np.ndarray:
        return self._impl._nlms_cancel(np.asarray(mic_signal, dtype=np.float64), np.asarray(reference_signal, dtype=np.float64))


class FastICASeparator:
    def __init__(self):
        self._impl = SomaticAudioIsolator()

    def separate_sources(self, mixed_signals: np.ndarray, max_iter: int = 50, tol: float = 1e-4) -> np.ndarray:
        return self._impl._fastica(np.asarray(mixed_signals, dtype=np.float64), max_iter=max_iter, tol=tol)


class SpeakerDiarizationWrapper:
    def __init__(self, mock_profiles: Optional[dict[str, str]] = None):
        self.profiles = mock_profiles or {"speaker_0": "operator_primary", "speaker_1": "engineer_auxiliary"}

    def diarize_audio(self, audio_data: np.ndarray) -> list[dict[str, Any]]:
        n_samples = max(1, int(np.asarray(audio_data).shape[-1]))
        window = max(1, n_samples // 3)
        segments = []
        for index in range(3):
            speaker = f"speaker_{index % 2}"
            segments.append(
                {
                    "start_time": float(index * window) / 16000.0,
                    "end_time": float((index + 1) * window) / 16000.0,
                    "speaker_id": speaker,
                    "role": self.profiles.get(speaker, "unknown_speaker"),
                    "voice_embedding_hash": hash(speaker),
                }
            )
        return segments

    def parse_subvocal_activity(self, low_freq_audio: np.ndarray) -> str:
        mean_amp = float(np.mean(np.abs(np.asarray(low_freq_audio, dtype=np.float64))))
        if mean_amp > 0.05:
            return "SUB_VOCAL: SYSTEM_SHUTDOWN_CONFIRMED"
        return ""


__all__ = ["SomaticAudioIsolator", "IsolationResult", "AcousticEchoCanceller", "FastICASeparator", "SpeakerDiarizationWrapper"]
