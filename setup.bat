@echo off
setlocal EnableExtensions

cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Failed to open the project directory.
    pause
    exit /b 1
)

echo ==================================================
echo   YouTube to Presentation Generator Setup
echo ==================================================
echo.

set "VENV_DIR=.venv"
set "SETUP_TEMP=%CD%\.setup-tmp"
set "PYTHON_CMD="

if not exist "%SETUP_TEMP%" mkdir "%SETUP_TEMP%"
if errorlevel 1 (
    echo [ERROR] Failed to create the setup temporary directory.
    pause
    exit /b 1
)
set "TEMP=%SETUP_TEMP%"
set "TMP=%SETUP_TEMP%"

where py >nul 2>&1
if not errorlevel 1 (
    py -3.12 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
    if not defined PYTHON_CMD (
        py -3.11 -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.11"
    )
    if not defined PYTHON_CMD (
        py -3.10 -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.10"
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10, 3.11, or 3.12 is required.
    echo [INFO] Python 3.14 is not supported by the pinned NumPy and OpenCV packages.
    pause
    exit /b 1
)

if exist "%VENV_DIR%\Scripts\python.exe" if exist "%VENV_DIR%\Scripts\pip.exe" (
    findstr /r /c:"^version = 3.1[0-2]\." "%VENV_DIR%\pyvenv.cfg" >nul
    if errorlevel 1 (
        echo [ERROR] The existing virtual environment uses an unsupported Python version.
        echo [INFO] Delete .venv and run setup.bat again.
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment already exists.
) else (
    echo [1/5] Creating Python virtual environment: %VENV_DIR%...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo [2/5] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 echo [WARNING] Failed to upgrade pip. Continuing with the installed version.

echo [3/5] Installing dependencies...
"%VENV_PYTHON%" -m pip install -r requirements.txt --prefer-binary
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [4/5] Installing Playwright browsers...
"%VENV_PYTHON%" -m playwright install
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browsers.
    pause
    exit /b 1
)

echo.
echo [5/5] Downloading yt-dlp.exe...
set "YT_DLP_URL=https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
set "YT_DLP_PATH=yt-dlp.exe"

if exist "%YT_DLP_PATH%" (
    echo [INFO] yt-dlp.exe already exists. Skipping download.
) else (
    echo [INFO] Downloading yt-dlp.exe from GitHub releases...
    powershell -NoProfile -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%YT_DLP_URL%' -OutFile '%YT_DLP_PATH%' -ErrorAction Stop}"
    if errorlevel 1 (
        echo [WARNING] Failed to download yt-dlp.exe automatically.
        echo [INFO] Download it manually from https://github.com/yt-dlp/yt-dlp/releases/latest
        echo        and place yt-dlp.exe in this project directory.
    ) else (
        echo [INFO] yt-dlp.exe downloaded successfully.
    )
)

echo.
echo Gemini API: set GEMINI_API_KEY to enable slide summarization.
echo API key: https://aistudio.google.com/apikey

echo.
echo ==================================================
echo   Setup complete! You can now run run.bat
echo ==================================================
pause
endlocal
