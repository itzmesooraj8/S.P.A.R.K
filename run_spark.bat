@echo off
title S.P.A.R.K - Complete Startup
color 0A
echo.
echo  ███████╗██████╗  █████╗ ██████╗ ██╗  ██╗
echo  ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝
echo  ███████╗██████╔╝███████║██████╔╝█████╔╝ 
echo  ╚════██║██╔═══╝ ██╔══██║██╔══██╗██╔═██╗ 
echo  ███████║██║     ██║  ██║██║  ██║██║  ██╗
echo  ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
echo.
echo  Smart Personal AI with Remote Knowledge
echo  ==========================================
echo.
pause

:: Start Backend in a new window
echo [1/2] Starting Backend Server...
start "SPARK Backend" cmd /k "cd /d %~dp0 && python run_server.py"

echo Waiting for backend to initialize...
timeout /t 5 /nobreak > nul

:: Start Frontend in a new window
echo [2/2] Starting Frontend Server...
start "SPARK Frontend" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo ====================================
echo  Starting SPARK Servers...
echo ====================================
echo.
echo Two windows have been opened:
echo   1. SPARK Backend (Python FastAPI)
echo   2. SPARK Frontend (Vite React)
echo.
echo Waiting for servers to be ready...
timeout /t 10 /nobreak > nul

echo.
echo Checking if servers are running...
python check_servers.py

echo.
echo You can close this window now.
echo The SPARK servers will continue running.
echo.
pause
