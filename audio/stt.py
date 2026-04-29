import speech_recognition as sr
import whisper
import warnings
import logging

# Suppress FP16 warnings
warnings.filterwarnings("ignore", category=UserWarning)
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        
        # [THE FIX] Make the microphone less sensitive to background noise
        # and wait longer before deciding you have stopped talking.
        self.recognizer.energy_threshold = 400 
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.5 # Wait 1.5s of silence before cutting off
        
    def listen(self):
        with sr.Microphone() as source:
            print("\nListening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                # [THE FIX] Increased timeout to 10 seconds.
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=20)
                
                with open("temp_audio.wav", "wb") as f:
                    f.write(audio.get_wav_data())
                
                result = self.model.transcribe("temp_audio.wav", fp16=False)
                text = result["text"].strip()
                
                # Filter out empty or hallucinated noise
                if not text or len(text) < 2 or text.lower() in ["thank you.", "though"]:
                    return None
                    
                return text
                
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                logger.error(f"[Audio Error]: {e}")
                return None
