@echo off
title S.P.A.R.K Launcher
color 0B

echo.
echo  ====================================================
echo   S.P.A.R.K  ^|  Sovereign AI OS
echo  ====================================================
echo.

:: Activate virtual environment
call "%~dp0venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] venv not found. Run: python -m venv venv ^& pip install -r requirements.txt
    pause
    exit /b 1
)

:: Start Backend in a new window
echo [1/2] Starting backend (port 8000)...
start "SPARK Backend" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python run_server.py"

:: Small delay so backend starts first
timeout /t 3 /nobreak >nul

:: Start Frontend in a new window
echo [2/2] Starting frontend (port 8080)...
start "SPARK Frontend" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo  Both services are starting up:
echo    Backend  ^-^>  http://localhost:8000
echo    Frontend ^-^>  http://localhost:8080
echo    API Docs ^-^>  http://localhost:8000/docs
echo.
echo  Close this window or press any key to exit launcher.
pause >nul
