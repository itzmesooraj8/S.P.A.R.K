# SPARK PROJECT - FINAL COMPLETION PLAN

## Objective
Complete S.P.A.R.K. (Sovereign Personal AI Resource Kit) to be a fully functional local AI assistant with:
- Voice command activation ("Hey Spark", "Spark")
- Personaplex-based voice synthesis
- Ollama Gemma 3:4b for local LLM
- Full task/briefing management
- Real-time WebSocket updates
- Complete integration testing

## Current State Analysis
✅ **Working**
- Backend FastAPI core with 80+ routers
- Session 3: Task & Briefing persistence (verified via TestClient)
- WebSocket system for real-time updates
- Wake word detection (using OpenWakeWord)
- TTS/STT integration
- Ollama local LLM with Gemini fallback
- Frontend React HUD with all modules
- Knowledge graph & cognitive loop

⚠️ **Issues to Fix**
- Uvicorn HTTP context issue (Windows-specific event loop)
- Wake word model uses "alexa" placeholder (needs "hey_spark")
- Personaplex not integrated yet
- Comprehensive verification tests missing
- Some HTTP endpoints fail via Uvicorn (TestClient works)

## Implementation Plan

### Phase 1: Voice Synthesis Enhancement (Personaplex Integration)
**Goal:** Add professional voice synthesis using NVIDIA Personaplex

**Steps:**
1. Clone Personaplex repo
2. Set up voice cloning environment
3. Create voice profile for "Spark"
4. Integrate with existing TTS router
5. Add voice cloning API endpoint

**Files to create/modify:**
- `/spark_core/voice/personaplex_engine.py` (NEW)
- `/spark_core/voice/tts_router.py` (MODIFY - add Personaplex option)
- `requirements.txt` (ADD personaplex dependencies)
- `.env` (ADD Personaplex config)

### Phase 2: Wake Word Enhancement
**Goal:** Proper detection for "Hey Spark" and "Spark"

**Steps:**
1. Train custom ONNX model for "hey_spark" + "spark"
2. Update WakeWordListener to use custom model
3. Configure confidence thresholds per wake word
4. Add wake word diagnostics endpoint
5. Test wake word detection reliability

**Files to create/modify:**
- `/spark_core/voice/wakeword.py` (MODIFY - update model loading)
- `/spark_core/voice/wakeword_trainer.py` (NEW - optional training script)
- `config/wakeword_models.yaml` (NEW - model configuration)

### Phase 3: HTTP Context Issue Resolution
**Goal:** Fix "threads can only be started once" error

**Strategies:**
1. Try: ThreadPoolExecutor with pre-initialized threads
2. Try: Switch to hypercorn ASGI server instead of Uvicorn
3. Try: ProactorEventLoop with thread pool executor
4. Try: Separate SQLite operations to background worker process
5. Fallback: Document workaround (use TestServer or alternative server)

**Files to modify:**
- `run_server.py` (MODIFY - try different servers/event loops)
- `spark_core/personal/task_memory.py` (MODIFY - if executor needed)

### Phase 4: Comprehensive Verification Tests
**Goal:** 100% test coverage of all systems

**Test Categories:**
1. Backend Core Tests (FastAPI, routing, lifespan)
2. Voice Engine Tests (TTS, STT, wake word)
3. LLM Tests (Ollama availability, model loading)
4. Persistence Tests (Task CRUD, Briefing CRUD)
5. WebSocket Tests (Broadcasting, real-time updates)
6. Frontend Integration Tests (Store sync, component rendering)
7. E2E Tests (Full workflow from wake word to response)
8. Performance Tests (Latency, memory usage)

**Files to create:**
- `/test_spark_complete_verification.py` (MAIN - comprehensive test suite)
- `/test_voice_engine.py` (Voice-specific tests)
- `/test_ollama_integration.py` (LLM tests)
- `/test_frontend_integration.py` (Frontend tests via TestClient)

### Phase 5: System Integration & Startup Script
**Goal:** Create production-ready startup system

**Features:**
1. Health check on startup (Ollama, audio devices, databases)
2. Auto-initialization of missing databases
3. Graceful handling of missing dependencies
4. Configuration validation
5. Startup diagnostics

