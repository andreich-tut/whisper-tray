@echo off
REM Run WhisperTray debug build directly

REM Run from project root regardless of where this script is called
cd /d "%~dp0.."

echo ============================================================
echo WhisperTray - Running DEBUG Version
echo ============================================================
echo.

if not exist "dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe" (
    echo [ERROR] Debug build not found. Run build_debug.bat first.
    pause
    exit /b 1
)

echo Starting WhisperTray_DEBUG.exe...
echo.
start "" "dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe"
echo Application started. Check console output for logs.
echo.
