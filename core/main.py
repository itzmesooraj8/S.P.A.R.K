# S.P.A.R.K. Core Orchestrator
# Implementation: Phase 4-6 Graduation State (Refactored for 2.0)

import asyncio
import structlog
import traceback
from core.config import settings
from core.logging_config import configure_logging
from spark.visuals.spark_visual import set_spark_visual_state, run_visual

# Initialize Logging
configure_logging()
logger = structlog.get_logger()

# --- SERVICES (Lazy Import / Injection) ---
# In a full DI setup, these would be injected. For now, we import global instances.
from core.personality import think_stream
from spark.integrations.mouth import stream_speak, play_streaming_audio
from spark.modules.memory import memory_engine
from tools.registry import spark_tools

async def listen_stream_async():
    """
    Async wrapper for DeepgramStreamer.listen_stream, returns the final transcript.
    """
    from spark.integrations.ears_stream import DeepgramStreamer
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    def on_partial(text):
        set_spark_visual_state("listening")
        # Logger might be too verbose for partials, keep it minimal
        # logger.debug("ears_partial", text=text) 
        print(f"[SPARK] Partial: {text}") # Keep for CLI feedback if needed

    def on_final(text):
        logger.info("ears_final", text=text)
        if not future.done():
            future.set_result(text)

    # Offload the synchronous listener to a thread to avoid blocking the async loop
    await loop.run_in_executor(None, lambda: DeepgramStreamer().listen_stream(on_partial, on_final))
    return await future

async def streaming_conversation_loop():
    logger.info("orchestrator_loop_started")
    try:
        while True:
            set_spark_visual_state("listening")
            logger.info("orchestrator_state", state="listening")
            
            # 1. Listen
            user_text = await listen_stream_async()
            if not user_text or not user_text.strip():
                logger.debug("orchestrator_no_input")
                continue
            
            # 2. Think
            set_spark_visual_state("thinking")
            logger.info("orchestrator_state", state="thinking")
            
            # Check for tool triggers first (Fast Path) or just let Brain handle it?
            # Current architecture: Brain streams text -> we speak it. 
            # Tool usage is inside brain's logic or post-processing?
            # "The user asked for 'Tool Chaining with Planning'". 
            # For now, we stick to the existing Brain-Stream-Mouth pipeline.
            
            response_chunks = think_stream(user_text)
            
            # 3. Speak
            set_spark_visual_state("speaking")
            logger.info("orchestrator_state", state="speaking")
            
            full_response = ""
            async for chunk in response_chunks:
                full_response += chunk
                print(chunk, end='', flush=True) # CLI output
                
                # Check for tool triggers in the chunk? 
                # (Advanced: Parsing stream for [EXECUTE:...] tokens)
                
                async for pcm, sr in stream_speak(chunk):
                    play_streaming_audio([(pcm, sr)])
            
            print("\n")
            logger.info("orchestrator_finished_speaking")
            
            # 4. Memory Store
            memory_engine.add_memory(f"User: {user_text}\nS.P.A.R.K: {full_response}")
            logger.info("orchestrator_memory_updated")
            
            set_spark_visual_state("idle")
            await asyncio.sleep(0.5)

    except Exception as e:
        logger.error("orchestrator_crash", error=str(e), traceback=traceback.format_exc())
        await asyncio.sleep(2) # Backoff before restart?
        # In a real loop, we might want to restart the loop inside main()

async def wait_for_wake_word():
    """Continuously listen for the wake word configured in settings."""
    from spark.integrations.ears_stream import DeepgramStreamer
    loop = asyncio.get_running_loop()
    wake_word = settings.audio.wake_word.lower()
    
    logger.info("orchestrator_waiting_wake_word", word=wake_word)
    
    # We use a Future to signal when the wake word is detected
    while True:
        future = loop.create_future()
        
        def on_partial(text):
            pass
        
        def on_final(text):
            logger.debug("ears_heard_background", text=text)
            if wake_word in text.lower() and not future.done():
                future.set_result(True)
            elif not future.done():
                # If not wake word, we just continue listening? 
                # Deepgram stream closes on final? 
                # The current ears_stream implementation closes on final.
                future.set_result(False)
        
        await loop.run_in_executor(None, lambda: DeepgramStreamer().listen_stream(on_partial, on_final))
        
        if await future:
            logger.info("orchestrator_wake_word_detected")
            break

async def orchestrate():
    """Main Async Entry Point"""
    from spark.modules.scanner import scanner
    
    # --- PHASE 4: INITIAL KNOWLEDGE SCAN ---
    # Now integrated properly via tools?
    # We run it once at startup.
    logger.info("system_startup_scan")
    request_scanner_scan = getattr(settings.memory, 'scan_on_startup', True) # hypothetical setting
    if request_scanner_scan:
         scanner.scan()
    
    while True:
        set_spark_visual_state("idle")
        await wait_for_wake_word()
        # Once wake word detected, enter conversation loop
        # We might want to run the conversation loop for *one* interaction or a session?
        # The previous code ran `streaming_conversation_loop` which had a `while True`.
        # That implies once awoken, it NEVER sleeps again?
        # Let's assume we want a session. For now, we call the loop.
        # But `streaming_conversation_loop` is infinite. 
        # So `wait_for_wake_word` is only called ONCE at boot?
        # That seems to be the logic of the original file. 
        await streaming_conversation_loop()

def main():
    import threading
    
    # Start the Visuals in the main thread (PyGame needs main thread usually, or decent thread)
    # But `run_visual` blocks!
    # So we must run the orchestration in a separate thread if we keep `run_visual` here.
    # OR we use asyncio for everything if visual supports it.
    # The original main.py ran `conversation_thread`. 
    
    thread = threading.Thread(target=lambda: asyncio.run(orchestrate()), daemon=True)
    thread.start()
    
    try:
        run_visual()
    except KeyboardInterrupt:
        logger.info("system_shutdown")

if __name__ == "__main__":
    main()
