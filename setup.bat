@echo off
echo ==================================================
echo   YouTube to Presentation Generator Setup
echo ==================================================
echo.

set VENV_DIR=.venv

if exist "%VENV_DIR%" (
    echo [INFO] Virtual environment already exists.
) else (
    echo [1/3] Creating Python virtual environment (.venv)...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [2/3] Installing dependencies...
"%VENV_DIR%\Scripts\python" -m pip install --upgrade pip
if errorlevel 1 echo [WARNING] Failed to upgrade pip.

"%VENV_DIR%\Scripts\pip" install -r requirements.txt --prefer-binary
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

"%VENV_DIR%\Scripts\python" -m playwright install
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browsers.
    pause
    exit /b 1
)

echo.
echo [3/3] Setup complete. You can now run run.bat to start the server.
pause
