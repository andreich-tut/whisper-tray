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

echo Starting WhisperTray Windows build...
echo.

echo [1/6] Checking Python...
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
echo OK
echo.

echo [2/6] Installing build dependencies with overlay support...
%PYTHON% -m pip install -e ".[build,ui]"
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)
echo OK
echo.

echo [3/6] Cleaning old build outputs...
if exist "dist" rmdir /s /q "dist"
if exist "build\whisper_tray" rmdir /s /q "build\whisper_tray"
if exist "build\WhisperTray" rmdir /s /q "build\WhisperTray"
echo OK
echo.

echo [4/6] Building with the maintained Windows spec...
%PYTHON% -m PyInstaller --clean --noconfirm packaging/windows/whisper_tray.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)
REM Remove stray bare bootloader that PyInstaller leaves in dist\ root.
REM The real build is dist\WhisperTray\WhisperTray.exe (with _internal alongside it).
if exist "dist\WhisperTray.exe" del /q "dist\WhisperTray.exe"
echo OK
echo.

echo [5/6] Verifying ONNX assets...
for /f "delims=" %%i in ('%PYTHON% -c "import faster_whisper, os; print(os.path.dirname(faster_whisper.__file__))"') do set "FW_DIR=%%i"
set "DEST_DIR=dist\WhisperTray\_internal\faster_whisper\assets"
if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"
copy "%FW_DIR%\assets\*.onnx" "%DEST_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy faster-whisper ONNX assets.
    pause
    exit /b 1
)
echo OK
echo.

echo [6/6] Build complete.
echo Output: dist\WhisperTray\WhisperTray.exe
echo.
echo This build includes the optional overlay backend.
echo Keep your .env file next to WhisperTray.exe, in the repo root, or in whisper_tray\.
echo Run dist\WhisperTray\WhisperTray.exe.
echo.
pause
