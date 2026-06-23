@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   ATS Checker Personal - Setup Script
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Download Python 3.12+ from https://python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Download Node.js from https://nodejs.org
    pause
    exit /b 1
)
for /f %%v in ('node --version') do set NODEVER=%%v
echo [OK] Node.js %NODEVER% found

echo.
echo ============================================================
echo   Setting up Backend (Python)
echo ============================================================
echo.

cd backend

:: Create venv
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

:: Activate and install
echo Installing Python dependencies (this may take a few minutes)...
call venv\Scripts\activate.bat

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
echo [OK] Python dependencies installed

:: Create data directories
if not exist "data\uploads" mkdir data\uploads
echo [OK] Data directories created

:: Download NLP models
echo.
echo Downloading NLP models (spaCy + SentenceTransformers)...
echo This is ~200MB and will take a few minutes on first run.
python setup_nlp.py
if errorlevel 1 (
    echo [WARNING] NLP model download had issues. Models will download on first use.
)

call venv\Scripts\deactivate.bat
cd ..

echo.
echo ============================================================
echo   Setting up Frontend (Node.js)
echo ============================================================
echo.

cd frontend
echo Installing Node.js dependencies...
npm install
if errorlevel 1 (
    echo [ERROR] Failed to install Node.js dependencies
    pause
    exit /b 1
)
echo [OK] Node.js dependencies installed
cd ..

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo To start the application, run: start.bat
echo.
echo The application will be available at:
echo   Frontend: http://localhost:3000
echo   Backend API: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
pause
