@echo off
setlocal enabledelayedexpansion

echo Starting WhisperTray build...
echo.

REM Set up log file
set "LOGFILE=build_log.txt"
echo Build started: %DATE% %TIME% > "%LOGFILE%"

REM Step 1: Check Python
echo [1/8] Checking Python...
python --version >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)
echo OK

REM Step 2: Install Dependencies
echo [2/8] Installing dependencies...
pip install faster-whisper sounddevice pynput pystray Pillow pyperclip requests python-dotenv pyinstaller pyinstaller-hooks-contrib >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)
echo OK

REM Step 3: Clean Previous Builds
echo [3/8] Cleaning previous builds...
if exist ..\build rmdir /s /q ..\build 2>nul
if exist ..\dist rmdir /s /q ..\dist 2>nul
echo OK

REM Step 4: Create .env if needed
echo [4/8] Checking environment...
if not exist .env (
    if exist .env.example copy .env.example .env >nul
)
echo OK

REM Step 5: Find faster-whisper
echo [5/8] Finding faster-whisper...
for /f "delims=" %%i in ('python -c "import faster_whisper, os; print(os.path.dirname(faster_whisper.__file__))"') do set "FW_DIR=%%i"
echo Found: %FW_DIR%

REM Step 6: Check CUDA
echo [6/8] Checking CUDA...
set "CUDA_PATH="

REM First check system CUDA installation
if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA" (
    for /d %%i in ("C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\*") do (
        if not defined CUDA_PATH set "CUDA_PATH=%%i"
    )
)

REM If system CUDA not found, try to find CUDA DLLs in Python packages
if not defined CUDA_PATH (
    echo System CUDA not found, searching Python packages...
    for /f "delims=" %%p in ('python -c "import ctranslate2, os; print(os.path.dirname(ctranslate2.__file__))" 2^>nul') do (
        if exist "%%p\cublas64*.dll" (
            set "CUDA_PATH=%%p"
            echo Found CUDA DLLs in ctranslate2 package: %%p
        )
    )
)

if defined CUDA_PATH (
    echo CUDA DLLs found: %CUDA_PATH%
) else (
    echo CUDA not found - executable will run in CPU mode
    echo To enable GPU, ensure faster-whisper with CUDA is installed via pip
)

REM Step 7: Build with PyInstaller
echo [7/8] Building WhisperTray.exe...
echo This may take a few minutes...
pyinstaller --clean --noconfirm whisper_tray.spec >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Build failed - see %LOGFILE%
    pause
    exit /b 1
)
echo Build successful

REM Step 8: Copy files
echo [8/8] Copying required files...
set "EXE_DIR=..\dist\WhisperTray"
set "INTERNAL_DIR=%EXE_DIR%\_internal"

if not exist "%INTERNAL_DIR%\faster_whisper\assets" mkdir "%INTERNAL_DIR%\faster_whisper\assets"
xcopy "%FW_DIR%\assets\*.onnx" "%INTERNAL_DIR%\faster_whisper\assets\" /E /I /Y >nul

if defined CUDA_PATH (
    set "CUDA_BIN=%CUDA_PATH%\bin"
    if exist "%CUDA_BIN%\cublas64*.dll" copy "%CUDA_BIN%\cublas64*.dll" "%INTERNAL_DIR%\" >nul
    if exist "%CUDA_BIN%\cudart64*.dll" copy "%CUDA_BIN%\cudart64*.dll" "%INTERNAL_DIR%\" >nul
    if exist "%CUDA_BIN%\cudnn64*.dll" copy "%CUDA_BIN%\cudnn64*.dll" "%INTERNAL_DIR%\" >nul 2>nul
    echo CUDA DLLs copied to %INTERNAL_DIR%
) else (
    echo WARNING: CUDA_PATH not set. Executable will run in CPU mode only.
    echo To enable GPU, install CUDA Toolkit or set CUDA_PATH environment variable.
)

echo.
echo ============================================================
echo SUCCESS! Find WhisperTray.exe in %EXE_DIR%
echo ============================================================
echo.
pause
