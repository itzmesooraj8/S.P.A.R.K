import pyttsx3
import threading
import logging

logger = logging.getLogger("SPARK_TTS")

class SparkVoice:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Voice (pyttsx3 - SAPI5)...")
        try:
            # FORCE Windows Speech API to prevent routing to dead audio drivers
            self.engine = pyttsx3.init('sapi5') 
            
            # Maximize internal volume
            self.engine.setProperty('volume', 1.0)
            
            # Adjust speed for clarity
            self.engine.setProperty('rate', 165) 

            # Safely select a voice
            voices = self.engine.getProperty('voices')
            if voices:
                # Iterate and try to find a male voice (often 'David' on Windows)
                voice_set = False
                for voice in voices:
                    if "David" in voice.name:
                        self.engine.setProperty('voice', voice.id)
                        voice_set = True
                        break
                # Fallback to the first available if David isn't found
                if not voice_set:
                    self.engine.setProperty('voice', voices[0].id)
                    
        except Exception as e:
            logger.error(f"CRITICAL: Failed to initialize TTS engine. Audio will be silent. Error: {e}")

    def speak(self, text):
        """Speaks text synchronously."""
        print(f"SPARK> {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS Engine failed to play audio: {e}")

    def speak_async(self, text):
        """Speaks text in a background thread."""
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()
