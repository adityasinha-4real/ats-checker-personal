@echo off
echo ============================================================
echo   ATS Checker Personal - Starting Application
echo ============================================================
echo.

:: Start Backend
echo Starting FastAPI backend on http://localhost:8000 ...
start "ATS Checker - Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak >nul

:: Start Frontend
echo Starting Next.js frontend on http://localhost:3000 ...
start "ATS Checker - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================================
echo   Application starting...
echo ============================================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo Both windows will open. Wait ~10 seconds for full startup.
echo Close both windows to stop the application.
echo.

:: Open browser after delay
timeout /t 8 /nobreak >nul
start http://localhost:3000
