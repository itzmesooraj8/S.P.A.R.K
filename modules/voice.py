import speech_recognition as sr
import pyttsx3
import threading
import queue

class VoiceModule:
    def __init__(self):
        print("🎙️ Voice Module Loading...")
        try:
            self.engine = pyttsx3.init()
            # Tuning the voice
            voices = self.engine.getProperty('voices')
            # Select a female voice if available, usually index 1 on Windows
            if len(voices) > 1:
                self.engine.setProperty('voice', voices[1].id)
            self.engine.setProperty('rate', 170) 
        except Exception as e:
            print(f"⚠️ TTS Init Error (Check audio drivers): {e}")
            self.engine = None

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Queue for speech tasks so we don't block the main thread
        self.speech_queue = queue.Queue()
        threading.Thread(target=self._speech_worker, daemon=True).start()

    def speak(self, text):
        """Adds text to the speech queue."""
        if self.engine:
            self.speech_queue.put(text)
        else:
            print(f"🔇 [Silent Mode]: {text}")

    def _speech_worker(self):
        """Consumer thread for text-to-speech."""
        while True:
            text = self.speech_queue.get()
            if text is None: break
            try:
                print(f"🗣️ S.P.A.R.K.: {text}")
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"⚠️ TTS Error: {e}")
            self.speech_queue.task_done()

    def listen(self, timeout=5):
        """Listens for a single command."""
        print("👂 Listening...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=timeout)
                command = self.recognizer.recognize_google(audio)
                print(f"🎤 You said: {command}")
                return command
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except Exception as e:
                print(f"⚠️ Mic Error: {e}")
                return None

# Singleton
voice = VoiceModule()
