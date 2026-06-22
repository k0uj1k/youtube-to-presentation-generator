@echo off
echo ==================================================
echo   YouTube to Presentation Generator Startup
echo ==================================================
echo.

set VENV_DIR=.venv

if not exist "%VENV_DIR%" (
    echo [ERROR] Virtual environment not found. Please set up the project first.
    pause
    exit /b 1
)

rem Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

echo [3/3] Starting local Web server...
start "" http://localhost:8000

rem Run uvicorn with auto-reload
"%VENV_DIR%\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
