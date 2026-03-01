"""
SPARK Routines
──────────────────────────────────────────────────────────────────────────────
Named multi-step operating-mode sequences.
Each step mirrors the Plan/Step machinery used by spark_commander_router:
  label   — human-readable description (shown in ActionFeed)
  tool    — executor key: open_app | open_url | run_command
                          | frontend_fx   (emits ROUTINE_FX WS frame)
                          | emit_alert    (emits ALERT WS frame)
  args    — tool arguments dict

Frontend FX tokens (frontend_fx tool):
  NAVIGATE_GLOBE        — navigate('/globe-monitor')
  NAVIGATE_ALERTS       — open alertlog module
  NAVIGATE_TOOLS        — open tools module
  NAVIGATE_ACTIONFEED   — open actionfeed module
  FOCUS_MODE_ON         — enable focus mode (reduces visual noise)
  FOCUS_MODE_OFF        — disable focus mode
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Type aliases ──────────────────────────────────────────────────────────────

RoutineStep = Dict[str, Any]


class Routine:
    def __init__(self, name: str, description: str, steps: List[RoutineStep]):
        self.name        = name
        self.description = description
        self.steps       = steps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":        self.name,
            "description": self.description,
            "steps":       self.steps,
        }


# ── Routine definitions ────────────────────────────────────────────────────────

_DEV = Routine(
    name="Dev Mode",
    description="Opens VS Code, starts SPARK core + agent, launches HUD, opens Action Feed.",
    steps=[
        {
            "label": "Launch VS Code",
            "tool":  "open_app",
            "args":  {"app_name": "code"},
        },
        {
            "label": "Open repo in editor",
            "tool":  "run_command",
            "args":  {"command": "code .", "background": True},
        },
        {
            "label": "Open SPARK HUD",
            "tool":  "open_url",
            "args":  {"url": "http://localhost:5173"},
        },
        {
            "label": "Open Action Feed panel",
            "tool":  "frontend_fx",
            "args":  {"fx": "NAVIGATE_ACTIONFEED"},
        },
        {
            "label": "Confirm Dev Mode active",
            "tool":  "emit_alert",
            "args":  {
                "severity": "info",
                "title":    "Dev Mode Active",
                "body":     "VS Code open · Action feed ready · Systems nominal.",
                "source":   "spark-routine",
            },
        },
    ],
)

_MONITOR = Routine(
    name="Monitor Mode",
    description="Opens Globe Monitor, Alert Log, and emits a monitor-activation notice.",
    steps=[
        {
            "label": "Open Globe Monitor",
            "tool":  "frontend_fx",
            "args":  {"fx": "NAVIGATE_GLOBE"},
        },
        {
            "label": "Open Alert Log",
            "tool":  "frontend_fx",
            "args":  {"fx": "NAVIGATE_ALERTS"},
        },
        {
            "label": "Confirm Monitor Mode active",
            "tool":  "emit_alert",
            "args":  {
                "severity": "info",
                "title":    "Monitor Mode Active",
                "body":     "Globe and threat tracking engaged · Alert log open.",
                "source":   "spark-routine",
            },
        },
    ],
)

_FOCUS = Routine(
    name="Focus Mode",
    description="Reduces HUD noise, opens Tool Activity feed, CRIT-only alerts.",
    steps=[
        {
            "label": "Enable Focus Mode overlay",
            "tool":  "frontend_fx",
            "args":  {"fx": "FOCUS_MODE_ON"},
        },
        {
            "label": "Open Tool Activity feed",
            "tool":  "frontend_fx",
            "args":  {"fx": "NAVIGATE_TOOLS"},
        },
        {
            "label": "Confirm Focus Mode active",
            "tool":  "emit_alert",
            "args":  {
                "severity": "info",
                "title":    "Focus Mode Active",
                "body":     "Noise reduced · Tool feed open · CRIT alerts only.",
                "source":   "spark-routine",
            },
        },
    ],
)


# ── Registry ──────────────────────────────────────────────────────────────────

ROUTINES: Dict[str, Routine] = {
    "dev":     _DEV,
    "monitor": _MONITOR,
    "focus":   _FOCUS,
}


def get_routine(name: str) -> Optional[Routine]:
    """Return a Routine by name (case-insensitive), or None if not found."""
    return ROUTINES.get(name.lower())


def list_routines() -> List[str]:
    """Return the list of available routine keys."""
    return list(ROUTINES.keys())
