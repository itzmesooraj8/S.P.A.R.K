import webrtcvad
from core.config import Config

class VoiceActivityDetector:
    def __init__(self, aggressiveness=3):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = Config.SAMPLE_RATE
        self.frame_duration_ms = 30 # webrtcvad supports 10, 20, 30ms frames
        self.bytes_per_frame = int(self.sample_rate * (self.frame_duration_ms / 1000.0) * 2) # 16-bit audio

    def is_speech(self, audio_frame):
        """
        Checks if the audio frame contains speech.
        Args:
            audio_frame (bytes): Raw audio data. length must correspond to 10, 20 or 30ms.
        """
        if len(audio_frame) != self.bytes_per_frame:
             # Handle incorrect frame size - silently ignore or log if critical
             # For robustness, we can just return False or buffer externally
             # But VAD requires specific frame sizes.
             return False
             
        try:
            return self.vad.is_speech(audio_frame, self.sample_rate)
        except Exception as e:
            print(f"VAD Error: {e}")
            return False
