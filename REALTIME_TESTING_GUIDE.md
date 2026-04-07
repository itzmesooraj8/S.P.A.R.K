# S.P.A.R.K Real-Time Features Testing Guide

## Overview

This guide will help you verify and test all real-time communication features in S.P.A.R.K, including:

- ✅ WebSocket connections for live data streaming
- ✅ Voice interfaces (wake word, STT, TTS)
- ✅ Real-time task and briefing synchronization
- ✅ Memory persistence and retrieval
- ✅ Frontend-backend integration

## Prerequisites

### 1. Backend Requirements
- Python 3.10+ installed
- All dependencies from `requirements.txt` installed
- Ollama running locally (for LLM features)

### 2. Frontend Requirements
- Node.js 18+ installed
- All dependencies from `package.json` installed

### 3. Services Running
Before testing, ensure these services are running:

```bash
# Terminal 1: Start Ollama (if using local LLM)
ollama serve

# Terminal 2: Start Backend
python run_server.py

# Terminal 3: Start Frontend
npm run dev
```

## Testing Methods

### Method 1: Automated Backend Tests

Run the comprehensive real-time features test suite:

```bash
# Using the batch file (Windows)
run_realtime_tests.bat

# Or directly with Python
pip install websockets httpx
python test_realtime_features.py
```

This will test:
- ✅ Backend health and version endpoints
- ✅ Memory system connectivity (ChromaDB, SQLite)
- ✅ All WebSocket namespaces (/ws/ai, /ws/system, /ws/combat, /ws/globe)
- ✅ Voice engine availability
- ✅ TTS synthesis
- ✅ Task CRUD operations
- ✅ Briefing CRUD operations
- ✅ WebSocket latency measurements

**Expected Output:**
```
====================================
  S.P.A.R.K Real-Time Features Test Suite
====================================

📋 Phase 1: Backend Service Verification
------------------------------------------------------------
✅ [Backend Health] PASS: Status: healthy
✅ [Backend Version] PASS: Version: X.X.X
✅ [Memory Stats] PASS: Entities: 0, Relations: 0
...

🎉 All critical tests passed! Real-time features are operational.
```

### Method 2: Frontend Integration Verification

Verify all frontend components and hooks are properly configured:

```bash
python verify_frontend_integration.py
```

This checks:
- ✅ WebSocket hooks (useVoiceEngine, useAIEvents, etc.)
- ✅ State stores (useTaskStore, useBriefingStore, etc.)
- ✅ API clients (tasks, briefings)
- ✅ HUD components
- ✅ Vite configuration for backend proxy
- ✅ Environment variable configuration

**Expected Output:**
```
====================================
  S.P.A.R.K Frontend Integration Verification
====================================

📋 Verifying WebSocket Hooks
------------------------------------------------------------
✅ Voice Engine Hook: Found at hooks/useVoiceEngine.ts
✅ Voice Engine WebSocket connection
...

🎉 All frontend integration checks passed!
```

### Method 3: Manual Browser Testing

1. **Open Browser**: Navigate to `http://localhost:5173`

2. **Test Voice Interface**:
   - Say "Hey SPARK" (wake word detection)
   - Or click the microphone button
   - Speak a command
   - Verify SPARK responds with voice

3. **Test Task Management**:
   - Open Task Panel from bottom dock
   - Create a new task
   - Verify it appears without refreshing (real-time sync)
   - Update/complete/delete tasks
   - Check persistence after browser refresh

4. **Test Chat Interface**:
   - Open Chat module
   - Send a message
   - Verify streaming response (token-by-token)
   - Check message history persists

5. **Test System Monitoring**:
   - Open System/Telemetry module
   - Verify live CPU, memory, disk metrics
   - Check metrics update in real-time

### Method 4: WebSocket Direct Testing

Use browser Developer Tools to test WebSocket connections:

```javascript
// Open Console in browser (F12)

// Test /ws/ai connection
const ws = new WebSocket('ws://localhost:8000/ws/ai');
ws.onmessage = (event) => {
    console.log('Received:', JSON.parse(event.data));
};
ws.onopen = () => {
    console.log('Connected to /ws/ai');
};
```

## Troubleshooting

### Backend Not Starting

**Issue**: `python run_server.py` fails

