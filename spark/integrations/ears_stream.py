
# ============================================================================== 
# S.P.A.R.K. - Final Streaming Ears (Deepgram Integration)
# Version: 2.0 (Updated for latest Deepgram API)
# ==============================================================================
import os
import json
import asyncio
import websockets
import sounddevice as sd
from core.config import settings

class DeepgramStreamer:
    def __init__(self):
        # Using centralized config
        if settings.secrets.deepgram_api_key:
            self.api_key = settings.secrets.deepgram_api_key.get_secret_value()
        else:
            self.api_key = None
            print("❌ DEEPGRAM_API_KEY missing in secrets.yaml or env!")
        self.audio_queue = asyncio.Queue()
        self.loop = None  # Will be set to the main event loop
        # --- THE MAIN FIX IS HERE ---
        # All configuration is now part of the URL.
        self.deepgram_url = (
            "wss://api.deepgram.com/v1/listen"
            "?encoding=linear16"
            "&sample_rate=16000"
            "&channels=1"
            "&interim_results=true"
            "&endpointing=800"  # Increased to 800ms for better end-of-speech detection
            "&smart_format=true" # Helps with punctuation and formatting
            "&model=nova-2-general" # Use the latest Nova-2 model
        )
        self.headers = {
            "Authorization": f"Token {self.api_key}"
        }

    def audio_callback(self, indata, frames, time, status):
        """This function is called by the microphone for each new audio chunk."""
        if self.loop:
            self.loop.call_soon_threadsafe(self.audio_queue.put_nowait, indata.tobytes())


    async def stream_audio(self, on_partial, on_final):
        """Connects to Deepgram and streams audio with debounce on_final."""
        import time
        debounce_seconds = 0.8
        last_final_time = 0
        last_final_transcript = None
        try:
            async with websockets.connect(self.deepgram_url, additional_headers=self.headers) as ws:
                async def sender(ws):
                    print("✅ Sender started. Listening for your voice...")
                    try:
                        while True:
                            data = await self.audio_queue.get()
                            if data is None:
                                await ws.send(json.dumps({"type": "CloseStream"}))
                                break
                            await ws.send(data)
                    except Exception as e:
                        print(f"❌ Error in sender: {e}")

                async def receiver(ws):
                    print("✅ Receiver started. Waiting for transcripts...")
                    nonlocal last_final_time, last_final_transcript
                    async for msg in ws:
                        res = json.loads(msg)
                        transcript = res.get('channel', {}).get('alternatives', [{}])[0].get('transcript', '')
                        is_final = res.get("is_final")
                        now = time.time()
                        if transcript:
                            if is_final:
                                last_final_time = now
                                last_final_transcript = transcript
                                # Wait for debounce period before calling on_final
                                await asyncio.sleep(debounce_seconds)
                                # If no new final transcript has arrived, trigger on_final
                                if last_final_time == now:
                                    print("[EARS] Debounced final transcript, ending listen.")
                                    on_final(last_final_transcript)
                                    break
                            else:
                                on_partial(transcript)

                await asyncio.gather(sender(ws), receiver(ws))
        except websockets.exceptions.InvalidStatus as e:
            print(f"❌ CONNECTION FAILED (HTTP Error): {e}")
            print("This could be an API Key (401) or another connection issue. Please check your key and URL.")
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")

    def listen_stream(self, on_partial, on_final):
        """Starts the microphone and the streaming process."""
        try:
            async def runner():
                self.loop = asyncio.get_running_loop()
                with sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=self.audio_callback):
                    await self.stream_audio(on_partial, on_final)
            asyncio.run(runner())
        except KeyboardInterrupt:
            print("\n🛑 Stream stopped by user.")
            if self.loop:
                self.loop.call_soon_threadsafe(self.audio_queue.put_nowait, None)
        except Exception as e:
            print(f"❌ A microphone error occurred: {e}")
