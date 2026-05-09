@echo off
setlocal
title S.P.A.R.K. Launcher

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Missing virtual environment at .venv\Scripts\python.exe
    exit /b 1
)

echo [INFO] Starting S.P.A.R.K. daemon...
start "SPARK-DAEMON" /min "%~dp0.venv\Scripts\python.exe" "%~dp0spark_daemon.py"
echo [INFO] Daemon launched in a separate window.
exit /b 0
