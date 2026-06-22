#!/usr/bin/env bash

set -euo pipefail

echo "=================================================="
echo "  YouTube to Presentation Generator Setup"
echo "=================================================="
echo

VENV_DIR=".venv"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[ERROR] Python 3 is not installed or not in PATH."
  exit 1
fi

if [ -d "${VENV_DIR}" ]; then
  echo "[INFO] Virtual environment already exists."
else
  echo "[1/3] Creating Python virtual environment (.venv)..."
  "${PYTHON_CMD}" -m venv "${VENV_DIR}"
fi

VENV_PYTHON="${VENV_DIR}/bin/python"
VENV_PIP="${VENV_DIR}/bin/pip"

echo "[2/3] Installing dependencies..."
"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PIP}" install -r requirements.txt --prefer-binary

echo
echo "[3/3] Installing Playwright browsers..."
"${VENV_PYTHON}" -m playwright install

echo
echo "[4/4] Gemini API Setup Guide"
echo "[INFO] To enable slide summarization with Gemini AI, set GEMINI_API_KEY:"
echo "       1. Get your API key from: https://aistudio.google.com/apikey"
echo "       2. export GEMINI_API_KEY=your-api-key-here"

echo
echo "=================================================="
echo "  Setup complete! Start the app with:"
echo "  ./run.sh"
echo "=================================================="
