#!/bin/bash
# WhisperTray - Build Linux Executable
# Run this from the whisper_tray folder

# Set up log file with timestamp
LOGFILE="../build_$(date +%Y%m%d_%H%M%S).log"

echo "============================================================"
echo "WhisperTray - Building Linux Executable"
echo "Logs saved to: $LOGFILE"
echo "============================================================"
echo ""

# Start logging to file
echo "============================================================" > "$LOGFILE"
echo "WhisperTray Build Log" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "============================================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Install Python 3.10+"
    echo "[ERROR] Python3 not found. Install Python 3.10+" >> "$LOGFILE"
    echo "" >> "$LOGFILE"
    echo "Build FAILED: $(date)" >> "$LOGFILE"
    echo "============================================================" >> "$LOGFILE"
    exit 1
fi

echo "Python found"
python3 --version
python3 --version >> "$LOGFILE"
echo ""
echo "" >> "$LOGFILE"

# Install dependencies
echo "Installing dependencies..."
echo "Installing dependencies..." >> "$LOGFILE"
pip3 install faster-whisper sounddevice pynput pystray Pillow pyperclip requests python-dotenv pyinstaller 2>&1 | tee -a "$LOGFILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    echo "[ERROR] Failed to install dependencies" >> "$LOGFILE"
    echo "" >> "$LOGFILE"
    echo "Build FAILED: $(date)" >> "$LOGFILE"
    echo "============================================================" >> "$LOGFILE"
    exit 1
fi
echo "Dependencies installed successfully"
echo "Dependencies installed successfully" >> "$LOGFILE"
echo ""
echo "" >> "$LOGFILE"

# Clean previous builds
echo "Cleaning previous builds..."
echo "Cleaning previous builds..." >> "$LOGFILE"
rm -rf ../build ../dist
echo ""
echo "" >> "$LOGFILE"

# Build with PyInstaller
echo "Building WhisperTray..."
echo "Building WhisperTray..." >> "$LOGFILE"
echo ""
echo "" >> "$LOGFILE"
pyinstaller --clean whisper_tray.spec 2>&1 | tee -a "$LOGFILE"
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo ""
    echo "============================================================"
    echo "[ERROR] Build failed - check log file for details"
    echo "============================================================"
    echo ""
    echo "============================================================" >> "$LOGFILE"
    echo "[ERROR] Build failed" >> "$LOGFILE"
    echo "Build FAILED: $(date)" >> "$LOGFILE"
    echo "============================================================" >> "$LOGFILE"
    exit 1
fi

echo ""
echo "============================================================"
echo "SUCCESS! Find WhisperTray in ../dist/ folder"
echo "============================================================"
echo ""
echo "" >> "$LOGFILE"
echo "============================================================" >> "$LOGFILE"
echo "SUCCESS! Find WhisperTray in ../dist/ folder" >> "$LOGFILE"
echo "Build COMPLETED: $(date)" >> "$LOGFILE"
echo "============================================================" >> "$LOGFILE"
echo ""
