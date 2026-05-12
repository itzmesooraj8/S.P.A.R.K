from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.json"


def load_config() -> dict[str, Any]:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


class SparkCore:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or load_config()
        self._memory: Any = None
        self._tools: Any = None
        self._llm: Any = None
        self._voice: Any = None
        self._security_daemon: Any = None
        self.loop_interval = int(self.config.get("loop_interval_seconds", 5))
        self.reflection_interval = int(self.config.get("reflection_interval_seconds", 86400))
        self._last_reflection = time.time()
        
        # Start security daemon
        self._start_security_daemon()

    @property
    def memory(self) -> SparkMemory:
        if self._memory is None:
            from spark.memory import SparkMemory as SM
            self._memory = SM(self.config)
        return self._memory

    @property
    def tools(self) -> ToolRegistry:
        if self._tools is None:
            from spark.tools import ToolRegistry as TR
            self._tools = TR(self.config)
        return self._tools

    @property
    def llm(self) -> SparkLLM:
        if self._llm is None:
            from spark.llm import SparkLLM as SL
            self._llm = SL(self.config, self.memory, self.tools)
        return self._llm

    @property
    def voice(self) -> SparkVoice:
        if self._voice is None:
            from spark.voice import SparkVoice as SV
            self._voice = SV(self.config)
        return self._voice

    @property
    def security_daemon(self) -> Any:
        if self._security_daemon is None:
            from core.security_daemon import SecurityDaemon as SD
            self._security_daemon = SD(self.config)
        return self._security_daemon

    def _start_security_daemon(self) -> None:
        """Start security daemon in background."""
        try:
            self.security_daemon.start()
        except Exception as e:
            print(f"[SPARK] Failed to start security daemon: {e}", file=sys.stderr)

    def run_once(self) -> dict[str, Any] | None:
        task = self.memory.get_next_task()
        if task:
            result = self.llm.execute(task)
            self.memory.log_outcome(task, result)
            next_tasks = self.llm.reflect(result, self.memory.recent_interactions(20))
            if next_tasks:
                self.memory.queue_tasks(next_tasks)
            return result

        now = time.time()
        if now - self._last_reflection >= self.reflection_interval:
            recent = self.memory.recent_interactions(50)
            if recent:
                new_prompt = self.llm.rewrite_system_prompt(recent)
                if new_prompt:
                    queue_prompt_review(new_prompt, {}, {"voice_loop": 1}, summary="Suggested system prompt rewrite from the minimal runtime.")
            self._last_reflection = now
        return None

    def run_forever(self) -> None:
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"[SPARK] loop error: {exc}", file=sys.stderr)
            time.sleep(self.loop_interval)

    def run_voice_once(self) -> dict[str, Any] | None:
        transcript = self.voice.listen().strip()
        if not transcript:
            return None

        result = self.llm.execute({"prompt": transcript, "source": "voice"})
        reply = str(result.get("reply") or "").strip() or "I heard you, but I do not have a response yet."
        self.memory.log_outcome({"prompt": transcript, "source": "voice"}, result)
        self._run_async(self.voice.speak(reply))
        return {"transcript": transcript, **result}

    def run_voice_loop(self) -> None:
        while True:
            try:
                self.run_voice_once()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"[SPARK] voice loop error: {exc}", file=sys.stderr)
            time.sleep(0.1)

    def _run_async(self, coroutine):
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()


def main(once: bool = False) -> int:
    core = SparkCore()
    if once:
        result = core.run_once()
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("SPARK is idle.")
        return 0
    core.run_forever()
    return 0
