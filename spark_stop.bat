@echo off
title S.P.A.R.K. — Shutdown

echo.
echo  [33m  S.P.A.R.K. SHUTDOWN SEQUENCE[0m
echo.

echo  [2m  Stopping SPARK-CORE...[0m
taskkill /FI "WindowTitle eq SPARK-CORE" /F >nul 2>&1

echo  [2m  Stopping SPARK-API...[0m
taskkill /FI "WindowTitle eq SPARK-API" /F >nul 2>&1

echo  [2m  Stopping SPARK-HUD...[0m
taskkill /FI "WindowTitle eq SPARK-HUD" /F >nul 2>&1

:: Also kill any stray uvicorn/vite/node processes on the known ports
echo  [2m  Freeing ports 8000 and 5173...[0m
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo  [92m  All SPARK services stopped.[0m
echo.
