@echo off
REM Checks whether live Wikipedia data collection works on this machine.
REM Usage: double-click, or:  CHECK_LIVE_DATA.bat "Steve Jobs"
cd /d "%~dp0backend"
if not exist ".venv" (
    echo [!] Backend not set up yet. Run START_REPERSONA.bat once first.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
set "NAME=%~1"
if "%NAME%"=="" set "NAME=Albert Einstein"
python check_wikipedia.py "%NAME%"
echo.
pause
