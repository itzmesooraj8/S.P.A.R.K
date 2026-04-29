import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self, mic_index=None):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base - Iron-Clad Filter)...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        self.mic_index = mic_index
        
        # Keep dynamic off so it doesn't adapt to fans
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 1.5 # Give you 1.5 seconds to pause
        
        # Hardcode a much higher baseline threshold to ignore keyboard clacks/fans
        self.base_threshold = 400 
        
        try:
            with sr.Microphone(device_index=self.mic_index, sample_rate=16000) as source:
                logger.info("🎤 CALIBRATING MICROPHONE... Please remain silent for 2 seconds...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                # Ensure the threshold never drops below our hardcoded baseline
                self.recognizer.energy_threshold = max(self.base_threshold, self.recognizer.energy_threshold + 150)
                logger.info(f"✅ Calibration complete. Audio threshold locked at: {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Calibration failed: {e}")

    def listen(self):
        try:
            with sr.Microphone(device_index=self.mic_index, sample_rate=16000) as source:
                try:
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=20)
                    audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
                    
                    # Add a strong primer to force it into command-mode context
                    primer = "Command S.P.A.R.K. to open YouTube, check the time, or execute an application."
                    
                    result = self.model.transcribe(
                        audio_data, 
                        fp16=False, 
                        language="en",
                        initial_prompt=primer,
                        # [THE FIX] Force it to drop low-confidence hallucinations
                        condition_on_previous_text=False,
                        no_speech_threshold=0.6 
                    )
                    
                    text = result["text"].strip()
                    text_lower = text.lower()
                    
                    # --------------------------------------------------------
                    # THE IRON-CLAD FILTER
                    # --------------------------------------------------------
                    
                    # 1. Reject empty or single-word strings (unless it's a specific wake/sleep word)
                    if not text or len(text.split()) < 2:
                        # Allow specific single words
                        if text_lower not in ["shutdown", "standby"]:
                            return None
                    
                    # 2. The Hallucination Blacklist (Expanded based on your logs)
                    hallucinations = [
                        "thank you.", "though", "you", "thanks.", "bye.", "okay.", 
                        "second bill.", "viscous", "minuteines", "i'm mat", "i don't know.",
                        "thanks for watching!", "thanks for watching.", "subscribe.",
                        "pay for it to listen to me", "so tell me once when you study from india"
                    ]
                    
                    # 3. Reject if the exact string is in the blacklist
                    if text_lower in hallucinations:
                        return None
                        
                    # 4. Reject if it looks like a YouTube auto-caption hallucination
                    if "subscribe" in text_lower or "thank you for watching" in text_lower:
                         return None

                    return text
                    
                except sr.WaitTimeoutError:
                    return "TIMEOUT"
                except Exception as e:
                    logger.error(f"STT Error: {e}")
                    return None
        except Exception as e:
            logger.error(f"Mic Error: {e}")
            return None
