#!/bin/bash
echo "=================================================="
echo "  YouTube to Presentation Generator Startup"
echo "=================================================="
echo

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[ERROR] Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

echo "Starting local Web server..."
# Try to open the browser in the background
if command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:8000" &
elif command -v open &>/dev/null; then
    open "http://localhost:8000" &
fi

# Run uvicorn with auto-reload
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
