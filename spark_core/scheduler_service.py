"""
SPARK Scheduler Service
────────────────────────────────────────────────────────────────────────────────
APScheduler-based task scheduler with:
  - One-shot reminders with system alerts
  - Interval-based periodic tasks
  - Cron-style scheduled jobs
  - Persistent job storage (SQLite via jobstores + JSON for reminders)

Endpoints:
  GET    /api/scheduler/reminders          — list all reminders
  POST   /api/scheduler/reminders          — create reminder
  DELETE /api/scheduler/reminders/{id}     — delete reminder
  PATCH  /api/scheduler/reminders/{id}     — update reminder
  GET    /api/scheduler/jobs               — list all scheduler jobs
  POST   /api/scheduler/jobs/cron          — create cron job
  POST   /api/scheduler/jobs/interval      — create interval job
  DELETE /api/scheduler/jobs/{id}          — delete job
  GET    /api/scheduler/history            — execution history
  POST   /api/scheduler/pause              — pause all jobs
  POST   /api/scheduler/resume            — resume all jobs
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ── Storage Paths ──────────────────────────────────────────────────────────────
_CONFIG_DIR = Path(os.path.dirname(__file__)) / ".." / "config"
_CONFIG_DIR.mkdir(exist_ok=True)

_REMINDERS_FILE = _CONFIG_DIR / "reminders.json"
_HISTORY_FILE = _CONFIG_DIR / "job_history.json"
_SCHEDULER_DB = f"sqlite:///{_CONFIG_DIR / 'apscheduler_jobs.sqlite'}"

def _load_json(path: Path) -> list:
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _save_json(path: Path, data: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Reminder Store ─────────────────────────────────────────────────────────────
# In-memory + file-backed
_reminders: Dict[str, Dict] = {r["id"]: r for r in _load_json(_REMINDERS_FILE)}
_history:   List[Dict]       = _load_json(_HISTORY_FILE)

def _persist_reminders():
    _save_json(_REMINDERS_FILE, list(_reminders.values()))

def _add_history(entry: dict):
    _history.append(entry)
    # Keep last 200
    if len(_history) > 200:
        _history[:] = _history[-200:]
    _save_json(_HISTORY_FILE, _history)


# ── Scheduler ─────────────────────────────────────────────────────────────────
_scheduler: Optional[AsyncIOScheduler] = None

def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


async def _fire_reminder(reminder_id: str):
    """Called by APScheduler when a reminder fires."""
    reminder = _reminders.get(reminder_id)
    if not reminder:
        return

    # Import here to avoid circular import
    from ws.manager import ws_manager
    from system.event_bus import event_bus

    msg = {
        "type":     "ALERT",
        "v":        1,
        "ts":       time.time() * 1000,
        "severity": reminder.get("severity", "info"),
        "title":    f"⏰ {reminder.get('title', 'Reminder')}",
        "body":     reminder.get("body", ""),
        "source":   "scheduler",
        "reminder_id": reminder_id,
    }

    await ws_manager.broadcast_json(msg, "system")

    # Also TTS-speak if voice enabled (non-blocking attempt)
    try:
        import edge_tts, io
        text = f"Reminder: {reminder.get('title', '')}. {reminder.get('body', '')}"
        communicate = edge_tts.Communicate(text, "en-US-GuyNeural", rate="+5%", pitch="-10Hz")
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        # Emit TTS audio over WS
        audio_data = buf.getvalue()
        if audio_data:
            await ws_manager.broadcast_json({
                "type": "TTS_AUDIO",
                "text": text,
                "reminder_id": reminder_id,
            }, "system")
    except Exception:
        pass  # TTS failure is non-critical

    # Record in history
    _add_history({
        "id":          str(uuid.uuid4()),
        "job_type":    "reminder",
        "reminder_id": reminder_id,
        "title":       reminder.get("title", ""),
        "fired_at":    time.time(),
        "success":     True,
    })

    # Mark one-shot reminders as fired
    if not reminder.get("recurring", False):
        reminder["status"] = "fired"
        reminder["fired_at"] = time.time()
        _persist_reminders()

    print(f"⏰ [SCHEDULER] Reminder fired: {reminder.get('title', reminder_id)}")


def _schedule_reminder(reminder: dict):
    """Register a reminder in APScheduler."""
    scheduler = get_scheduler()
    rid = reminder["id"]

    # Remove existing job if any
    try:
        scheduler.remove_job(rid)
    except Exception:
        pass

    if not reminder.get("enabled", True):
        return

    fire_at_ts = reminder.get("fire_at")
    cron_expr  = reminder.get("cron")
    interval_s = reminder.get("interval_seconds")

    try:
        if cron_expr:
            parts = cron_expr.strip().split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0], hour=parts[1], day=parts[2],
                    month=parts[3], day_of_week=parts[4], timezone="UTC"
                )
                scheduler.add_job(_fire_reminder, trigger, id=rid, args=[rid], replace_existing=True)
        elif interval_s:
            trigger = IntervalTrigger(seconds=int(interval_s))
            scheduler.add_job(_fire_reminder, trigger, id=rid, args=[rid], replace_existing=True)
        elif fire_at_ts:
            fire_dt = datetime.fromtimestamp(fire_at_ts, tz=timezone.utc)
            if fire_dt > datetime.now(tz=timezone.utc):
                scheduler.add_job(_fire_reminder, DateTrigger(run_date=fire_dt), id=rid, args=[rid], replace_existing=True)
    except Exception as e:
        print(f"⚠️ [SCHEDULER] Failed to schedule {rid}: {e}")


def init_scheduler():
    """
    Start the scheduler with SQLite job store for persistence.
    Jobs survive server restarts.
    """
    global _scheduler
    
    # Configure SQLAlchemy job store (SQLite database)
    try:
        jobstores = {
            'default': SQLAlchemyJobStore(url=_SCHEDULER_DB)
        }
        
        executors = {
            'default': {'type': 'asyncio'},
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        
        _scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC"
        )
        
        if not _scheduler.running:
            _scheduler.start()
            print("⏰ [SCHEDULER] APScheduler started with SQLite persistence.")
        
        # Restore persisted reminders from JSON
        for reminder in _reminders.values():
            if reminder.get("status") not in ("fired", "cancelled"):
                _schedule_reminder(reminder)
        
        print(f"⏰ [SCHEDULER] Restored {len(_reminders)} reminders from JSON.")
        
    except Exception as e:
        # Fallback to in-memory scheduler if SQLite fails
        print(f"⚠️ [SCHEDULER] SQLite jobstore failed ({e}), using in-memory scheduler.")
        _scheduler = AsyncIOScheduler(timezone="UTC")
        if not _scheduler.running:
            _scheduler.start()
        
        for reminder in _reminders.values():
            if reminder.get("status") not in ("fired", "cancelled"):
                _schedule_reminder(reminder)



# ── FastAPI Router ─────────────────────────────────────────────────────────────
scheduler_router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class ReminderCreate(BaseModel):
    title: str
    body: str = ""
    fire_at: Optional[float] = None          # Unix timestamp for one-shot
    cron: Optional[str] = None               # cron expression "*/5 * * * *"
    interval_seconds: Optional[int] = None   # repeat every N seconds
    severity: str = "info"                   # info / warning / critical
    enabled: bool = True
    tags: List[str] = []


class ReminderPatch(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    fire_at: Optional[float] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


@scheduler_router.get("/reminders")
async def list_reminders(status: Optional[str] = None):
    """List all reminders, optionally filtered by status."""
    reminders = list(_reminders.values())
    if status:
        reminders = [r for r in reminders if r.get("status") == status]
    # Sort by creation time
    reminders.sort(key=lambda r: r.get("created_at", 0), reverse=True)
    return {"reminders": reminders, "total": len(reminders)}


@scheduler_router.post("/reminders", status_code=201)
async def create_reminder(req: ReminderCreate):
    """Create a new reminder or scheduled task."""
    rid = str(uuid.uuid4())

    if not req.fire_at and not req.cron and not req.interval_seconds:
        # Default: fire in 10 minutes
        req.fire_at = time.time() + 600

    reminder = {
        "id":               rid,
        "title":            req.title,
        "body":             req.body,
        "fire_at":          req.fire_at,
        "cron":             req.cron,
        "interval_seconds": req.interval_seconds,
        "severity":         req.severity,
        "enabled":          req.enabled,
        "tags":             req.tags,
        "status":           "pending",
        "created_at":       time.time(),
        "fired_at":         None,
        "recurring":        bool(req.cron or req.interval_seconds),
    }

    _reminders[rid] = reminder
    _persist_reminders()

    if req.enabled:
        _schedule_reminder(reminder)

    msg = "non-recurring" if not reminder["recurring"] else f"recurring ({req.cron or f'every {req.interval_seconds}s'})"
    print(f"⏰ [SCHEDULER] Created {msg} reminder: {req.title}")

    return {"status": "created", "reminder": reminder}


@scheduler_router.get("/reminders/{reminder_id}")
async def get_reminder(reminder_id: str):
    r = _reminders.get(reminder_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return r


@scheduler_router.patch("/reminders/{reminder_id}")
async def update_reminder(reminder_id: str, req: ReminderPatch):
    r = _reminders.get(reminder_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")

    if req.title is not None:     r["title"]    = req.title
    if req.body  is not None:     r["body"]     = req.body
    if req.fire_at is not None:   r["fire_at"]  = req.fire_at; r["status"] = "pending"
    if req.severity is not None:  r["severity"] = req.severity
    if req.enabled is not None:
        r["enabled"] = req.enabled
        if req.enabled:
            _schedule_reminder(r)
        else:
            try:
                get_scheduler().remove_job(reminder_id)
            except Exception:
                pass

    _persist_reminders()
    return {"status": "updated", "reminder": r}


@scheduler_router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    if reminder_id not in _reminders:
        raise HTTPException(status_code=404, detail="Reminder not found")
    try:
        get_scheduler().remove_job(reminder_id)
    except Exception:
        pass
    del _reminders[reminder_id]
    _persist_reminders()
    return {"status": "deleted", "id": reminder_id}


@scheduler_router.get("/jobs")
async def list_jobs():
    """List all running APScheduler jobs."""
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id":       job.id,
            "name":     job.name or job.id,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger":  str(job.trigger),
        })
    return {
        "jobs":    jobs,
        "running": scheduler.running,
        "count":   len(jobs),
    }


@scheduler_router.get("/history")
async def job_history(limit: int = 50):
    """Return the last N scheduler job executions."""
    recent = sorted(_history, key=lambda h: h.get("fired_at", 0), reverse=True)[:limit]
    return {"history": recent, "total": len(_history)}


@scheduler_router.post("/pause")
async def pause_scheduler():
    get_scheduler().pause()
    return {"status": "paused"}


@scheduler_router.post("/resume")
async def resume_scheduler():
    get_scheduler().resume()
    return {"status": "resumed"}


@scheduler_router.get("/status")
async def scheduler_status():
    scheduler = get_scheduler()
    pending   = sum(1 for r in _reminders.values() if r.get("status") == "pending")
    fired     = sum(1 for r in _reminders.values() if r.get("status") == "fired")
    return {
        "running":          scheduler.running,
        "jobs":             len(scheduler.get_jobs()),
        "reminders_total":  len(_reminders),
        "reminders_pending": pending,
        "reminders_fired":  fired,
        "history_count":    len(_history),
    }
