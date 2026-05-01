# S.P.A.R.K. — Sovereign Personal AI Runtime Kernel

An autonomous, J.A.R.V.I.S.-style personal AI operating system with a production-grade React HUD, local Whisper STT, and persistent ChromaDB semantic memory. 

## Quickstart (Windows)

Launch the entire stack in under 3 minutes:

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd S.P.A.R.K
   ```

2. **Install Python backend dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install React HUD dependencies:**
   ```bash
   cd "spark src"
   npm install
   cd ..
   ```

4. **Configure Environment:**
   Copy `.env.example` to `.env` and add your keys (Groq API, etc).

5. **Launch S.P.A.R.K.:**
   Double-click `start.bat` or run from terminal:
   ```cmd
   start.bat
   ```

This master boot script will launch the FastAPI WebSocket bridge, the Core Cognitive Loop, and the React HUD simultaneously. Once booted, the HUD will open in your browser. 

**Press F9 to initiate the voice link.**

---

### Architecture
- **Backend**: Python, Groq `llama-3.3-70b-versatile`, Edge TTS, local Whisper STT.
- **Memory**: ChromaDB semantic vector store.
- **Bridge**: FastAPI WebSockets (`ws://localhost:8000/ws`).
- **Frontend**: React + Vite + TailwindCSS + Zustand + D3.js.

*Note: Phase 03+ features (continuous hotword wake, multi-agent routing) are currently marked as roadmap items and are actively being built.*
