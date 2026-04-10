# WhisperTray Deployment Guide

Complete guide for building and distributing WhisperTray on Windows.

## Table of Contents

- [Quick Start](#quick-start)
- [Building on Windows](#building-on-windows)
- [Building on Linux via GitHub Actions](#building-on-linux-via-github-actions)
- [Configuration](#configuration)
- [Distribution](#distribution)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Download Pre-built EXE

1. Go to **Releases** page on GitHub
2. Download the latest `WhisperTray-Windows.zip`
3. Extract to any folder
4. Run `WhisperTray.exe`
5. (Optional) Create a `.env` file next to the executable to customize settings

No Python installation required!

---

## Building on Windows

### Prerequisites

- **Windows 10/11** (64-bit)
- **Python 3.12+** - Download from [python.org](https://www.python.org/downloads/)
  - ✅ Check "Add Python to PATH" during installation
- **PyInstaller 6.15+** when building with Python 3.14
- **NVIDIA GPU** (optional, for GPU acceleration)

### Step-by-Step Build

#### 1. Install Build Dependencies

```bash
# From project root
pip install -e ".[build,ui]"
```

This installs `pyinstaller`, the optional `PySide6` overlay backend, and all
runtime dependencies.

If you are building with Python 3.14, make sure the environment resolves
`PyInstaller>=6.15.0`. Older PyInstaller releases can produce broken bundles
that fail to load `python314.dll`.

If you want a smaller tray-only build without the overlay window, you can still
use:

```bash
pip install -e ".[build]"
```

#### 2. Build the Executable

```bash
pyinstaller --clean --noconfirm packaging/windows/whisper_tray.spec
```

Or use PowerShell:

```powershell
$env:DEVICE = "cuda"  # or "cpu"
pyinstaller --clean --noconfirm packaging/windows/whisper_tray.spec
```

#### 3. Verify Build Output

The executable will be created at:

```
dist/WhisperTray/
├── WhisperTray.exe
└── _internal/
    └── faster_whisper/
        └── assets/
            └── silero_vad_v6.onnx  ← Critical file!
```

#### 4. Test the Executable

```bash
.\dist\WhisperTray\WhisperTray.exe
```

A system tray icon should appear. Hold `Ctrl+Shift+Space` to test recording.
If you want to test the on-screen overlay in the packaged build, create a
`.env` file next to the executable with settings like:

```env
OVERLAY_ENABLED=true
TRAY_BACKEND=auto
```

If you want to compare the legacy and unified tray runtimes during Windows QA,
set `TRAY_BACKEND=pystray` or `TRAY_BACKEND=qt` in that same `.env` file.

### Overlay QA Matrix

For Windows release verification, run this matrix against the packaged build:

1. `TRAY_BACKEND=qt`
2. `TRAY_BACKEND=pystray`

For each combination, verify:

- the overlay stays topmost and click-through
- the overlay does not steal focus
- the hotkey flow still records, transcribes, and pastes end to end
- successful transcriptions stay visible until the clipboard changes
- both `OVERLAY_SCREEN=primary` and `OVERLAY_SCREEN=cursor` behave correctly
- packaged-build behavior matches the same settings in source mode

### Debug Build (with Console)

For troubleshooting, build with a visible console:

```bash
pyinstaller --clean --noconfirm --name WhisperTray_DEBUG --console --onedir packaging/windows/whisper_tray.spec
```

Run `dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe` to see console output.

---

## Building on Linux via GitHub Actions

Build Windows executables from Linux using GitHub Actions - no Windows machine required!

### Method 1: One-Click Script

```bash
./trigger-windows-build.sh
```

This script will:
- ✅ Check your GitHub setup
- ✅ Push your code
- ✅ Trigger the GitHub Actions workflow
- ✅ Show you where to download the `.exe`

### Method 2: Manual Push

```bash
git add -A
git commit -m "build: trigger windows build"
git push
```

The workflow auto-triggers on push to `main` or `master`.

### Method 3: GitHub Web Interface

1. Go to your repo on GitHub
2. Click **Actions** tab
3. Click **"Build Windows EXE"** workflow
4. Click **"Run workflow"** → **"Run workflow"** button
5. Wait ~5-10 minutes

### Download the Build

**Via GitHub CLI:**
```bash
gh run list --workflow=build-windows.yml --limit 3
gh run download <run-id>
```

**Via Web Browser:**
1. Go to **Actions** → **Build Windows EXE** → Latest run
2. Scroll to **"Artifacts"** section
3. Click **"WhisperTray-Windows"** to download
4. Extract the zip → Run `WhisperTray.exe`

### What Gets Built

```
WhisperTray-Windows.zip
├── WhisperTray.exe           ← Release version (no console)
├── _internal/
│   └── faster_whisper/
│       └── assets/
│           └── silero_vad_v6.onnx  ← Auto-bundled ✅
└── ... (all dependencies)
```

Also creates: `WhisperTray-Windows-DEBUG.zip` (with console for debugging)

### Workflow Triggers

| Trigger | How |
|---------|-----|
| **Push to main/master** | Automatic |
| **Push tag (v*)** | Automatic + creates Release |
| **Pull Request** | Automatic (test only, no release) |
| **Manual** | Actions tab → Run workflow |

### Build Logs

If the build fails:
1. Go to **Actions** → Failed run
2. Click **"Build WhisperTray for Windows"** job
3. Read the step-by-step logs
4. Fix the issue and push again

### Tips

- **Artifact retention:** 30 days (download before they expire)
- **Build time:** ~5-10 minutes
- **Cost:** Free (GitHub Actions free tier: 2000 min/month)
- **No Windows needed:** Everything runs in GitHub's cloud!

---

## Configuration

### Using Environment Variables

Create a `.env` file next to `WhisperTray.exe` (or in project root for source mode):

```env
# Local model settings
MODEL_SIZE=large-v3
DEVICE=cuda
COMPUTE_TYPE=float16
LANGUAGE=en

# Hotkey settings
HOTKEY=ctrl,shift,space

# Behavior settings
AUTO_PASTE=true
PASTE_DELAY=0.1

# Optional overlay and tray runtime settings
OVERLAY_ENABLED=true
TRAY_BACKEND=auto
```

### No CUDA Installation Options

You can use WhisperTray **without installing CUDA Toolkit separately**:

#### Option A: Auto-Bundle CUDA from pip Packages

When you run `pip install faster-whisper`, CUDA DLLs are downloaded as part of the `ctranslate2` package. The build script bundles them automatically.

1. Ensure faster-whisper works with CUDA:
   ```cmd
   python -c "from faster_whisper import WhisperModel; model = WhisperModel('tiny', device='cuda'); print('CUDA works!')"
   ```

2. Build normally - CUDA DLLs will be auto-bundled

3. Verify CUDA DLLs were bundled:
   ```cmd
   dir dist\WhisperTray\_internal\cublas*.dll
   ```

#### Option B: CPU Mode Only

**Pros:** Zero dependencies, works everywhere  
**Cons:** Much slower transcription (5-10x)

```env
DEVICE=cpu
MODEL_SIZE=base
```

Use smaller models (`base` or `small`) for acceptable CPU performance.

---

## Distribution

### Sharing with Others

1. **Zip the entire `dist\WhisperTray\` folder** (including `_internal`)
2. Users just need to:
   - Extract the zip
   - Run `WhisperTray.exe`
   - No Python installation required!

### System Requirements for End Users

- Windows 10/11 (64-bit)
- 8GB+ RAM
- NVIDIA GPU with 4GB+ VRAM (or CPU mode fallback)

### Creating a GitHub Release

To create a permanent release with the `.exe` attached:

```bash
# Tag a version
git tag v1.0.0
git push origin v1.0.0
```

This auto-creates a GitHub Release with the `.exe` attached!

---

## Troubleshooting

### Common Build Issues

**"Python not found"**
- Install Python 3.12+ from python.org
- Check "Add Python to PATH" during installation
- Restart your terminal/PowerShell

**Build fails with "ModuleNotFoundError"**
```bash
pip install --upgrade faster-whisper sounddevice pynput pystray Pillow pyperclip python-dotenv pyinstaller
```

**"Failed to load Python DLL ...\\python314.dll"**
- This usually means the bundle was built with an older PyInstaller release or
  the generated `_internal` folder is missing next to the executable.
- Upgrade the packager and rebuild clean:
  ```bash
  pip install --upgrade "pyinstaller>=6.15.0"
  ```
- Run the executable from the generated app folder:
  ```cmd
  dist\WhisperTray\WhisperTray.exe
  ```
- Keep `WhisperTray.exe` and its sibling `_internal` directory together when
  copying or zipping the app.

**"NO_SUCHFILE: Load model from ...silero_vad_v6.onnx failed"**

The ONNX file wasn't bundled correctly.

**Solution:**
1. Check if ONNX exists in `_internal`:
   ```cmd
   dir /s dist\WhisperTray\_internal\faster_whisper\assets\silero_vad_v6.onnx
   ```

2. If missing, copy it manually:
   ```bash
   python -c "import faster_whisper, os, shutil; fw=os.path.dirname(faster_whisper.__file__); src=os.path.join(fw,'assets','silero_vad_v6.onnx'); dst=r'dist\WhisperTray\_internal\faster_whisper\assets'; os.makedirs(dst, exist_ok=True); shutil.copy(src, dst); print('Copied!')"
   ```

3. Rebuild with the updated spec file

**"cublas64_*.dll not found" (CUDA error)**

**Option A: Copy CUDA DLLs**
```bash
# Find your CUDA installation
set CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6

# Copy to EXE directory
copy "%CUDA_PATH%\bin\cublas64_*.dll" dist\WhisperTray\
copy "%CUDA_PATH%\bin\cudart64_*.dll" dist\WhisperTray\
```

**Option B: Use CPU Mode**
```env
DEVICE=cpu
```

### Common Runtime Issues

**App crashes on startup**

Run the debug version to see console output:
```
dist\WhisperTray_DEBUG\WhisperTray_DEBUG.exe
```

Check `whisper_tray.log` in the same folder as the EXE for detailed error messages.

**No tray icon appears**
- Check system tray overflow (click the `^` arrow)
- Ensure no other instance is already running
- Run debug version to see errors

**"CUDA out of memory"**
- Use a smaller model: `MODEL_SIZE=base` or `small`
- Close other GPU-intensive applications

**Hotkey not working**
- Run application as Administrator
- Check if hotkey is used by another application
- Change `HOTKEY` configuration in `.env`

**Transcription is slow**
- Ensure CUDA is properly installed
- Check GPU utilization in Task Manager
- Try a smaller model size

### Verifying the Build

After building, verify everything works:

1. ✅ Tray icon appears (yellow while loading, then gray)
2. ✅ Hold `Ctrl+Shift+Space` - icon turns red (recording)
3. ✅ Release - transcription appears and auto-pastes
4. ✅ Right-click menu works (Language, Auto-Paste, Exit)
5. ✅ Check `whisper_tray.log` for any warnings

---

## Build Output Structure

After a successful build, the folder structure looks like:

```
dist/
├── WhisperTray/                  # Release version
│   ├── WhisperTray.exe           # Main executable
│   └── _internal/                # Bundled dependencies
│       ├── faster_whisper/
│       │   └── assets/
│       │       └── silero_vad_v6.onnx
│       ├── sounddevice/
│       ├── PIL/
│       └── ... (other packages)
└── WhisperTray_DEBUG/            # Debug version (if built)
    ├── WhisperTray_DEBUG.exe
    └── _internal/
        └── ...
```

---

**Last updated:** 2026-04-09