**Files to create:**
- `/spark_startup.py` (NEW - comprehensive startup script)
- `/health_check.py` (NEW - system diagnostics)

### Phase 6: Documentation & User Guide
**Goal:** Complete documentation

**Files to create:**
- `/STARTUP_GUIDE.md` - How to start SPARK
- `/VOICE_CONFIGURATION.md` - Voice setup
- `/TROUBLESHOOTING.md` - Common issues
- `/API_REFERENCE.md` - All endpoints

---

## Detailed Implementation Steps

### STEP 1: Install & Configure Personaplex
```bash
# Clone Personaplex
cd /path/to/spark
git clone https://github.com/NVIDIA/personaplex.git
cd personaplex
pip install -e .

# Install dependencies
pip install numpy scipy librosa soundfile torch torchaudio

# Setup voice profiles
python personaplex/setup_voice.py --voice spark --output ./voice_profiles/spark.pt
```

### STEP 2: Create Personaplex Integration
**File:** `spark_core/voice/personaplex_engine.py`
```python
class PersonaplexEngine:
    """NVIDIA Personaplex voice synthesis with voice cloning"""

    def __init__(self, voice_profile_path: str = None):
        self.model = personaplex.load_model()
        self.voice_profile = personaplex.load_voice(voice_profile_path)

    async def synthesize(self, text: str, speed: float = 1.0) -> bytes:
        """Generate speech from text using cloned voice"""
        audio = self.model.synthesize(
            text=text,
            voice=self.voice_profile,
            speed=speed
        )
        return audio.to_wav()
```

### STEP 3: Update TTS Router
**File:** `spark_core/voice/tts_router.py`
```python
# Add to engine selection logic:
if PERSONAPLEX_AVAILABLE:
    TTS_ENGINE = "personaplex"  # Primary
elif CUDA_AVAILABLE and VRAM ≥ 4GB:
    TTS_ENGINE = "luxtts"       # Secondary
else:
    TTS_ENGINE = "edge-tts"     # Fallback
```

### STEP 4: Wake Word Configuration
**File:** `config/wakeword_models.yaml`
```yaml
wake_words:
  - name: "hey_spark"
    model: "models/openwakeword/hey_spark_v0.1.onnx"
    threshold: 0.5
    priority: 1
  - name: "spark"
    model: "models/openwakeword/spark_v0.1.onnx"
    threshold: 0.6
    priority: 2

default_wake_word: "hey_spark"
sample_rate: 16000
chunk_duration_ms: 100
```

### STEP 5: Update Wake Word Listener
**File:** `spark_core/voice/wakeword.py`
```python
class WakeWordListener:
    def __init__(self):
        self.models = self._load_all_models()  # Load all wake words
        self.running = False
        self.thread = None

    async def _load_all_models(self):
        """Load all configured wake word models"""
        config = load_yaml('config/wakeword_models.yaml')
        models = {}
        for ww_config in config['wake_words']:
            model = openwakeword.load_model(ww_config['model'])
            models[ww_config['name']] = {
                'model': model,
                'threshold': ww_config['threshold'],
                'priority': ww_config['priority']
            }
        return models

    async def _detect_wake_words(self, audio_chunk):
        """Check all wake words, return highest confidence"""
        results = {}
        for name, config in self.models.items():
            confidence = config['model'].predict(audio_chunk)
            if confidence > config['threshold']:
                results[name] = confidence
        return results
```

### STEP 6: Health Check System
**File:** `health_check.py`
```python
async def full_health_check():
    """Complete system diagnostics"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "systems": {}
    }

    # Check components
    results["systems"]["ollama"] = check_ollama_availability()
    results["systems"]["audio"] = check_audio_devices()
    results["systems"]["databases"] = check_database_files()
    results["systems"]["voice_models"] = check_voice_models()
    results["systems"]["memory"] = check_memory_usage()

    return results

# Usage in startup:
health = await full_health_check()
all_ok = all(s.get("status") == "OK" for s in health["systems"].values())
if not all_ok:
    print("⚠️ Warning: Some systems not ready")
    for sys, status in health["systems"].items():
        print(f"  - {sys}: {status['status']} ({status.get('detail', '')})")
```

