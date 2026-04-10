@echo off
setlocal

REM Run from project root regardless of where this script is called
cd /d "%~dp0\..\.."

echo Building WhisperTray debug executable with console output...
echo.

call "%~dp0build_debug.bat"
