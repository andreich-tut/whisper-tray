@echo off
setlocal

REM Run from project root regardless of where this script is called
cd /d "%~dp0\..\.."

set "PYTHON=python"
if defined WHISPER_TRAY_PYTHON (
    set "PYTHON=%WHISPER_TRAY_PYTHON%"
)
if not defined WHISPER_TRAY_PYTHON (
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=py -3.12"
    )
)

echo Building WhisperTray debug executable...
echo.

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12+ and make sure `py -3.12`, `py -3.14`, or `python` works.
    pause
    exit /b 1
)
for /f "delims=" %%i in ('%PYTHON% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VER=%%i"
if "%PY_VER%"=="3.14" (
    echo INFO: Python 3.14 detected. WhisperTray requires PyInstaller 6.15+ for Python 3.14 builds.
)

%PYTHON% -m pip install -e ".[build,ui]"
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

if exist "dist" rmdir /s /q "dist"
if exist "build\whisper_tray" rmdir /s /q "build\whisper_tray"
if exist "build\WhisperTray_DEBUG" rmdir /s /q "build\WhisperTray_DEBUG"

set "WHISPER_TRAY_DEBUG=1"
set "WHISPER_TRAY_NAME=WhisperTray_DEBUG"
%PYTHON% -m PyInstaller --clean --noconfirm build/windows/whisper_tray.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('%PYTHON% -c "import faster_whisper, os; print(os.path.dirname(faster_whisper.__file__))"') do set "FW_DIR=%%i"
set "DEST_DIR=dist\WhisperTray_DEBUG\_internal\faster_whisper\assets"
if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"
copy "%FW_DIR%\assets\*.onnx" "%DEST_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy faster-whisper ONNX assets.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe
echo Run dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe.
echo.
pause
