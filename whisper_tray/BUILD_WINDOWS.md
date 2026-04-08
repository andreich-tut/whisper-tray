# Windows Build Guide for WhisperTray

This guide explains how to build WhisperTray as a Windows `.exe` executable with all required dependencies properly bundled.

## Prerequisites

1. **Windows 10/11** (64-bit)
2. **Python 3.10+** - Download from https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
3. **NVIDIA GPU** (optional, for GPU acceleration)
   - CUDA Toolkit installed
   - Latest NVIDIA drivers

## Quick Build (Recommended)

### Step 1: Clone/Download the Project

```bash
# If you have the project files
cd path\to\whisper-tray\whisper_tray
```

### Step 2: Run the Build Script

**For Release Version (no console):**
```bash
build.bat
```

**For Debug Version (with console for troubleshooting):**
```bash
build_console.bat
```

The script will:
- ✅ Install all dependencies
- ✅ Download the Whisper model assets
- ✅ Bundle the Silero VAD ONNX file
- ✅ Copy CUDA DLLs (if available)
- ✅ Create `WhisperTray.exe` in `..\dist\` folder

### Step 3: Test the Executable

**Release version:**
```
..\dist\WhisperTray\WhisperTray.exe
```

**Debug version:**
```
..\dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe
```

A system tray icon should appear. Hold `Ctrl+Space` to test recording.

## Manual Build (If Scripts Fail)

If the automated scripts don't work, follow these steps:

### 1. Install Dependencies

```bash
pip install faster-whisper sounddevice pynput pystray Pillow pyperclip requests python-dotenv pyinstaller
```

### 2. Verify ONNX File Exists

```bash
python -c "import faster_whisper, os; fw_dir = os.path.dirname(faster_whisper.__file__); print(os.path.join(fw_dir, 'assets', 'silero_vad_v6.onnx'))"
```

Expected output: A path like `C:\Users\...\Python\Python312\site-packages\faster_whisper\assets\silero_vad_v6.onnx`

### 3. Build with PyInstaller

```bash
cd whisper_tray
pyinstaller --clean --noconfirm whisper_tray.spec
```

### 4. Copy ONNX Files Manually

```bash
# Get faster-whisper location
python -c "import faster_whisper, os; print(os.path.dirname(faster_whisper.__file__))"

# Copy the ONNX file to _internal folder
# Replace PATH_TO_FW with the output from above command
mkdir ..\dist\WhisperTray\_internal\faster_whisper\assets
copy "PATH_TO_FW\assets\silero_vad_v6.onnx" "..\dist\WhisperTray\_internal\faster_whisper\assets\"
```

### 5. Copy CUDA DLLs (If Using GPU)

If you have CUDA installed, copy these DLLs to the `dist\WhisperTray\` folder:
- `cublas64_*.dll`
- `cublasLt64_*.dll`
- `cudart64_*.dll`
- `cudnn64_*.dll` (if using cuDNN)
- `cufft64_*.dll`
- `curand64_*.dll`

Usually located in: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin`

## Troubleshooting

### Error: "NO_SUCHFILE : Load model from ...silero_vad_v6.onnx failed"

**Cause:** The ONNX file wasn't bundled correctly or is in the wrong location.

**Solution:**

1. **Check if ONNX exists in _internal:**
   ```
   dir /s ..\dist\WhisperTray\_internal\faster_whisper\assets\silero_vad_v6.onnx
   ```

2. **If missing, copy it manually:**
   ```bash
   python -c "import faster_whisper, os, shutil; fw=os.path.dirname(faster_whisper.__file__); src=os.path.join(fw,'assets','silero_vad_v6.onnx'); dst=r'..\dist\WhisperTray\_internal\faster_whisper\assets'; os.makedirs(dst, exist_ok=True); shutil.copy(src, dst); print('Copied!')"
   ```

3. **Rebuild with the updated spec file** - it now explicitly includes the ONNX file.

