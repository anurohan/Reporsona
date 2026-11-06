@echo off
REM RePersona - backend launcher (called by START_REPERSONA.bat)
cd /d "%~dp0"
title RePersona Backend

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found on PATH. Install Python 3.11+ from https://python.org and re-run.
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [RePersona] First run: creating virtual environment and installing dependencies...
    echo [RePersona] This can take a couple of minutes. Please wait.
    python -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call ".venv\Scripts\activate.bat"
)

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo [RePersona] Backend starting on http://localhost:8000  (API docs at /docs)
echo [RePersona] Leave this window open. Close it to stop the backend.
echo.
uvicorn app.main:app --reload
pause
