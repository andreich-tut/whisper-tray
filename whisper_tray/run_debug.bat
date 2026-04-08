@echo off
REM WhisperTray - Run with Console for Debugging
REM This shows all errors and log output

echo ============================================================
echo WhisperTray - Starting (Debug Mode)
echo ============================================================
echo.
echo Watch this window for errors. The app will appear in the
echo system tray (bottom-right corner). Click the ^ arrow if
echo you don't see it.
echo.
echo Press Ctrl+C to exit.
echo ============================================================
echo.

cd /d "%~dp0"
python whisper_tray.py

echo.
echo ============================================================
echo WhisperTray has exited.
echo ============================================================
pause
