from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

from config import LLM_HOST
from core.memory_loop import retrieve as retrieve_turns
from core.scheduler import list_reminders
from tools.sysmon import get_raw_metrics
from tools.web_search import web_search_answer


log = logging.getLogger("spark.agentic_brain")
ARTIFACT_DIR = Path("spark_dev_memory/agentic_brain")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
PLANNING_MODEL = os.getenv("SPARK_PLANNING_MODEL", os.getenv("LLM_MODEL", "llama3.1:8b"))

# LLM routing thresholds and patterns
FACTUAL_KEYWORDS = {
    "what", "when", "where", "who", "how much", "define", "explain", "tell me",
    "weather", "time", "date", "current", "latest", "today", "now",
}

MULTI_STEP_KEYWORDS = {
    "research", "compare", "recommend", "best", "upgrade", "choose", "buy", "purchase",
    "benchmark", "evaluate", "analyze", "diagnose", "plan", "design", "build", "create",
    "strategy", "approach", "steps", "process", "workflow",
}

PRIVATE_KEYWORDS = {
    "file", "folder", "directory", "local", "home", "desktop", "document", "code",
    "project", "repository", "system", "computer", "machine", "device", "private",
    "personal", "calendar", "email", "my ", "mine",
}

AVAILABLE_TOOLS: dict[str, str] = {
    "web_search": "Search the internet for current information",
    "system_check": "Check local system hardware, RAM, CPU, storage",
    "file_write": "Save a report or artifact to disk",
    "calendar_check": "Check upcoming events and schedule",
    "code_exec": "Run a Python snippet and return output",
    "ollama_chat": "Ask a question and get a conversational response",
}

EventSink = Callable[[str, dict[str, Any]], None]


class QueryClassification:
    """Result of query complexity classification."""
    def __init__(self, query_type: str, complexity: float, recommended_backend: str):
        self.query_type = query_type  # FACTUAL, MULTI_STEP, LOCAL_PRIVATE
        self.complexity = complexity  # 0.0 - 1.0
        self.recommended_backend = recommended_backend  # groq, agentic, ollama


def classify_query(goal: str) -> QueryClassification:
    """
    Fast classifier for LLM routing.
    Determines query type and recommends optimal backend.
    
    Returns:
    - FACTUAL (low complexity): Route to Groq llama-3.3-70b for fast factual answers
    - MULTI_STEP (high complexity): Route to agentic brain with planning
    - LOCAL_PRIVATE: Route to Ollama for privacy (local/system queries)
    """
    text = goal.lower().strip()
    if not text:
        return QueryClassification("FACTUAL", 0.1, "groq")
    
    # Check for private/local queries first (highest priority)
    private_score = sum(1 for keyword in PRIVATE_KEYWORDS if keyword in text)
    if private_score >= 2:
        return QueryClassification("LOCAL_PRIVATE", 0.3, "ollama")
    
    # Check for multi-step complex queries
    multi_score = sum(1 for keyword in MULTI_STEP_KEYWORDS if keyword in text)
    if multi_score >= 2:
        return QueryClassification("MULTI_STEP", 0.8, "agentic")
    
    # Check question length (longer = more complex)
    word_count = len(text.split())
    if word_count > 25:
        return QueryClassification("MULTI_STEP", 0.7, "agentic")
    
    # Check for factual indicators
    factual_score = sum(1 for keyword in FACTUAL_KEYWORDS if keyword in text)
    if factual_score >= 1:
        return QueryClassification("FACTUAL", 0.2, "groq")
    
    # Default: treat as factual but slightly uncertain
    return QueryClassification("FACTUAL", 0.5, "groq")


def is_agentic_goal(goal: str) -> bool:
    """
    DEPRECATED: Use classify_query() instead.
    Legacy function for backward compatibility.
    Returns True if goal should be routed to agentic brain.
    """
    classification = classify_query(goal)
    return classification.recommended_backend in ("agentic", "ollama")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "agentic-run"


def _truncate(text: str, limit: int = 240) -> str:
    stripped = text.strip()
    return stripped if len(stripped) <= limit else stripped[: limit - 3].rstrip() + "..."


