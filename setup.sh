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

# 4. Download yt-dlp (Linux binary)
echo
echo "[4/4] Downloading yt-dlp..."
YT_DLP_URL="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
YT_DLP_PATH="./yt-dlp"

if [ -f "$YT_DLP_PATH" ]; then
    echo "[INFO] yt-dlp already exists. Skipping download."
else
    echo "[INFO] Downloading yt-dlp from GitHub releases..."
    DOWNLOAD_SUCCESS=false

    if command -v curl &>/dev/null; then
        curl -L -o "$YT_DLP_PATH" "$YT_DLP_URL"
        if [ $? -eq 0 ]; then DOWNLOAD_SUCCESS=true; fi
    elif command -v wget &>/dev/null; then
        wget -O "$YT_DLP_PATH" "$YT_DLP_URL"
        if [ $? -eq 0 ]; then DOWNLOAD_SUCCESS=true; fi
    fi

    if [ "$DOWNLOAD_SUCCESS" = true ] && [ -f "$YT_DLP_PATH" ]; then
        chmod +x "$YT_DLP_PATH"
        echo "[INFO] yt-dlp downloaded successfully."
        echo "[INFO] Location: $(pwd)/$YT_DLP_PATH"
    else
        echo "[WARNING] Failed to download yt-dlp automatically."
        echo "[INFO] You can download it manually from:"
        echo "       https://github.com/yt-dlp/yt-dlp/releases/latest"
        echo "       (Download the Linux binary, place it in the project root directory, and run: chmod +x yt-dlp)"
    fi
fi

# 5. Gemini API Setup Guide
echo
echo "[5/5] Gemini API Setup Guide"
echo "[INFO] To enable slide summarization with Gemini AI, set GEMINI_API_KEY:"
echo "       1. Get your API key from: https://aistudio.google.com/apikey"
echo "       2. Linux/macOS: export GEMINI_API_KEY=\"your-api-key-here\""
echo "          (You can add this to your ~/.bashrc or ~/.zshrc for a persistent setup)"

echo
echo "=================================================="
echo "  Setup complete! You can now run run.sh"
echo "=================================================="
