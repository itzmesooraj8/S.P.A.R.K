# S.P.A.R.K. Core Orchestrator
# Implementation: Phase 4-6 Graduation State (Refactored for 2.0)

import asyncio
import structlog
import traceback
from core.initialization import ensure_ffmpeg

# FIX: Ensure FFmpeg is loaded before any audio modules
ensure_ffmpeg()

from core.config import settings
from core.logging_config import configure_logging
from spark.visuals.spark_visual import set_spark_visual_state, run_visual

# Initialize Logging
configure_logging()
logger = structlog.get_logger()

import sounddevice as sd

# --- SERVICES (Lazy Import / Injection) ---
# In a full DI setup, these would be injected. For now, we import global instances.
# FIX: Use the new Brain Manager (Hybrid Intelligence)
from spark.modules.brain_manager import brain_manager
from spark.integrations.mouth import stream_speak
from spark.modules.memory import memory_engine
from tools.registry import spark_tools
# NEW: Orchestrator Integration (Phase 3)
from spark.core.orchestrator import orchestrator, EventType

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

async def execute_tool(payload):
    """
    Helper to execute tools safely using the legacy tool runner for now.
    """
    tool_name = payload['tool']
    args = payload['args']
    
    # Bridge to spark_tools._run_with_timeout or direct call
    # In Phase 4, we rewrite tools to conform to V2 interface entirely.
    if tool_name in ["search_web", "system_status", "read_file", "write_file", "delete_file", "terminal_command", "get_active_window"]:
        # Bridge to spark_tools.tools execution
        arg_val = args.get('raw', '')
        # Strip quotes if present
        arg_val = arg_val.strip('"').strip("'")
        
        logger.info("orchestrator_executing_tool", tool=tool_name, args=arg_val)
        
        # Use existing registry runner logic
        try:
            result = await asyncio.to_thread(spark_tools._run_with_timeout, tool_name, arg_val)
            return f"Tool {tool_name} returned: {result}"
        except Exception as e:
            return f"Tool execution failed: {e}"
        
    return f"[SYSTEM_ERROR: Tool '{tool_name}' logic not bridged in main.py yet.]"

async def handle_user_input(user_text):
    """
    Central Decision Router (Orchestrator Driven).
    """
    try:
        set_spark_visual_state("thinking")
        logger.info("orchestrator_thinking", input=user_text)

        # 1. Orchestrator Decision
        event = await orchestrator.process_user_input(user_text)
        
        set_spark_visual_state("speaking")
        logger.info("orchestrator_decision", type=event.type.value)

        # 2. Act on Event
        if event.type == EventType.RESPONSE:
            # Speak Response
            async for pcm, sr in stream_speak(event.payload):
                if len(pcm) > 0: await asyncio.to_thread(sd.play, pcm, sr, blocking=True)

        elif event.type == EventType.CONFIRMATION_REQUIRED:
            # Speak Confirmation Prompt
            prompt = event.payload
            async for pcm, sr in stream_speak(prompt):
                if len(pcm) > 0: await asyncio.to_thread(sd.play, pcm, sr, blocking=True)
            # Logic: We return to loop, next input will be processed by Orchestrator which remembers state

        elif event.type == EventType.AUTH_REQUIRED:
            # Speak Auth Prompt
            prompt = event.payload
            async for pcm, sr in stream_speak(prompt):
                 if len(pcm) > 0: await asyncio.to_thread(sd.play, pcm, sr, blocking=True)
            # Treated as confirmation for now

        elif event.type == EventType.TOOL_EXECUTION:
            # Speak "Executing..."
            async for pcm, sr in stream_speak("Executing request..."):
                 if len(pcm) > 0: await asyncio.to_thread(sd.play, pcm, sr, blocking=True)
            
            # Run Tool
            result = await execute_tool(event.payload)
            
            # Speak Result
            # In Phase 4, we might maximize this to a summary
            summary = f"Done. {result[:150]}..." if len(result) > 150 else result
            async for pcm, sr in stream_speak(summary):
                 if len(pcm) > 0: await asyncio.to_thread(sd.play, pcm, sr, blocking=True)
                 
        elif event.type == EventType.ERROR:
             # Speak Error
             async for pcm, sr in stream_speak(event.payload):
                 if len(pcm) > 0: await asyncio.to_thread(sd.play, pcm, sr, blocking=True)

        # 3. Memory Update (Simplified for now)
        # memory_engine.add_memory(f"User: {user_text}\nS.P.A.R.K: [Event: {event.type.value}]")
        
        set_spark_visual_state("idle")
        
    except Exception as e:
        logger.error("orchestrator_handler_failed", error=str(e))
        set_spark_visual_state("idle")

async def streaming_conversation_loop():
    logger.info("orchestrator_loop_started")
    
    # Warmup Local Brain
    asyncio.create_task(brain_manager.warmup())
    
    try:
        while True:
            set_spark_visual_state("listening")
            logger.info("orchestrator_state", state="listening")
            
            # 1. Listen
            user_text = await listen_stream_async()
            if not user_text or not user_text.strip():
                logger.debug("orchestrator_no_input")
                continue
            
            # 2. Handle Input (Await for Voice Safety)
            await handle_user_input(user_text)

    except Exception as e:
        logger.error("orchestrator_crash", error=str(e), traceback=traceback.format_exc())
        await asyncio.sleep(2)

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
    logger.info("system_startup_scan")
    request_scanner_scan = getattr(settings.memory, 'scan_on_startup', True) 
    if request_scanner_scan:
        try:
             scanner.scan()
        except Exception as e:
             logger.error("startup_scan_failed", error=str(e))
    
    # Global Loop with robust error handling
    while True:
        try:
            set_spark_visual_state("idle")
            await wait_for_wake_word()
            
            # Protected Conversation Loop
            # If the loop crashes, we log and restart listening
            await streaming_conversation_loop()
        
        except asyncio.CancelledError:
            logger.info("orchestrator_cancelled")
            break
        except Exception as e:
            logger.critical("global_orchestrator_crash", error=str(e), traceback=traceback.format_exc())
            logger.info("system_restarting_services")
            await asyncio.sleep(5) # Valid backoff

def main():
    import threading
    
    # Start the Visuals in the main thread (PyGame needs main thread usually, or decent thread)
    # But `run_visual` blocks!
    # So we must run the orchestration in a separate thread if we keep `run_visual` here.
    # OR we use asyncio for everything if visual supports it.
    # The original main.py ran `conversation_thread`. 
    
    # Start the orchestrator thread
    import threading
    shutdown_event = threading.Event()

    def run_orchestrator():
        try:
            asyncio.run(orchestrate())
        except Exception as e:
            logger.critical("orchestrator_thread_crash", error=str(e))

    thread = threading.Thread(target=run_orchestrator, daemon=True)
    thread.start()
    
    try:
        run_visual()
    except KeyboardInterrupt:
        logger.info("system_shutdown_requested")
    finally:
        print("[System] Shutting down...")
        # Since the thread is daemon, it will die when main exits.
        # But we can add cleanup logic here if needed.

if __name__ == "__main__":
    main()
