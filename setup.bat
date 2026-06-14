@echo off
echo "=================================================="
echo "  YouTube to Presentation Generator Setup"
echo "=================================================="
echo.

set VENV_DIR=.venv

if exist "%VENV_DIR%" (
    echo "[INFO] Virtual environment already exists."
) else (
    echo "[1/3] Creating Python virtual environment (.venv)..."
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo "[ERROR] Failed to create virtual environment."
        pause
        exit /b 1
    )
)

echo "[2/3] Installing dependencies..."
"%VENV_DIR%\Scripts\python" -m pip install --upgrade pip
if errorlevel 1 echo "[WARNING] Failed to upgrade pip."

"%VENV_DIR%\Scripts\pip" install -r requirements.txt --prefer-binary
if errorlevel 1 (
    echo "[ERROR] Failed to install dependencies."
    pause
    exit /b 1
)

"%VENV_DIR%\Scripts\python" -m playwright install
if errorlevel 1 (
    echo "[ERROR] Failed to install Playwright browsers."
    pause
    exit /b 1
)

echo.
echo "[3/3] Installing Playwright browsers..."
"%VENV_DIR%\Scripts\python" -m playwright install
if errorlevel 1 (
    echo "[ERROR] Failed to install Playwright browsers."
    pause
    exit /b 1
)

echo.
echo "[4/4] Downloading yt-dlp.exe..."
set YT_DLP_URL=https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
set YT_DLP_PATH=.\yt-dlp.exe

if exist "%YT_DLP_PATH%" (
    echo "[INFO] yt-dlp.exe already exists. Skipping download."
) else (
    echo "[INFO] Downloading yt-dlp.exe from GitHub releases..."
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%YT_DLP_URL%' -OutFile '%YT_DLP_PATH%' -ErrorAction Stop}" >nul 2>&1
    if errorlevel 1 (
        echo "[WARNING] Failed to download yt-dlp.exe automatically."
        echo "[INFO] You can download it manually from:"
        echo "       https://github.com/yt-dlp/yt-dlp/releases/latest"
        echo "       (Download yt-dlp.exe and place it in the project root directory)"
    ) else (
        echo "[INFO] yt-dlp.exe downloaded successfully."
        if exist "%YT_DLP_PATH%" (
            echo "[INFO] Location: %cd%\%YT_DLP_PATH%"
        )
    )
)

echo.
echo "[5/5] Gemini API Setup Guide"
echo "[INFO] To enable slide summarization with Gemini AI, set GEMINI_API_KEY:"
echo "       1. Get your API key from: https://aistudio.google.com/apikey"
echo "       2. Windows: setx GEMINI_API_KEY your-api-key-here"
echo "       3. Or set in PowerShell: $env:GEMINI_API_KEY='your-api-key-here'"

pip install uvicorn
pip install fastapi
pip install opencv-python
pip install youtube-transcript-api
pip install yt-dlp
pip install python-pptx
pip install python-dotenv

echo.
echo "=================================================="
echo "  Setup complete! You can now run run.bat"
echo "=================================================="
pause
