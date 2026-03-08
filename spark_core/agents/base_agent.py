"""
SPARK Multi-Agent Framework — Base Agent
All SPARK agents inherit from BaseAgent and communicate via the event bus.
"""
import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from system.event_bus import event_bus
from ws.manager import ws_manager


class AgentState(str, Enum):
    IDLE      = "IDLE"
    THINKING  = "THINKING"
    EXECUTING = "EXECUTING"
    WAITING   = "WAITING"
    ERROR     = "ERROR"


@dataclass
class AgentTask:
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 5          # 1 (highest) … 10 (lowest)
    session_id: Optional[str] = None
    created_at: float = field(default_factory=time.monotonic)


@dataclass
class AgentResult:
    task_id: str
    agent_name: str
    success: bool
    output: Any
    reasoning: str = ""
    confidence: float = 1.0
    elapsed_ms: float = 0.0
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base for all SPARK agents.
    
    Subclasses implement `execute(task)` which returns an AgentResult.
    The agent registers itself with the event bus and handles tasks asynchronously.
    """

    name: str = "base_agent"
    description: str = "Abstract base agent"
    capabilities: list = []   # list of task_type strings this agent handles

    def __init__(self):
        self.state = AgentState.IDLE
        self._task_queue: asyncio.Queue = asyncio.Queue(maxsize=20)
        self._current_task: Optional[AgentTask] = None
        self._stats = {"completed": 0, "failed": 0, "total_ms": 0.0}
        self._started = False
        print(f"🤖 [Agent:{self.name}] Initialized")

    def start(self):
        """Start the agent — safe to call at import time (no event loop needed)."""
        # No-op here; actual task creation is deferred to ensure_started()
        pass

    async def ensure_started(self):
        """Create the asyncio background task. Must be called inside a running loop."""
        if not self._started:
            asyncio.create_task(self._resilient_loop())
            self._started = True
            print(f"🚀 [Agent:{self.name}] Started with crash recovery enabled")

    async def submit(self, task: AgentTask) -> Optional[str]:
        """Queue a task. Returns task_id or None if queue full."""
        try:
            await self._task_queue.put(task)
            return task.task_id
        except asyncio.QueueFull:
            return None

    async def _resilient_loop(self):
        """
        Wraps _run_loop with crash recovery.
        If the loop crashes for any reason:
          1. Publish AGENT_ERROR to WebSocket
          2. Sleep 5 seconds
          3. Restart the loop automatically
        This ensures agents are "immortal" — they never die from runtime errors.
        """
        while True:
            try:
                await self._run_loop()
            except asyncio.CancelledError:
                # Task was cancelled — don't restart, just exit
                raise
            except Exception as exc:
                # Unhandled exception — agent crashed, recover it
                self.state = AgentState.ERROR
                error_msg = f"{type(exc).__name__}: {str(exc)}"
                stack_trace = traceback.format_exc()
                
                print(f"💥 [Agent:{self.name}] CRASHED: {error_msg}")
                print(f"💥 [Agent:{self.name}] Stack trace:\n{stack_trace}")
                
                # Publish AGENT_ERROR event to /ws/system for frontend warning badge
                try:
                    await ws_manager.broadcast_json({
                        "type": "AGENT_ERROR",
                        "agent": self.name,
                        "error": error_msg,
                        "timestamp": time.time(),
                    }, "system")
                except Exception as broadcast_err:
                    print(f"⚠️ [Agent:{self.name}] Failed to broadcast error: {broadcast_err}")
                
                # Sleep 5 seconds before restart
                print(f"⏳ [Agent:{self.name}] Restarting in 5 seconds...")
                await asyncio.sleep(5)
                
                # Reset state and restart the loop
                self.state = AgentState.IDLE
                print(f"♻️ [Agent:{self.name}] Restarting agent loop...")

    async def _run_loop(self):
        """Continuously processes tasks from the queue."""
        while True:
            task = await self._task_queue.get()
            self._current_task = task
            self.state = AgentState.THINKING

            t0 = time.monotonic()
            try:
                result = await self.execute(task)
                result.elapsed_ms = (time.monotonic() - t0) * 1000
                self._stats["completed"] += 1
                self._stats["total_ms"] += result.elapsed_ms
                self.state = AgentState.IDLE

                # Publish result to event bus
                event_bus.publish("agent_result", {
                    "agent": self.name,
                    "task_id": task.task_id,
                    "result": result.__dict__,
                    "session_id": task.session_id,
                })

            except asyncio.CancelledError:
                self.state = AgentState.IDLE
                raise
            except Exception as exc:
                self._stats["failed"] += 1
                self.state = AgentState.ERROR
                error_result = AgentResult(
                    task_id=task.task_id,
                    agent_name=self.name,
                    success=False,
                    output=None,
                    error=str(exc),
                    elapsed_ms=(time.monotonic() - t0) * 1000,
                )
                event_bus.publish("agent_result", {
                    "agent": self.name,
                    "task_id": task.task_id,
                    "result": error_result.__dict__,
                    "session_id": task.session_id,
                })
                self.state = AgentState.IDLE
                print(f"❌ [Agent:{self.name}] Task {task.task_id} failed: {exc}")

            finally:
                self._current_task = None
                self._task_queue.task_done()

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Subclasses implement core task logic here."""
        ...

    def get_status(self) -> Dict[str, Any]:
        avg = self._stats["total_ms"] / max(self._stats["completed"], 1)
        return {
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "queue_depth": self._task_queue.qsize(),
            "capabilities": self.capabilities,
            "stats": {
                "completed": self._stats["completed"],
                "failed": self._stats["failed"],
                "avg_latency_ms": round(avg, 1),
            },
        }
