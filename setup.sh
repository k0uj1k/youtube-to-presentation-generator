#!/bin/bash

echo "=================================================="
echo "  YouTube to Presentation Generator Setup"
echo "=================================================="
echo

VENV_DIR=".venv"

# Check Python version
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    if command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python 3 is not installed. Please install Python 3."
        exit 1
    fi
fi

# 1. Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "[INFO] Virtual environment already exists."
else
    echo "[1/3] Creating Python virtual environment ($VENV_DIR)..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        exit 1
    fi
fi

# 2. Install dependencies
echo "[2/3] Installing dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "[WARNING] Failed to upgrade pip."
fi

"$VENV_DIR/bin/pip" install -r requirements.txt --prefer-binary
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi

# 3. Install Playwright browsers
echo "[3/3] Installing Playwright browsers..."
"$VENV_DIR/bin/python" -m playwright install
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install Playwright browsers."
    exit 1
fi


echo
echo "=================================================="
echo "  Setup complete! You can now run run.sh"
echo "=================================================="
