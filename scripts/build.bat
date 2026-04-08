@echo off
setlocal enabledelayedexpansion

REM Run from project root regardless of where this script is called
cd /d "%~dp0.."

echo Starting WhisperTray build...
echo.

REM Set up log file
set "LOGFILE=build_log.txt"
echo Build started: %DATE% %TIME% > "%LOGFILE%"

REM Step 1: Check Python
echo [1/7] Checking Python...
python --version >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)
echo OK

REM Step 2: Install Dependencies
echo [2/7] Installing dependencies...
pip install -e ".[build]" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)
echo OK

REM Step 3: Clean Previous Builds
echo [3/7] Cleaning previous builds...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
echo OK

REM Step 4: Find faster-whisper
echo [4/7] Finding faster-whisper...
for /f "delims=" %%i in ('python -c "import faster_whisper, os; print(os.path.dirname(faster_whisper.__file__))"') do set "FW_DIR=%%i"
echo Found: %FW_DIR%

REM Step 5: Check CUDA
echo [5/7] Checking CUDA...
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

REM Step 6: Build with PyInstaller
echo [6/7] Building WhisperTray.exe...
echo This may take a few minutes...
pyinstaller --clean --noconfirm --name WhisperTray --windowed --onedir --collect-binaries ctranslate2 --collect-binaries faster_whisper whisper_tray/whisper_tray.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Build failed - see %LOGFILE%
    pause
    exit /b 1
)
echo Build successful

REM Step 7: Copy ONNX assets and CUDA DLLs
echo [7/7] Copying required files...
set "INTERNAL_DIR=dist\WhisperTray\_internal"

if not exist "%INTERNAL_DIR%\faster_whisper\assets" mkdir "%INTERNAL_DIR%\faster_whisper\assets"
xcopy "%FW_DIR%\assets\*.onnx" "%INTERNAL_DIR%\faster_whisper\assets\" /E /I /Y >nul

REM Always copy CUDA DLLs from ctranslate2 package first — these are the exact
REM versions ctranslate2 was compiled against and what the EXE needs at runtime.
for /f "delims=" %%p in ('python -c "import ctranslate2, os; print(os.path.dirname(ctranslate2.__file__))" 2^>nul') do (
    set "CT2_DIR=%%p"
)
if defined CT2_DIR (
    echo Copying CUDA DLLs from ctranslate2 package: %CT2_DIR%
    copy "%CT2_DIR%\*.dll" "%INTERNAL_DIR%\" >nul 2>nul
    echo ctranslate2 DLLs copied to %INTERNAL_DIR%
) else (
    echo WARNING: ctranslate2 package not found. CUDA may not work at runtime.
)

if defined CUDA_PATH (
    set "CUDA_BIN=%CUDA_PATH%\bin"
    if exist "%CUDA_BIN%\cudart64*.dll" copy "%CUDA_BIN%\cudart64*.dll" "%INTERNAL_DIR%\" >nul
    if exist "%CUDA_BIN%\cudnn64*.dll" copy "%CUDA_BIN%\cudnn64*.dll" "%INTERNAL_DIR%\" >nul 2>nul
    echo System CUDA DLLs copied from %CUDA_BIN%
) else (
    echo NOTE: System CUDA not found - relying on ctranslate2 bundled DLLs only.
)

echo.
echo ============================================================
echo SUCCESS! Find WhisperTray.exe in dist\WhisperTray
echo ============================================================
echo.
pause
