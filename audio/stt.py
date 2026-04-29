import tempfile
import warnings
from pathlib import Path

import speech_recognition as sr
import whisper

warnings.filterwarnings("ignore", category=UserWarning)


class SparkEars:
    def __init__(self):
        print("Initializing S.P.A.R.K. Ears (Whisper Base)...")
        # CHANGED: 'tiny.en' to 'base.en' for much better accent recognition
        self.model = whisper.load_model("base.en")
        self.recognizer = sr.Recognizer()

        # ADDED: Calibrate energy threshold dynamically for better silence detection
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def listen(self):
        with sr.Microphone() as source:
            print("\nListening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    temp_path = Path(temp_file.name)
                    temp_file.write(audio.get_wav_data())

                try:
                    result = self.model.transcribe(str(temp_path), fp16=False, language="en")
                    text = result["text"].strip()
                    print(f"You said: {text}")
                    return text or None
                finally:
                    temp_path.unlink(missing_ok=True)
            except sr.WaitTimeoutError:
                return None
            except Exception as exc:
                print(f"[Audio Error]: {exc}")
                return None
