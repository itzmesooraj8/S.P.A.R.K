import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self, mic_index=None): # Use None to let Windows decide the default device
        logger.info(f"Initializing S.P.A.R.K. Ears (Whisper Base - Mark 4.3)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        self.mic_index = mic_index
        
        # Stability configuration
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 2.0 
        
        # Calibration
        try:
            # Passing device_index=None uses the system default microphone
            with sr.Microphone(device_index=self.mic_index, sample_rate=16000) as source:
                logger.info("🎤 CALIBRATING... Please remain silent for 2 seconds...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                # Sensitive buffer
                self.recognizer.energy_threshold += 80 
                logger.info(f"✅ Calibration complete. Threshold locked at: {self.recognizer.energy_threshold:.2f}")
        except Exception as e:
            logger.error(f"Calibration failed: {e}")

    def listen(self):
        """Records raw audio directly from the hardware."""
        try:
            with sr.Microphone(device_index=self.mic_index, sample_rate=16000) as source:
                try:
                    # Wait up to 15 seconds for you to start speaking
                    audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=30)
                    
                    # Pure RAM translation
                    audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
                    
                    # Force English
                    result = self.model.transcribe(audio_data, fp16=False, language="en")
                    text = result["text"].strip()
                    text_lower = text.lower()
                    
                    hallucinations = [
                        "thank you.", "though", "you", "thanks.", "bye.", "okay.", 
                        "second bill.", "viscous", "minuteines", "i'm mat", "i don't know.",
                        "thanks for watching!", "thanks for watching.", "subscribe."
                    ]
                    
                    if not text or len(text) <= 2 or text_lower in hallucinations:
                        return None
                        
                    return text
                    
                except sr.WaitTimeoutError:
                    return "TIMEOUT"
                except Exception as e:
                    logger.error(f"STT Error: {e}")
                    return None
        except Exception as e:
            logger.error(f"Hardware Error: {e}")
            return None
