@echo off
REM RePersona - frontend launcher (called by START_REPERSONA.bat)
cd /d "%~dp0"
title RePersona Frontend

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js/npm not found on PATH. Install Node 18+ from https://nodejs.org and re-run.
    echo.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [RePersona] First run: installing frontend dependencies with npm install...
    echo [RePersona] This can take a few minutes. Please wait.
    call npm install
)

if not exist ".env.local" copy ".env.example" ".env.local" >nul

echo.
echo [RePersona] Frontend starting on http://localhost:3000
echo [RePersona] Leave this window open. Close it to stop the frontend.
echo.
call npm run dev
pause
