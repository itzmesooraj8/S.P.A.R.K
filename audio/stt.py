import speech_recognition as sr
import whisper
import warnings
import logging
import numpy as np

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger("SPARK_STT")

class SparkEars:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Ears (Whisper Base - Context Calibrated)...")
        # Base model is still required; tiny is too weak for regional accents
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()
        
        # [THE FIX] Re-enable dynamic thresholding so it adapts to YOUR specific laptop mic
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300 
        self.recognizer.pause_threshold = 1.0 # Give you 1 full second to pause between words
        
    def listen(self):
        with sr.Microphone(sample_rate=16000) as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                audio_data = np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0
                
                # --------------------------------------------------------
                # [THE FIX] THE CONTEXT HACK
                # By passing this prompt, we force Whisper to expect these types of words
                # and adapt its latent space to Indian English phrasing.
                # --------------------------------------------------------
                primer = "Hello S.P.A.R.K. Open YouTube. What is the time? Open calendar. My name is Sooraj. I am speaking English with an Indian accent."
                
                result = self.model.transcribe(
                    audio_data, 
                    fp16=False,
                    initial_prompt=primer
                )
                
                text = result["text"].strip()
                
                # Hard filter for absolute silence hallucinations
                if not text or len(text) < 2 or text.lower() in ["thank you.", "though", "you", "thanks.", "bye.", "okay."]:
                    return None
                    
                return text
                
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                logger.error(f"Memory STT Error: {e}")
                return None
