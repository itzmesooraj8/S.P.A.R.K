"""
SPARK Wake Word Listener
────────────────────────────────────────────────────────────────────────────────
Runs openwakeword on a continuous microphone stream in a background thread.
Detects "Hey SPARK" (using 'hey spark' as placeholder) and publishes events.
"""

import threading
import time
import numpy as np
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from openwakeword.model import Model as _Model  # noqa: F401

try:
    import sounddevice as sd
    SOUNDDEVICE_OK = True
except ImportError:
    SOUNDDEVICE_OK = False
    sd = None

try:
    from openwakeword.model import Model  # type: ignore[import-untyped]
    OPENWAKEWORD_OK = True
except ImportError:
    OPENWAKEWORD_OK = False
    Model = None  # type: ignore[assignment,misc]


class WakeWordListener:
    """
    Listens for wake word on a continuous audio stream.
    Runs in a background daemon thread.
    """
    
    # Configuration
    SAMPLE_RATE = 16000  # openwakeword expects 16kHz
    CHUNK_DURATION_MS = 100  # Process 100ms chunks
    CHUNK_SIZE = (SAMPLE_RATE * CHUNK_DURATION_MS) // 1000  # 1600 samples per chunk
    DETECTION_THRESHOLD = 0.5  # Confidence score (0-1) required to trigger
    
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.model: Optional[object] = None  # openwakeword.model.Model when loaded
        self.stream = None
        
        # Model key must match the .onnx filename stem (e.g. hey_spark_v0.1.onnx → "hey_spark_v0.1")
        # Swap for a custom "hey_spark" model once trained.
        self.wake_word_name = "alexa"
        # Human-readable name shown in logs and broadcast to the frontend
        self.display_name = "Alexa"
    
    def start(self):
        """Start the wake word listener in a background daemon thread."""
        if not SOUNDDEVICE_OK:
            print("⚠️ [WakeWord] sounddevice not installed — wake word disabled")
            return
        
        if not OPENWAKEWORD_OK:
            print("⚠️ [WakeWord] openwakeword not installed — wake word disabled")
            return
        
        if self.running:
            print("⚠️ [WakeWord] Already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_detection_loop, daemon=True)
        self.thread.start()
        print("🎤 [WakeWord] Listener started in background thread")
    
    def stop(self):
        """Stop the wake word listener."""
        self.running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        print("🎤 [WakeWord] Listener stopped")
    
    def _run_detection_loop(self):
        """
        Main detection loop — runs in background thread.
        Continuously captures audio and runs inference.
        """
        try:
            # Initialize openwakeword model
            self.model = Model(
                wakeword_models=[self.wake_word_name],
                inference_framework="onnx"
            )
            
            # Open audio stream
            self.stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                blocksize=self.CHUNK_SIZE,
                dtype=np.float32
            )
            self.stream.start()
            print(f"🎤 [WakeWord] Audio stream opened – listening for '{self.display_name}'")
            
            # Inference loop
            while self.running:
                try:
                    # Read audio chunk
                    chunk, overflowed = self.stream.read(self.CHUNK_SIZE)
                    
                    if overflowed:
                        # Audio buffer overflowed; skip this chunk
                        continue
                    
                    # Flatten to 1D if needed
                    if chunk.ndim > 1:
                        chunk = chunk.squeeze()
                    
                    # Run inference
                    prediction = self.model.predict(chunk)
                    
                    # prediction is a dict: {'model_name': confidence_score}
                    confidence = prediction.get(self.wake_word_name, 0.0)
                    
                    # Check for wake word detection
                    if confidence > self.DETECTION_THRESHOLD:
                        print(f"🎤 [WakeWord] DETECTED '{self.display_name}' (confidence: {confidence:.2f})")
                        self._publish_wake_word_event(confidence)
                    
                except Exception as audio_err:
                    print(f"⚠️ [WakeWord] Audio processing error: {audio_err}")
                    # Continue listening despite transient errors
                    time.sleep(0.1)
        
        except Exception as init_err:
            print(f"❌ [WakeWord] Initialization failed: {init_err}")
            print("   Audio will not trigger Command Bar. Voice input available via explicit mic button.")
            self.running = False
    
    def _publish_wake_word_event(self, confidence: float):
        """
        Publish WAKE_WORD_DETECTED event via WebSocket.
        """
        try:
            from ws.manager import ws_manager
        except ImportError:
            print("⚠️ [WakeWord] WebSocket manager not available")
            return
        
        import asyncio
        import time as time_module
        
        try:
            # Broadcast to all connected sessions
            asyncio.create_task(ws_manager.broadcast_json({
                "type": "WAKE_WORD_DETECTED",
                "wake_word": self.display_name,
                "confidence": round(confidence, 3),
                "timestamp": time_module.time() * 1000,
            }, "system"))
        except Exception as broadcast_err:
            print(f"⚠️ [WakeWord] Failed to broadcast event: {broadcast_err}")


# Singleton instance
_wakeword_listener: Optional[WakeWordListener] = None


def start_wakeword_listener():
    """Initialize and start the wake word listener."""
    global _wakeword_listener
    
    if _wakeword_listener is None:
        _wakeword_listener = WakeWordListener()
    
    _wakeword_listener.start()


def stop_wakeword_listener():
    """Stop the wake word listener."""
    global _wakeword_listener
    if _wakeword_listener:
        _wakeword_listener.stop()
