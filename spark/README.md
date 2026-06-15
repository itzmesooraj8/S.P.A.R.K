# S.P.A.R.K. — AI Operating System

A continuously-running, environment-aware, goal-pursuing agent built in Python. Inspired by Tony Stark's JARVIS.

```
Observe → Understand → Predict → Plan → Act → Reflect → Learn → Observe
Forever. 24/7.
```

## What SPARK Is

SPARK is not a chatbot wrapper. It's an AI operating system that:

- Observes your screen and active applications every 5 seconds
- Builds a live confidence model of what you're doing
- Routes requests through an LLM intent classifier (Groq → Ollama → Deterministic)
- Reasons about options using actual LLM scoring
- Manages four types of memory (working/episodic/semantic/procedural)
- Gates every action through a permission system
- Retries failures with strategy switching
- Falls back gracefully when backends are unavailable
- Responds to voice commands with wake word detection
- Exposes everything through a JARVIS-style desktop dashboard

## Quick Start

```bash
# Install base dependencies
pip install -e .

# Install optional features as needed
pip install -e ".[llm]"          # LLM support (Groq)
pip install -e ".[vision]"       # Screen capture, OCR
pip install -e ".[browser]"      # Playwright automation
pip install -e ".[memory]"       # ChromaDB vector memory
pip install -e ".[voice]"        # Voice I/O (PyAudio, pyttsx3)
pip install -e ".[iot]"          # MQTT device control
pip install -e ".[web]"          # FastAPI dashboard
pip install -e ".[all]"          # Everything

# Install Playwright browsers (if using browser automation)
python -m playwright install

# Run SPARK (text mode)
python -m spark

# Run SPARK (voice mode)
python -m spark --voice

# Run tests
python -m pytest spark/tests/ -v
```

## Voice Mode

SPARK supports always-on voice interaction:

1. Say **"Hey SPARK"** to activate
2. Hear a **beep** confirmation
3. Speak your command
4. SPARK processes and responds via TTS

```bash
python -m spark --voice

# Voice commands:
# "Hey SPARK" — wake word
# "What time is it" — get current time
# "Open notepad" — launch application
# "Remember my name is Sooraj" — store in memory
# "Stop" / "Cancel" — interrupt current action
```

## JARVIS Dashboard

SPARK includes a full JARVIS-style desktop dashboard:

```bash
# Start the dashboard server
python -c "from spark.web.server import DashboardServer; from spark.os import SparkOS; os = SparkOS(); os.initialize(); DashboardServer(os).start()"

# Open browser to http://localhost:8080
```

Dashboard features:
- Three-column layout (sidebar + chat + system stats)
- Dark terminal style with electric blue accent
- Real-time system monitoring
- Module status indicators
- Quick command buttons
- Voice mode overlay
- WebSocket live updates

## Intent Routing

SPARK classifies user intent using LLM (Groq → Ollama → Deterministic fallback):

| Intent | Example |
|--------|---------|
| `goal_creation` | "create a goal to learn FastAPI" |
| `action_execution` | "open Chrome browser", "search for Python", "what news" |
| `memory_query` | "remember my name is Sooraj", "what is my name" |
| `status_check` | "show me the dashboard" |
| `conversation` | "hello", "what time is it", "who are you" |

## Configuration

SPARK uses environment variables for secrets:

```bash
# .env.example
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
DISCORD_TOKEN=your_discord_token
TELEGRAM_TOKEN=your_telegram_token
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
MQTT_BROKER=localhost
MQTT_PORT=1883
```

## Test Suite

```bash
python -m pytest spark/tests/ -v

# 136 tests covering:
# - Intent classification (19 + 19 regression tests)
# - LLM bridge + fallback (14 tests)
# - World model dynamic confidence (15 tests)
# - Reasoning engine (12 tests)
# - Autonomous loop (10 tests)
# - Authority + retry + recovery (26 tests)
# - Integration tests (21 tests)
```

## Security

SPARK has a layered security model:

1. **Policy Engine** — Constitution for all actions (like OPA/Rego)
2. **Authority Layer** — Permission gating (ALLOW/CONFIRM/DENY)
3. **Risk Engine** — Pre-action risk assessment
4. **Secrets Manager** — Never stores secrets in code
5. **Sandbox** — Isolated execution for tools

Every action passes: `Policy Engine → Authority Validator → Risk Engine → Execution`

## Architecture

```
spark/
├── core/              — Event Bus, State Manager, DI Container, Config
├── cognition/         — Goal Engine, Reasoning, Reflection, Planning
├── awareness/         — Screen, App, Context, User, World Model
├── memory/            — Semantic (ChromaDB), Episodic, Procedural, Working
├── agents/            — Planner, Executor, Memory, Reflection, Observer
├── autonomy/          — Continuous Agent Loop (the brain)
├── planning/          — LLM Planner, Replanner, Multi-Agent Deliberation
├── automation/        — Playwright, Desktop Intel, IoT, Autonomous Workflows
├── integrations/      — Discord, Email, Telegram
├── voice/             — Voice Loop (wake word, STT, TTS)
├── communication/     — Voice Channel, Chat Channel
├── authority/         — Permission Policy, Action Validator
├── reliability/       — Risk Engine, Retry Manager, Failure Recovery
├── observability/     — Metrics, Tracing, Audit Log
├── security/          — Secrets, Permission Scopes, Sandbox
├── policy/            — Security Constitution
├── conversation/      — Conversation Manager
├── user/              — User Model, Preference Learning
├── learning/          — Learning Engine, Advanced Learning
├── goals/             — Long-Term Goal Management
├── skills/            — Reusable Skill System
├── capabilities/      — Capability Registry
├── decisions/         — Decision Log
├── sync/              — Cross-Device Synchronization
├── multimodal/        — Camera, Microphone, Sensors
├── audio/             — STT (Whisper) + TTS (edge-tts/pyttsx3)
├── tools/             — Voice stubs (PyAudio/pyttsx3)
├── vision/            — Screen Capture, OCR, Vision Understanding
├── web/               — FastAPI + JARVIS Dashboard (HTML/CSS/JS)
├── ui/                — Text Dashboard
├── llm_router.py      — LLM Intent Classifier
├── llm_bridge.py      — Clean LLM Interface (Groq → Ollama → Fallback)
├── os.py              — Main Orchestrator
└── tests/             — 136 tests
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design and data flow
- [Security](docs/SECURITY.md) — Threat model and mitigations
- [Runtime](docs/RUNTIME.md) — Startup sequence and configuration

## Tech Stack

- **Language:** Python 3.11+
- **LLM:** Groq (cloud) + Ollama (local) + Deterministic fallback
- **Memory:** ChromaDB + sentence-transformers
- **Vision:** PyAutoGUI + EasyOCR / Tesseract
- **Voice:** Whisper (STT) + edge-tts / pyttsx3 (TTS)
- **Browser:** Playwright
- **IoT:** paho-mqtt + Home Assistant
- **Dashboard:** FastAPI + HTML/CSS/JS (JARVIS-style)
- **Testing:** pytest + pytest-asyncio

## License

MIT
