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
    py -3.14 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.14"
    if not defined PYTHON_CMD (
        py -3.13 -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.13"
    )
    if not defined PYTHON_CMD (
        py -3.12 -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.12"
    )
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
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; assert (3, 10) <= sys.version_info < (3, 15)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10 through 3.14 is required.
    pause
    exit /b 1
)

if exist "%VENV_DIR%\Scripts\python.exe" if exist "%VENV_DIR%\Scripts\pip.exe" goto :venv_exists

echo [1/4] Creating Python virtual environment: %VENV_DIR%...
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
goto :venv_ready

:venv_exists
findstr /r /c:"^version = 3.1[0-4]\." "%VENV_DIR%\pyvenv.cfg" >nul
if errorlevel 1 (
    echo [ERROR] The existing virtual environment uses an unsupported Python version.
    echo [INFO] Delete .venv and run setup.bat again.
    pause
    exit /b 1
)
echo [INFO] Virtual environment already exists.

:venv_ready

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo [2/4] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 echo [WARNING] Failed to upgrade pip. Continuing with the installed version.

echo [3/4] Installing dependencies...
"%VENV_PYTHON%" -m pip install -r requirements.txt --prefer-binary
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [4/4] Installing Playwright browsers...
"%VENV_PYTHON%" -m playwright install
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browsers.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo   Setup complete! You can now run run.bat
echo ==================================================
pause
endlocal
