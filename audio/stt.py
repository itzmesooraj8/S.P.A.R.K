from faster_whisper import WhisperModel
import os
from core.config import Config

class SpeechToText:
    def __init__(self):
        model_size = Config.WHISPER_MODEL_SIZE
        # Run on GPU with FP16
        # If no GPU, force int8 on CPU
        device = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"Loading Whisper Model ({model_size}) on {device}...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print("Whisper Model Loaded.")
        except Exception as e:
            print(f"Error loading Whisper: {e}")
            self.model = None

    def transcribe(self, audio_data):
        """
        Transcribes audio data (must be a file path or similar, Whisper handles files best).
        For stream, we might need to save to temp file or use specific stream logic.
        """
        if not self.model:
            return ""
        
        try:
            segments, info = self.model.transcribe(audio_data, beam_size=5)
            text = ""
            for segment in segments:
                # Debug Mode: Print everything
                print(f"[DEBUG RAW] Segment: '{segment.text}' (Score: {segment.avg_logprob})")
                
                # Filter low confidence (exp(-0.7) ~ 50%)
                # if segment.avg_logprob > -0.7:
                text += segment.text
            return text.strip()
        except Exception as e:
            print(f"Transcription Error: {e}")
            return ""
