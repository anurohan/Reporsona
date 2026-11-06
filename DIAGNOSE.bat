@echo off
REM ============================================================
REM   RePersona - DIAGNOSTIC
REM   Runs every setup/build/test step and writes a full report
REM   to diagnose_report.txt. Paste that file back for help.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "LOG=%~dp0diagnose_report.txt"
color 0E

echo RePersona diagnostic report > "%LOG%"
echo Generated: %DATE% %TIME% >> "%LOG%"

call :section "TOOL VERSIONS"
echo --- python --- >> "%LOG%" 2>&1
python --version >> "%LOG%" 2>&1
echo --- node --- >> "%LOG%" 2>&1
node --version >> "%LOG%" 2>&1
echo --- npm --- >> "%LOG%" 2>&1
call npm --version >> "%LOG%" 2>&1

call :section "BACKEND: create venv + install deps"
cd /d "%~dp0backend"
if not exist ".venv" (
    python -m venv .venv >> "%LOG%" 2>&1
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >> "%LOG%" 2>&1
pip install -r requirements.txt >> "%LOG%" 2>&1
if not exist ".env" copy ".env.example" ".env" >nul 2>&1

call :section "BACKEND: import check (does the app load?)"
python -c "import app.main; print('BACKEND IMPORT: OK')" >> "%LOG%" 2>&1

call :section "BACKEND: pytest"
pytest -q >> "%LOG%" 2>&1

call :section "FRONTEND: npm install"
cd /d "%~dp0frontend"
if not exist ".env.local" copy ".env.example" ".env.local" >nul 2>&1
call npm install >> "%LOG%" 2>&1

call :section "FRONTEND: TypeScript typecheck (tsc --noEmit)"
call npx --yes tsc --noEmit >> "%LOG%" 2>&1

call :section "FRONTEND: production build (next build)"
call npm run build >> "%LOG%" 2>&1

call :section "DIAGNOSTIC COMPLETE"

echo.
echo ============================================================
echo   Report saved to:
echo     %LOG%
echo ============================================================
echo.
echo ----- BEGIN REPORT (copy everything below) -----
echo.
type "%LOG%"
echo.
echo ----- END REPORT -----
echo.
echo Copy the report above (or open diagnose_report.txt) and paste it back.
pause
exit /b 0

:section
echo. >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo == %~1 >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo.
echo [RePersona]  %~1 ...
goto :eof
