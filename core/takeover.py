from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
import os

from core.automation import run_automation_cycle
from core.camera_vision import analyze_camera_frame
from core.morning import generate_morning_briefing
from core.prompt_adaptation import run_prompt_evolution_cycle
from tools.file_watch import build_integrity_snapshot, check_integrity
from tools.iot import control_smart_plug
from tools.sysmon import get_system_health


logger = logging.getLogger("SPARK_TAKEOVER")


@dataclass(frozen=True)
class TakeoverReport:
    timestamp: str
    system_health: str
    file_changes: list[dict]
    morning_briefing: str
    camera_summary: str = ""
    smart_home_result: str = ""


_takeover_thread: threading.Thread | None = None
_stop_event = threading.Event()
_last_snapshot: dict[str, str] | None = None


def _night_window(now: datetime) -> bool:
    return now.hour >= 22 or now.hour < 6


def _prepare_report() -> TakeoverReport:
    global _last_snapshot
    current_snapshot = build_integrity_snapshot(".")
    file_changes: list[dict] = []
    if _last_snapshot is not None:
        file_changes = check_integrity(_last_snapshot)
    _last_snapshot = current_snapshot

    now = datetime.now()
    system_health = get_system_health()
    morning_briefing = generate_morning_briefing()
    camera_summary = analyze_camera_frame() if _night_window(now) else "Camera scan skipped outside night window."
    smart_home_enabled = os.getenv("TAKEOVER_SMART_HOME_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    smart_home_result = (
        control_smart_plug("off")
        if _night_window(now) and smart_home_enabled
        else "Smart home action skipped. Enable TAKEOVER_SMART_HOME_ENABLED to allow it."
    )

    return TakeoverReport(
        timestamp=now.isoformat(),
        system_health=system_health,
        file_changes=file_changes,
        morning_briefing=morning_briefing,
        camera_summary=camera_summary,
        smart_home_result=smart_home_result,
    )


def run_takeover_cycle() -> TakeoverReport:
    run_automation_cycle()
    run_prompt_evolution_cycle()
    return _prepare_report()


def _loop() -> None:
    logger.info("Nightly takeover loop started.")
    while not _stop_event.is_set():
        now = datetime.now()
        next_run = now.replace(hour=22, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_seconds = max(1.0, (next_run - now).total_seconds())

        if _stop_event.wait(timeout=wait_seconds):
            break

        try:
            report = run_takeover_cycle()
            logger.info("Takeover report: %s", report)
        except Exception as exc:
            logger.error("Takeover cycle failed: %s", exc, exc_info=True)


def start_takeover_mode() -> threading.Thread:
    global _takeover_thread
    if _takeover_thread and _takeover_thread.is_alive():
        return _takeover_thread
    _stop_event.clear()
    _takeover_thread = threading.Thread(target=_loop, name="spark-nightly-takeover", daemon=True)
    _takeover_thread.start()
    return _takeover_thread


def stop_takeover_mode() -> None:
    _stop_event.set()
    if _takeover_thread:
        _takeover_thread.join(timeout=2)
