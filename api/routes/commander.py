from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.agentic_brain import get_agentic_brain, is_agentic_goal
from core.memory_loop import write_turn
from core.main import broadcast_hud_event, run_agent_turn
from security.content_sanitizer import sanitize_for_llm
from security.intent_validator import validate_intent_text


router = APIRouter()


def _extract_text(payload: dict[str, Any]) -> str:
    for key in ("text", "message", "query", "content", "command"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    params = payload.get("params")
    if isinstance(params, dict):
        for key in ("text", "message", "query"):
            value = params.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def _summarize_snapshot(snapshot: Any) -> dict[str, Any]:
    return snapshot if isinstance(snapshot, dict) else {}


def _command_event_sink(module: str, action: str, goal: str):
    def _emit(event_type: str, payload: dict[str, Any]) -> None:
        level = "info"
        action_text = event_type.replace("_", " ").title()
        data_text = ""

        if event_type == "plan_started":
            level = "system"
            action_text = "Plan started"
            data_text = f"{payload.get('step_count', 0)} steps for {goal}"
        elif event_type == "context_loaded":
            level = "system"
            action_text = "Context loaded"
            recent_turns = payload.get("recent_turns") or []
            data_text = f"{len(recent_turns)} recent turns recalled"
        elif event_type == "step_started":
            level = "info"
            step = payload.get("step") or {}
            action_text = f"Step {step.get('index', '?')} started"
            data_text = f"{step.get('tool', 'unknown')}: {step.get('title', '')}"
        elif event_type == "step_completed":
            level = "ai"
            step = payload.get("step") or {}
            action_text = f"Step {step.get('index', '?')} complete"
            data_text = payload.get("preview") or step.get("output", "")
        elif event_type == "step_failed":
            level = "critical"
            step = payload.get("step") or {}
            action_text = f"Step {step.get('index', '?')} failed"
            data_text = payload.get("error") or step.get("output", "")
        elif event_type == "plan_completed":
            level = "ai"
            action_text = "Plan complete"
            final_answer = payload.get("final_answer") or {}
            data_text = final_answer.get("recommendation") or final_answer.get("summary") or payload.get("report_path", "")
        elif event_type == "artifact_written":
            level = "system"
            action_text = "Artifact saved"
            data_text = payload.get("path", "")
        else:
            data_text = json.dumps(payload, ensure_ascii=False)[:220]

        broadcast_hud_event(
            "agent_log",
            {
                "type": level,
                "agent": "BRAIN",
                "action": action_text,
                "data": data_text,
            },
        )
        if event_type in {"plan_started", "context_loaded", "artifact_written", "step_failed", "plan_completed"}:
            broadcast_hud_event(
                "runtime_event",
                {
                    "type": f"brain_{event_type}",
                    "payload": {
                        "module": module,
                        "action": action,
                        "goal": goal,
                        **payload,
                    },
                },
            )

    return _emit


def _handle_non_agent_module(module: str, action: str, text: str, context_snapshot: dict[str, Any]) -> dict[str, Any]:
    result = f"Module '{module}' activated."
    broadcast_hud_event(
        "agent_log",
        {
            "type": "system",
            "agent": "COMMAND",
            "action": f"No backend execution for {module}",
            "data": action or text or module,
        },
    )
    broadcast_hud_event(
        "runtime_event",
        {
            "type": "command_complete",
            "payload": {
                "module": module,
                "action": action,
                "result_preview": result,
            },
        },
    )
    return {
        "status": "ok",
        "module": module,
        "action": action,
        "result": result,
        "context_snapshot": context_snapshot,
    }


def _handle_empty_command(module: str, action: str, context_snapshot: dict[str, Any]) -> dict[str, Any]:
    result = "No command text provided."
    broadcast_hud_event(
        "agent_log",
        {
            "type": "warning",
            "agent": "COMMAND",
            "action": "Rejected empty command",
            "data": module,
        },
    )
    return {
        "status": "ignored",
        "module": module,
        "action": action,
        "result": result,
        "context_snapshot": context_snapshot,
    }


def _handle_blocked_command(module: str, action: str, text: str, context_snapshot: dict[str, Any]) -> dict[str, Any]:
    result = {
        "status": "blocked",
        "goal": text,
        "reason": "Security policy blocked the requested goal.",
    }
    broadcast_hud_event(
        "agent_log",
        {
            "type": "critical",
            "agent": "COMMAND",
            "action": "Blocked command",
            "data": text,
        },
    )
    return {
        "status": "blocked",
        "module": module,
        "action": action,
        "result": result,
        "context_snapshot": context_snapshot,
    }


async def _handle_agentic_command(module: str, action: str, sanitized_text: str, context_snapshot: dict[str, Any]) -> dict[str, Any]:
    import core.memory as memory_module
    context = await memory_module.get_context(sanitized_text)
    full_prompt = f"[MEMORY CONTEXT]\n{context}\n\n[CURRENT REQUEST]\n{sanitized_text}" if context else sanitized_text

    brain = get_agentic_brain()
    result = await asyncio.to_thread(
        brain.run,
        full_prompt,
        context_snapshot,
        _command_event_sink(module, action, full_prompt),
    )

    final_response_str = json.dumps(result.get("final_answer", {}), ensure_ascii=False)
    try:
        write_turn("user", sanitized_text, metadata={"source": "agentic_brain", "module": module, "action": action})
        write_turn("assistant", final_response_str, metadata={"source": "agentic_brain", "module": module, "action": action})
        await memory_module.save_memory(sanitized_text, final_response_str)
    except Exception:
        pass

    return {
        "status": result.get("status", "ok"),
        "mode": "agentic",
        "module": module,
        "action": action,
        "goal": sanitized_text,
        "plan": result,
        "context_snapshot": context_snapshot,
    }


async def _handle_standard_command(module: str, action: str, sanitized_text: str, context_snapshot: dict[str, Any]) -> dict[str, Any]:
    import core.memory as memory_module
    context = await memory_module.get_context(sanitized_text)
    full_prompt = f"[MEMORY CONTEXT]\n{context}\n\n[CURRENT REQUEST]\n{sanitized_text}" if context else sanitized_text

    result = await asyncio.to_thread(run_agent_turn, full_prompt, False, True)
    await memory_module.save_memory(sanitized_text, str(result))

    preview = result[:240] if isinstance(result, str) else str(result)[:240]

    broadcast_hud_event(
        "agent_log",
        {
            "type": "ai",
            "agent": "S.P.A.R.K.",
            "action": "Command complete",
            "data": preview,
        },
    )
    broadcast_hud_event(
        "runtime_event",
        {
            "type": "command_complete",
            "payload": {
                "module": module,
                "action": action,
                "result_preview": preview,
            },
        },
    )

    return {
        "status": "ok",
        "module": module,
        "action": action,
        "result": result,
        "context_snapshot": context_snapshot,
    }


async def _run_commander(payload: dict[str, Any]) -> dict[str, Any]:
    module = str(payload.get("module") or "agent")
    action = str(payload.get("action") or "")
    text = _extract_text(payload)
    context_snapshot = _summarize_snapshot(payload.get("context_snapshot"))

    validation = validate_intent_text(text) if text else None
    sanitized_text = sanitize_for_llm(validation.cleaned_text or text) if validation and validation.cleaned_text else text

    broadcast_hud_event(
        "runtime_event",
        {
            "type": "command_received",
            "payload": {
                "module": module,
                "action": action,
                "has_text": bool(text),
                "context_snapshot": context_snapshot,
            },
        },
    )

    broadcast_hud_event(
        "agent_log",
        {
            "type": "info",
            "agent": "COMMAND",
            "action": f"Received {module}",
            "data": text or action or "module activation",
        },
    )

    if module not in {"agent", "llm"}:
        return _handle_non_agent_module(module, action, text, context_snapshot)

    if not sanitized_text:
        return _handle_empty_command(module, action, context_snapshot)

    if validation and not validation.allowed:
        return _handle_blocked_command(module, action, text, context_snapshot)

    if is_agentic_goal(sanitized_text):
        return await _handle_agentic_command(module, action, sanitized_text, context_snapshot)

    return await _handle_standard_command(module, action, sanitized_text, context_snapshot)


@router.post("/api/commander/run")
async def commander_run(payload: dict[str, Any]):
    return await _run_commander(payload)


@router.post("/api/commander/routine/{routine_name}")
async def commander_routine(routine_name: str, payload: dict[str, Any] | None = None):
    routine = routine_name.strip().lower()
    body = dict(payload or {})
    body["module"] = "mode"
    body["action"] = routine
    body.setdefault("text", routine)

    result = {
        "dev": "Developer HUD mode armed.",
        "monitor": "Monitor HUD mode armed.",
        "focus": "Focus HUD mode armed.",
    }.get(routine, f"Routine '{routine}' acknowledged.")

    broadcast_hud_event(
        "agent_log",
        {
            "type": "system",
            "agent": "COMMAND",
            "action": f"Routine {routine}",
            "data": result,
        },
    )
    broadcast_hud_event(
        "runtime_event",
        {
            "type": "routine_activated",
            "payload": {
                "routine": routine,
                "result_preview": result,
            },
        },
    )

    return {
        "status": "ok",
        "name": routine,
        "intent": "ROUTINE",
        "result": result,
        "context_snapshot": _summarize_snapshot(body.get("context_snapshot")),
    }


@router.websocket("/ws/command")
async def commander_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            result = await _run_commander(payload if isinstance(payload, dict) else {})
            await websocket.send_json({"type": "command_result", **result})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
