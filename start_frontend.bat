@echo off
echo ====================================
echo Starting S.P.A.R.K Frontend Server
echo ====================================
echo.

cd /d "%~dp0"

echo Checking Node.js installation...
node --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

echo.
echo Starting frontend dev server...
echo.
echo NOTE: Keep this window open! The frontend will run here.
echo       To stop the frontend, press Ctrl+C
echo.

npm run dev

pause
