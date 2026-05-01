"""
core/scheduler.py — S.P.A.R.K. Proactive Agency Engine
Manages scheduled reminders and timed tasks via APScheduler.
SPARK can register jobs through the `set_reminder` tool.
When a job fires, it pushes a WS event to the HUD AND speaks proactively.
"""
 
import logging
import threading
import requests
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
 
logger = logging.getLogger(__name__)
 
# Global scheduler instance (singleton)
_scheduler: BackgroundScheduler | None = None
_voice_ref = None  # Injected from main.py
 
 
def init_scheduler(voice=None):
    """
    Initialize and start the APScheduler background daemon.
    Call this once from main.py during boot.
    voice: SparkVoice instance so reminders can speak proactively.
    """
    global _scheduler, _voice_ref
    if _scheduler and _scheduler.running:
        logger.warning("[SCHEDULER] Already running — skipping re-init.")
        return _scheduler
 
    _voice_ref = voice
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.start()
    logger.info("[SCHEDULER] ✅ Proactive agency engine started.")
    return _scheduler
 
 
def shutdown_scheduler():
    """Gracefully stop the scheduler on exit."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Scheduler shut down.")
 
 
def _fire_reminder(message: str, job_id: str):
    """
    Internal callback executed by APScheduler when a job fires.
    1. Pushes HUD amber overlay via WebSocket broadcast.
    2. Calls voice.speak() so SPARK initiates the conversation.
    """
    logger.info(f"[SCHEDULER] Reminder fired: {message}")
 
    # 1. Push to HUD
    def _broadcast():
        try:
            requests.post(
                "http://127.0.0.1:8000/internal/broadcast",
                json={
                    "type": "reminder",
                    "payload": {
                        "message": message,
                        "job_id": job_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                timeout=0.5
            )
        except Exception as e:
            logger.warning(f"[SCHEDULER] HUD broadcast failed: {e}")
 
    threading.Thread(target=_broadcast, daemon=True).start()
 
    # 2. Speak proactively
    if _voice_ref:
        def _speak():
            try:
                _voice_ref.speak(f"Sir, a reminder: {message}")
            except Exception as e:
                logger.warning(f"[SCHEDULER] Voice speak failed: {e}")
        threading.Thread(target=_speak, daemon=True).start()
 
 
def set_reminder(message: str, delay_seconds: int) -> str:
    """
    Tool interface: register a one-shot reminder.
    Called by the LLM tool executor in main.py.
 
    Args:
        message:       The reminder text to speak/display.
        delay_seconds: How many seconds from now to fire.
 
    Returns:
        Human-readable confirmation string for SPARK to relay to the user.
    """
    global _scheduler
    if not _scheduler or not _scheduler.running:
        return "Error: Scheduler is not running. Cannot set reminder."
 
    if delay_seconds <= 0:
        return "Error: delay_seconds must be a positive integer."
 
    fire_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
    job_id = f"reminder_{fire_at.strftime('%Y%m%d%H%M%S')}_{message[:10].replace(' ', '_')}"
 
    _scheduler.add_job(
        func=_fire_reminder,
        trigger=DateTrigger(run_date=fire_at),
        args=[message, job_id],
        id=job_id,
        replace_existing=True
    )
 
    minutes = delay_seconds // 60
    seconds = delay_seconds % 60
    time_str = f"{minutes} minute{'s' if minutes != 1 else ''}" if minutes > 0 else f"{seconds} second{'s' if seconds != 1 else ''}"
    if minutes > 0 and seconds > 0:
        time_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
 
    logger.info(f"[SCHEDULER] Reminder registered: '{message}' in {delay_seconds}s (job_id={job_id})")
    return f"Reminder set. I will alert you in {time_str}: '{message}'."
 
 
def list_reminders() -> list[dict]:
    """Returns a list of all pending scheduled jobs for HUD display."""
    global _scheduler
    if not _scheduler:
        return []
    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "next_run": next_run.isoformat() if next_run else "unknown",
            "args": job.args
        })
    return jobs
 
 
def cancel_reminder(job_id: str) -> str:
    """Tool interface: cancel a pending reminder by job ID."""
    global _scheduler
    if not _scheduler:
        return "Scheduler not running."
    try:
        _scheduler.remove_job(job_id)
        return f"Reminder '{job_id}' has been cancelled."
    except Exception:
        return f"No reminder found with ID '{job_id}'."
