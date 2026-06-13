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
- Routes requests through an LLM intent classifier
- Reasons about options using actual LLM scoring
- Manages four types of memory (working/episodic/semantic/procedural)
- Gates every action through a permission system
- Retries failures with strategy switching
- Falls back gracefully when backends are unavailable
- Exposes everything through a real-time React dashboard

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
├── voice/             — Voice Engine + Always-Listening Loop
├── communication/     — Voice Channel, Chat Channel
├── authority/         — Permission Policy, Action Validator
├── reliability/       — Risk Engine, Retry Manager, Failure Recovery
├── observability/     — Metrics, Tracing, Audit Log
├── security/          — Secrets, Permission Scopes, Sandbox
├── user/              — User Model, Preference Learning
├── learning/          — Learning Engine, Advanced Learning
├── goals/             — Long-Term Goal Management
├── skills/            — Reusable Skill System
├── capabilities/      — Capability Registry
├── decisions/         — Decision Log
├── sync/              — Cross-Device Synchronization
├── multimodal/        — Camera, Microphone, Sensors
├── web/               — FastAPI + React Dashboard
├── ui/                — JARVIS-Style Text Dashboard
├── llm_router.py      — LLM Intent Classifier
├── llm_bridge.py      — Clean LLM Interface (Groq → Ollama → Fallback)
├── os.py              — Main Orchestrator
└── tests/             — 117 tests
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright (optional, for browser automation)
playwright install

# Run SPARK
python -m spark

# Run tests
python -m pytest spark/tests/ -v
```

## Configuration

SPARK uses environment variables for secrets:

```bash
# .env.example
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
DISCORD_TOKEN=your_discord_token
TELEGRAM_TOKEN=your_telegram_token
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_app_password
```

## Intent Routing

SPARK classifies user intent using LLM (Groq → Ollama → Deterministic fallback):

| Intent | Example |
|--------|---------|
| `goal_creation` | "create a goal to learn FastAPI" |
| `action_execution` | "open Chrome browser" |
| `memory_query` | "remember my name is Sooraj" |
| `status_check` | "show me the dashboard" |
| `conversation` | "tell me a joke" |

## Test Suite

```bash
python -m pytest spark/tests/ -v

# 117 tests covering:
# - Intent classification (19 tests)
# - LLM bridge + fallback (14 tests)
# - World model dynamic confidence (15 tests)
# - Reasoning engine (12 tests)
# - Autonomous loop (10 tests)
# - Authority + retry + recovery (26 tests)
# - Integration tests (21 tests)
```

## Tech Stack

- **Language:** Python 3.11+
- **LLM:** Groq (cloud) + Ollama (local) + Deterministic fallback
- **Memory:** ChromaDB + sentence-transformers
- **Vision:** DXCam / MSS / PyAutoGUI + EasyOCR / Tesseract
- **Browser:** Playwright
- **IoT:** paho-mqtt + Home Assistant
- **Dashboard:** FastAPI + React/Next.js
- **Testing:** pytest + pytest-asyncio

## License

MIT
