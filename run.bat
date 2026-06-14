@echo off
echo ==================================================
echo   YouTube to Presentation Generator Startup
echo ==================================================
echo.

set VENV_DIR=.venv

if not exist "%VENV_DIR%" (
    echo [ERROR] Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

echo [3/3] Starting local Web server...
echo Opening http://localhost:8000 in your browser...
echo.

start http://localhost:8000

"%VENV_DIR%\Scripts\python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
