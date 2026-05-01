@echo off
title S.P.A.R.K. Master Boot Sequence
color 0b

echo ===================================================
echo   S.P.A.R.K. Sovereign AI OS - Master Boot Sequence
echo ===================================================
echo.

echo [INFO] Starting FastAPI WebSocket Bridge...
start "SPARK Bridge API" cmd /k "uvicorn api.server:app --port 8000"

echo [INFO] Starting S.P.A.R.K. Core Cognitive Loop...
start "SPARK Core Engine" cmd /k "python core\main.py"

echo [INFO] Waiting for services to initialize...
timeout /t 5 /nobreak >nul

echo [INFO] Launching React HUD...
if exist "spark src" (
    cd "spark src"
    start "SPARK React HUD" cmd /k "npm run dev"
    cd ..
    timeout /t 3 /nobreak >nul
    start http://localhost:5173
) else (
    echo [WARN] "spark src" folder not found. Skipping React HUD boot.
)

echo.
echo ===================================================
echo   BOOT COMPLETE. Press F9 to activate voice link.
echo ===================================================
pause
