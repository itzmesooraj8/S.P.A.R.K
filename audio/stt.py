import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

# Suppress FP16 and Numpy warnings for a clean terminal
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base - IN-MEMORY PIPELINE)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        
        # Enterprise calibration: High energy threshold prevents picking up breathing/fans
        self.recognizer.energy_threshold = 500 
        self.recognizer.dynamic_energy_threshold = False # Fixed threshold is more stable
        self.recognizer.pause_threshold = 0.8 # Faster response time after you stop speaking
        
    def listen(self):
        # Force 16kHz sample rate, which is the exact frequency Whisper requires
        with sr.Microphone(sample_rate=16000) as source:
            # We remove the print("Listening...") spam from here.
            # The system should listen silently in the background.
            self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
            
            try:
                # Capture audio to RAM
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=15)
                
                # --------------------------------------------------------
                # [THE FIX] IN-MEMORY CONVERSION (NO DISK I/O)
                # Convert the raw bytes into a flat, 32-bit float NumPy array
                # --------------------------------------------------------
                audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
                
                # Pass the RAM buffer directly to Whisper
                result = self.model.transcribe(audio_data, fp16=False)
                text = result["text"].strip()
                
                # Hard-filter Whisper's common hallucinations when it hears dead silence
                hallucinations = ["thank you.", "though", "you", "thanks.", "bye.", "okay."]
                if not text or len(text) < 2 or text.lower() in hallucinations:
                    return None
                    
                return text
                
            except sr.WaitTimeoutError:
                # Silent timeout. Just return None and let the loop continue instantly.
                return None
            except Exception as e:
                logger.error(f"Memory STT Error: {e}")
                return None
