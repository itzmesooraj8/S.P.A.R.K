@echo off
title S.P.A.R.K — Sovereign AI OS
color 0A

echo.
echo  ███████╗██████╗  █████╗ ██████╗ ██╗  ██╗
echo  ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝
echo  ███████╗██████╔╝███████║██████╔╝█████╔╝
echo  ╚════██║██╔═══╝ ██╔══██║██╔══██╗██╔═██╗
echo  ███████║██║     ██║  ██║██║  ██║██║  ██╗
echo  ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
echo  Sovereign AI OS — v3.0.0  (SOVEREIGN)
echo  ============================================
echo.

rem ── Resolve project root (the directory this .bat lives in) ─────────────────
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

rem ── Detect Python / venv ──────────────────────────────────────────────────
if exist "%ROOT%\venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%\venv\Scripts\python.exe"
    echo [OK] Python venv detected: %ROOT%\venv
) else if exist "%ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
    echo [OK] Python .venv detected: %ROOT%\.venv
) else (
    set "PYTHON=python"
    echo [WARN] No venv found — using system Python
)

rem ── Detect Node / npm ─────────────────────────────────────────────────────
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

rem ── Check .env ────────────────────────────────────────────────────────────
if not exist "%ROOT%\.env" (
    echo [WARN] .env not found — copying from .env.example
    copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo [WARN] Edit .env and set your API keys before using full features.
)

echo.
echo [1/3] Starting SPARK Core Backend  (port 8000)...
start "SPARK Core" cmd /k "cd /d "%ROOT%\spark_core" && "%PYTHON%" main.py"

echo [2/3] Starting Desktop Agent       (port 7700, local-only)...
start "SPARK Agent" cmd /k "cd /d "%ROOT%" && "%PYTHON%" spark_agent/server.py"

echo [3/3] Starting React HUD           (port 8080)...
start "SPARK HUD" cmd /k "cd /d "%ROOT%" && npm run dev"

echo.
echo  All systems launching. Give them 5-10 seconds to come online.
echo.
echo  Core Backend : http://localhost:8000/api/health
echo  API Docs     : http://localhost:8000/docs
echo  React HUD    : http://localhost:8080
echo  Desktop Agent: http://127.0.0.1:7700/agent/health
echo.
echo  Press any key to close this launcher (services continue running)
pause >nul
