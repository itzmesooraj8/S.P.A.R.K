# SPARK
**A Smart Personal AI Assistant**

SPARK is a definitive, autonomous personal AI assistant. 
The HUD is SPARK's "face" where all interactions occur. Features like the Globe, Sentinel cybersecurity tools, and WiFi presence awareness are specialized intelligence panels running inside SPARK. There is only one cohesive product: SPARK.

## Core Capabilities
- **Core Intelligence**: Powered by Ollama & Gemini 2.0 Flash in a hybrid engine, featuring an autonomous 120-second cognitive loop.
- **Voice System**: Full duplex "Hey SPARK" wake-word detection (via OpenWakeWord ONNX), batch Whisper STT, and responsive TTS.
- **Personal AI**: Includes seamless morning briefings, adaptive task management, an app launcher, focus modes, and weather context. 
- **HUD Interface**: A robust SparkPanel frontend supporting Chat, Cognition (Autonomous Loop Logs), Session History, and a dedicated Personal AI dashboard.
- **Intelligence Panels**: Includes real-time Globe integration via WebSockets, Sentinel threat feeds, and Playwright-powered Browser Agent exploration.

## Architecture
- **Backend**: FastAPI + Uvicorn, APScheduler for tasks, ChromaDB for memory, and WebSockets for real-time telemetry.
- **Frontend**: React (Vite) + Tailwind CSS, with distinct modules dynamically injected into the HUD.

## Deployment
SPARK is fully containerized. To spin it up locally:
1. Copy `.env.example` to `.env` and fill out any provider API keys you plan to use.
2. Ensure you have Docker running.
3. Use `docker compose up` to start all services (Backend, Frontend, Ollama, ChromaDB).

## Notes
- SPARK is highly sovereign. It operates with a local-first philosophy.
- The `spark_core/personal` routers represent the brain of SPARK's personal proactive behaviors.

*“The best way to predict the future is to invent it.”* 
