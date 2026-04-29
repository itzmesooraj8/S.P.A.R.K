import os
import logging
import threading
import requests
import tempfile
import pygame
import time

logger = logging.getLogger("SPARK_TTS")

class SparkVoice:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Voice (Grok TTS)...")
        self.api_key = os.getenv("XAI_VOICE_API_KEY")
        self.voice_id = "leo" # 'leo' or 'rex' for a professional JARVIS feel
        
        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")

    def speak(self, text):
        """Speaks text using Grok TTS API."""
        print(f"SPARK> {text}")
        
        if not self.api_key:
            logger.error("XAI_VOICE_API_KEY not found. Falling back to PowerShell TTS.")
            self._speak_powershell(text)
            return

        url = "https://api.x.ai/v1/tts"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "voice_id": self.voice_id,
            "language": "en"
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            # Save audio to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            
            # Play the audio using pygame
            try:
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.music.unload()
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            logger.error(f"Grok TTS Error: {e}. Falling back to PowerShell.")
            self._speak_powershell(text)

    def _speak_powershell(self, text):
        """Fallback TTS using Windows PowerShell."""
        try:
            clean_text = text.replace("'", "")
            ps_command = f"Add-Type -AssemblyName System.speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak('{clean_text}')"
            import subprocess
            subprocess.run(["powershell", "-Command", ps_command], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            logger.error(f"PowerShell TTS also failed: {e}")

    def speak_async(self, text):
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()