### STEP 7: Comprehensive Test Suite
**File:** `test_spark_complete_verification.py`
```python
class TestSPARKComplete:
    """Complete SPARK system verification"""

    async def test_wake_word_detection(self):
        """Test wake word listener"""
        # Load audio samples
        # Test detection of "hey spark"
        # Test detection of "spark"
        # Verify WebSocket broadcast

    async def test_voice_synthesis(self):
        """Test TTS engines"""
        # Test Personaplex
        # Test LuxTTS
        # Test edge-tts fallback

    async def test_speech_recognition(self):
        """Test STT"""
        # Test faster-whisper with sample audio
        # Verify transcription accuracy

    async def test_ollama_connection(self):
        """Test local LLM"""
        # Check Ollama server availability
        # Test model loading
        # Test inference

    async def test_task_persistence(self):
        """Test Session 3 task system"""
        # CRUD operations x10
        # Database persistence
        # WebSocket broadcast

    async def test_end_to_end_workflow(self):
        """Test complete flow"""
        # Wake word → Command Bar
        # Voice input → STT
        # Intent → Router
        # LLM → Response
        # Response → TTS → Audio
```

### STEP 8: Startup Script
**File:** `spark_startup.py`
```python
async def main():
    print("🚀 Starting S.P.A.R.K. System...")

    # Phase 1: Health Check
    print("\n📋 Running system diagnostics...")
    health = await full_health_check()

    # Phase 2: Initialize Components
    print("\n🔧 Initializing components...")
    await initialize_ollama()
    await initialize_voice_engine()
    await initialize_wake_word_listener()
    await initialize_databases()

    # Phase 3: Start Server
    print("\n🌐 Starting FastAPI server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        loop="proactor"  # Windows ProactorEventLoop
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Expected Outcomes

### After Phase 1 (Voice Synthesis)
- ✅ Personaplex integrated
- ✅ Professional voice synthesis with cloned "Spark" voice
- ✅ Fallback chain: Personaplex → LuxTTS → edge-tts → pyttsx3

### After Phase 2 (Wake Word)
- ✅ "Hey Spark" wake word detection
- ✅ "Spark" wake word detection (shorter, for conversational flow)
- ✅ Priority-based detection (prefer "Hey Spark" if both detected)
- ✅ Confidence reporting and diagnostics

### After Phase 3 (HTTP Fix)
- ✅ Uvicorn HTTP requests working (or documented alternative)
- ✅ All API endpoints accessible
- ✅ Persistence layer working through HTTP

### After Phase 4 (Tests)
- ✅ 100+ test cases passing
- ✅ All systems verified
- ✅ E2E workflow tested
- ✅ Performance metrics collected

### After Phase 5 (Startup)
- ✅ Single command to start: `python spark_startup.py`
- ✅ Automatic diagnostics on startup
- ✅ Graceful error handling
- ✅ Clear status reporting

---

## Success Criteria

✅ **Project Complete When:**
1. User can say "Hey Spark" → wake word detected
2. Command bar opens → ready for voice input
3. User speaks command → STT transcribes
4. Spark processes command → local Ollama generates response
5. Personaplex synthesizes response with Spark's voice
6. Audio plays through speakers
7. Task/briefing management works via both voice and UI
8. All 100+ tests pass
9. No "threads" error on Windows
10. Complete documentation provided

---

## Timeline Estimate
- Phase 1 (Personaplex): 2-3 hours
- Phase 2 (Wake Words): 1-2 hours
- Phase 3 (HTTP Fix): 1-3 hours
- Phase 4 (Tests): 2-3 hours
- Phase 5 (Startup): 1 hour
- Phase 6 (Docs): 1 hour

**Total: ~8-13 hours for complete implementation**

---

## Critical Dependencies
- NVIDIA Personaplex: GitHub repo
- Ollama: Running locally on port 11434
- Audio devices: Working microphone + speakers
- Gemma 3:4b model: Downloaded by Ollama (auto on first run)
- Python 3.10+ (required for all async features)
