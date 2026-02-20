# SPARK AI Core v2 (Sovereign Core)

This is the newly architected, production-ready backend for SPARK, built on FastAPI.
It handles real-time WebSockets, serving the front-end, System Monitoring, and Hybrid LLM routing.

## 🚀 Setup Instructions

### 1. Requirements

Ensure you have your environment set properly. From this directory `spark_core/`:
```bash
pip install -r requirements.txt
```

### 2. Ollama Setup (Local AI)

SPARK v2 uses `llama3:8b` (or `mistral:7b` if you prefer).
1. Download [Ollama for Windows](https://ollama.com/download/windows).
2. Open terminal and run:
   ```bash
   ollama run llama3:8b
   ```
   *Wait for it to download and verify it runs.*
3. Keep the Ollama tray app running in the background. It exposes `http://localhost:11434` which `hybrid_engine.py` targets.

### 3. Build React Frontend (HUD)

To serve the React UI directly from FastAPI, build the UI first. Navigate to the root `S.P.A.R.K` directory:
```bash
npm install
npm run build
```
This generates a `dist/` folder which `spark_core/main.py` serves statically.

### 4. Boot SPARK Core

From this `spark_core/` folder, run:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
or 
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

*NOTE: You must start it from inside `spark_core` so imports resolve correctly.*

### 5. Accessing HUD

- **Laptop:** Open `http://localhost:8000`
- **Phone:** Connect to your laptop's Local IP, e.g., `http://192.168.1.XX:8000`

## 🧠 Connecting the React HUD to WebSockets

In your React codebase (e.g., `src/sockets/socketManager.ts`), connect like this:
```typescript
const aiSocket = new WebSocket("ws://localhost:8000/ws/ai");
const systemSocket = new WebSocket("ws://localhost:8000/ws/system");

aiSocket.onmessage = (event) => console.log("AI says:", event.data);
systemSocket.onmessage = (event) => console.log("System Metric:", JSON.parse(event.data));
```
