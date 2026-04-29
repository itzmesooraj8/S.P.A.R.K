import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base - Mark 4)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        
        # Set a fixed safe floor and let it auto-adjust
        self.recognizer.energy_threshold = 80 
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0 # 1 second of silence marks the end of a sentence
        
        # [THE ENTERPRISE FIX: STARTUP CALIBRATION]
        with sr.Microphone(sample_rate=16000) as source:
            logger.info("🎤 CALIBRATING MICROPHONE... Please remain silent for 1 second...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info(f"✅ Calibration complete. Base threshold: {self.recognizer.energy_threshold}")

    def listen(self):
        with sr.Microphone(sample_rate=16000) as source:
            try:
                # Wait up to 5 seconds for you to start speaking
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=20)
                
                # Pure RAM translation. No disk writing. No temp files.
                audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
                
                # Force English to stop hallucinated language switching
                result = self.model.transcribe(audio_data, fp16=False, language="en")
                text = result["text"].strip()
                text_lower = text.lower()
                
                # The Iron-Clad Blacklist
                hallucinations = [
                    "thank you.", "though", "you", "thanks.", "bye.", "okay.", 
                    "second bill.", "viscous", "minuteines", "i'm mat", "i don't know.",
                    "thanks for watching!", "thanks for watching.", "subscribe."
                ]
                
                if not text or len(text) <= 2 or text_lower in hallucinations:
                    return None
                    
                return text
                
            except sr.WaitTimeoutError:
                # If you don't speak for 5 seconds, return "TIMEOUT" so the brain knows to go to sleep
                return "TIMEOUT"
            except Exception as e:
                logger.error(f"STT Error: {e}")
                return None
