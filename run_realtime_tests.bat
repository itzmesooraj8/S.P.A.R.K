@echo off
echo ====================================
echo S.P.A.R.K Real-Time Test Runner
echo ====================================
echo.

echo [1/3] Installing dependencies...
pip install websockets httpx --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Checking if backend is running...
curl -s http://localhost:8000/api/health > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Backend doesn't appear to be running!
    echo Please start the backend first with: python run_server.py
    echo.
    pause
    exit /b 1
)

echo Backend is running ✓
echo.
echo [3/3] Running real-time feature tests...
echo.
python test_realtime_features.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Tests completed with errors
    pause
    exit /b 1
)

echo.
echo Tests completed successfully!
pause
