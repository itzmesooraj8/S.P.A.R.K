"""
SPARK — AI Operating System v4.0

The closest practical approximation of JARVIS.

Phase 1: Foundation ✅
Phase 2: Awareness ✅
Phase 3: Autonomy ✅
Phase 4: Communication ✅
Phase 5: Automation ✅
Phase 6: Dashboard ✅
Continuous Agent Loop ✅

Priority 1: Voice Loop ✅
Priority 2: User Model ✅
Priority 3: Learning Engine ✅
Priority 4: Long-Term Goals ✅
Priority 5: Reliability ✅

v4: User Preference Learning ✅
v4: Advanced Learning Engine ✅
v4: Production Monitoring ✅
v4: Security Hardening ✅
v4: Cross-Device Sync ✅
v4: Multi-Modal Awareness ✅

Observe → Understand → Predict → Plan → Act → Reflect → Learn → Observe
Forever. 24/7.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from spark.core.container import Container
from spark.core.events import Event
from spark.cognition.goal_engine import GoalEngine
from spark.cognition.reasoning import ReasoningEngine
from spark.cognition.reflection import ReflectionEngine
from spark.persona.identity import PersonaIdentity
from spark.persona.style import CommunicationStyle
from spark.memory.semantic import SemanticMemory
from spark.memory.episodic import EpisodicMemory
from spark.memory.procedural import ProceduralMemory
from spark.memory.working import WorkingMemory
from spark.awareness.screen import ScreenAwareness
from spark.awareness.application import ApplicationAwareness
from spark.awareness.context import ContextAwareness
from spark.awareness.user import UserAwareness
from spark.awareness.environment import EnvironmentAwareness
from spark.awareness.bus import AwarenessBus
from spark.awareness.world_model import WorldModel
from spark.agents.planner import PlannerAgent
from spark.agents.executor import ExecutorAgent
from spark.agents.memory_agent import MemoryAgent
from spark.agents.reflection_agent import ReflectionAgent
from spark.agents.observer import ObserverAgent
from spark.orchestration.tool_executor import ToolExecutor
from spark.orchestration.scheduler import TaskScheduler
from spark.authority.validator import ActionValidator
from spark.authority.policy import AuthorityPolicy
from spark.communication.voice_channel import VoiceChannel
from spark.communication.chat_channel import ChatChannel
from spark.voice.engine import VoiceEngine
from spark.automation.browser import BrowserAutomation
from spark.automation.desktop import DesktopAutomation
from spark.automation.file_control import FileAutomation
from spark.ui.dashboard import Dashboard
from spark.actions.registry import ActionRegistry
from spark.skills.skill import SkillRegistry
from spark.capabilities.registry import CapabilityRegistry
from spark.decisions.log import DecisionLog
from spark.vision.capture import ScreenCapture
from spark.vision.ocr import VisionOCR
from spark.vision.understand import VisionUnderstander
from spark.planning.llm_planner import LLMPlanner
from spark.planning.replanner import AutoReplanner
from spark.planning.deliberation import MultiAgentDeliberation
from spark.automation.playwright_browser import PlaywrightBrowser
from spark.automation.desktop_intel import DesktopIntelligence
from spark.automation.iot import IoTController
from spark.automation.autonomous import AutonomousWorkflow
from spark.integrations.discord_channel import DiscordIntegration
from spark.integrations.email_channel import EmailIntegration
from spark.integrations.telegram_channel import TelegramIntegration
from spark.autonomy.loop import ContinuousAgentLoop
from spark.llm_router import classify_intent
from spark.voice.loop import VoiceLoop
from spark.user.model import UserModel
from spark.user.preferences import PreferenceLearner
from spark.learning.engine import LearningEngine
from spark.learning.advanced import AdvancedLearningEngine
from spark.goals.lifecycle import LifeGoalManager
from spark.reliability.risk import RiskEngine
from spark.reliability.retry import RetryManager
from spark.reliability.recovery import FailureRecovery
from spark.observability.metrics import MetricsCollector
from spark.observability.tracer import Tracer
from spark.observability.audit import AuditLogger
from spark.security.secrets import SecretsManager
from spark.security.scopes import PermissionScope, Scope
from spark.security.sandbox import Sandbox
from spark.sync.coordinator import DeviceCoordinator
from spark.multimodal.camera import CameraStream
from spark.multimodal.microphone import MicrophoneStream
from spark.multimodal.sensor import SensorHub

logger = logging.getLogger("spark")


class SparkOS:
    """SPARK AI Operating System v4.0 — Closest practical approximation of JARVIS."""

    def __init__(self) -> None:
        self.container = Container.get_instance()
        self._initialized = False
        self._running = False

    def initialize(self) -> None:
        if self._initialized:
            return

        logger.info("Initializing SPARK AI Operating System v4.0...")
        self.container.initialize()

        self.persona = PersonaIdentity()
        self.style = CommunicationStyle()

        self.goal_engine = GoalEngine()
        self.reasoning = ReasoningEngine()
        self.reflection = ReflectionEngine()

        self.semantic_memory = SemanticMemory()
        self.episodic_memory = EpisodicMemory()
        self.procedural_memory = ProceduralMemory()
        self.working_memory = WorkingMemory()

        self.screen = ScreenAwareness()
        self.app_awareness = ApplicationAwareness()
        self.context = ContextAwareness()
        self.user = UserAwareness()
        self.env_awareness = EnvironmentAwareness()
        self.awareness_bus = AwarenessBus(self.container.events)
        self.world_model = WorldModel()

        self.planner_agent = PlannerAgent(self.container.events)
        self.executor_agent = ExecutorAgent(self.container.events)
        self.memory_agent = MemoryAgent(self.container.events)
        self.reflection_agent = ReflectionAgent(self.container.events)
        self.observer_agent = ObserverAgent(self.container.events, self.awareness_bus)

        self.tool_executor = ToolExecutor(self.container.events)
        self.scheduler = TaskScheduler()
        self.action_validator = ActionValidator(AuthorityPolicy(), self.container.events)
        self.actions = ActionRegistry(self.action_validator, self.container.events)

        self.voice_channel = VoiceChannel()
        self.chat_channel = ChatChannel()
        self.voice_engine = VoiceEngine()

        self.browser = BrowserAutomation()
        self.desktop = DesktopAutomation()
        self.file_control = FileAutomation()

        self.dashboard = Dashboard()
        self.skill_registry = SkillRegistry()
        self.capability_registry = CapabilityRegistry()
        self.decision_log = DecisionLog()

        self.screen_capture = ScreenCapture()
        self.vision_ocr = VisionOCR()
        self.vision_understand = VisionUnderstander()

        self.llm_planner = LLMPlanner()
        self.auto_replanner = AutoReplanner(self.llm_planner)
        self.deliberation = MultiAgentDeliberation(self.llm_planner)

        self.playwright = PlaywrightBrowser()
        self.desktop_intel = DesktopIntelligence()
        self.iot = IoTController()
        self.autonomous_workflows = AutonomousWorkflow()

        self.discord = DiscordIntegration()
        self.email = EmailIntegration()
        self.telegram = TelegramIntegration()

        self.continuous_loop = ContinuousAgentLoop(
            event_bus=self.container.events,
            awareness_bus=self.awareness_bus,
            observer=self.observer_agent,
            executor=self.executor_agent,
            goal_engine=self.goal_engine,
            reasoning=self.reasoning,
            reflection=self.reflection,
            planner=self.llm_planner,
            replanner=self.auto_replanner,
            deliberation=self.deliberation,
            working_memory=self.working_memory,
            world_model=self.world_model,
            decision_log=self.decision_log,
            skill_registry=self.skill_registry,
        )

        self.voice_loop = VoiceLoop()
        self.user_model = UserModel()
        self.preference_learner = PreferenceLearner()
        self.learning_engine = LearningEngine()
        self.advanced_learning = AdvancedLearningEngine()
        self.life_goals = LifeGoalManager()
        self.risk_engine = RiskEngine()
        self.retry_manager = RetryManager()
        self.failure_recovery = FailureRecovery()

        self.metrics = MetricsCollector()
        self.tracer = Tracer()
        self.audit = AuditLogger()
        self.secrets = SecretsManager()
        self.permission_scope = PermissionScope()
        self.sandbox = Sandbox()

        self.device_coordinator = DeviceCoordinator()
        self.camera = CameraStream()
        self.microphone = MicrophoneStream()
        self.sensor_hub = SensorHub()

        self._register_default_tools()
        self._setup_awareness_handlers()

        self._initialized = True
        logger.info("SPARK AI Operating System v4.0 initialized")

    def _register_default_tools(self) -> None:
        tools = {
            "web_search": lambda query: self.browser.search(query),
            "open_url": lambda url: self.browser.open_url(url),
            "take_screenshot": lambda: self.desktop.take_screenshot(),
            "open_application": lambda app: self.desktop.open_application(app),
            "type_text": lambda text: self.desktop.type_text(text),
            "read_clipboard": lambda: self.desktop.get_clipboard(),
            "write_clipboard": lambda text: self.desktop.set_clipboard(text),
            "system_monitor": lambda: self.env_awareness.get_health(),
            "file_search": lambda pattern: self.file_control.search_files(pattern),
            "screen_capture": lambda: self.screen_capture.capture(),
            "ocr_extract": lambda path: self.vision_ocr.extract_text(path),
            "vision_understand": lambda path, q="": self.vision_understand.understand(path, q),
        }
        for name, handler in tools.items():
            self.actions.register(name, handler)

    def _setup_awareness_handlers(self) -> None:
        async def on_screen_changed(event):
            self.working_memory.update_context(current_window=event.data.get("current", {}).get("active_window", ""))

        async def on_app_changed(event):
            focused = event.data.get("current", {}).get("focused", "")
            self.working_memory.update_context(current_app=focused)
            self.preference_learner.observe_action("app_switch", {"app": focused})
            self.metrics.increment("awareness.app_changes")

        async def on_user_changed(event):
            present = event.data.get("current", {}).get("present", False)
            self.working_memory.update_context(user_present=present)

        self.awareness_bus.on("screen_changed", on_screen_changed)
        self.awareness_bus.on("application_changed", on_app_changed)
        self.awareness_bus.on("user_changed", on_user_changed)

    async def start_continuous(self) -> None:
        self._running = True
        await self.continuous_loop.start(interval=5.0)
        self.audit.log("system_start", "spark", "continuous_loop_started")

    async def start_voice_loop(self) -> None:
        self.voice_loop.initialize()
        self.voice_loop.on_process(self._voice_process)
        asyncio.create_task(self.voice_loop.start())

    async def _voice_process(self, text: str) -> str:
        self.user_model.increment_interactions()
        import datetime
        self.user_model.track_active_hours(datetime.datetime.now().hour)
        result = await self.process(text, source="voice")
        return str(result.get("reply", ""))

    async def process(self, user_input: str, source: str = "chat") -> dict[str, Any]:
        trace_id = self.tracer.start_trace("process_request", {"input": user_input[:50], "source": source})

        self.user.mark_interaction()
        self.user_model.increment_interactions()
        self.episodic_memory.record("user", user_input, {"source": source})
        self.memory_agent.extract_and_store(user_input)
        self.working_memory.push_conversation("user", user_input, {"source": source})
        self.metrics.increment("requests.total")
        self.metrics.increment(f"requests.{source}")

        context = self.context.update()
        self.working_memory.update_context(**context)

        observer_snapshot = await self.observer_agent.run()

        reasoning_result = self.reasoning.reason(context=str(context), question=user_input)

        result = await self._handle_request(user_input, context)

        self.working_memory.push_conversation("assistant", str(result.get("reply", "")), {"action": result.get("action")})
        self.episodic_memory.record("assistant", str(result.get("reply", "")), {"source": source})
        self.metrics.record_action(result.get("action", "unknown"), True)

        self.tracer.finish_trace(trace_id)
        self.audit.log("process_request", source, result.get("action", ""), {"input": user_input[:50]})

        return result

    async def _handle_request(self, user_input: str, context: dict[str, Any]) -> dict[str, Any]:
        intent = await classify_intent(user_input)
        self.metrics.increment(f"intent.{intent}")

        if intent == "goal_creation":
            return await self._handle_goal(user_input)

        if intent == "action_execution":
            return await self._handle_action(user_input)

        if intent == "memory_query":
            return await self._handle_memory(user_input)

        if intent == "status_check":
            return await self._handle_status(user_input)

        return await self._handle_conversation(user_input)

    async def _handle_goal(self, user_input: str) -> dict[str, Any]:
        lower = user_input.lower()

        if any(w in lower for w in ["life goal", "long term", "my goal"]):
            goal_desc = user_input.replace("life goal", "").replace("long term", "").replace("my goal", "").strip()
            self.life_goals.add_goal(goal_desc, category="long_term")
            return {"reply": f"Life goal added: {goal_desc}", "action": "life_goal"}

        if any(w in lower for w in ["progress", "how am i doing"]):
            report = self.life_goals.get_progress_report()
            return {"reply": str(report), "action": "progress_report"}

        plan_result = await self.planner_agent.run(user_input)
        goal_id = plan_result.get("goal_id", "")
        self.working_memory.set_objective(user_input, plan_result.get("steps", 0))
        self.decision_log.log("goal_created", f"Created goal: {user_input[:50]}", {"goal_id": goal_id})
        return {"reply": f"Goal created with {plan_result.get('steps', 0)} steps", "action": "plan", "goal_id": goal_id}

    async def _handle_action(self, user_input: str) -> dict[str, Any]:
        lower = user_input.lower()

        if any(w in lower for w in ["screenshot", "screen", "what do you see"]):
            path = self.screen_capture.capture()
            if path:
                analysis = self.vision_understand.analyze_activity(path)
                self.metrics.increment("vision.analyses")
                return {"reply": f"I see: {analysis.get('details', 'unknown')}", "action": "vision", "analysis": analysis}
            return {"reply": "Could not capture screen", "action": "error"}

        if any(w in lower for w in ["open", "launch", "start"]):
            app_name = user_input.split("open")[-1].strip() if "open" in lower else user_input
            risk = self.risk_engine.assess("open_application")
            if risk.requires_confirmation:
                return {"reply": f"This requires confirmation: {risk.reason}", "action": "confirm_needed"}
            result = await self.retry_manager.execute_with_retry(
                lambda app=app_name: self.actions.execute("open_application", {"app": app}, source="chat"),
                strategies=["direct", "shell_command"],
            )
            self.decision_log.log("open_app", f"Opened: {app_name}")
            self.learning_engine.record("open_application", "desktop", result.get("success", False))
            self.advanced_learning.record_outcome("open_application", "desktop", result.get("success", False))
            self.user_model.learn_tool_preference("open_application", result.get("success", False))
            self.preference_learner.observe_tool_use("open_application", result.get("success", False))
            return {"reply": str(result), "action": "open"}

        if any(w in lower for w in ["search", "find", "look up"]):
            query = user_input.replace("search", "").replace("find", "").replace("look up", "").strip()
            search_result = await self.actions.execute("web_search", {"query": query}, source="chat")
            return {"reply": str(search_result), "action": "search"}

        if any(w in lower for w in ["browse", "playwright", "navigate"]):
            url = user_input.replace("browse", "").replace("playwright", "").replace("navigate", "").strip()
            result = await self.playwright.navigate(url)
            return {"reply": str(result), "action": "browse"}

        if any(w in lower for w in ["skill", "learn", "how to"]):
            skill = self.skill_registry.find_best(user_input)
            if skill:
                return {"reply": f"Known skill: {skill.name} ({skill.use_count} uses, {skill.success_rate:.0%} success)", "action": "skill_found"}
            return {"reply": f"Skill not found. I can learn: {user_input}", "action": "skill_learn"}

        return {"reply": f"Action received: {user_input}", "action": "acknowledge"}

    async def _handle_memory(self, user_input: str) -> dict[str, Any]:
        lower = user_input.lower()

        if any(w in lower for w in ["who am i", "about me", "my profile"]):
            profile = self.user_model.get_profile()
            return {"reply": str(profile), "action": "user_profile"}

        if any(w in lower for w in ["preferences", "what do i prefer"]):
            prefs = self.preference_learner.snapshot()
            return {"reply": str(prefs.get("inferred", {})), "action": "preferences"}

        mem_result = await self.memory_agent.run("recall", query=user_input)
        return {"reply": str(mem_result.get("results", [])), "action": "memory"}

    async def _handle_status(self, user_input: str) -> dict[str, Any]:
        lower = user_input.lower()

        if any(w in lower for w in ["metrics", "performance"]):
            return {"reply": str(self.metrics.snapshot()), "action": "metrics"}

        if any(w in lower for w in ["devices", "sync"]):
            devices = self.device_coordinator.get_all_devices()
            return {"reply": f"Connected devices: {len(devices)}", "action": "devices", "devices": devices}

        return {"reply": self.run_dashboard(), "action": "dashboard"}

    async def _handle_conversation(self, user_input: str) -> dict[str, Any]:
        return {"reply": f"Received: {user_input}", "action": "conversation"}

    def learn_skill(self, name: str, steps: list[dict[str, Any]], description: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        skill = self.skill_registry.learn_from_action(name, steps, description, tags)
        self.decision_log.log("skill_learned", f"Learned skill: {name}", {"steps": len(steps)})
        return {"learned": True, "skill": skill.to_dict()}

    def dashboard_snapshot(self) -> dict[str, Any]:
        wm_snapshot = self.working_memory.snapshot()
        goal_stats = self.goal_engine.stats()
        goal_graph = {}
        root_goals = self.goal_engine.root_goals()
        if root_goals:
            goal_graph = self.goal_engine.goal_tree(root_goals[0].id) or {}

        self.dashboard.update("working_memory", wm_snapshot)
        self.dashboard.update("current_goal", goal_stats["goals"][0] if goal_stats["goals"] else None)
        self.dashboard.update("goal_graph", goal_graph)
        self.dashboard.update("memory_stats", {
            "semantic_count": self.semantic_memory.count(),
            "episodic_count": self.episodic_memory.count(),
            "working_active": "active" if self.working_memory.has_objective() else "idle",
        })
        self.dashboard.update("context", self.context.snapshot())
        self.dashboard.update("world_model", self.world_model.snapshot())
        self.dashboard.update("running_agents", [
            {"name": a.name, "status": a.status.value}
            for a in [self.planner_agent, self.executor_agent, self.memory_agent, self.reflection_agent, self.observer_agent]
        ])
        self.dashboard.update("agent_health", [
            {"name": a.name, "status": a.status.value, "latency_ms": 0, "errors": 0}
            for a in [self.planner_agent, self.executor_agent, self.memory_agent, self.reflection_agent, self.observer_agent]
        ])
        self.dashboard.update("system_health", self.env_awareness.get_health())
        self.dashboard.update("permissions", self.action_validator.policy.get_permissions())
        self.dashboard.update("awareness_feed", self.awareness_bus.recent(limit=10))
        self.dashboard.update("decision_log", self.decision_log.recent(limit=10))
        self.dashboard.update("skills", self.skill_registry.list_all())
        self.dashboard.update("capabilities", self.capability_registry.list_all())
        return self.dashboard.get_snapshot()

    def run_dashboard(self) -> str:
        self.dashboard_snapshot()
        return self.dashboard.render_text()

    def shutdown(self) -> None:
        logger.info("Shutting down SPARK AI Operating System v4.0...")
        self._running = False
        self.continuous_loop.stop()
        self.voice_loop.stop()
        self.observer_agent.stop_observing()
        self.scheduler.stop()
        self.voice_engine.stop()
        self.camera.stop()
        self.microphone.stop()
        self.sandbox.cleanup()
        self.audit.log("system_shutdown", "spark", "shutdown_complete")
        Container.reset()
        logger.info("SPARK v4.0 shutdown complete")
