"""SPARK interactive CLI with full tool execution, memory, and security."""

from __future__ import annotations

import subprocess
import json
import logging
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Any

# Ensure the `spark` package directory is importable
package_dir = Path(__file__).resolve().parent / "spark"
pkg = ModuleType("spark")
pkg.__path__ = [str(package_dir)]
sys.modules.setdefault("spark", pkg)

from spark.core import SparkCore, load_config


log = logging.getLogger("spark.cli")
logging.basicConfig(
    level=logging.WARNING,
    format="[%(name)s] %(message)s"
)


class SparkCLI:
    """Interactive CLI with tool execution, memory recall, and security.
    
    3-Engine Architecture Explained:
    
    Engine 1 — Autonomous Loop (runs in background, not in CLI):
        while True:
            task = memory.get_next_task()
            if task:
                result = llm.execute(task)
                memory.log_outcome(task, result)
                new_tasks = llm.reflect(result)
                memory.queue_tasks(new_tasks)
    
    Engine 2 — Self-Improvement (every 24h):
        "Here are my last 50 interactions. These 8 failed or got negative feedback.
         Rewrite my system prompt to fix these patterns."
        → Saves new system prompt to memory
        → Tomorrow SPARK is smarter without you touching anything
    
    Engine 3 — Self-Extension (when hitting a wall):
        User: "SPARK, check my CPU temperature"
        SPARK: "I don't have that tool. Writing it now."
        → Generates tools/cpu_temp.py
        → Hot-reloads it
        → Executes immediately
        → Logs as permanent capability
    
    This CLI is the user-facing interface to all 3 engines.
    """

    def __init__(self):
        self.config = load_config()
        self.core = SparkCore(self.config)
        self.session_count = 0
        self._start_ollama_keepalive()
        try:
            import threading
            from core.local_brain_chain import warmup_chain
            threading.Thread(target=warmup_chain, daemon=True, name="spark-warmup").start()
        except Exception:
            pass

    def _start_ollama_keepalive(self) -> None:
        def _ensure_ollama() -> None:
            try:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                pass

        threading.Thread(target=_ensure_ollama, daemon=True).start()

    def get_memory_context(self, query: str) -> str:
        """Get context from previous interactions (lightweight, non-blocking)."""
        try:
            interactions = self.core.memory.recent_interactions(3)
            if not interactions or len(interactions) < 2:
                return ""
            
            context_items = []
            for interaction in interactions[-2:]:
                task = interaction.get("task", "")
                if task and len(task) > 5:
                    context_items.append(f"• {task[:70]}")
            
            if context_items:
                return "Recent context:\n" + "\n".join(context_items) + "\n"
            return ""
        except Exception as e:
            log.debug(f"Memory context: {e}")
            return ""

    def execute_query(self, user_query: str) -> str:
        """Execute query through SPARK with memory context.
        
        Flow:
        1. Get memory context (non-blocking)
        2. Execute through unified core brain entry (core/spark_brain.handle)
        3. Log outcome (feeds Engine 2: self-improvement)
        """
        try:
            # Build task; SparkLLM already enriches context internally
            task = {
                "prompt": user_query,
                "source": "cli",
                "include_tools": True,
            }
            
            # Execute through unified brain entry path
            result = self.core.llm.execute(task)
            
            # Extract reply
            if not isinstance(result, dict):
                result = {"reply": str(result)}
            
            reply = result.get("reply", "").strip()
            if not reply:
                reply = "I processed your query but have no immediate response."
            
            # Log outcome (Engine 2 learns from this)
            try:
                self.core.memory.log_outcome(
                    {"prompt": user_query, "source": "cli"},
                    result
                )
            except Exception as e:
                log.debug(f"Memory logging: {e}")
            
            return reply
            
        except Exception as exc:
            log.debug(f"Query execution: {exc}")
            return f"Error: {str(exc)[:100]}"

    def run(self) -> int:
        """Main interactive loop."""
        print("=" * 70)
        print("SPARK Interactive CLI — Your Personal AI Assistant")
        print("=" * 70)
        print()
        print("I have access to:")
        print("  • Tools: Web search, system info, app control, file operations")
        print("  • Memory: Previous conversations and learned patterns")
        print("  • Security: Permission checks before sensitive actions")
        print()
        print("Type 'exit' or press Ctrl-C to quit")
        print("=" * 70)
        print()
        
        try:
            while True:
                try:
                    user_input = input("You: ").strip()
                except EOFError:
                    break
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("exit", "quit"):
                    print("Goodbye!")
                    break
                
                # Show processing indicator
                print("[processing...]", flush=True)
                
                # Execute with full integration
                reply = self.execute_query(user_input)
                print(f"SPARK: {reply}", flush=True)
                print()
                
                self.session_count += 1
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            return 0
        
        return 0


def main() -> int:
    """Entry point."""
    try:
        cli = SparkCLI()
        return cli.run()
    except Exception as e:
        print(f"SPARK CLI Fatal Error: {e}")
        log.exception("Fatal error in CLI")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
