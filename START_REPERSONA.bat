@echo off
REM ============================================================
REM   RePersona - ONE-CLICK LAUNCHER
REM   Double-click this file to start the whole project.
REM   (First run installs dependencies automatically.)
REM ============================================================
cd /d "%~dp0"
title RePersona Launcher
color 0B

echo.
echo   ============================================
echo      RePersona  -  starting up...
echo   ============================================
echo.
echo   Two windows will open (Backend + Frontend).
echo   The first launch installs dependencies and
echo   may take a few minutes. Keep both windows open.
echo.

REM --- launch backend and frontend in their own windows ---
start "RePersona Backend"  cmd /k call "%~dp0backend\run_backend.bat"
start "RePersona Frontend" cmd /k call "%~dp0frontend\run_frontend.bat"

REM --- wait for the servers, then open the browser ---
echo   Waiting for the servers to come up...
REM 20s on a normal run; give the first-time install more time by
REM waiting until the frontend port answers (best-effort loop).
set /a tries=0
:waitloop
timeout /t 3 /nobreak >nul
set /a tries+=1
powershell -NoProfile -Command "try{ (New-Object Net.Sockets.TcpClient('127.0.0.1',3000)).Close(); exit 0 } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 goto ready
if %tries% GEQ 60 goto ready
goto waitloop

:ready
echo   Opening http://localhost:3000 ...
start "" http://localhost:3000
echo.
echo   RePersona is running. You can close THIS window.
echo   To stop the app, close the Backend and Frontend windows.
timeout /t 4 /nobreak >nul
exit /b 0
