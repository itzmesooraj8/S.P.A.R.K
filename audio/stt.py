import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base - Auto-Fallback)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 2.0 
        
        # Try to calibrate using the default microphone
        try:
            with sr.Microphone(sample_rate=16000) as source:
                logger.info("🎤 CALIBRATING DEFAULT MICROPHONE... Please remain silent for 2 seconds...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.recognizer.energy_threshold += 150 
                logger.info(f"✅ Calibration complete. Base threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Failed to calibrate default microphone. Error: {e}")
            logger.info("Will attempt raw capture during listen phase.")

    def _process_audio(self, audio):
        """Helper function to process the audio and handle hallucinations."""
        audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
        
        # Strong primer
        primer = "Command S.P.A.R.K. to open YouTube, check the time, or execute an application."
        
        result = self.model.transcribe(
            audio_data, 
            fp16=False, 
            language="en",
            initial_prompt=primer,
            condition_on_previous_text=False,
            no_speech_threshold=0.6 
        )
        
        text = result["text"].strip()
        text_lower = text.lower()
        
        # Word count filter
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
        """Attempts to listen using the default microphone."""
        try:
            # We explicitly do NOT pass a device_index here. We let Windows choose the default.
            with sr.Microphone(sample_rate=16000) as source:
                try:
                    # Extended timeout to 15 seconds, phrase limit to 30
                    audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=30)
                    return self._process_audio(audio)
                    
                except sr.WaitTimeoutError:
                    return "TIMEOUT"
                except Exception as e:
                    logger.error(f"STT Error during listening: {e}")
                    return None
        except Exception as e:
            logger.error(f"Failed to access default microphone. Error: {e}")
            return None
