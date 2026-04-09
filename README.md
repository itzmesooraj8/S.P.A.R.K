# S.P.A.R.K. (Sovereign Personal AI & Reasoning Kernel)

S.P.A.R.K. is an advanced, fully local, Jarvis-inspired AI assistant architecture. It is built to operate autonomously, executing tasks across multiple intelligence layers, voice interfaces, and cognitive reasoning engines.

## 🧠 Core Architecture

S.P.A.R.K. is structured as a robust multi-agent operating system:
* **Commander Router (`commander.py`)**: The central brain that dynamically classifies and routes natural language requests to specialized sub-agents (Code, Risk, Intelligence, Research).
* **Voice Engine (`tts_router.py` & `wakeword.py`)**: Real-time auditory interface combining LuxTTS (local CUDA-accelerated text-to-speech) with Edge-TTS fallbacks, powered by openwakeword daemon listeners.
* **Cognitive Loop (`cognitive.loop`)**: Background reasoning sequence that continuously integrates memory, global threat feeds, and task progression.
* **LLM Engine (`model_router.py`)**: Smart LLM selection prioritizing local `llama3` for rapid execution, with graceful escalation to external models.

## 🚀 Quick Start

Ensure you have Python 3.11 installed (as required by the OpenWakeWord TFLite runtime).

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch the Core Server**:
   ```bash
   python run_server.py
   ```
   *This starts the unified FastAPI entrypoint over Uvicorn on port 8000.*

## ⚙️ Development & Configuration
- **Entry Points**: The consolidated entrypoint is `spark_core/main.py` (executed via `run_server.py` at the root).
- **Environment**: Set up a `.env` based on `.env.example`.
- **System Monitoring**: `sys_monitor` provides real-time system metrics (CPU, RAM, Network) mapped to the frontend HUD over WebSockets.
- **Local Fallbacks**: The system aggressively prefers local processing (e.g., Pyttsx3 TTS fallback, offline Wake Word models) to guarantee resilience during network failure.
