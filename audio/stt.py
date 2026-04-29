import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore")
logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self, mic_index=1): # Defaulting to Index 1 (Microphone Array - AMD)
        logger.info(f"Initializing S.P.A.R.K. Ears (Whisper Base - Mark 4.2) using Mic Index {mic_index}...")
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        self.mic_index = mic_index # Store the index
        
        # Stability configuration
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 2.0 
        
        # Use the specific microphone index for calibration
        try:
            with sr.Microphone(device_index=self.mic_index, sample_rate=16000) as source:
                logger.info(f"🎤 CALIBRATING MICROPHONE [Index {self.mic_index}]... Please remain silent for 1 second...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                # Add a slight buffer above room noise
                self.recognizer.energy_threshold += 150 
                logger.info(f"✅ Calibration complete. Base threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Failed to calibrate microphone at index {self.mic_index}. Error: {e}")

    def listen(self):
        """Records raw audio directly from the specified hardware index."""
        try:
            with sr.Microphone(device_index=self.mic_index, sample_rate=16000) as source:
                try:
                    # Wait up to 15 seconds for you to start speaking
                    audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=30)
                    
                    # Pure RAM translation. No disk writing.
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
                    # Silent timeout - triggers auto-sleep in main.py
                    return "TIMEOUT"
                except Exception as e:
                    logger.error(f"STT Error during listening: {e}")
                    return None
        except Exception as e:
            logger.error(f"Failed to access microphone at index {self.mic_index} for listening. Error: {e}")
            return None
