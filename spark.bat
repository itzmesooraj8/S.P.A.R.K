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

:: Ensure we are exactly in the S.P.A.R.K root folder
cd /d "%~dp0"

:: [THE FIX] Set the Python Path to the root folder so it can see 'audio' and 'core'
set PYTHONPATH=%cd%

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: [THE FIX] Run main as a module, not a raw file path
python -m core.main

pause
