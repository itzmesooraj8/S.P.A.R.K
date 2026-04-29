import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base - Mark 4.1)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        
        # Turn off dynamic threshold to prevent it from adapting to background noise and going deaf
        self.recognizer.dynamic_energy_threshold = False
        
        # [THE FIX] Increase pause threshold to 2.0 seconds. 
        # This gives you a full 2 seconds to pause between words before it thinks you are done.
        self.recognizer.pause_threshold = 2.0 
        
        # Auto-Calibration
        with sr.Microphone(sample_rate=16000) as source:
            logger.info("🎤 CALIBRATING MICROPHONE... Please remain silent for 1 second...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            # Add a slight buffer above room noise
            self.recognizer.energy_threshold += 150 
            logger.info(f"✅ Calibration complete. Base threshold: {self.recognizer.energy_threshold}")

    def listen(self):
        with sr.Microphone(sample_rate=16000) as source:
            try:
                # [THE FIX] Increase timeout to 15 seconds. 
                # This gives you 15 seconds to START speaking before it goes to sleep.
                audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=30)
                
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
                # It will only return TIMEOUT if you sit in silence for 15 full seconds
                return "TIMEOUT"
            except Exception as e:
                logger.error(f"STT Error: {e}")
                return None
