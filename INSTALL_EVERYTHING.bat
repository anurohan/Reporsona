@echo off
REM ============================================================
REM   RePersona - INSTALL EVERYTHING (one shot)
REM   Python AI deps + Ollama + Tesseract + FFmpeg + Llama model
REM   Uses winget (built into Windows 11). UAC prompts may appear.
REM   Large download (~3-4 GB total). Needs internet.
REM ============================================================
setlocal
cd /d "%~dp0"
title RePersona - install everything
color 0B

echo.
echo ============================================================
echo   STEP 1/3  -  Python AI stack (embeddings, FAISS, Whisper, OCR libs)
echo ============================================================
cd /d "%~dp0backend"
if not exist ".venv" python -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements-full.txt
cd /d "%~dp0"

echo.
echo ============================================================
echo   STEP 2/3  -  System tools via winget (Ollama, Tesseract, FFmpeg)
echo ============================================================
where winget >nul 2>nul
if errorlevel 1 (
    echo [!] winget not found. Open Microsoft Store, update "App Installer",
    echo     then re-run this file. Skipping system tools for now.
) else (
    echo   Installing Ollama...
    winget install --id Ollama.Ollama -e --silent --accept-source-agreements --accept-package-agreements
    echo   Installing Tesseract-OCR...
    winget install --id UB-Mannheim.TesseractOCR -e --silent --accept-source-agreements --accept-package-agreements
    echo   Installing FFmpeg...
    winget install --id Gyan.FFmpeg -e --silent --accept-source-agreements --accept-package-agreements
)

echo.
echo ============================================================
echo   STEP 3/3  -  Download the Llama model (for human-like answers)
echo ============================================================
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if exist "%OLLAMA_EXE%" (
    "%OLLAMA_EXE%" pull llama3.2:3b
) else (
    where ollama >nul 2>nul && (ollama pull llama3.2:3b) || (
        echo [i] Ollama CLI not on PATH in THIS window yet.
        echo     Open a NEW terminal after this finishes and run:
        echo         ollama pull llama3.2:3b
    )
)

echo.
echo ============================================================
echo   DONE.
echo   1) Close any old Backend/Frontend windows.
echo   2) Run START_REPERSONA.bat again.
echo   3) First real question downloads the embedding model (~470 MB, once).
echo   Check /settings in the app: embedding_backend should say
echo   'sentence-transformers' and vector_store 'FaissVectorStore'.
echo ============================================================
echo.
pause
