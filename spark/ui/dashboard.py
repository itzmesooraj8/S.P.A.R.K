"""Dashboard — JARVIS-style system dashboard.

Shows:
- Current Goal
- Current Plan
- Current Memory
- Current Context
- Running Agents
- Tool Usage
- System Health
- Permissions
- Goal Graph
- Agent Health
- Awareness Feed
- Decision Log
"""

from __future__ import annotations

import time
from typing import Any


class Dashboard:
    """JARVIS-style dashboard that shows system state, not just chat."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {
            "current_goal": None,
            "current_plan": None,
            "memory_stats": {},
            "context": {},
            "running_agents": [],
            "tool_usage": {},
            "system_health": {},
            "permissions": {},
            "recent_activity": [],
            "goal_graph": {},
            "agent_health": [],
            "awareness_feed": [],
            "decision_log": [],
            "world_model": {},
            "working_memory": {},
            "skills": [],
            "capabilities": [],
        }

    def update(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get_snapshot(self) -> dict[str, Any]:
        return {**self._data, "timestamp": time.time(), "status": "operational"}

    def render_text(self) -> str:
        lines = [
            "=" * 60,
            "  S.P.A.R.K. AI OPERATING SYSTEM — JARVIS DASHBOARD",
            "=" * 60,
            "",
        ]

        wm = self._data.get("working_memory", {})
        obj = wm.get("objective", {})
        lines.append("  ┌─ WORKING MEMORY ─────────────────────────────────────┐")
        lines.append(f"  │ Objective: {obj.get('description', 'None')[:45]:<45} │")
        lines.append(f"  │ Progress:  {obj.get('subtasks_done', 0)}/{obj.get('subtasks_total', 0)} subtasks completed{' ' * 25} │")
        task = wm.get("task", {})
        lines.append(f"  │ Task:      {task.get('description', 'idle')[:45]:<45} │")
        lines.append(f"  │ Status:    {task.get('status', 'idle'):<45} │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        goal = self._data.get("current_goal")
        lines.append("  ┌─ CURRENT GOAL ───────────────────────────────────────┐")
        if goal:
            lines.append(f"  │ {goal.get('description', 'None')[:53]:<53} │")
            lines.append(f"  │ Priority: {goal.get('priority', 5)}  |  Status: {goal.get('status', 'unknown'):<28} │")
        else:
            lines.append("  │ No active goal                                     │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        goal_graph = self._data.get("goal_graph", {})
        if goal_graph:
            lines.append("  ┌─ GOAL GRAPH ────────────────────────────────────────┐")
            self._render_goal_tree(lines, goal_graph, indent=5)
            lines.append("  └──────────────────────────────────────────────────────┘")
            lines.append("")

        agent_health = self._data.get("agent_health", [])
        lines.append("  ┌─ AGENT HEALTH ──────────────────────────────────────┐")
        for agent in agent_health:
            name = agent.get("name", "?")
            status = agent.get("status", "?")
            latency = agent.get("latency_ms", 0)
            errors = agent.get("errors", 0)
            indicator = "●" if status == "idle" else "◉" if status == "running" else "✗"
            lines.append(f"  │ {indicator} {name:<15} {status:<10} {latency:>5.0f}ms  errors:{errors:<3} │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        wm_stats = self._data.get("memory_stats", {})
        lines.append("  ┌─ MEMORY ────────────────────────────────────────────┐")
        lines.append(f"  │ Semantic: {wm_stats.get('semantic_count', 0):<6}  Episodic: {wm_stats.get('episodic_count', 0):<6}       │")
        lines.append(f"  │ Working Memory: {wm_stats.get('working_active', 'active'):<39} │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        awareness_feed = self._data.get("awareness_feed", [])
        lines.append("  ┌─ AWARENESS FEED ────────────────────────────────────┐")
        for event in awareness_feed[-5:]:
            etype = event.get("event_type", "?")
            ts = time.strftime("%H:%M:%S", time.localtime(event.get("timestamp", 0)))
            lines.append(f"  │ {ts} {etype:<45} │")
        if not awareness_feed:
            lines.append("  │ No awareness events yet                            │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        health = self._data.get("system_health", {})
        lines.append("  ┌─ SYSTEM HEALTH ─────────────────────────────────────┐")
        lines.append(f"  │ Status: {health.get('status', 'unknown'):<15} Platform: {health.get('platform', '?'):<20} │")
        lines.append(f"  │ CPU: {health.get('cpu_percent', '?')}%  |  Memory: {health.get('memory_percent', '?')}%  |  Net: {health.get('net_recv_mb', '?')}MB recv  │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        ctx = self._data.get("context", {})
        world = self._data.get("world_model", {})
        lines.append("  ┌─ CONTEXT & WORLD MODEL ─────────────────────────────┐")
        lines.append(f"  │ Active Window: {ctx.get('active_window', '?')[:40]:<40} │")
        lines.append(f"  │ User Present: {ctx.get('user_present', '?'):<41} │")
        lines.append(f"  │ Activity: {world.get('current_activity', 'unknown'):<45} │")
        predictions = world.get("predictions", [])
        if predictions:
            lines.append(f"  │ Predicted Need: {predictions[0].get('need', '?'):<39} │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        decision_log = self._data.get("decision_log", [])
        lines.append("  ┌─ DECISION LOG ──────────────────────────────────────┐")
        for decision in decision_log[-3:]:
            action = decision.get("action", "?")[:20]
            reason = decision.get("reason", "?")[:25]
            ts = time.strftime("%H:%M:%S", time.localtime(decision.get("timestamp", 0)))
            lines.append(f"  │ {ts} {action:<20} {reason:<25} │")
        if not decision_log:
            lines.append("  │ No decisions recorded yet                          │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        skills = self._data.get("skills", [])
        lines.append("  ┌─ SKILLS ────────────────────────────────────────────┐")
        for skill in skills[:5]:
            name = skill.get("name", "?")[:25]
            uses = skill.get("use_count", 0)
            rate = skill.get("success_rate", 0)
            lines.append(f"  │ {name:<25} uses:{uses:<4} rate:{rate:.0%}          │")
        if not skills:
            lines.append("  │ No skills learned yet                              │")
        lines.append("  └──────────────────────────────────────────────────────┘")
        lines.append("")

        perms = self._data.get("permissions", {})
        granted = sum(1 for v in perms.values() if v)
        lines.append(f"  PERMISSIONS: {granted}/{len(perms)} granted")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _render_goal_tree(self, lines: list[str], node: dict[str, Any], indent: int = 5) -> None:
        prefix = " " * indent
        desc = node.get("description", "?")[:40]
        status = node.get("status", "?")
        lines.append(f"  │ {prefix}├─ {desc} [{status}]")
        for child in node.get("children", []):
            self._render_goal_tree(lines, child, indent + 4)
