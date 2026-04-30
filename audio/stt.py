import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base - Confidence Gated)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 1.5 
        
        self.base_threshold = 400 
        
        try:
            with sr.Microphone(sample_rate=16000) as source:
                logger.info("🎤 CALIBRATING MICROPHONE...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.recognizer.energy_threshold = max(self.base_threshold, self.recognizer.energy_threshold + 150)
                logger.info(f"✅ Calibration complete. Threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Calibration failed: {e}")

    def _process_audio(self, audio):
        """Processes audio with confidence gating to prevent hallucinations."""
        audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
        
        primer = "Command S.P.A.R.K. to open YouTube, check the time, or execute an application."
        
        # We use a lower level call or inspect result to get confidence
        result = self.model.transcribe(
            audio_data, 
            fp16=False, 
            language="en",
            initial_prompt=primer,
            condition_on_previous_text=False,
            # We want more metadata for confidence gating
            verbose=None
        )
        
        text = result["text"].strip()
        text_lower = text.lower()
        
        # --- CONFIDENCE GATING ---
        # Whisper segments contain no_speech_prob
        segments = result.get("segments", [])
        if segments:
            # Check for silent/noisy audio
            avg_no_speech_prob = sum(s.get("no_speech_prob", 0) for s in segments) / len(segments)
            # If no_speech_prob is high, it's likely background noise or a hallucination
            if avg_no_speech_prob > 0.5:
                logger.warning(f"Low confidence (no_speech_prob: {avg_no_speech_prob:.2f}). Dropping transcription: '{text}'")
                return "LOW_CONFIDENCE"
        
        # Word count filter (Mark 4.4 logic)
        if not text or len(text.split()) < 2:
            if text_lower not in ["shutdown", "standby"]:
                return None
        
        # Hallucination Blacklist
        hallucinations = [
            "thank you.", "though", "you", "thanks.", "bye.", "okay.", 
            "second bill.", "viscous", "minuteines", "i'm mat", "i don't know.",
            "thanks for watching!", "thanks for watching.", "subscribe.",
            "pay for it to listen to me", "so tell me once when you study from india"
        ]
        
        if text_lower in hallucinations or "subscribe" in text_lower or "thank you for watching" in text_lower:
            return None

        return text

    def listen(self):
        try:
            with sr.Microphone(sample_rate=16000) as source:
                try:
                    audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=30)
                    return self._process_audio(audio)
                except sr.WaitTimeoutError:
                    return "TIMEOUT"
                except Exception as e:
                    logger.error(f"STT Error: {e}")
                    return None
        except Exception as e:
            logger.error(f"Mic Error: {e}")
            return None
