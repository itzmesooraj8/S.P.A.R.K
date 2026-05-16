import threading
import time
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta

from tools.sysmon import get_system_health
from core.scheduler import list_reminders
from core.automation import run_automation_cycle
from core.prompt_adaptation import run_prompt_evolution_cycle
from core.main import broadcast_hud_event
from tools.voice import speak

logger = logging.getLogger("SPARK_HEARTBEAT")

_heartbeat_thread = None
_stop_event = threading.Event()

# Proactive cycle timers
_last_calendar_scan = 0
_last_briefing_check = 0
_calendar_scan_interval = 5 * 60  # 5 minutes
_briefing_interval = 30 * 60  # 30 minutes

USER_MODEL_PATH = Path("spark_dev_memory/user_model.json")


def _load_user_model() -> dict:
    """Load user behavioral model."""
    if not USER_MODEL_PATH.exists():
        return {
            "sooraj": {
                "wake_hour": 7,
                "morning_routines": [],
                "anomalies_detected": [],
                "last_briefing": None,
            }
        }
    try:
        return json.loads(USER_MODEL_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Could not load user model: {e}")
        return {}


def _save_user_model(model: dict) -> None:
    """Save user behavioral model."""
    try:
        USER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        USER_MODEL_PATH.write_text(json.dumps(model, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"Could not save user model: {e}")


def _check_calendar_proactively() -> list[dict]:
    """
    Scan calendar for upcoming events and anomalies.
    Returns list of proactive alerts (meetings soon, unusual activity, etc).
    """
    alerts = []
    try:
        from tools.calendar import get_calendar_events
        
        now = datetime.now()
        upcoming_window = now + timedelta(minutes=30)
        
        # Try to get upcoming events
        try:
            events = get_calendar_events(max_results=5)
            for event in events:
                event_start = event.get("start")
                if not event_start:
                    continue
                
                # Parse ISO format datetime
                try:
                    event_dt = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
                except:
                    continue
                
                time_until = (event_dt - now).total_seconds() / 60  # Minutes
                
                # Alert if meeting in 10-30 minutes
                if 10 <= time_until <= 30:
                    title = event.get("summary", "Meeting")
                    alerts.append({
                        "type": "upcoming_meeting",
                        "title": title,
                        "minutes_until": int(time_until),
                        "message": f"Sir, your {title} starts in {int(time_until)} minutes.",
                    })
        except Exception as e:
            logger.debug(f"Calendar check failed: {e}")
    
    except ImportError:
        logger.debug("Calendar tool not available")
    
    return alerts


def _detect_anomalies() -> list[dict]:
    """
    Detect unusual system behavior or missing routines.
    Returns list of anomalies (e.g., "No weather check today" if habit-breaking).
    """
    anomalies = []
    try:
        user_model = _load_user_model()
        sooraj = user_model.get("sooraj", {})
        morning_routines = sooraj.get("morning_routines", [])
        
        now = datetime.now()
        current_hour = now.hour
        
        # If it's morning (7-9 AM) and no weather routine logged, flag it
        if 7 <= current_hour < 9 and "weather_check" in morning_routines:
            # This would require logging actual actions — stub for now
            pass
        
        return anomalies
    except Exception as e:
        logger.debug(f"Anomaly detection failed: {e}")
        return []


def _broadcast_proactive_briefing() -> None:
    """
    Compile a brief news/weather/market update and announce proactively.
    Only triggers if enough time has passed since last briefing.
    """
    try:
        user_model = _load_user_model()
        sooraj = user_model.get("sooraj", {})
        last_briefing_str = sooraj.get("last_briefing")
        
        # Don't brief more than once per hour
        if last_briefing_str:
            try:
                last_briefing = datetime.fromisoformat(last_briefing_str)
                if (datetime.now() - last_briefing).total_seconds() < 3600:
                    return
            except:
                pass
        
        briefing_parts = []
        
        # Try to fetch weather
        try:
            from tools.weather import get_weather
            weather = get_weather("your location")
            if weather:
                briefing_parts.append(f"Weather: {weather}")
        except:
            pass
        
        # Try to fetch news
        try:
            from tools.news import get_news
            news = get_news(limit=1)
            if news:
                briefing_parts.append(f"Top news: {news[0]}")
        except:
            pass
        
        if briefing_parts:
            briefing = " ".join(briefing_parts)
            broadcast_hud_event(
                "agent_log",
                {
                    "type": "info",
                    "agent": "HEARTBEAT",
                    "action": "Proactive Briefing",
                    "data": briefing[:100],
                }
            )
            
            # Speak proactively
            try:
                import asyncio
                asyncio.create_task(speak(f"Sir, here's your update. {briefing}"))
            except:
                pass
            
            # Update last_briefing timestamp
            user_model["sooraj"]["last_briefing"] = datetime.now().isoformat()
            _save_user_model(user_model)
    except Exception as e:
        logger.debug(f"Proactive briefing failed: {e}")


def _update_user_model_from_patterns() -> None:
    """
    Accumulate behavioral patterns into user_model.json.
    This drives future proactive actions.
    """
    try:
        from core.memory_loop import read_turns
        
        user_model = _load_user_model()
        sooraj = user_model.setdefault("sooraj", {})
        
        turns = read_turns()
        if not turns:
            return
        
        # Detect morning routine patterns
        morning_actions = []
        for turn in turns[-20:]:  # Last 20 turns
            if turn.get("role") != "user":
                continue
            
            content = str(turn.get("content", "")).lower()
            if any(word in content for word in ["weather", "forecast", "temperature"]):
                morning_actions.append("weather_check")
            elif any(word in content for word in ["news", "headline"]):
                morning_actions.append("news_check")
            elif any(word in content for word in ["calendar", "schedule"]):
                morning_actions.append("calendar_check")
        
        # Store unique morning routines
        if morning_actions:
            sooraj["morning_routines"] = list(set(sooraj.get("morning_routines", []) + morning_actions))[:5]
        
        _save_user_model(user_model)
    except Exception as e:
        logger.debug(f"User model update failed: {e}")


def _heartbeat_loop():
    logger.info("Heartbeat engine started — proactive agency mode active.")
    global _last_calendar_scan, _last_briefing_check
    
    while not _stop_event.is_set():
        time.sleep(60)  # 60-second background cron base
        if _stop_event.is_set():
            break
        
        current_time = time.time()
        
        try:
            # Every 5 minutes: scan calendar for upcoming meetings
            if current_time - _last_calendar_scan >= _calendar_scan_interval:
                _last_calendar_scan = current_time
                try:
                    calendar_alerts = _check_calendar_proactively()
                    for alert in calendar_alerts:
                        broadcast_hud_event(
                            "agent_log",
                            {
                                "type": "warning",
                                "agent": "HEARTBEAT",
                                "action": "Calendar Alert",
                                "data": alert.get("message", "")[:100]
                            }
                        )
                        # Speak the alert proactively
                        try:
                            import asyncio
                            asyncio.create_task(speak(alert.get("message", "")))
                        except:
                            pass
                except Exception as cal_exc:
                    logger.debug(f"Calendar scan failed: {cal_exc}")
            
            # Every 30 minutes: broadcast briefing and check for anomalies
            if current_time - _last_briefing_check >= _briefing_interval:
                _last_briefing_check = current_time
                try:
                    _broadcast_proactive_briefing()
                except Exception as briefing_exc:
                    logger.debug(f"Briefing broadcast failed: {briefing_exc}")
                
                try:
                    anomalies = _detect_anomalies()
                    for anomaly in anomalies:
                        broadcast_hud_event(
                            "agent_log",
                            {
                                "type": "warning",
                                "agent": "HEARTBEAT",
                                "action": "Anomaly Detected",
                                "data": anomaly.get("message", "")[:100]
                            }
                        )
                except Exception as anom_exc:
                    logger.debug(f"Anomaly detection failed: {anom_exc}")
            
            # Update user model from recent patterns (every cycle)
            _update_user_model_from_patterns()
            
            # Check for auto-approvable tools and prompts (every cycle)
            try:
                from core.tool_forge import _auto_approve_high_confidence_tools
                _auto_approve_high_confidence_tools()
            except Exception as e:
                logger.debug(f"Tool auto-approval check failed: {e}")
            
            # Existing reminders check
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


def start_heartbeat():
    """Start the proactive heartbeat daemon if it is not already running."""
    global _heartbeat_thread
    if _heartbeat_thread is not None and _heartbeat_thread.is_alive():
        return
    _stop_event.clear()
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _heartbeat_thread.start()
