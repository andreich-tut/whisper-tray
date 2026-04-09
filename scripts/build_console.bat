@echo off
setlocal enabledelayedexpansion
REM WhisperTray - Build DEBUG Version with Console and Progress Bar
REM Run this from anywhere — script auto-switches to project root

REM Run from project root regardless of where this script is called
cd /d "%~dp0.."

REM ============================================================
REM ANSI Escape Codes Setup
REM ============================================================
for /f %%a in ('"prompt $E& echo on|cmd /k"') do set "ESC=%%a"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "CYAN=%ESC%[96m"
set "RED=%ESC%[91m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"
set "CURSOR_HIDE=%ESC%[?25l"
set "CURSOR_SHOW=%ESC%[?25h"
set "CLEAR_LINE=%ESC%[2K"

echo %CURSOR_HIDE%

REM ============================================================
REM Helper Functions
REM ============================================================

:show_progress
set "PROGRESS_PERCENT=%~1"
set "PROGRESS_MSG=%~2"
set /a FILLED=PROGRESS_PERCENT*50/100
set /a EMPTY=50-FILLED
set "BAR="
for /l %%a in (1,1,!FILLED!) do set "BAR=!BAR!█"
for /l %%a in (1,1,!EMPTY!) do set "BAR=!BAR!░"
if !PROGRESS_PERCENT! lss 30 (
    set "COLOR=%RED%"
) else if !PROGRESS_PERCENT! lss 70 (
    set "COLOR=%YELLOW%"
) else (
    set "COLOR=%GREEN%"
)
<nul set /p "=%CLEAR_LINE%%BOLD%!COLOR![!BAR!] !PROGRESS_PERCENT!%%%RESET%  %PROGRESS_MSG%%ESC%[0m"
goto :eof

:spinner_step
set /a SPINNER_IDX=SPINNER_IDX %% 4
if !SPINNER_IDX!==0 set "SPINNER_CHAR=⠋"
if !SPINNER_IDX!==1 set "SPINNER_CHAR=⠙"
if !SPINNER_IDX!==2 set "SPINNER_CHAR=⠹"
if !SPINNER_IDX!==3 set "SPINNER_CHAR=⠸"
set /a SPINNER_IDX+=1
goto :eof

REM ============================================================
REM Main Build Process
REM ============================================================

echo.
echo %BOLD%%CYAN%  WhisperTray - Building DEBUG Version (with console)%RESET%
echo.

REM --- Step 1: Check Python (10%) ---
call :show_progress 5 "Checking Python..."
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo %RED%[ERROR] Python not found. Install Python 3.12+ from python.org%RESET%
    echo %CURSOR_SHOW%
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
call :show_progress 10 "Python %PY_VER% found ✓"
echo.

REM --- Step 2: Install Dependencies (30%) ---
call :show_progress 15 "Installing dependencies..."
pip install -e ".[build]" >nul 2>&1
if errorlevel 1 (
    echo.
    echo %RED%[ERROR] Failed to install dependencies%RESET%
    echo %CURSOR_SHOW%
    pause
    exit /b 1
)
call :show_progress 30 "Dependencies installed ✓"
echo.

REM --- Step 3: Clean Previous Builds (40%) ---
call :show_progress 35 "Cleaning previous builds..."
if exist build rmdir /s /q build >nul 2>&1
if exist dist rmdir /s /q dist >nul 2>&1
call :show_progress 40 "Clean complete ✓"
echo.

REM --- Step 4: Find faster-whisper (50%) ---
call :show_progress 48 "Locating faster-whisper..."
for /f "delims=" %%i in ('python -c "import faster_whisper, os; print(os.path.dirname(faster_whisper.__file__))"') do set "FW_DIR=%%i"
call :show_progress 50 "Found: %FW_DIR:~0,40%... ✓"
echo.

REM --- Step 5: Check ONNX (55%) ---
if not exist "%FW_DIR%\assets\silero_vad_v6.onnx" (
    echo %RED%[ERROR] ONNX not found at %FW_DIR%\assets\silero_vad_v6.onnx%RESET%
    echo %CURSOR_SHOW%
    pause
    exit /b 1
)
call :show_progress 55 "ONNX file verified ✓"
echo.

REM --- Step 6: Build with PyInstaller (60-90%) ---
echo %BOLD%%CYAN%  Building WhisperTray_DEBUG.exe...%RESET%
echo.

set "SPINNER_IDX=0"
set /a BUILD_PROGRESS=60

start /b cmd /c "pyinstaller --clean --noconfirm --name WhisperTray_DEBUG --console --onedir whisper_tray/whisper_tray.py > "%TEMP%\wt_debug_build.log" 2>&1"

:build_loop
timeout /t 1 >nul
tasklist | find /i "pyinstaller" >nul 2>&1
if not errorlevel 1 (
    call :spinner_step
    set /a BUILD_PROGRESS+=2
    if !BUILD_PROGRESS! gtr 88 set "BUILD_PROGRESS=88"
    call :show_progress !BUILD_PROGRESS! "Building... !SPINNER_CHAR!"
    goto build_loop
)

REM Check build result
if exist "dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe" (
    call :show_progress 90 "Copying ONNX assets..."
    set "INTERNAL_DIR=dist\WhisperTray_DEBUG\_internal"
    if not exist "%INTERNAL_DIR%\faster_whisper\assets" mkdir "%INTERNAL_DIR%\faster_whisper\assets"
    xcopy "%FW_DIR%\assets\*.onnx" "%INTERNAL_DIR%\faster_whisper\assets\" /E /I /Y >nul
    call :show_progress 95 "Finalizing..."
    call :show_progress 100 "Build complete ✓"
    echo.
    echo.
    echo %BOLD%%GREEN%  SUCCESS! Find WhisperTray_DEBUG.exe in dist\WhisperTray_DEBUG\%RESET%
    echo.
) else (
    echo.
    echo %RED%[ERROR] Build failed - see %TEMP%\wt_debug_build.log%RESET%
    echo %CURSOR_SHOW%
    type "%TEMP%\wt_debug_build.log"
    pause
    exit /b 1
)

echo %CURSOR_SHOW%
pause
