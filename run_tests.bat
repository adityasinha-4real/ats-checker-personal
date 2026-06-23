@echo off
echo ============================================================
echo   ATS Checker - Running Test Suite
echo ============================================================
echo.

cd backend
call venv\Scripts\activate.bat

echo Running all tests with verbose output...
echo.
python -m pytest tests/ -v --tb=short 2>&1

echo.
echo Test run complete.
call venv\Scripts\deactivate.bat
cd ..
pause
