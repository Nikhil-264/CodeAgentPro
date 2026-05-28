@echo off
title CodeAgent Pro - Launcher
color 0B
echo =======================================================================
echo               🤖 CodeAgent Pro: Agentic AI Coding Assistant 🤖
echo =======================================================================
echo.
echo  This script will automatically configure and run both your FastAPI
echo  backend and Vite/React frontend.
echo.
echo  Prerequisites:
echo  1. Make sure Docker Desktop is running (required for Execution Sandbox).
echo  2. Make sure Ollama is installed and running.
echo.
echo =======================================================================
echo  Step 1: Check and Install Backend Dependencies
echo =======================================================================
echo.
if not exist ".venv" (
    echo [WARNING] No .venv folder found. Creating virtual environment...
    python -m venv .venv
)
echo Installing python dependencies...
call .venv\Scripts\pip install -r backend\requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install backend dependencies. Please check Python installation.
    pause
    exit /b %ERRORLEVEL%
)
echo Backend dependencies installed successfully.
echo.
echo =======================================================================
echo  Step 2: Check and Install Frontend Dependencies
echo =======================================================================
echo.
cd frontend
if not exist "node_modules" (
    echo Installing frontend node modules...
    call npm install
) else (
    echo Frontend dependencies already installed.
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install frontend dependencies. Please check Node.js installation.
    cd ..
    pause
    exit /b %ERRORLEVEL%
)
cd ..
echo.
echo =======================================================================
echo  Step 3: Pull Ollama Model (deepseek-coder:6.7b)
echo =======================================================================
echo.
echo Checking if deepseek-coder:6.7b is pulled. You can skip this if you've done it.
choice /M "Do you want to run 'ollama pull deepseek-coder:6.7b' now?" /C YN /D N /T 5
if %ERRORLEVEL% equ 1 (
    echo Pulling deepseek-coder:6.7b...
    call ollama pull deepseek-coder:6.7b
)
echo.
echo =======================================================================
echo  Step 4: Launch Backend & Frontend Servers
echo =======================================================================
echo.
echo Starting FastAPI backend in a new window...
start "CodeAgent Pro - Backend API" cmd /k "cd backend && ..\.venv\Scripts\python main.py"

echo Starting React/Vite frontend in a new window...
start "CodeAgent Pro - Frontend UI" cmd /k "cd frontend && npm run dev"

echo.
echo =======================================================================
echo  ✅ Servers launched!
echo =======================================================================
echo  - React Frontend:  http://localhost:3000
echo  - Backend API:     http://localhost:8000
echo  - API Swagger Docs: http://localhost:8000/docs
echo =======================================================================
echo.
pause
