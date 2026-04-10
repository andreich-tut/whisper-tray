@echo off
REM Test if pystray tray icon works on this system

REM Run from project root regardless of where this script is called
cd /d "%~dp0\..\.."

echo ============================================================
echo Testing pystray Tray Icon
echo ============================================================
echo.
echo This will show if the basic tray icon functionality works.
echo You should see a BLUE icon in the system tray.
echo.
echo Click the ^ arrow in the system tray if you don't see it!
echo.
echo ============================================================
echo.

python scripts/windows/test_tray_icon.py

echo.
echo Test finished.
pause
