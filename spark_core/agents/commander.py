"""
SPARK Commander — Multi-Agent Orchestration Hub

Routes incoming tasks to the appropriate sub-agent based on task classification.
Maintains a registry of all agents and their capabilities.

Architecture:
    Commander AI
     ├── Research Agent     (Vane Local Deep Research Engine)
     ├── Code Agent         (code gen, debug, review)
     ├── Intelligence Agent (globe events, geopolitical)
     ├── Risk Agent         (PentAGI Red Team Orchestrator)
     └── Optimization Agent (performance, strategy)
"""
import asyncio
import uuid
import time
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseAgent, AgentTask, AgentResult
from llm.model_router import model_router, TaskType, LatencyClass
from system.event_bus import event_bus


class Commander:
    """
    Central command brain. Classifies tasks and routes them to specialized agents.
    Also handles direct 'ask SPARK' requests by choosing the best agent + model combo.
    """

    def __init__(self):
        print("🎖️  [Commander] Initializing multi-agent system...")

        self._agents: Dict[str, BaseAgent] = {}
        self._pending_results: Dict[str, asyncio.Future] = {}
        # A pure intent router does not blindly instantiate heavy background agents!
        # Swarm effectively neutered by SPARK protocols. 
        print(f"🎖️  [Commander] Swarm background execution disabled. Operating as direct Intent Router.")
        event_bus.subscribe("agent_result")(self._handle_result)
        print(f"🎖️  [Commander] {len(self._agents)} agents registered: {list(self._agents.keys())}")

    def _register(self, agent: BaseAgent):
        # Don't start here — deferred to startup() called from FastAPI lifespan
        self._agents[agent.name] = agent

    async def startup(self):
        """Start all agent loops — call this from inside the running event loop."""
        for agent in self._agents.values():
            await agent.ensure_started()
        print(f"🎖️  [Commander] All {len(self._agents)} agents started")

    # ── Task routing ──────────────────────────────────────────────────────────

    def _classify(self, text: str) -> str:
        """Heuristic task classifier → agent name."""
        t = text.lower()
        # Code-related
        if any(k in t for k in ["code", "debug", "refactor", "function", "class", "script", "python", "typescript", "fix this", "write a "]):
            return "code_agent"
        # Risk / safety
        if any(k in t for k in ["risk", "threat", "danger", "escalat", "attack", "probability", "how likely", "simulate"]):
            return "risk_agent"
        # Intelligence / globe
        if any(k in t for k in ["conflict", "war", "geopolit", "region", "country", "missile", "sanction", "intel", "brief", "globe"]):
            return "intelligence_agent"
        # Optimization
        if any(k in t for k in ["optim", "performance", "slow", "improv", "bottleneck", "memory usage", "cpu", "strategy"]):
            return "optimization_agent"
        # Default: research
        return "research_agent"

    async def dispatch(
        self,
        task_type: str,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        priority: int = 5,
        wait: bool = False,
        timeout: float = 60.0,
    ) -> Optional[AgentResult]:
        """
        Dispatch a task to the appropriate agent.
        If wait=True, blocks until the agent returns a result (up to timeout seconds).
        """
        # Find capable agent
        agent = self._agents.get(task_type)
        if not agent:
            # Fall back to classification
            agent_name = self._classify(task_type + " " + payload.get("query", payload.get("request", "")))
            agent = self._agents.get(agent_name)
        if not agent:
            agent = self._agents["research_agent"]  # safe fallback

        task = AgentTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            payload=payload,
            priority=priority,
            session_id=session_id,
        )

        if wait:
            future: asyncio.Future = asyncio.get_event_loop().create_future()
            self._pending_results[task.task_id] = future

        await agent.submit(task)

        if wait:
            try:
                return await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                self._pending_results.pop(task.task_id, None)
                return AgentResult(
                    task_id=task.task_id, agent_name=agent.name,
                    success=False, output=None, error="Agent timeout",
                )
        return None

    async def ask(
        self,
        user_text: str,
        session_id: Optional[str] = None,
        wait: bool = False,
    ) -> Optional[AgentResult]:
        """
        Natural-language task routing. Classifies the request and routes to best agent.
        """
        agent_name = self._classify(user_text)
        payload_key = "query" if agent_name in ("research_agent", "intelligence_agent") else "request"
        return await self.dispatch(
            task_type=agent_name,
            payload={payload_key: user_text},
            session_id=session_id,
            wait=wait,
        )

    async def _handle_result(self, payload: Dict[str, Any]):
        task_id = payload.get("task_id")
        future = self._pending_results.pop(task_id, None)
        if future and not future.done():
            result_data = payload.get("result", {})
            result = AgentResult(**result_data)
            future.set_result(result)

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        try:
            pending = len(list(self._pending_results.keys()))
        except Exception:
            pending = len(self._pending_results)
            
        return {
            "agents": {name: agent.get_status() for name, agent in self._agents.items()},
            "pending_tasks": pending,
        }

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)


# ── Singleton ─────────────────────────────────────────────────────────────────
commander = Commander()
