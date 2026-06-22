#!/usr/bin/env bash

set -euo pipefail

echo "=================================================="
echo "  YouTube to Presentation Generator Startup"
echo "=================================================="
echo

VENV_DIR=".venv"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[ERROR] Virtual environment not found. Please run ./setup.sh first."
  exit 1
fi

VENV_PYTHON="${VENV_DIR}/bin/python"

if [ ! -x "${VENV_PYTHON}" ]; then
  echo "[ERROR] Virtual environment Python executable not found: ${VENV_PYTHON}"
  exit 1
fi

echo "[1/2] Starting local Web server..."

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:8000" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "http://localhost:8000" >/dev/null 2>&1 &
fi

echo "[2/2] Launching uvicorn..."
"${VENV_PYTHON}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
