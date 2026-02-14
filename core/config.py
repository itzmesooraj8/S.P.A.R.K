import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Core
    # WAKE_WORD_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "") # Deprecated
    WAKE_WORD_MODEL_PATH = os.getenv("WAKE_WORD_MODEL_PATH", "") # Path to .ppn file if custom
    
    # Audio
    SAMPLE_RATE = 16000
    CHANNELS = 1
    FRAME_LENGTH = 1280 # OpenWakeWord prefers chunks of 1280 samples (80ms) but handles buffering. 
                        # Keeping 512 for VAD/PyAudio compatibility, OWW handles it.
    VAD_AGGRESSIVENESS = 3  # 0-3 (3 is most aggressive in filtering non-speech)
    SILENCE_THRESHOLD_MS = 700
    
    # Models
    OLLAMA_MODEL = "llama3"
    OLLAMA_HOST = "http://localhost:11434"
    WHISPER_MODEL_SIZE = "base" # tiny, base, small, medium, large-v2
    TTS_VOICE = "en-US-ChristopherNeural" # Edge-TTS voice

    # System
    MEMORY_PATH = os.path.join(os.getcwd(), "brain_data")
    
    @staticmethod
    def validate():
        pass
