"""
Voice I/O Integration (Whisper, ElevenLabs)
Stub for ASR and TTS.
"""

import sounddevice as sd
import numpy as np
import whisper
import os

class VoiceIO:
    def __init__(self):
        self.samplerate = 16000
        self.duration = 5  # seconds
        # Load the local Whisper model from the whisper directory (use 'medium' for higher accuracy)
        self.model = whisper.load_model("medium", download_root=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../whisper')))

    def record_audio(self):
        print("Listening... Speak now.")
        audio = sd.rec(int(self.duration * self.samplerate), samplerate=self.samplerate, channels=1, dtype='int16')
        sd.wait()
        return audio.flatten()

    def save_wav(self, audio, filename):
        import wave
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())

    def transcribe(self):
        audio = self.record_audio()
        wav_path = "temp.wav"
        self.save_wav(audio, wav_path)
        print("Transcribing with local Whisper model...")
        result = self.model.transcribe(wav_path)
        text = result.get("text", "")
        print("You said:", text)
        return text

    def synthesize(self, text):
        # Use ElevenLabs for TTS
        pass
