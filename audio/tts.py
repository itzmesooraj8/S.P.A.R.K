import asyncio
import edge_tts
from core.config import Config
import pygame
import os
import time

class TextToSpeech:
    def __init__(self):
        self.voice = Config.TTS_VOICE
        self.rate = "+0%"
        self.pitch = "+0Hz"
        self.counter = 0
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init()
        except:
            pass # Already initialized

    async def speak(self, text):
        """
        Synthesizes speech to a UNIQUE file and plays it.
        """
        # Create a unique filename for this sentence
        filename = f"tts_{self.counter}.mp3"
        self.counter = (self.counter + 1) % 10 # Recycle filenames 0-9
        
        try:
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
            await communicate.save(filename)
            
            # Wait for previous audio to finish
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            # Load and play
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            # Keep this thread alive while playing so we don't delete the file too early
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            # Cleanup: Unload the file so we can delete it later
            # pygame.mixer.music.unload() only exists in pygame 2.0.2+
            # If standard unload isn't available, loading a dummy might work, but let's assume valid pygame version.
            if hasattr(pygame.mixer.music, 'unload'):
                pygame.mixer.music.unload()
            
        except Exception as e:
            print(f"TTS Error: {e}")

    def speak_non_blocking(self, text):
        import threading
        def task():
            asyncio.run(self.speak(text))
        t = threading.Thread(target=task)
        t.start()
        
    def speak_sync(self, text):
        """Synchronous wrapper for speak"""
        asyncio.run(self.speak(text))

    def stop(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            if hasattr(pygame.mixer.music, 'unload'):
                pygame.mixer.music.unload()
    
    def is_busy(self):
        return pygame.mixer.music.get_busy()
