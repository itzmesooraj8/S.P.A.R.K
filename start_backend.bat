@echo off
echo ====================================
echo Starting S.P.A.R.K Backend Server
echo ====================================
echo.

cd /d "%~dp0"

echo Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

echo.
echo Starting backend on port 8000 (or next available)...
echo.
echo NOTE: Keep this window open! The backend will run here.
echo       To stop the backend, press Ctrl+C
echo.

python run_server.py

pause
