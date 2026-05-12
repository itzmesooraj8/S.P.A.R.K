import threading
import time
import logging

from tools.sysmon import get_system_health
from core.scheduler import list_reminders
from core.automation import run_automation_cycle
from core.prompt_adaptation import run_prompt_evolution_cycle
from core.main import broadcast_hud_event

logger = logging.getLogger("SPARK_HEARTBEAT")

_heartbeat_thread = None
_stop_event = threading.Event()

def _heartbeat_loop():
    logger.info("Heartbeat engine started.")
    while not _stop_event.is_set():
        time.sleep(60) # 60-second background cron
        if _stop_event.is_set():
            break
        
        try:
            reminders = list_reminders()
            if reminders:
                broadcast_hud_event(
                    "agent_log",
                    {
                        "type": "info",
                        "agent": "HEARTBEAT",
                        "action": "Task Queue",
                        "data": f"Pending tasks: {len(reminders)}"
                    }
                )

            try:
                run_automation_cycle()
            except Exception as automation_exc:
                logger.warning("Automation cycle failed: %s", automation_exc)

            try:
                run_prompt_evolution_cycle()
            except Exception as prompt_exc:
                logger.warning("Prompt evolution cycle failed: %s", prompt_exc)

            health_status = get_system_health()
            if "heavy load" in health_status.lower() or "unable" in health_status.lower():
                broadcast_hud_event(
                    "agent_log",
                    {
                        "type": "warning",
                        "agent": "HEARTBEAT",
                        "action": "System Alert",
                        "data": health_status[:100]
                    }
                )
            else:
                broadcast_hud_event(
                    "agent_log",
                    {
                        "type": "system",
                        "agent": "HEARTBEAT",
                        "action": "System Nominal",
                        "data": "Telemetry indicates normal operation."
                    }
                )

        except Exception as e:
            logger.error(f"Heartbeat tick failed: {e}")

def start_heartbeat():
    global _heartbeat_thread
    if _heartbeat_thread is not None and _heartbeat_thread.is_alive():
        return
    _stop_event.clear()
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _heartbeat_thread.start()

def stop_heartbeat():
    _stop_event.set()
    if _heartbeat_thread:
        _heartbeat_thread.join(timeout=2)
