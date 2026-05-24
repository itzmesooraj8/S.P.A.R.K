from __future__ import annotations

import base64
import os
import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from config import LLM_HOST, LLM_MODEL
from core.spark_brain import client, _groq_cooldown_until, token_counter, GroqFallbackError
from core.local_brain_chain import local_chain_complete
from tools.web_search import web_search_answer

logger = logging.getLogger("spark.swarm")

SANDBOX_NAME = "sandbox/temp_build"
SANDBOX_DIR = Path(SANDBOX_NAME).resolve()
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

def verify_safe_path(path: str | Path) -> Path:
    """Resolve path relative to sandbox directory and verify it is strictly within the sandbox folder."""
    p = Path(path)
    if p.is_absolute():
        target = p.resolve()
    else:
        p_parts = p.parts
        if len(p_parts) >= 2 and p_parts[0] == "sandbox" and p_parts[1] == "temp_build":
            target = p.resolve()
        else:
            target = (SANDBOX_DIR / p).resolve()
            
    if target != SANDBOX_DIR and SANDBOX_DIR not in target.parents:
        raise PermissionError(f"Security Violation: Path '{path}' (resolved to '{target}') is outside the sandbox '{SANDBOX_DIR}'")
    return target

def _call_llm(prompt: str, system_prompt: str = "You are an autonomous assistant.") -> str:
    """Call Groq LLM if available and not rate-limited; fall back to local model chain."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # Check budget and cooldown for Groq
    groq_allowed = True
    try:
        if token_counter.get_remaining_today() < 5000:
            groq_allowed = False
    except Exception:
        pass

    if time.time() < _groq_cooldown_until or client is None:
        groq_allowed = False

    if groq_allowed:
        from core.model_router import get_groq_model
        model_name = get_groq_model()
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
                max_tokens=1500
            )
            content = response.choices[0].message.content
            if content:
                return str(content).strip()
        except Exception as exc:
            logger.warning(f"Groq failed in swarm LLM call, falling back to local: {exc}")

    # Local fallback
    try:
        result = local_chain_complete(messages, auto_start=True)
        if result.success:
            return result.text
    except Exception as exc:
        logger.error(f"Local model chain failed in swarm: {exc}")

    return "Failed to get LLM response."

class CodeAgent:
    """Agent responsible for writing and running code files safely within the sandbox."""
    
    def write_code(self, filename: str, code: str) -> str:
        safe_path = verify_safe_path(filename)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(code, encoding="utf-8")
        return f"Successfully wrote code to {filename} ({len(code)} bytes)"

    def read_code(self, filename: str) -> str:
        safe_path = verify_safe_path(filename)
        if not safe_path.exists():
            return f"Error: File {filename} does not exist."
        return safe_path.read_text(encoding="utf-8")

    def run_python_script(self, filename: str) -> str:
        safe_path = verify_safe_path(filename)
        if not safe_path.exists():
            return f"Error: File {filename} does not exist."
        
        try:
            result = subprocess.run(
                [sys.executable, str(safe_path)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(SANDBOX_DIR)
            )
            output = f"Exit code: {result.returncode}\n"
            if result.stdout:
                output += f"Stdout:\n{result.stdout}\n"
            if result.stderr:
                output += f"Stderr:\n{result.stderr}\n"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Script execution timed out (limit: 10s)."
        except Exception as exc:
            return f"Error executing script: {exc}"

class FileAgent:
    """Agent responsible for local file actions restricted to the sandbox folder."""

    def list_files(self, subfolder: str = ".") -> str:
        safe_path = verify_safe_path(Path(SANDBOX_DIR) / subfolder)
        items = []
        for p in safe_path.rglob("*"):
            rel = p.relative_to(SANDBOX_DIR)
            if p.is_dir():
                items.append(f"[DIR] {rel}")
            else:
                items.append(f"[FILE] {rel} ({p.stat().st_size} bytes)")
        if not items:
            return "Sandbox workspace is empty."
        return "\n".join(items)

    def delete_file(self, filename: str) -> str:
        safe_path = verify_safe_path(filename)
        if not safe_path.exists():
            return f"Error: File {filename} does not exist."
        if safe_path.is_dir():
            import shutil
            shutil.rmtree(safe_path)
            return f"Successfully deleted directory {filename}"
        else:
            safe_path.unlink()
            return f"Successfully deleted file {filename}"

class ResearchAgent:
    """Agent responsible for fetching research items and storing summaries."""

    def search_web(self, query: str) -> str:
        try:
            return web_search_answer(query) or "No web search results found."
        except Exception as e:
            return f"Search failed: {e}"

    def write_research_notes(self, topic: str, notes: str) -> str:
        filename = f"research_{re.sub(r'[^a-zA-Z0-9]+', '_', topic.lower())}.txt"
        safe_path = verify_safe_path(filename)
        safe_path.write_text(notes, encoding="utf-8")
        return f"Saved research notes to {filename}"

class SwarmCoordinator:
    """Coordinator that plans, delegates tasks to agents, and returns final unified reports."""
    
    def __init__(self):
        self.code_agent = CodeAgent()
        self.file_agent = FileAgent()
        self.research_agent = ResearchAgent()

    def execute_swarm_task(self, goal: str) -> dict[str, Any]:
        logger.info(f"Swarm coordinating task: {goal}")
        
        system_prompt = (
            "You are the SPARK Swarm Coordinator. Your goal is to break the request down into a JSON list of steps. "
            "Available Agents and Actions:\n"
            "- CodeAgent: write_code(filename, code), read_code(filename), run_python_script(filename)\n"
            "- FileAgent: list_files(subfolder), delete_file(filename)\n"
            "- ResearchAgent: search_web(query), write_research_notes(topic, notes)\n\n"
            "Return ONLY a JSON array of steps in this format:\n"
            '[{"agent": "ResearchAgent", "action": "search_web", "args": {"query": "..."}}, '
            '{"agent": "CodeAgent", "action": "write_code", "args": {"filename": "app.py", "code": "..."}}, '
            '{"agent": "CodeAgent", "action": "run_python_script", "args": {"filename": "app.py"}}]\n'
            "Keep the workflow simple and limit it to at most 4 steps. Provide ONLY raw valid JSON, no markdown formatting."
        )

        prompt = f"Deconstruct this goal: '{goal}'"
        plan_raw = _call_llm(prompt, system_prompt)
        
        # Remove any Markdown code block backticks
        plan_raw_clean = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", plan_raw, flags=re.DOTALL).strip()
        
        try:
            steps = json.loads(plan_raw_clean)
        except Exception as exc:
            logger.warning(f"Failed to parse swarm plan JSON: {exc}. Prompting plan fallback.")
            # Simple fallback plan: search then chat
            steps = [
                {"agent": "ResearchAgent", "action": "search_web", "args": {"query": goal}},
                {"agent": "ResearchAgent", "action": "write_research_notes", "args": {"topic": "summary", "notes": "Goal: " + goal}}
            ]

        results = []
        for idx, step in enumerate(steps):
            agent_name = step.get("agent")
            action = step.get("action")
            args = step.get("args", {})
            
            logger.info(f"Swarm Step {idx+1}: {agent_name}.{action}({args})")
            
            try:
                if agent_name == "CodeAgent":
                    agent = self.code_agent
                elif agent_name == "FileAgent":
                    agent = self.file_agent
                elif agent_name == "ResearchAgent":
                    agent = self.research_agent
                else:
                    raise ValueError(f"Unknown agent: {agent_name}")

                method = getattr(agent, action, None)
                if not method:
                    raise ValueError(f"Unknown action {action} for agent {agent_name}")

                out = method(**args)
                results.append({"step": idx+1, "status": "success", "agent": agent_name, "action": action, "output": out})
            except Exception as e:
                results.append({"step": idx+1, "status": "failed", "agent": agent_name, "action": action, "error": str(e)})

        # Synthesize final report
        synthesis_prompt = (
            f"You are the SPARK Swarm Coordinator. Synthesize a brief final summary report of the task.\n\n"
            f"Original Goal: {goal}\n\n"
            f"Execution Results:\n{json.dumps(results, indent=2)}\n\n"
            "Format the summary clearly, highlighting successes and listing files created/modified."
        )
        report = _call_llm(synthesis_prompt, "You are a compiler of swarm results.")

        # Write report to workspace
        report_path = SANDBOX_DIR / "swarm_report.md"
        report_path.write_text(report, encoding="utf-8")

        return {
            "status": "completed",
            "goal": goal,
            "steps": steps,
            "results": results,
            "report": report,
            "report_path": str(report_path)
        }
