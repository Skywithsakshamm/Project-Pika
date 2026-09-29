@echo off
title Selvie AI Desktop Assistant
color 0b

echo ===================================================
echo     SELVIE - YOUR PERSONAL AI DESKTOP ASSISTANT
echo         Voice-First Companion for Saksham
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo [2/3] Checking Ollama LLM service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [NOTE] Ollama is not currently active.
    echo Starting Ollama in background...
    start "" /b ollama serve
    timeout /t 2 /nobreak >nul
) else (
    echo [OK] Ollama is ready.
)

echo [3/3] Launching Selvie Floating Assistant...
python run_selvie.py %*

if %errorlevel% neq 0 (
    echo.
    echo Selvie closed with an error. Running backend-only fallback...
    python run_selvie.py --backend-only
    pause
)