### Error: "cublas64_*.dll not found"

**Cause:** CUDA DLLs not bundled or CUDA not installed.

**Solutions:**

**Option A: Copy CUDA DLLs**
```bash
# Find your CUDA installation
set CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6

# Copy to EXE directory
copy "%CUDA_PATH%\bin\cublas64_*.dll" ..\dist\WhisperTray\
copy "%CUDA_PATH%\bin\cudart64_*.dll" ..\dist\WhisperTray\
```

**Option B: Use CPU Mode**
Set environment variable before running:
```bash
set DEVICE=cpu
WhisperTray.exe
```

### Error: "Python not found" when running build.bat

- Install Python from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"
- Restart your terminal/PowerShell

### Build Fails with "ModuleNotFoundError"

Run this to ensure all dependencies are installed:
```bash
pip install --upgrade faster-whisper sounddevice pynput pystray Pillow pyperclip requests python-dotenv pyinstaller
```

### App Crashes on Startup

**Run the debug version** to see console output:
```
build_console.bat
```

Check `whisper_tray.log` in the same folder as the EXE for detailed error messages.

### No Tray Icon Appears

- Check system tray overflow (click the `^` arrow)
- Ensure no other instance is already running
- Run debug version to see errors

## Build Output Structure

After a successful build, the folder structure looks like:

```
dist/
└── WhisperTray/                  # or WhisperTray_DEBUG/
    ├── WhisperTray.exe           # Main executable
    └── _internal/                # Bundled dependencies
        ├── faster_whisper/
        │   └── assets/
        │       └── silero_vad_v6.onnx  # ← Critical file!
        ├── sounddevice/
        ├── PIL/
        └── ... (other packages)
```

## Distribution

To share WhisperTray with others:

1. **Zip the entire `dist\WhisperTray\` folder** (including `_internal`)
2. Users just need to:
   - Extract the zip
   - Run `WhisperTray.exe`
   - No Python installation required!

**Note:** Recipients still need:
- Windows 10/11
- NVIDIA drivers + CUDA (for GPU mode)
- Or they can use LM Studio mode (no GPU needed)

## Build Configuration

### Environment Variables

Create a `.env` file in the `whisper_tray` folder to customize the build:

```env
# Transcription mode: local or lmstudio
WHISPERTRAY_MODE=local

# Device: cuda or cpu
DEVICE=cuda

# Compute type: float16, int8, etc.
COMPUTE_TYPE=float16

# LM Studio URL (if using LM Studio mode)
LM_STUDIO_URL=http://localhost:1234

# LM Studio model name (leave empty for auto-detect)
LM_STUDIO_MODEL=
```

### Changing the Whisper Model

Edit `whisper_tray.py` line ~140:
```python
MODEL_SIZE: str = "large-v3"  # Change to: base, small, medium, large-v3
```

Smaller models = faster but less accurate.

## Verifying the Build

After building, verify everything works:

1. ✅ Tray icon appears (yellow while loading, then gray/green)
2. ✅ Hold `Ctrl+Space` - icon turns red (recording)
3. ✅ Release - transcription appears and auto-pastes
4. ✅ Right-click menu works (Language, Auto-Paste, Exit)
5. ✅ Check `whisper_tray.log` for any warnings

## Advanced: Custom PyInstaller Build

If you need more control:

```bash
pyinstaller --clean --noconfirm ^
    --name WhisperTray ^
    --onedir ^
    --windowed ^
    --add-data "path\to\faster_whisper\assets;faster_whisper\assets" ^
    --hidden-import=pynput.keyboard._win32 ^
    --hidden-import=pynput.mouse._win32 ^
    whisper_tray.py
```

## Support

- **Logs:** Check `whisper_tray.log` in the EXE directory
- **Debug mode:** Use `build_console.bat` for console output
- **Issues:** The spec file now explicitly bundles the ONNX file - rebuild if you have issues

---

**Last updated:** 2026-04-08
