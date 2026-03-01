"""
SPARK CommanderRouter — Intent Classifier + Plan Executor
──────────────────────────────────────────────────────────────────────────────
Classifies natural-language commands into structured intents, decomposes them
into executable steps, emits PLAN/STEP frames to /ws/system, and executes
desktop/web/agent actions with full evidence streaming to the HUD Action Feed.

Intent taxonomy:
    CHAT            → route to brain.py agent_loop (conversational)
    TASK            → open-app / open-url / run-command on host OS
    GLOBE_QUERY     → query globe / geopolitical intelligence pipeline
    SYSTEM_QUERY    → inspect SPARK internal state, metrics, logs
    CREATE_CASE     → persist a tactical case / alert to memory
    RESEARCH        → delegate to research/intelligence agent
    CODE            → delegate to code agent
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from system.event_bus import event_bus

# Lazy import of ws_manager to avoid circular initialization
def _ws():
    from ws.manager import ws_manager
    return ws_manager


# ── Intent taxonomy ───────────────────────────────────────────────────────────

class Intent(str, Enum):
    CHAT         = "CHAT"
    TASK         = "TASK"
    GLOBE_QUERY  = "GLOBE_QUERY"
    SYSTEM_QUERY = "SYSTEM_QUERY"
    CREATE_CASE  = "CREATE_CASE"
    RESEARCH     = "RESEARCH"
    CODE         = "CODE"


# ── Plan primitives ───────────────────────────────────────────────────────────

class StepStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    SKIPPED  = "skipped"


@dataclass
class PlanStep:
    idx: int
    label: str
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    ts_start: Optional[float] = None
    ts_end: Optional[float] = None


@dataclass
class Plan:
    plan_id: str
    intent: Intent
    query: str
    steps: List[PlanStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


# ── Intent patterns ───────────────────────────────────────────────────────────

_TASK_OPEN_APP = re.compile(
    r"(?:open|launch|start|run|fire up)\s+(?:the\s+)?(?P<app>[a-zA-Z0-9 _\-+.]+?)(?:\s+app(?:lication)?)?$",
    re.I,
)
_TASK_OPEN_URL = re.compile(
    r"(?:go to|open|visit|navigate to|browse|show me)\s+(?P<url>(?:https?://)?[\w\-./]+\.[a-z]{2,}(?:/\S*)?)",
    re.I,
)
_TASK_RUN_CMD = re.compile(
    r"(?:run|execute|shell|terminal)\s+(?:command\s+)?[`'\"]?(?P<cmd>.+)[`'\"]?$",
    re.I,
)
_GLOBE_KW = (
    "conflict", "war", "geopolit", "region", "country", "missile",
    "sanction", "intel", "brief", "globe", "event", "crisis", "threat map",
    "breaking news", "news", "attack", "invasion",
)
_SYSTEM_KW = (
    "cpu", "ram", "memory", "disk", "gpu", "status", "health", "ping",
    "uptime", "processes", "metric", "performance", "agent status",
    "model status", "system",
)
_CASE_KW   = ("create case", "new case", "add case", "log case", "report", "escalate")
_CODE_KW   = ("code", "debug", "refactor", "function", "class", "script",
               "python", "typescript", "write a ", "fix this", "generate a")
_RESEARCH_KW = ("research", "find", "search", "look up", "what is", "tell me about",
                "explain", "summarize", "summary", "who is", "where is")


def classify_intent(text: str) -> Intent:
    """Heuristic + pattern-based intent classification."""
    t = text.strip()
    tl = t.lower()

    # TASK: open app
    if _TASK_OPEN_APP.search(t):
        return Intent.TASK
    # TASK: open URL
    if _TASK_OPEN_URL.search(t):
        return Intent.TASK
    # TASK: run command
    if _TASK_RUN_CMD.search(tl):
        return Intent.TASK
    # Explicit task verbs without regex match
    if any(tl.startswith(v) for v in ("open ", "launch ", "start ", "run ", "execute ")):
        return Intent.TASK

    # Globe / geopolitical
    if any(k in tl for k in _GLOBE_KW):
        return Intent.GLOBE_QUERY

    # System query
    if any(k in tl for k in _SYSTEM_KW):
        return Intent.SYSTEM_QUERY

    # Case creation
    if any(k in tl for k in _CASE_KW):
        return Intent.CREATE_CASE

    # Code
    if any(k in tl for k in _CODE_KW):
        return Intent.CODE

    # Research / OSINT
    if any(k in tl for k in _RESEARCH_KW):
        return Intent.RESEARCH

    return Intent.CHAT


# ── Plan builders ─────────────────────────────────────────────────────────────

def build_plan(text: str, intent: Intent, ctx: Dict[str, Any]) -> Plan:
    plan = Plan(
        plan_id=str(uuid.uuid4()),
        intent=intent,
        query=text,
        context=ctx,
    )
    t  = text.strip()
    tl = t.lower()

    if intent == Intent.TASK:
        _build_task_steps(plan, t, tl)
    elif intent == Intent.GLOBE_QUERY:
        plan.steps = [
            PlanStep(0, "Query globe intelligence pipeline", tool="globe_query", args={"q": t}),
            PlanStep(1, "Format and return results"),
        ]
    elif intent == Intent.SYSTEM_QUERY:
        plan.steps = [
            PlanStep(0, "Fetch live system metrics", tool="get_system_state"),
            PlanStep(1, "Synthesize answer"),
        ]
    elif intent == Intent.CREATE_CASE:
        plan.steps = [
            PlanStep(0, "Extract case details"),
            PlanStep(1, "Persist to memory store", tool="memory_store"),
            PlanStep(2, "Confirm and notify"),
        ]
    elif intent == Intent.CODE:
        plan.steps = [
            PlanStep(0, "Understand code request"),
            PlanStep(1, "Route to Code Agent"),
            PlanStep(2, "Return code response"),
        ]
    elif intent == Intent.RESEARCH:
        plan.steps = [
            PlanStep(0, "Decompose research query"),
            PlanStep(1, "Route to Research Agent"),
            PlanStep(2, "Return synthesized report"),
        ]
    else:  # CHAT
        plan.steps = [
            PlanStep(0, "Process with SPARK brain"),
            PlanStep(1, "Stream response"),
        ]

    return plan


def _build_task_steps(plan: Plan, text: str, tl: str):
    """Decompose a TASK intent into concrete tool steps."""
    # Try open URL
    m_url = _TASK_OPEN_URL.search(text)
    if m_url:
        url = m_url.group("url")
        plan.steps = [
            PlanStep(0, f"Navigate to {url}", tool="open_url", args={"url": url}),
        ]
        return

    # Try open app
    m_app = _TASK_OPEN_APP.search(text)
    if m_app:
        app = m_app.group("app").strip()
        plan.steps = [
            PlanStep(0, f"Launch '{app}'", tool="open_app", args={"app_name": app}),
        ]
        return

    # Try run command
    m_cmd = _TASK_RUN_CMD.search(tl)
    if m_cmd:
        cmd = m_cmd.group("cmd").strip(" `'\"")
        plan.steps = [
            PlanStep(0, f"Execute: {cmd}", tool="run_command", args={"command": cmd}),
        ]
        return

    # Generic start/launch
    for prefix in ("open ", "launch ", "start ", "run "):
        if tl.startswith(prefix):
            target = text[len(prefix):].strip()
            # URL vs app heuristic
            if "." in target and " " not in target:
                plan.steps = [PlanStep(0, f"Open {target}", tool="open_url", args={"url": target})]
            else:
                plan.steps = [PlanStep(0, f"Launch '{target}'", tool="open_app", args={"app_name": target})]
            return

    # Fallback
    plan.steps = [PlanStep(0, "Execute task", tool="run_command", args={"command": text})]


# ── WS emission helpers ───────────────────────────────────────────────────────

async def _emit(payload: Dict[str, Any]):
    import json
    try:
        await _ws().broadcast(json.dumps(payload), "system")
    except Exception as e:
        print(f"[CommanderRouter] WS emit error: {e}")


async def emit_plan(plan: Plan):
    await _emit({
        "v": 1,
        "type": "PLAN",
        "plan_id": plan.plan_id,
        "intent": plan.intent.value,
        "query": plan.query,
        "steps": [
            {"idx": s.idx, "label": s.label, "tool": s.tool, "status": s.status.value}
            for s in plan.steps
        ],
        "ts": plan.ts,
    })


async def emit_step(plan_id: str, step: PlanStep):
    await _emit({
        "v": 1,
        "type": "STEP",
        "plan_id": plan_id,
        "step_idx": step.idx,
        "label": step.label,
        "tool": step.tool,
        "status": step.status.value,
        "result": step.result,
        "ts": time.time(),
    })


# ── Executor ──────────────────────────────────────────────────────────────────

async def execute_plan(plan: Plan) -> str:
    """
    Execute each step in plan sequentially.
    Emits STEP frames before and after each step.
    Returns a summary string.
    """
    from tools.desktop import open_app, open_url, run_command

    # ── Built-in virtual tools ─────────────────────────────────────────────

    async def _frontend_fx(args: Dict[str, Any]) -> str:
        """Emit a ROUTINE_FX frame so the HUD can navigate/change state."""
        fx = args.get("fx", "")
        await _emit({
            "v":    1,
            "type": "ROUTINE_FX",
            "fx":   fx,
            "args": args,
            "ts":   time.time(),
        })
        return f"✅ FX:{fx}"

    async def _emit_alert_step(args: Dict[str, Any]) -> str:
        """Emit an ALERT frame into the HUD alert log."""
        await _emit({
            "v":        1,
            "type":     "ALERT",
            "severity": args.get("severity", "info"),
            "title":    args.get("title", "SPARK"),
            "body":     args.get("body", ""),
            "source":   args.get("source", "spark-routine"),
            "ts":       time.time(),
        })
        return "✅ Alert emitted"

    _DESKTOP_TOOLS = {
        "open_app":    open_app,
        "open_url":    open_url,
        "run_command": run_command,
        "frontend_fx": _frontend_fx,
        "emit_alert":  _emit_alert_step,
    }

    results: List[str] = []

    for step in plan.steps:
        step.status = StepStatus.RUNNING
        step.ts_start = time.time()
        await emit_step(plan.plan_id, step)

        try:
            if step.tool and step.tool in _DESKTOP_TOOLS:
                result = await _DESKTOP_TOOLS[step.tool](step.args)
                step.result = result
                step.status = StepStatus.DONE
                results.append(result)
            elif step.tool in (None, "get_system_state"):
                # Non-tool step — mark done immediately
                step.status = StepStatus.DONE
                step.result = "✅ OK"
            else:
                # Unknown tool — skip gracefully
                step.status = StepStatus.SKIPPED
                step.result = f"(tool '{step.tool}' not in desktop executor)"
        except Exception as e:
            step.status = StepStatus.FAILED
            step.result = f"❌ {e}"

        step.ts_end = time.time()
        await emit_step(plan.plan_id, step)

    return "\n".join(r for r in results if r) or "Done."


# ── CommanderRouter singleton ─────────────────────────────────────────────────

class CommanderRouter:
    """
    High-level entry point: classify → build plan → emit PLAN frame → execute.
    """

    async def run(
        self,
        text: str,
        context_snapshot: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Classify and execute a user command.
        Returns a dict with plan_id, intent, steps, and a summary result.
        """
        ctx = context_snapshot or {}

        intent = classify_intent(text)
        plan   = build_plan(text, intent, ctx)

        # Emit PLAN frame immediately (HUD shows it before execution)
        await emit_plan(plan)

        if intent == Intent.TASK:
            # Execute desktop actions directly
            result = await execute_plan(plan)
            return {
                "plan_id": plan.plan_id,
                "intent":  intent.value,
                "steps":   [{"idx": s.idx, "label": s.label, "status": s.status.value, "result": s.result} for s in plan.steps],
                "result":  result,
            }

        # For agent-routable intents, delegate to SPARK brain/agents
        bg_result = await self._delegate_to_brain(intent, text, plan, session_id)
        return {
            "plan_id":   plan.plan_id,
            "intent":    intent.value,
            "steps":     [{"idx": s.idx, "label": s.label, "status": s.status.value, "result": s.result} for s in plan.steps],
            "result":    bg_result,
        }

    async def _delegate_to_brain(
        self,
        intent: Intent,
        text: str,
        plan: Plan,
        session_id: Optional[str],
    ) -> str:
        """Route non-TASK intents through the appropriate agent/brain."""
        try:
            if intent in (Intent.CHAT, Intent.CODE, Intent.RESEARCH):
                from orchestrator.brain import orchestrator
                tokens: List[str] = []
                async for chunk in orchestrator.agent_loop(text, session_id or "commander"):
                    tokens.append(chunk)
                result = "".join(tokens)
            elif intent == Intent.GLOBE_QUERY:
                from agents.intelligence_agent import IntelligenceAgent
                # Use commander's intelligence agent if available
                from agents.commander import commander
                ar = await commander.ask(text, session_id=session_id, wait=True)
                result = (ar.output if ar and ar.success else None) or "No intelligence result."
            elif intent == Intent.SYSTEM_QUERY:
                from system.state import unified_state
                state = unified_state.get_state()
                metrics = state.get("metrics", {})
                result = (
                    f"CPU: {metrics.get('cpu_percent', 0):.1f}% | "
                    f"RAM: {metrics.get('memory_percent', 0):.1f}% | "
                    f"Ping: {metrics.get('ping_ms', 0):.0f}ms | "
                    f"Threat: {state.get('threat_level', 'unknown')}"
                )
            elif intent == Intent.CREATE_CASE:
                from agents.commander import commander
                ar = await commander.ask(text, session_id=session_id, wait=True)
                result = (ar.output if ar and ar.success else None) or "Case logged."
            else:
                result = "Processed."

            # Mark all plan steps done
            for step in plan.steps:
                if step.status == StepStatus.PENDING:
                    step.status = StepStatus.DONE
                    step.result = "✅"
                    await emit_step(plan.plan_id, step)

            return result

        except Exception as e:
            for step in plan.steps:
                if step.status == StepStatus.PENDING:
                    step.status = StepStatus.FAILED
                    step.result = f"❌ {e}"
                    await emit_step(plan.plan_id, step)
            return f"Error processing command: {e}"


# ── Singleton ─────────────────────────────────────────────────────────────────
commander_router = CommanderRouter()
