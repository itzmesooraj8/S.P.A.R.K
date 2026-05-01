@echo off
setlocal EnableDelayedExpansion
title S.P.A.R.K. — Sovereign Personal AI Runtime Kernel

:: ============================================================
:: S.P.A.R.K. MASTER BOOT SEQUENCE
:: Launches all services in the correct order:
::   1. FastAPI WebSocket Bridge  (api/server.py)
::   2. S.P.A.R.K. Cognitive Core (core/main.py)
::   3. React HUD Frontend         (spark src/)
:: Phase 03: Scheduler + Clipboard Watcher auto-start via main.py
:: Phase 04: Wake Word Engine      (core/wake_word.py via main.py)
:: ============================================================

:: ANSI color support (Windows 10 1511+)
for /f "tokens=*" %%i in ('ver') do set WIN_VER=%%i

echo.
echo  [96m ███████╗██████╗  █████╗ ██████╗ ██╗  ██╗[0m
echo  [96m ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝[0m
echo  [96m ███████╗██████╔╝███████║██████╔╝█████╔╝ [0m
echo  [96m ╚════██║██╔═══╝ ██╔══██║██╔══██╗██╔═██╗ [0m
echo  [96m ███████║██║     ██║  ██║██║  ██║██║  ██╗[0m
echo  [96m ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝[0m
echo.
echo  [33m  Sovereign Personal AI Runtime Kernel[0m
echo  [2m  Phase 03 — Proactive Agency Engine Active[0m
echo.

:: ── ENV CHECK ────────────────────────────────────────────────
if not exist ".env" (
    echo  [91m[BOOT] ERROR: .env file not found.[0m
    echo  [2m  Copy .env.example to .env and fill in your GROQ_API_KEY.[0m
    pause
    exit /b 1
)

:: ── PYTHON CHECK ─────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [91m[BOOT] ERROR: Python not found in PATH.[0m
    echo  [2m  Install Python 3.11+ and ensure it is on your PATH.[0m
    pause
    exit /b 1
)

:: ── NODE CHECK ───────────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo  [91m[BOOT] ERROR: Node.js not found in PATH.[0m
    echo  [2m  Install Node.js 18+ from https://nodejs.org[0m
    pause
    exit /b 1
)

:: ── VENV ACTIVATION (optional, uncomment if using venv) ──────
:: if exist "venv\Scripts\activate.bat" (
::     echo  [2m[BOOT] Activating virtual environment...[0m
::     call venv\Scripts\activate.bat
:: )

:: ── DEPENDENCY CHECK ─────────────────────────────────────────
echo  [2m[BOOT] Checking Python dependencies...[0m
python -c "import fastapi, groq, chromadb, apscheduler, pyperclip" >nul 2>&1
if errorlevel 1 (
    echo  [33m[BOOT] Installing missing dependencies...[0m
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo  [91m[BOOT] pip install failed. Check requirements.txt[0m
        pause
        exit /b 1
    )
)
echo  [92m[BOOT] Dependencies OK[0m

:: ── HUD DEPENDENCY CHECK ─────────────────────────────────────
if exist "spark src\node_modules" (
    echo  [92m[BOOT] HUD node_modules OK[0m
) else (
    echo  [33m[BOOT] Installing HUD dependencies (first run)...[0m
    cd "spark src"
    call npm install --silent
    if errorlevel 1 (
        echo  [91m[BOOT] npm install failed.[0m
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo  [92m[BOOT] HUD dependencies installed.[0m
)

echo.
echo  [96m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[0m
echo  [33m  INITIATING BOOT SEQUENCE...[0m
echo  [96m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[0m
echo.

:: ── STEP 1: FastAPI WebSocket Bridge ─────────────────────────
echo  [96m[01/03][0m Starting WebSocket Bridge...
start "SPARK-API" /min cmd /c "python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload 2>&1 | python -c ""import sys; [print('[API] ' + l, end='') for l in sys.stdin]"" 2>logs\api.log"
timeout /t 2 /nobreak >nul
echo        [92m✓ Bridge live on ws://127.0.0.1:8000/ws[0m

:: ── STEP 2: Cognitive Core (includes scheduler + watcher) ────
echo  [96m[02/03][0m Starting Cognitive Core + Phase 03 Daemons...
start "SPARK-CORE" /min cmd /c "python core/main.py 2>&1 | python -c ""import sys; [print('[CORE] ' + l, end='') for l in sys.stdin]"" 2>logs\core.log"
timeout /t 2 /nobreak >nul
echo        [92m✓ Cognitive core + scheduler + clipboard watcher active[0m

:: ── STEP 3: React HUD ────────────────────────────────────────
echo  [96m[03/03][0m Launching React HUD...
start "SPARK-HUD" /min cmd /c "cd ""spark src"" && npm run dev 2>&1 | python -c ""import sys; [print('[HUD] ' + l, end='') for l in sys.stdin]"" 2>..\logs\hud.log"
timeout /t 3 /nobreak >nul
echo        [92m✓ HUD launching on http://localhost:5173[0m

:: ── LOG DIRECTORY ────────────────────────────────────────────
if not exist "logs" mkdir logs

echo.
echo  [96m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[0m
echo  [92m  ALL SYSTEMS NOMINAL[0m
echo  [96m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[0m
echo.
echo  [33m  HUD[0m          http://localhost:5173
echo  [33m  API Docs[0m     http://localhost:8000/docs
echo  [33m  WebSocket[0m    ws://localhost:8000/ws
echo.
echo  [2m  Phase 03 Services:[0m
echo  [2m  • Scheduler (APScheduler) — remind me in N minutes[0m
echo  [2m  • Clipboard Watcher — contextual URL/code assistance[0m
echo  [2m  • Wake Word Engine — say 'Hey SPARK' (if openWakeWord installed)[0m
echo  [2m  • CLI Access — run: python spark_cli.py[0m
echo.
echo  [2m  Press any key to open HUD in browser...[0m
timeout /t 4 /nobreak >nul
start http://localhost:5173

echo.
echo  [2m  Logs: logs\api.log | logs\core.log | logs\hud.log[0m
echo  [2m  To stop all services: close the SPARK-API, SPARK-CORE, SPARK-HUD windows[0m
echo  [2m  or run: spark_stop.bat[0m
echo.
echo  [96m  S.P.A.R.K. is online.[0m
echo.
