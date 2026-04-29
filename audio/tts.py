import threading

import pyttsx3


class SparkVoice:
    def __init__(self):
        print("Initializing S.P.A.R.K. Voice (pyttsx3)...")
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty("voices")
        if voices:
            self.engine.setProperty("voice", voices[0].id)
        self.engine.setProperty("rate", 170)

    def speak(self, text):
        print(f"SPARK> {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def speak_async(self, text):
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()
