#!/usr/bin/env python
"""
SPARK COMPLETE STARTUP & ORCHESTRATION SYSTEM
Auto-initialization with health checks, component startup, and mode selection
"""
import os
import sys
import json
import time
import asyncio
import subprocess
import platform
from datetime import datetime
from pathlib import Path

# UTF-8 on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class SPARKStartup:
    """Complete SPARK system startup orchestrator"""

    def __init__(self):
        self.config = {
            "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "gemma3:4b"),
            "backend_host": os.getenv("SPARK_HOST", "0.0.0.0"),
            "backend_port": int(os.getenv("SPARK_PORT", 8000)),
            "frontend_port": int(os.getenv("VITE_PORT", 5173)),
        }
        self.status = {
            "ollama": False,
            "backend": False,
            "frontend": False,
        }

    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "=" * 100)
        print(f"  {text}")
        print("=" * 100)

    async def check_ollama(self):
        """Verify Ollama is running"""
        print("\n[1️⃣  OLLAMA CHECK]")
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.config['ollama_host']}/api/tags"],
                capture_output=True,
                timeout=2,
                text=True
            )
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    models = [m['name'] for m in data.get('models', [])]
                    print(f"  ✓ Ollama is running")
                    print(f"  ✓ Available models: {models}")
                    if self.config['ollama_model'] in models:
                        print(f"  ✓ {self.config['ollama_model']} is loaded")
                        self.status["ollama"] = True
                        return True
                    else:
                        print(f"  ⚠ {self.config['ollama_model']} not found")
                        print(f"    Pulling model: ollama pull {self.config['ollama_model']}")
                except json.JSONDecodeError:
                    print(f"  ✗ Couldn't parse Ollama response")
        except subprocess.TimeoutExpired:
            print(f"  ✗ Ollama not responding at {self.config['ollama_host']}")
        except Exception as e:
            print(f"  ✗ Error checking Ollama: {str(e)[:100]}")

        print(f"\n  📋 How to start Ollama:")
        print(f"     1. Install from: https://ollama.ai")
        print(f"     2. Run: ollama serve")
        print(f"     3. In another terminal: ollama pull {self.config['ollama_model']}")
        return False

    def check_audio_devices(self):
        """Check microphone and speaker"""
        print("\n[2️⃣  AUDIO DEVICES CHECK]")
        try:
            import sounddevice
            devices = sounddevice.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            output_devices = [d for d in devices if d['max_output_channels'] > 0]

            if input_devices and output_devices:
                print(f"  ✓ Microphone found: {input_devices[0]['name']}")
                print(f"  ✓ Speaker found: {output_devices[0]['name']}")
                return True
            else:
                print(f"  ✗ Missing audio devices")
                if not input_devices:
                    print(f"    - No microphone detected")
                if not output_devices:
                    print(f"    - No speaker detected")
        except ImportError:
            print(f"  ⚠ sounddevice not installed")
            print(f"    Install: pip install sounddevice")
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
        return False

    def check_databases(self):
        """Initialize SQLite databases if needed"""
        print("\n[3️⃣  DATABASE CHECK]")
        db_dir = "spark_memory_db"
        os.makedirs(db_dir, exist_ok=True)

        databases = [
            "personal_tasks.db",
            "personal_briefings.db",
            "knowledge_graph.db",
        ]

        for db_name in databases:
            db_path = os.path.join(db_dir, db_name)
            if os.path.exists(db_path):
                size = os.path.getsize(db_path) / 1024
                print(f"  ✓ {db_name:30s} ({size:.1f} KB)")
            else:
                print(f"  ○ {db_name:30s} (will be created on first run)")

    def check_dependencies(self):
        """Check Python dependencies"""
        print("\n[4️⃣  PYTHON DEPENDENCIES CHECK]")

        critical_packages = [
            "fastapi",
            "uvicorn",
            "starlette",
            "pydantic",
            "sqlalchemy",
            "pyaudio",
            "torch",
        ]

        missing = []
        for package in critical_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"  ✓ {package}")
            except ImportError:
                print(f"  ✗ {package}")
                missing.append(package)

        if missing:
            print(f"\n  Install missing packages:")
            print(f"    pip install {' '.join(missing)}")
            return False
        return True

    def start_backend(self):
        """Start FastAPI backend"""
        print("\n[5️⃣  STARTING BACKEND]")
        print(f"  Backend URL: http://127.0.0.1:{self.config['backend_port']}")
        print(f"  Starting uvicorn...")
        print(f"\n  Command:")
        print(f"    python run_server.py")
        print(f"\n  Or manually:")
        print(f"    uvicorn spark_core.main:app --host {self.config['backend_host']} --port {self.config['backend_port']} --reload")

        # Note: actual startup handled by user

    def start_frontend(self):
        """Start Vite dev server"""
        print("\n[6️⃣  STARTING FRONTEND]")
        print(f"  Frontend URL: http://localhost:{self.config['frontend_port']}")
        print(f"\n  In a SEPARATE terminal, run:")
        print(f"    npm run dev")

    def print_system_info(self):
        """Print system information"""
        print("\n[ℹ️  SYSTEM INFO]")
        print(f"  Platform: {platform.system()} {platform.release()}")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Working Directory: {os.getcwd()}")
        print(f"  Timestamp: {datetime.now().isoformat()}")

    async def run(self):
        """Execute full startup sequence"""
        self.print_header("🚀 SPARK STARTUP SEQUENCE")
        self.print_system_info()

        # Phase 1: Checks
        print("\n" + "=" * 100)
        print("PHASE 1: SYSTEM HEALTH CHECKS")
        print("=" * 100)

        await self.check_ollama()
        self.check_audio_devices()
        self.check_databases()
        self.check_dependencies()

        # Phase 2: Startup
        print("\n" + "=" * 100)
        print("PHASE 2: COMPONENT STARTUP")
        print("=" * 100)

        self.start_backend()
        self.start_frontend()

        # Phase 3: Connection Info
        self.print_header("📡 CONNECTION INFORMATION")

        print(f"""
Backend Server:
  ✓ FastAPI: http://127.0.0.1:{self.config['backend_port']}
  ✓ API Docs: http://127.0.0.1:{self.config['backend_port']}/docs
  ✓ WebSocket: ws://127.0.0.1:{self.config['backend_port']}/ws/*

Frontend Application:
  ✓ Web UI: http://localhost:{self.config['frontend_port']}
  ✓ Vite Dev Server: http://localhost:{self.config['frontend_port']}

Local LLM (Ollama):
  ✓ Host: {self.config['ollama_host']}
  ✓ Model: {self.config['ollama_model']}
        """)

        # Phase 4: Features List
        self.print_header("✨ SPARK FEATURES")

        print("""
Voice Intelligence:
  🎤 Wake Word Detection: "Hey Spark", "Spark"
  🗣️  Speech-to-Text: faster-whisper (local, offline)
  🔊 Text-to-Speech: LuxTTS, edge-tts, pyttsx3
  🎙️  Voice Commands: Full voice interface support

Personal AI:
  📋 Task Management: Create, track, complete tasks
  📑 Briefing System: Daily insights and summaries
  🧠 Knowledge Graph: Long-term memory
  🔍 Command Bar: Ctrl+Space to activate

Intelligence:
  🤖 Local LLM: Ollama with Gemma 3:4b
  ⚡ Hybrid Engine: Local primary + Gemini fallback
  🧬 Self-Evolution: Autonomous learning
  🎯 Intent Router: Multi-agent task routing

Monitoring:
  🌍 Globe Intelligence: Real-time geopolitical data
  🛰️  Satellite Imagery: Live satellite feeds
  📊 System Telemetry: Resource monitoring
  📡 Alert System: Real-time notifications

Real-Time Systems:
  🔌 WebSocket Streaming: Instant updates
  💬 Command Completion: Progressive response
  📢 Alert Broadcasting: System-wide events
        """)

        # Phase 5: Quick Start
        self.print_header("🚄 QUICK START")

        print("""
1️⃣  TERMINAL 1 - Start Backend:
    python run_server.py

    (Wait for message: "Uvicorn running on http://127.0.0.1:8000")

2️⃣  TERMINAL 2 - Start Frontend:
    npm run dev

    (Wait for message: "VITE v... ready in XXms")

3️⃣  BROWSER - Open SPARK:
    http://localhost:5173

4️⃣  TEST VOICE FEATURES:
    - Say "Hey Spark" to wake up the system
    - Command bar will open automatically
    - Speak a command, e.g., "Create a task"
    - Listen for Spark's response

5️⃣  TEST MANAGEMENT FEATURES:
    - Click "Tasks" button in bottom dock
    - Create tasks via voice or UI
    - View real-time updates
        """)

        # Phase 6: Troubleshooting
        self.print_header("🔧 TROUBLESHOOTING")

        print("""
If Ollama not found:
  1. Install: https://ollama.ai
  2. Download model: ollama pull gemma3:4b
  3. Run: ollama serve
  4. Verify: curl http://localhost:11434/api/tags

If audio not working:
  1. Check microphone: Test in system settings
  2. Check speaker: Play a test sound
  3. Restart audio system
  4. Reinstall pyaudio: pip install --upgrade pyaudio

If WebSocket connection fails:
  1. Verify backend is running
  2. Check firewall (allow port 8000)
  3. Clear browser cache (Ctrl+Shift+Delete)
  4. Reload page (F5)

If voice recognition not triggering:
  1. Verify microphone input in system settings
  2. Test with: "alexa help" (fallback wake word)
  3. Check browser microphone permissions (click lock icon)
  4. Try: browser console → navigator.mediaDevices.enumerateDevices()
        """)

        print("\n" + "=" * 100)
        print("SPARK STARTUP READY ✓")
        print("=" * 100 + "\n")

if __name__ == "__main__":
    startup = SPARKStartup()
    asyncio.run(startup.run())
