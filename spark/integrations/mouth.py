"""
Mouth Module: Text-to-Speech using ElevenLabs (default) and Coqui TTS (backup, commented)
"""
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play

# --- Coqui TTS backup (uncomment and use in a Python 3.10/3.11 environment) ---
# from TTS.api import TTS
# import sounddevice as sd
# import numpy as np
# tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)
# def speak_coqui(text):
#     wav = tts.tts(text=text, speaker=tts.speakers[0] if hasattr(tts, 'speakers') else None)
#     sd.play(wav, tts.synthesizer.output_sample_rate)
#     sd.wait()
#     print("S.P.A.R.K. spoke the answer (Coqui TTS)!")
# ---------------------------------------------------------------------------

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "cgSgspJ2msm6clMCkdW9"
MODEL_ID = "eleven_multilingual_v2"

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


# Streaming ElevenLabs TTS
import asyncio
import sounddevice as sd
import numpy as np
import io
import pydub



async def stream_speak(text):
    """
    Async generator that yields the full ElevenLabs TTS audio as a single chunk (non-streaming, SDK limitation).
    Handles generator output from ElevenLabs SDK.
    """
    if not ELEVENLABS_API_KEY:
        print("No ElevenLabs API key found.")
        return
    audio_gen = client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        output_format="mp3_44100_128",
    )
    # If audio_gen is a generator, join all chunks
    if hasattr(audio_gen, '__iter__') and not isinstance(audio_gen, (bytes, bytearray)):
        audio_bytes = b"".join(audio_gen)
    else:
        audio_bytes = audio_gen
    audio_segment = pydub.AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
    pcm = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768.0
    yield pcm, audio_segment.frame_rate

def play_streaming_audio(chunk_iter):
    """
    Play audio chunks in real time as they are yielded from the async generator.
    """
    for pcm, sr in chunk_iter:
        sd.play(pcm, sr, blocking=True)
    sd.stop()

def speak(text):
    """
    Backward-compatible: non-streaming TTS (plays after full audio is ready).
    """
    if not ELEVENLABS_API_KEY:
        print("No ElevenLabs API key found.")
        return
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        output_format="mp3_44100_128",
    )
    play.play(audio)
    print("S.P.A.R.K. spoke the answer!")

if __name__ == "__main__":
    test_text = "Hello, I am S.P.A.R.K. and I can speak!"
    speak(test_text)
