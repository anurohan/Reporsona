@echo off
REM ============================================================
REM   RePersona - install FULL-POWER dependencies
REM   (semantic embeddings + FAISS + Whisper + OCR libs)
REM   NOTE: large download (~2-3 GB incl. PyTorch). Needs internet.
REM ============================================================
cd /d "%~dp0backend"
color 0B

if not exist ".venv" (
    echo [!] Backend not set up yet. Run START_REPERSONA.bat once first, then re-run this.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo.
echo [RePersona] Installing full AI stack into the backend venv...
echo [RePersona] This can take several minutes (PyTorch is big). Please wait.
echo.
python -m pip install --upgrade pip
pip install -r requirements-full.txt
set INSTALL_RC=%ERRORLEVEL%

echo.
echo ============================================================
if "%INSTALL_RC%"=="0" (
    echo   Python AI deps installed OK.
) else (
    echo   Some Python deps failed to install ^(exit %INSTALL_RC%^).
    echo   Paste the errors back for help. The app still runs on fallbacks.
)
echo ============================================================
echo.
echo   STILL NEEDED (these are NOT pip packages):
echo.
echo   1) OLLAMA  (for real, human-like generated answers)
echo        - Download + install from:  https://ollama.com/download
echo        - Then in a terminal run:   ollama pull llama3.2:3b
echo        - Keep Ollama running; the app auto-detects it (LLM_PROVIDER=auto).
echo.
echo   2) TESSERACT-OCR  (only if you want OCR on uploaded images)
echo        - Windows installer (UB Mannheim build):
echo          https://github.com/UB-Mannheim/tesseract/wiki
echo        - Add its install folder to your PATH, then restart the terminal.
echo.
echo   3) FFmpeg  (recommended for Whisper on some audio/video files)
echo        - https://www.gyan.dev/ffmpeg/builds/  (add /bin to PATH)
echo.
echo   After this, close old server windows and run START_REPERSONA.bat again.
echo   First real question will download the embedding model (~470 MB, once).
echo.
pause
