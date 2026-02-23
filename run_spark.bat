@echo off
echo Starting S.P.A.R.K. System (v2)...
echo --------------------------------
echo [1/2] Starting SPARK Backend Core...
cd spark_core
start cmd /k "python main.py"

echo [2/2] Starting SPARK React HUD...
cd ..
start cmd /k "npm run dev"

echo S.P.A.R.K. Initialization complete! Desktop HUD and Backend are now running.
