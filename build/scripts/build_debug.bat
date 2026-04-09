@echo off
setlocal enabledelayedexpansion
REM WhisperTray - Build DEBUG Version with Console Window
REM Run this from anywhere — script auto-switches to project root

REM Run from project root regardless of where this script is called
cd /d "%~dp0.."

echo ============================================================
echo WhisperTray - Building DEBUG Version (with console)
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.12+ from python.org
    pause
    exit /b 1
)

echo Python found
echo.

REM Install dependencies
echo Installing dependencies...
pip install -e ".[build]"

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build with console window enabled for debugging
echo Building WhisperTray_DEBUG.exe...
call pyinstaller --clean ^
    --name WhisperTray_DEBUG ^
    --console ^
    --onedir ^
    whisper_tray/whisper_tray.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo [ERROR] Build failed
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Find WhisperTray_DEBUG.exe in dist\ folder
echo ============================================================
echo.
echo This version shows a console window for debugging.
echo Check the console output and whisper_tray.log for errors.
echo.
pause
