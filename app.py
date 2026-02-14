# Ensure main() is defined

# --- ASYNC STREAMING PIPELINE ---
import asyncio
from spark.visuals.spark_visual import set_spark_visual_state, run_visual

async def listen_stream_async():
    """
    Async wrapper for DeepgramStreamer.listen_stream, returns the final transcript.
    """
    from spark.integrations.ears_stream import DeepgramStreamer
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    def on_partial(text):
        set_spark_visual_state("listening")
        print(f"[SPARK] Partial: {text}")
    def on_final(text):
        print(f"[SPARK] Final: {text}")
        if not future.done():
            future.set_result(text)
    await loop.run_in_executor(None, lambda: DeepgramStreamer().listen_stream(on_partial, on_final))
    return await future

async def streaming_conversation_loop():
    import traceback
    from spark.modules.brain import think_stream
    from spark.integrations.mouth import stream_speak, play_streaming_audio
    from spark.modules.memory import memory_engine
    
    while True:
        try:
            set_spark_visual_state("listening")
            print("[SPARK] Listening (stream)...")
            user_text = await listen_stream_async()
            # Only proceed if we have a non-empty, final transcript
            if not user_text or not user_text.strip():
                print("[SPARK] No final transcript detected, restarting loop.")
                continue
            
            set_spark_visual_state("thinking")
            print("[SPARK] Thinking...")
            # Stream Gemini response
            response_chunks = think_stream(user_text)
            set_spark_visual_state("speaking")
            print("[SPARK] Speaking (streaming)...")
            
            full_response = ""
            # Stream TTS and play audio as soon as available
            async for chunk in response_chunks:
                full_response += chunk
                print(chunk, end='', flush=True)
                async for pcm, sr in stream_speak(chunk):
                    play_streaming_audio([(pcm, sr)])
            
            print("\n[SPARK] Finished speaking.")
            
            # --- PHASE 4: STORE IN MEMORY ---
            memory_engine.add_memory(f"User said: {user_text}\nS.P.A.R.K responded: {full_response}")
            
            set_spark_visual_state("idle")
            await asyncio.sleep(0.5)
        except Exception as e:
            print("[SPARK] Exception in streaming conversation loop:")
            traceback.print_exc()
            await asyncio.sleep(2)


async def wait_for_wake_word():
    """Continuously listen for the wake word 'spark' and return when detected."""
    from spark.integrations.ears_stream import DeepgramStreamer
    loop = asyncio.get_running_loop()
    print("[SPARK] Waiting for wake word 'spark'...")
    while True:
        future = loop.create_future()
        def on_partial(text):
            pass  # Don't show anything for partials
        def on_final(text):
            print(f"[SPARK] Heard: {text}")
            if 'spark' in text.lower() and not future.done():
                future.set_result(True)
            elif not future.done():
                future.set_result(False)
        await loop.run_in_executor(None, lambda: DeepgramStreamer().listen_stream(on_partial, on_final))
        if await future:
            break

def main():
    from spark.visuals.spark_visual import set_spark_visual_state, run_visual
    from spark.modules.scanner import scanner
    
    # --- PHASE 4: INITIAL KNOWLEDGE SCAN ---
    scanner.scan()
    
    set_spark_visual_state("idle")
    async def orchestrate():
        while True:
            set_spark_visual_state("idle")
            await wait_for_wake_word()
            set_spark_visual_state("listening")
            await streaming_conversation_loop()
    def run_async_loop():
        asyncio.run(orchestrate())
    import threading
    conversation_thread = threading.Thread(target=run_async_loop, daemon=True)
    conversation_thread.start()
    run_visual()

if __name__ == "__main__":
    main()
