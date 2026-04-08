@echo off
setlocal enabledelayedexpansion
REM WhisperTray - Build DEBUG Version with Console and Progress Bar
REM Run this from the whisper_tray folder on Windows

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
    echo %RED%[ERROR] Python not found. Install Python 3.10+ from python.org%RESET%
    echo %CURSOR_SHOW%
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
call :show_progress 10 "Python %PY_VER% found ✓"
echo.

REM --- Step 2: Install Dependencies (30%) ---
call :show_progress 15 "Installing dependencies..."
pip install faster-whisper sounddevice pynput pystray Pillow pyperclip requests python-dotenv pyinstaller pyinstaller-hooks-contrib >nul 2>&1
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
if exist ..\build rmdir /s /q ..\build >nul 2>&1
if exist ..\dist rmdir /s /q ..\dist >nul 2>&1
call :show_progress 40 "Clean complete ✓"
echo.

REM --- Step 4: Create .env if needed (45%) ---
if not exist .env (
    call :show_progress 42 "Creating .env from .env.example..."
    if exist .env.example copy .env.example .env >nul
)
call :show_progress 45 "Environment ready ✓"
echo.

REM --- Step 5: Find faster-whisper (50%) ---
call :show_progress 48 "Locating faster-whisper..."
for /f "delims=" %%i in ('python -c "import faster_whisper, os; print(os.path.dirname(faster_whisper.__file__))"') do set "FW_DIR=%%i"
call :show_progress 50 "Found: %FW_DIR:~0,40%... ✓"
echo.

REM --- Step 6: Check ONNX (55%) ---
if not exist "%FW_DIR%\assets\silero_vad_v6.onnx" (
    echo %RED%[ERROR] ONNX not found at %FW_DIR%\assets\silero_vad_v6.onnx%RESET%
    echo %CURSOR_SHOW%
    pause
    exit /b 1
)
call :show_progress 55 "ONNX file verified ✓"
echo.

REM --- Step 7: Build with PyInstaller (60-90%) ---
echo %BOLD%%CYAN%  Building WhisperTray_DEBUG.exe...%RESET%
echo.

set "SPINNER_IDX=0"
set /a BUILD_PROGRESS=60

start /b cmd /c "pyinstaller --clean --noconfirm --name WhisperTray_DEBUG --console --onedir whisper_tray.spec > "%TEMP%\wt_debug_build.log" 2>&1 && echo BUILD_SUCCESS > "%TEMP%\wt_debug_build_status.txt" || echo BUILD_FAILED > "%TEMP%\wt_debug_build_status.txt""

:build_loop
if exist "%TEMP%\wt_debug_build_status.txt" (
    set "BUILD_DONE=1"
) else (
    call :spinner_step
    call :show_progress !BUILD_PROGRESS! "!SPINNER_CHAR! PyInstaller running..."
    timeout /t 1 /nobreak >nul 2>&1
    set /a BUILD_PROGRESS+=1
    if !BUILD_PROGRESS! gtr 89 set /a BUILD_PROGRESS=89
    goto :build_loop
)

set /p BUILD_STATUS=<"%TEMP%\wt_debug_build_status.txt"
del "%TEMP%\wt_debug_build_status.txt" >nul 2>&1

if "!BUILD_STATUS!"=="BUILD_SUCCESS" (
    call :show_progress 90 "Build successful ✓"
    echo.
) else (
    echo.
    echo %RED%[ERROR] Build FAILED%RESET%
    echo %CURSOR_SHOW%
    echo Build log: %TEMP%\wt_debug_build.log
    type "%TEMP%\wt_debug_build.log"
    pause
    exit /b 1
)

REM --- Step 8: Verify EXE (92%) ---
set "EXE_DIR=..\dist\WhisperTray_DEBUG"
set "INTERNAL_DIR=%EXE_DIR%\_internal"

if not exist "%EXE_DIR%\WhisperTray_DEBUG.exe" (
    echo %RED%[ERROR] EXE not found at %EXE_DIR%\WhisperTray_DEBUG.exe%RESET%
    echo %CURSOR_SHOW%
    pause
    exit /b 1
)
call :show_progress 92 "EXE verified ✓"
echo.

REM --- Step 9: Copy ONNX Files (95%) ---
call :show_progress 93 "Copying ONNX models..."
if not exist "%INTERNAL_DIR%\faster_whisper\assets" mkdir "%INTERNAL_DIR%\faster_whisper\assets"
xcopy "%FW_DIR%\assets\*.onnx" "%INTERNAL_DIR%\faster_whisper\assets\" /E /I /Y >nul
xcopy "%FW_DIR%\assets\*.onnx" "%INTERNAL_DIR%\faster_whisper\" /Y >nul
call :show_progress 95 "ONNX files copied ✓"
echo.

REM --- Step 10: Copy CUDA DLLs (98%) ---
set "CUDA_PATH="
if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA" (
    for /d %%i in ("C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\*") do (
        if not defined CUDA_PATH set "CUDA_PATH=%%i"
    )
)

if defined CUDA_PATH (
    call :show_progress 97 "Copying CUDA DLLs..."
    set "CUDA_BIN=%CUDA_PATH%\bin"
    if exist "%CUDA_BIN%\cublas64*.dll" copy "%CUDA_BIN%\cublas64*.dll" "%EXE_DIR\" >nul
    if exist "%CUDA_BIN%\cublasLt64*.dll" copy "%CUDA_BIN%\cublasLt64*.dll" "%EXE_DIR\" >nul 2>nul
    if exist "%CUDA_BIN%\cudart64*.dll" copy "%CUDA_BIN%\cudart64*.dll" "%EXE_DIR\" >nul
    if exist "%CUDA_BIN%\cudnn64*.dll" copy "%CUDA_BIN%\cudnn64*.dll" "%EXE_DIR\" >nul 2>nul
    if exist "%CUDA_BIN%\cufft64*.dll" copy "%CUDA_BIN%\cufft64*.dll" "%EXE_DIR\" >nul
    if exist "%CUDA_BIN%\curand64*.dll" copy "%CUDA_BIN%\curand64*.dll" "%EXE_DIR\" >nul
    if exist "%CUDA_BIN%\nvrtc64*.dll" copy "%CUDA_BIN%\nvrtc64*.dll" "%EXE_DIR\" >nul 2>nul
    if exist "%CUDA_BIN%\nvToolsExt64*.dll" copy "%CUDA_BIN%\nvToolsExt64*.dll" "%EXE_DIR\" >nul 2>nul
    call :show_progress 98 "CUDA DLLs copied ✓"
    echo.
) else (
    call :show_progress 98 "Skipping CUDA DLLs (not found)"
    echo.
)

REM --- Step 11: Done! (100%) ---
call :show_progress 100 "BUILD COMPLETE ✓"
echo.
echo.
echo %BOLD%%GREEN%  ╔══════════════════════════════════════════════════╗%RESET%
echo %BOLD%%GREEN%  ║  SUCCESS! DEBUG build complete!                  ║%RESET%
echo %BOLD%%GREEN%  ║  Location: %EXE_DIR%\WhisperTray_DEBUG.exe%RESET%
echo %BOLD%%GREEN%  ║  Run with console to see logs                    ║%RESET%
echo %BOLD%%GREEN%  ╚══════════════════════════════════════════════════╝%RESET%
echo.
echo %CURSOR_SHOW%
pause
