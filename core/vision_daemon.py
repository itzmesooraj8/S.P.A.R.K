import threading
import time
import logging
import os

from core.tools import SparkTools
from core.vision import describe_screen
from core.main import broadcast_hud_event

logger = logging.getLogger("SPARK_VISION_DAEMON")

_vision_thread = None
_stop_event = threading.Event()
_tools = SparkTools()

def _vision_loop():
    logger.info("Screen Vision daemon started.")
    while not _stop_event.is_set():
        # Sleep for 30 seconds
        for _ in range(30):
            if _stop_event.is_set():
                return
            time.sleep(1)
            
        try:
            broadcast_hud_event("agent_log", {"type": "system", "agent": "VISION", "action": "Scanning", "data": "Capturing screen context..."})
            response, snap_path = _tools.take_screenshot()
            
            if snap_path and os.path.exists(snap_path):
                question = "Describe the active window and what the user is currently working on or looking at in detail."
                # We prioritize Grok Vision if the XAI API key is configured
                observation = describe_screen(snap_path, question, use_grok=True)
                
                # Import memory lazily to avoid circular imports
                from core.main import memory
                if memory:
                    memory.remember("system", f"[SCREEN CONTEXT] User is currently looking at: {observation}", metadata={"source": "vision_daemon"})
                    
                broadcast_hud_event("agent_log", {"type": "ai", "agent": "VISION", "action": "Context Analyzed", "data": observation[:150] + "..."})
                
                try:
                    os.remove(snap_path)
                except OSError:
                    pass
        except Exception as e:
            logger.error(f"Vision daemon error: {e}")

def start_vision_daemon():
    global _vision_thread
    if _vision_thread is not None and _vision_thread.is_alive():
        return
    _stop_event.clear()
    _vision_thread = threading.Thread(target=_vision_loop, daemon=True)
    _vision_thread.start()

def stop_vision_daemon():
    _stop_event.set()
    if _vision_thread:
        _vision_thread.join(timeout=2)
