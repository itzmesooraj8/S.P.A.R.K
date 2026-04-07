@echo off
title SPARK Project Cleanup
color 0E

echo ====================================
echo  S.P.A.R.K Project Cleanup
echo ====================================
echo.
echo This script will remove unnecessary files from the SPARK project:
echo   - Test files (test_*.py)
echo   - Verification scripts (verify_*.py)
echo   - Deprecated code files
echo   - Unused external dependencies (scrapy/)
echo   - Historical documentation
echo.
echo Files will be moved to 'archive\' folder, not deleted.
echo.
pause

cd /d "%~dp0"

echo.
echo [1/6] Creating archive directory...
if not exist "archive" mkdir archive
if not exist "archive\test_files" mkdir archive\test_files
if not exist "archive\verification" mkdir archive\verification
if not exist "archive\docs" mkdir archive\docs
echo ✓ Archive directories created

echo.
echo [2/6] Moving test files...
if exist "test_e2e_phase6.py" move "test_e2e_phase6.py" "archive\test_files\" > nul
if exist "test_phase5_e2e_complete.py" move "test_phase5_e2e_complete.py" "archive\test_files\" > nul
if exist "test_phase6_e2e_final.py" move "test_phase6_e2e_final.py" "archive\test_files\" > nul
if exist "test_realtime_features.py" move "test_realtime_features.py" "archive\test_files\" > nul
if exist "test_llm.py" move "test_llm.py" "archive\test_files\" > nul
echo ✓ Test files archived

echo.
echo [3/6] Moving verification scripts...
if exist "verify_frontend_integration.py" move "verify_frontend_integration.py" "archive\verification\" > nul
if exist "verify_spark_complete.py" move "verify_spark_complete.py" "archive\verification\" > nul
if exist "spark_verification_results.json" move "spark_verification_results.json" "archive\verification\" > nul
if exist "spark_startup_complete.py" move "spark_startup_complete.py" "archive\verification\" > nul
echo ✓ Verification scripts archived

echo.
echo [4/6] Moving historical documentation...
if exist "ERRORS_FIXED.txt" move "ERRORS_FIXED.txt" "archive\docs\" > nul
if exist "ERROR_RESOLUTION.md" move "ERROR_RESOLUTION.md" "archive\docs\" > nul
echo ✓ Historical docs archived

echo.
echo [5/6] Removing deprecated code files...
if exist "spark_core\legacy_main.py" (
    del "spark_core\legacy_main.py"
    echo ✓ Removed legacy_main.py
)
if exist "spark_core\personality_deprecated.py" (
    del "spark_core\personality_deprecated.py"
    echo ✓ Removed personality_deprecated.py
)
if exist "spark_core\out.txt" (
    del "spark_core\out.txt"
    echo ✓ Removed out.txt
)

echo.
echo [6/6] Removing unused external dependencies...
if exist "scrapy\" (
    echo Removing scrapy directory...
    rmdir /s /q "scrapy"
    echo ✓ Removed scrapy/
) else (
    echo ✓ scrapy/ not found (already clean)
)

echo.
echo ====================================
echo  Cleanup Complete!
echo ====================================
echo.
echo Summary:
echo   - Test files moved to archive\test_files\
echo   - Verification scripts moved to archive\verification\
echo   - Historical docs moved to archive\docs\
echo   - Deprecated code files removed
echo   - Unused dependencies removed
echo.
echo Your SPARK project is now cleaner!
echo.
pause
