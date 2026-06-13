# SPARK Runtime

## Startup Sequence

1. `python -m spark` calls `spark/__main__.py:main()`
2. `SparkOS()` created
3. `os.initialize()` wires all subsystems
4. Interactive REPL loop starts

## System Components Initialized

```
SparkOS.initialize():
  ├── PersonaIdentity (name, style)
  ├── GoalEngine (goal management)
  ├── ReasoningEngine (LLM reasoning)
  ├── ReflectionEngine (self-improvement)
  ├── SemanticMemory (ChromaDB vectors)
  ├── EpisodicMemory (conversation log)
  ├── ProceduralMemory (learned skills)
  ├── WorkingMemory (session context)
  ├── ScreenAwareness (screen capture)
  ├── ApplicationAwareness (running apps)
  ├── ContextAwareness (situation)
  ├── UserAwareness (presence)
  ├── EnvironmentAwareness (CPU/mem)
  ├── AwarenessBus (event publishing)
  ├── WorldModel (activity patterns)
  ├── 5 Agents (planner, executor, memory, reflection, observer)
  ├── ToolExecutor (tool dispatch)
  ├── TaskScheduler (scheduling)
  ├── ActionValidator (permissions)
  ├── AuthorityPolicy (rules)
  ├── VoiceChannel (voice I/O)
  ├── ChatChannel (text I/O)
  ├── VoiceEngine (TTS/STT)
  ├── Browser (Playwright)
  ├── Desktop (PyAutoGUI)
  ├── FileControl (file ops)
  ├── Dashboard (JARVIS display)
  ├── SkillRegistry (learned skills)
  ├── CapabilityRegistry (tool groups)
  ├── DecisionLog (audit trail)
  ├── Vision (screen capture + OCR)
  ├── LLMPlanner (goal planning)
  ├── AutoReplanner (failure recovery)
  ├── Deliberation (multi-agent)
  ├── PlaywrightBrowser (browser automation)
  ├── DesktopIntelligence (smart desktop)
  ├── IoTController (device control)
  ├── AutonomousWorkflow (self-executing)
  ├── DiscordIntegration
  ├── EmailIntegration
  ├── TelegramIntegration
  ├── ContinuousAgentLoop (the brain)
  ├── VoiceLoop (always listening)
  ├── UserModel (user profile)
  ├── PreferenceLearner (behavior patterns)
  ├── LearningEngine (strategy tracking)
  ├── AdvancedLearningEngine (evolution)
  ├── LifeGoalManager (long-term goals)
  ├── RiskEngine (risk assessment)
  ├── RetryManager (intelligent retry)
  ├── FailureRecovery (error diagnosis)
  ├── MetricsCollector (metrics)
  ├── Tracer (distributed tracing)
  ├── AuditLogger (compliance)
  ├── SecretsManager (key management)
  ├── PermissionScope (access control)
  ├── Sandbox (isolated execution)
  ├── DeviceCoordinator (cross-device)
  ├── CameraStream (video)
  ├── MicrophoneStream (audio)
  ├── SensorHub (IoT sensors)
  └── PolicyEngine (constitution)
```

## Configuration

Environment variables (`.env`):
- `GROQ_API_KEY` — Groq API key
- `DISCORD_TOKEN` — Discord bot token
- `TELEGRAM_TOKEN` — Telegram bot token
- `SMTP_HOST` — Email SMTP server
- `MQTT_BROKER` — IoT MQTT broker