**Solutions**:
1. Check Python version: `python --version` (should be 3.10+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check port availability: Default is 8000, will auto-fallback to 8001, 8002
4. Check logs for specific error messages

### WebSocket Connection Fails

**Issue**: WebSocket tests fail with connection errors

**Solutions**:
1. Verify backend is running: `curl http://localhost:8000/api/health`
2. Check firewall isn't blocking WebSocket connections
3. Ensure CORS is enabled (already configured in main.py)
4. Check browser console for specific WebSocket errors

### Voice Features Not Working

**Issue**: Wake word detection or TTS not responding

**Solutions**:
1. **PyAudio not available**: Voice features will gracefully degrade, still usable via text
2. **Microphone permissions**: Browser will prompt for microphone access
3. **Wake word model**: Ensure openwakeword is installed (may not work on Python 3.12+)
4. **Check logs**: Look for voice engine initialization messages in backend logs

### Tasks/Briefings Not Persisting

**Issue**: Data lost after refresh

**Solutions**:
1. Check `spark_memory_db/` directory exists
2. Verify SQLite databases are created:
   - `personal_tasks.db`
   - `personal_briefings.db`
3. Check browser console for API errors
4. Verify Zustand stores are configured with persistence

### Frontend Not Connecting to Backend

**Issue**: API calls fail, "Network Error"

**Solutions**:
1. Check `.env` file has correct `VITE_API_BASE=http://localhost:8000`
2. Verify Vite proxy is configured in `vite.config.ts`
3. Check backend is running on expected port
4. Clear browser cache and restart dev server

## Performance Benchmarks

### Expected Performance Metrics

| Metric | Target | Acceptable |
|--------|--------|------------|
| WebSocket Latency | < 50ms | < 100ms |
| Voice Response Time | < 2s | < 5s |
| Task CRUD Operations | < 100ms | < 500ms |
| LLM First Token | < 1s | < 3s |
| Page Load Time | < 2s | < 5s |

### Measuring Performance

The automated test suite includes performance measurements:

```bash
python test_realtime_features.py
```

Look for:
```
📋 Phase 5: Performance Metrics
------------------------------------------------------------
✅ [WebSocket Latency] PASS: 45.23ms
⚠️  [Voice Response Time] Not measured (requires audio hardware)
```

## Real-Time Feature Checklist

Use this checklist to verify all features:

### Core Real-Time Features
- [ ] Backend starts without errors
- [ ] All 4 WebSocket namespaces accept connections
- [ ] WebSocket latency < 100ms
- [ ] Memory system (ChromaDB + SQLite) initialized
- [ ] Tasks persist across browser refresh
- [ ] Briefings persist across browser refresh

### Voice Features
- [ ] Wake word detection triggers ("Hey SPARK")
- [ ] Speech-to-text converts voice to text
- [ ] Text-to-speech generates audio
- [ ] Complete voice pipeline works end-to-end
- [ ] Voice features degrade gracefully without audio hardware

### Frontend Features
- [ ] All WebSocket hooks connect successfully
- [ ] Task panel shows real-time updates
- [ ] Chat messages stream token-by-token
- [ ] System metrics update in real-time
- [ ] No console errors in browser

### Integration Features
- [ ] Frontend receives backend WebSocket messages
- [ ] Backend receives frontend WebSocket messages
- [ ] Task create/update/delete syncs immediately
- [ ] Briefing create/update/delete syncs immediately
- [ ] Auto-reconnection works after connection loss

## Known Issues & Limitations

### Windows-Specific
- **HTTP Requests via Uvicorn**: Threading pool interaction on Windows may cause issues with direct HTTP requests to Uvicorn. Use frontend (Vite proxy) or TestClient for testing.
- **ProactorEventLoop**: Required for Windows, already configured in `run_server.py`

### Voice Engine
- **OpenWakeWord**: May not support Python 3.12+. Will gracefully disable if unavailable.
- **PyAudio**: Requires system audio drivers. Will fall back to text-only mode if unavailable.

### Performance
- **First LLM Response**: May take 2-5 seconds on first request (model loading)
- **ChromaDB Indexing**: Initial indexing of knowledge base may take 10-30 seconds

## Advanced Testing

### Load Testing WebSockets

Test multiple simultaneous connections:

```python
import asyncio
import websockets

async def stress_test():
    connections = []
    for i in range(100):
        ws = await websockets.connect('ws://localhost:8000/ws/ai')
        connections.append(ws)
    print(f"Created {len(connections)} connections")
    # Keep alive
    await asyncio.sleep(60)
    # Cleanup
    for ws in connections:
        await ws.close()

asyncio.run(stress_test())
```

### Memory Leak Testing

Monitor backend memory usage:

```bash
# Windows
while ($true) { Get-Process python | Select-Object Name,PM,VM; Start-Sleep 5 }

# Linux/Mac
watch -n 5 'ps aux | grep python'
```

## Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Look at backend console output for error messages
2. **Browser Console**: Check for JavaScript errors (F12)
3. **Verification Results**: Check `spark_verification_results.json` for system status
4. **Status Report**: Review `SPARK_STATUS_REPORT.md` for known issues
5. **E2E Tests**: Run `python test_phase6_e2e_final.py` for comprehensive validation

## Success Criteria

Your S.P.A.R.K installation is working correctly if:

✅ All automated tests pass (0 failures)
✅ Frontend verification shows 0 failed checks
✅ WebSocket latency < 100ms
✅ Tasks and briefings persist after browser refresh
✅ Voice pipeline works (or gracefully degrades)
✅ No errors in backend logs or browser console

---

**Last Updated**: 2026-04-07
**S.P.A.R.K Version**: Latest (check `/api/version`)
