@echo off
:: S.P.A.R.K. Enterprise Launcher
title S.P.A.R.K. Core Initialization

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] Administrator privileges confirmed.
    goto :START_SPARK
) else (
    echo [WARNING] Administrative rights required for Hotkey Hooks. Requesting elevation...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %~dp0 && %~s0' -Verb RunAs"
    exit /b
)

:START_SPARK
echo [INFO] Booting S.P.A.R.K. V1...
cd /d %~dp0
call .venv\Scripts\activate.bat
python core/main.py
pause
