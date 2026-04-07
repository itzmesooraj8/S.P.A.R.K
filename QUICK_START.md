# 🚀 S.P.A.R.K Quick Start Guide

## Option 1: Complete Automated Startup (Recommended)

**Double-click this file:**
```
run_spark.bat
```

This will:
1. ✅ Open two terminal windows (Backend and Frontend)
2. ✅ Start both servers automatically
3. ✅ Verify servers are running
4. ✅ Show you the URLs to access SPARK

**Wait for the message:** "✓ All servers are running!"

**Then open your browser to:** http://localhost:5173

---

## Option 2: Manual Startup (Advanced)

### Step 1: Start Backend
**Double-click:** `start_backend.bat`

Or manually in terminal:
```bash
cd C:\Users\itzme\Downloads\S.P.A.R.K
python run_server.py
```

**Wait for:** "🛸 [SPARK] All systems online. Sovereign AI OS ready."

### Step 2: Start Frontend
**Double-click:** `start_frontend.bat`

Or manually in terminal:
```bash
cd C:\Users\itzme\Downloads\S.P.A.R.K
npm run dev
```

**Wait for:** "Local: http://localhost:5173/"

### Step 3: Open Browser
Navigate to: http://localhost:5173

---

## Verify Servers Are Running

**Double-click:** `check_servers.py`

Or run:
```bash
python check_servers.py
```

This will check both backend and frontend and show their status.

---

## Expected Output

### Backend (Terminal 1)
```
✅ [SPARK] Loaded .env from C:\Users\itzme\Downloads\S.P.A.R.K\.env
🚀 [SPARK] Starting backend on 0.0.0.0:8000
🛸 [SPARK] Sovereign AI OS Initializing...
📂 [SPARK] Workspace root: ...
🧠 [SPARK] Knowledge graph memory online.
✅ [SPARK] Background monitor started.
🌍 [SPARK] Globe WS broadcaster started.
🔮 [SPARK] Cognitive loop started.
⏰ [SPARK] Task scheduler initialized.
🎖️  [SPARK] Commander agents online.
📚 [SPARK] Knowledge base file watcher active.
🎤 [SPARK] Wake word listener started in background thread.
📊 [SPARK] System history recorder started (10s intervals).
⚠️  [SPARK] Threat predictor feed started.
🛸 [SPARK] All systems online. Sovereign AI OS ready.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Frontend (Terminal 2)
```
> vite_react_shadcn_ts@0.0.0 dev
> vite

  VITE v5.4.19  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
  ➜  press h + enter to show help
```

---

## Access SPARK

### Main Interface
**URL:** http://localhost:5173

**Features Available:**
- 🎤 Voice commands ("Hey SPARK")
- 💬 Chat interface
- ✅ Task management
- 📊 System monitoring
- 🌍 Globe intelligence
- 🔐 Combat mode
- 🎵 Music player
- 🌐 Browser agent

### API Documentation
**URL:** http://localhost:8000/docs

Interactive API documentation (Swagger UI)

### API Health Check
**URL:** http://localhost:8000/api/health

Returns: `{"status": "healthy", "version": "..."}`

---

## Troubleshooting

### Backend Won't Start

**Error:** "Python not found"
- **Solution:** Install Python 3.10+ from python.org

**Error:** "Module not found"
- **Solution:** Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

**Error:** "Port 8000 already in use"
- **Solution:** The script will automatically try ports 8001, 8002
- Or manually change port in `.env`: `SPARK_PORT=8001`

### Frontend Won't Start

**Error:** "Node.js not found"
- **Solution:** Install Node.js 18+ from nodejs.org

**Error:** "Cannot find module"
- **Solution:** Install dependencies:
  ```bash
  npm install
  ```

**Error:** "Port 5173 already in use"
- **Solution:** Vite will automatically try next available port
- Or manually specify in `vite.config.ts`

### Can't Access in Browser

**Error:** "Cannot connect to localhost:5173"
- **Check:** Is frontend running? Look for "Local: http://localhost:5173/"
- **Check:** Firewall isn't blocking the port
- **Try:** http://127.0.0.1:5173 instead

**Error:** "API calls failing"
- **Check:** Is backend running on port 8000?
- **Check:** `.env` has `VITE_API_BASE=http://localhost:8000`
- **Test:** Open http://localhost:8000/api/health

### Voice Not Working

**Warning:** "PyAudio not available"
- **Solution:** This is OK! SPARK will work with text input
- **Optional:** Install PyAudio for voice features
  ```bash
  pip install pyaudio
  ```

**Warning:** "Wake word model not loaded"
- **Solution:** This is OK! Use microphone button instead
- **Optional:** Install openwakeword (Python <3.12):
  ```bash
  pip install openwakeword
  ```

---

## Stopping SPARK

### Option 1: Close Windows
Simply close both terminal windows:
- "SPARK Backend"
- "SPARK Frontend"

### Option 2: Ctrl+C
In each terminal window, press `Ctrl+C`

### Option 3: Task Manager (Emergency)
1. Open Task Manager (Ctrl+Shift+Esc)
2. Find "python.exe" and "node.exe" processes
3. End tasks

---

## Testing After Startup

### Quick Test Checklist

1. **Backend Health:**
   ```bash
   curl http://localhost:8000/api/health
   ```
   Should return: `{"status":"healthy"}`

2. **Frontend Loaded:**
   - Open http://localhost:5173
   - See SPARK HUD interface

3. **Voice Test:**
   - Say "Hey SPARK" or click microphone
   - Speak a command
   - Get a response

4. **Task Test:**
   - Open Task Panel
   - Create a new task
   - See it appear immediately

5. **Real-Time Test:**
   - Open System Monitor
   - Watch live CPU/memory metrics

### Automated Testing

Run comprehensive tests:
```bash
# Backend real-time features
python test_realtime_features.py

# Frontend integration
python verify_frontend_integration.py

# Full E2E tests
python test_phase6_e2e_final.py
```

---

## Performance Tips

### For Faster Startup
1. Keep Ollama running in background:
   ```bash
   ollama serve
   ```

2. Preload model:
   ```bash
   ollama run gemma3:4b
   ```

### For Better Performance
1. Use local LLM (Ollama) instead of cloud API
2. Close unused modules in SPARK interface
3. Limit concurrent WebSocket connections

---

## Next Steps

### First Time Using SPARK?
1. **Try voice:** Say "Hey SPARK, what can you do?"
2. **Create a task:** "Add 'test SPARK features' to my tasks"
3. **Check weather:** "What's the weather like?"
4. **Ask questions:** "Tell me about yourself"

### Want to Customize?
- Edit `.env` for API keys and settings
- Modify `config/settings.yaml` for SPARK behavior
- Add knowledge to `knowledge_base/` directory

### Want to Develop?
- See `REALTIME_TESTING_GUIDE.md` for testing
- Check `README.md` for architecture details
- Review `SPARK_STATUS_REPORT.md` for current status

---

## Support

### Check Status
```bash
python check_servers.py
```

### View Logs
- **Backend:** Look at terminal window "SPARK Backend"
- **Frontend:** Look at terminal window "SPARK Frontend"
- **Browser:** Open Developer Tools (F12) → Console

### Common Issues
See `REALTIME_TESTING_GUIDE.md` for comprehensive troubleshooting

---

**Last Updated:** 2026-04-07
**SPARK Version:** Check http://localhost:8000/api/version

🎉 **Enjoy using SPARK!**
