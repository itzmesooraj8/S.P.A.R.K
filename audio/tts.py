import os
import pygame
import logging
import asyncio
import edge_tts

logger = logging.getLogger("SPARK_TTS")

class SparkVoice:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Voice (Microsoft Edge TTS - FREE)...")
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        # "en-GB-ThomasNeural" is a highly professional, British Jarvis-like voice.
        self.voice = "en-GB-ThomasNeural" 

    def speak(self, text):
        """Generates high-quality audio for free and plays it."""
        print(f"SPARK> {text}")
        try:
            # We must run the async Edge-TTS function inside a synchronous wrapper
            asyncio.run(self._generate_and_play(text))
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    async def _generate_and_play(self, text):
        # 1. Generate the audio file
        audio_file = "response.mp3"
        communicate = edge_tts.Communicate(text, self.voice, rate="+10%")
        await communicate.save(audio_file)
        
        # 2. Play the audio using pygame
        pygame.mixer.music.load(audio_file)
        
        # Broadcast speaking state
        import threading
        import requests
        def _send():
            try:
                requests.post("http://127.0.0.1:8000/internal/broadcast", json={"type": "voice_state", "payload": {"status": "speaking", "isListening": False}}, timeout=0.1)
            except: pass
        threading.Thread(target=_send, daemon=True).start()

        pygame.mixer.music.play()
        
        # 3. Wait for the audio to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # Broadcast idle state
        def _send_idle():
            try:
                requests.post("http://127.0.0.1:8000/internal/broadcast", json={"type": "voice_state", "payload": {"status": "idle", "isListening": False}}, timeout=0.1)
            except: pass
        threading.Thread(target=_send_idle, daemon=True).start()
            
        # 4. Unload and clean up the file
        pygame.mixer.music.unload()
        try:
            os.remove(audio_file)
        except OSError:
            pass

    def speak_async(self, text):
        import threading
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()
