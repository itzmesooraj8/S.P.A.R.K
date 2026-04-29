import subprocess
import logging
import threading

logger = logging.getLogger("SPARK_TTS")

class SparkVoice:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Voice (Native Windows PowerShell)...")

    def speak(self, text):
        """Speaks text using native Windows TTS to bypass routing issues."""
        print(f"SPARK> {text}")
        try:
            # Escape single quotes in the text to prevent PowerShell errors
            clean_text = text.replace("'", "")
            
            # Use PowerShell's built-in speech synthesizer
            ps_command = f"Add-Type -AssemblyName System.speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak('{clean_text}')"
            subprocess.run(["powershell", "-Command", ps_command], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            logger.error(f"TTS Engine failed to play audio: {e}")

    def speak_async(self, text):
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()