def _run_coroutine_sync(coro: Awaitable[Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: list[BaseException] = []

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:
            error.append(exc)

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()
    worker.join()

    if error:
        raise error[0]

    return result.get("value")


@dataclass
class BrainStep:
    index: int
    tool: str
    title: str
    input: str = ""
    status: str = "pending"
    output: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainRun:
    goal: str
    intent: str = "research"
    status: str = "pending"
    steps: list[BrainStep] = field(default_factory=list)
    results: list[str] = field(default_factory=list)
    report_path: str = ""
    summary: str = ""
    final_answer: dict[str, Any] = field(default_factory=dict)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    recent_context: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


class AgenticBrain:
    def __init__(self) -> None:
        self.log = log

    async def call_ollama(self, model: str, prompt: str) -> str:
        response = httpx.post(
            f"{LLM_HOST}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30.0,
        )
        response.raise_for_status()
        return str(response.json().get("response", "")).strip()

    async def plan_steps(self, query: str) -> list[str]:
        """Ask the LLM which tools to use for this query."""
        tool_list = "\n".join(
            f"- {name}: {desc}" for name, desc in AVAILABLE_TOOLS.items()
        )
        prompt = f"""You are SPARK's planning engine.
Given this user request: "{query}"
Available tools:
{tool_list}

Return ONLY a JSON array of tool names to call in order.
Example: ["web_search", "file_write"]
Max 4 tools. Only include tools that are actually needed."""

        try:
            response = await self.call_ollama("phi3:mini", prompt)
        except Exception:
            response = ""

        import json
        import re
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return ["ollama_chat"]  # safe fallback

    def _step_title(self, tool: str) -> str:
        titles = {
            "web_search": "Research current recommendations",
            "system_check": "Inspect local machine telemetry",
            "calendar_check": "Check scheduled activity",
            "file_write": "Write a brief artifact",
            "ollama_chat": "Synthesize the final answer",
        }
        return titles.get(tool, tool.replace("_", " ").title())

    def _step_input(self, tool: str, goal: str) -> str:
        if tool == "web_search":
            return goal.strip()
        if tool == "calendar_check":
            return goal.strip()
        if tool == "ollama_chat":
            return goal.strip()
        return ""

    def plan(self, goal: str, context_snapshot: dict[str, Any] | None = None) -> BrainRun:
        run = BrainRun(goal=goal, context_snapshot=context_snapshot or {})
        planned_steps = _run_coroutine_sync(self.plan_steps(goal))
        run.steps = [
            BrainStep(
                index=index + 1,
                tool=tool,
                title=self._step_title(tool),
                input=self._step_input(tool, goal),
            )
            for index, tool in enumerate(planned_steps)
        ]
        return run

    def _emit(self, sink: EventSink | None, event_type: str, payload: dict[str, Any]) -> None:
        if not sink:
            return
        try:
            sink(event_type, payload)
        except Exception:
            self.log.debug("Event sink failed for %s", event_type, exc_info=True)

    def _format_system_check(self, metrics: dict[str, Any]) -> str:
        gpu_name = str(metrics.get("gpu_name") or "N/A")
        gpu_util = metrics.get("gpu_util", 0)
        ram_used = metrics.get("ram_used_gb", 0.0)
        ram_total = metrics.get("ram_total_gb", 0.0)
        cpu = metrics.get("cpu_percent", metrics.get("cpu", 0))
        disk = metrics.get("disk_percent", 0)
        battery = metrics.get("batteryPercent", 100)
        return (
            f"CPU {cpu:.0f}%, RAM {ram_used:.1f}/{ram_total:.1f} GB used, "
            f"Disk {disk:.0f}%, GPU {gpu_name} at {gpu_util:.0f}% util, battery {battery:.0f}%"
        )

    def _format_calendar_check(self) -> str:
        reminders = list_reminders()
        if not reminders:
            return "No scheduled reminders or calendar-like tasks are currently pending."

        lines = []
        for reminder in reminders[:5]:
            next_run = reminder.get("next_run", "unknown")
            reminder_args = reminder.get("args") or []
            message = str(reminder_args[0]) if reminder_args else "Scheduled item"
            lines.append(f"{next_run}: {message}")
        return "Upcoming scheduled items: " + " | ".join(lines)

    async def _synthesize_with_ollama(self, run: BrainRun, findings: dict[str, Any]) -> str:
        context_lines = []
        for name, value in findings.items():
            if isinstance(value, str):
                context_lines.append(f"- {name}: {value}")
            else:
                context_lines.append(f"- {name}: {json.dumps(value, ensure_ascii=False)}")

        prompt = (
            "You are SPARK. Produce a concise, structured final answer based only on the gathered evidence. "
            "Include a short summary, recommendation, and next steps.\n\n"
            f"Goal: {run.goal}\n\n"
            "Findings:\n"
            + "\n".join(context_lines)
        )

        try:
            response = httpx.post(
                f"{LLM_HOST}/api/chat",
                json={
                    "model": PLANNING_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are SPARK's final synthesis engine."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            message = response.json().get("message", {})
            content = str(message.get("content", "")).strip()
            if content:
                return content
        except Exception:
            pass

        fallback = self._compose_final_answer(run)
        return json.dumps(fallback, ensure_ascii=False)

    def _build_report(self, run: BrainRun) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        slug = _slugify(run.goal)
        report_path = ARTIFACT_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slug}.md"

        step_lines = []
        for step in run.steps:
            step_lines.append(
                f"- [{step.status.upper()}] {step.tool}: {step.title}"
            )

        memory_lines = []
        for item in run.recent_context[-4:]:
            role = item.get("role", "unknown")
            content = _truncate(str(item.get("content", "")), 220)
            memory_lines.append(f"- {role}: {content}")

        report = [
            f"# Agentic Brain Report",
            f"- Generated: {timestamp}",
            f"- Goal: {run.goal}",
            "",
            "## Step Trace",
            *step_lines,
            "",
            "## Recent Memory",
            *(memory_lines or ["- No recent memory context was available."]),
            "",
            "## Context Snapshot",
            "```json",
            json.dumps(run.context_snapshot, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Findings",
        ]

        for key, value in run.final_answer.get("findings", {}).items():
            report.append(f"- {key}: {value}")

        report.extend([
            "",
            "## Recommendation",
            run.final_answer.get("recommendation", "No recommendation was generated."),
            "",
        ])

        report_path.write_text("\n".join(report), encoding="utf-8")
        return str(report_path)

    def _compose_final_answer(self, run: BrainRun) -> dict[str, Any]:
        web_findings = run.final_answer.get("findings", {}).get("web_search", "")
        system_summary = run.final_answer.get("findings", {}).get("system_check", "")

        if "gpu" in run.goal.lower() and "upgrade" in run.goal.lower():
            recommendation = (
                "Shortlist GPUs that fit your budget, PSU headroom, case clearance, and target resolution. "
                "If you want a future-proof purchase, prioritize VRAM and power efficiency over raw benchmark spikes."
            )
            next_steps = [
                "Confirm your PSU wattage and available power connectors.",
                "Measure case clearance and cooler height before buying.",
                "Compare VRAM capacity against the games or workloads you care about.",
            ]
        else:
            recommendation = (
                "Use the search findings and local system snapshot together, then validate any missing constraints before acting."
            )
            next_steps = [
                "Review the search result summary.",
                "Check the local system snapshot for any constraints.",
                "Decide whether you need a deeper comparison pass.",
            ]

        return {
            "summary": f"Completed a structured agentic run for: {run.goal}",
            "findings": {
                "web_search": web_findings,
                "system_check": system_summary,
                "report_path": run.report_path,
            },
            "recommendation": recommendation,
            "next_steps": next_steps,
        }

    def run(
        self,
        goal: str,
        context_snapshot: dict[str, Any] | None = None,
        event_sink: EventSink | None = None,
    ) -> dict[str, Any]:
        run = self.plan(goal, context_snapshot=context_snapshot)
        run.status = "running"

        self._emit(
            event_sink,
            "plan_started",
            {
                "goal": run.goal,
                "step_count": len(run.steps),
                "context_snapshot": run.context_snapshot,
            },
        )

        run.recent_context = retrieve_turns(goal, k_recent=4, k_semantic=4)
        if run.recent_context:
            self._emit(
                event_sink,
                "context_loaded",
                {
                    "goal": run.goal,
                    "recent_turns": [
                        {
                            "role": item.get("role", "unknown"),
                            "content": _truncate(str(item.get("content", "")), 160),
                        }
                        for item in run.recent_context[-4:]
                    ],
                },
            )

        findings: dict[str, Any] = {}
        system_metrics: dict[str, Any] = {}

        for step in run.steps:
            self._emit(
                event_sink,
                "step_started",
                {
                    "goal": run.goal,
                    "step": asdict(step),
                },
            )

            try:
                if step.tool == "web_search":
                    result = web_search_answer(step.input or run.goal)
                    findings[step.tool] = result
                    step.output = result
                    step.details = {"query": step.input or run.goal}

                elif step.tool == "system_check":
                    system_metrics = get_raw_metrics()
                    result = self._format_system_check(system_metrics)
                    findings[step.tool] = result
                    step.output = result
                    step.details = system_metrics

                elif step.tool == "calendar_check":
                    result = self._format_calendar_check()
                    findings[step.tool] = result
                    step.output = result
                    step.details = {"reminders": list_reminders()[:5]}

                elif step.tool == "file_write":
                    report_stub = BrainRun(
                        goal=run.goal,
                        context_snapshot=run.context_snapshot,
                        recent_context=run.recent_context,
                        final_answer={"findings": findings},
                    )
                    report_stub.report_path = self._build_report(report_stub)
                    result = f"Saved research brief to {report_stub.report_path}"
                    run.report_path = report_stub.report_path
                    findings[step.tool] = result
                    step.output = result
                    step.details = {"report_path": report_stub.report_path}
                    run.artifacts.append({"kind": "report", "path": report_stub.report_path})
                    self._emit(
                        event_sink,
                        "artifact_written",
                        {
                            "goal": run.goal,
                            "path": report_stub.report_path,
                            "kind": "report",
                        },
                    )

                elif step.tool == "ollama_chat":
                    result = _run_coroutine_sync(self._synthesize_with_ollama(run, findings))
                    try:
                        parsed = json.loads(result)
                        run.final_answer = parsed if isinstance(parsed, dict) else {"summary": result}
                    except Exception:
                        run.final_answer = {"summary": result}
                    findings[step.tool] = run.final_answer
                    step.output = result
                    step.details = run.final_answer

                else:
                    result = f"Unsupported step: {step.tool}"
                    findings[step.tool] = result
                    step.output = result

                step.status = "done"
                run.results.append(result)
                self._emit(
                    event_sink,
                    "step_completed",
                    {
                        "goal": run.goal,
                        "step": asdict(step),
                        "preview": _truncate(result, 220),
                    },
                )
            except Exception as exc:
                step.status = "failed"
                step.output = str(exc)
                run.status = "blocked"
                self._emit(
                    event_sink,
                    "step_failed",
                    {
                        "goal": run.goal,
                        "step": asdict(step),
                        "error": str(exc),
                    },
                )
                break

        if not run.report_path:
            # Persist a report even if the final response step failed.
            fallback_stub = BrainRun(
                goal=run.goal,
                context_snapshot=run.context_snapshot,
                recent_context=run.recent_context,
                final_answer={"findings": findings},
            )
            fallback_stub.report_path = self._build_report(fallback_stub)
            run.report_path = fallback_stub.report_path

        if run.status != "blocked":
            run.status = "done"

        if not run.final_answer:
            run.final_answer = self._compose_final_answer(run)
            run.final_answer["findings"] = {
                "web_search": findings.get("web_search", ""),
                "system_check": findings.get("system_check", ""),
                "calendar_check": findings.get("calendar_check", ""),
                "report_path": run.report_path,
            }

        if run.report_path:
            try:
                self._build_report(run)
            except Exception:
                pass

        self._emit(
            event_sink,
            "plan_completed",
            {
                "goal": run.goal,
                "status": run.status,
                "report_path": run.report_path,
                "final_answer": run.final_answer,
                "steps": [asdict(step) for step in run.steps],
            },
        )

        recent_context_summary = [
            {
                "role": item.get("role", "unknown"),
                "content": _truncate(str(item.get("content", "")), 180),
                "ts": item.get("ts"),
            }
            for item in run.recent_context[-4:]
        ]

        return {
            "goal": run.goal,
            "intent": run.intent,
            "status": run.status,
            "steps": [asdict(step) for step in run.steps],
            "results": run.results,
            "report_path": run.report_path,
            "final_answer": run.final_answer,
            "context_snapshot": run.context_snapshot,
            "recent_context": recent_context_summary,
            "artifacts": run.artifacts,
        }


_BRAIN = AgenticBrain()


def get_agentic_brain() -> AgenticBrain:
    return _BRAIN
