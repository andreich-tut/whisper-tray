# WhisperTray Windows Deployment Guide

## Quick Start (For End Users)

If you just want to use WhisperTray without building from source:

1. **Download** the pre-built `WhisperTray.exe` from the releases page
2. **Create** a `.env` file next to the executable (optional)
3. **Run** `WhisperTray.exe`
4. **Look** for the WhisperTray icon in the system tray

## Building from Source

### Prerequisites

- **Windows 10/11**
- **Python 3.10+** (64-bit)

### Build Steps

#### Option A: Using the Batch File (Easiest)

1. Copy the `whisper-tray` folder to Windows
2. Open the `whisper_tray` subfolder
3. Double-click `build.bat`
4. Find `WhisperTray.exe` in the `dist\` folder (parent directory)

#### Option B: Manual Build

```bash
# Navigate to whisper_tray folder
cd whisper_tray

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install faster-whisper sounddevice pynput pystray Pillow pyperclip python-dotenv pyinstaller

# Build the executable
pyinstaller --clean whisper_tray.spec
```

### Configuration

Create a `.env` file next to `WhisperTray.exe`:

```env
MODEL_SIZE=large-v3
DEVICE=cuda
COMPUTE_TYPE=float16
```

## Distribution

### Sharing with Others

1. **Copy** `dist/WhisperTray.exe` to a folder
2. **Copy** `.env` file (if created)
3. **Share** via USB, network, cloud, or ZIP

### System Requirements

- Windows 10/11 (64-bit)
- 8GB+ RAM
- NVIDIA GPU with 4GB+ VRAM (or CPU mode will be used as fallback)

## Troubleshooting

**"Python not found"**
- Install Python 3.10+ from python.org
- Check "Add Python to PATH" during installation

**Build fails**
- Run as Administrator
- Close any running WhisperTray instances

**"NO_SUCHFILE : Load model from ...silero_vad_v6.onnx failed"**
- The spec file now automatically bundles faster-whisper assets
- Rebuild with: `build.bat` (the spec file collects ONNX files automatically)
- Ensure you have the latest `whisper_tray.spec` file

**"cublas64_12.dll is not found" (CUDA error)**
- The build script now copies CUDA DLLs automatically if CUDA is installed
- Make sure CUDA Toolkit is installed: https://developer.nvidia.com/cuda-downloads
- Run `build_console.bat` or `build.bat` - CUDA DLLs will be copied to dist folder
- If CUDA is not in default location, add CUDA_PATH/bin to system PATH

**No tray icon appears**
- Click the ^ arrow in the system tray to show hidden icons
- Run `run_debug.bat` to see console output for errors
- Check `whisper_tray.log` for error messages

## Support

For more details:
- `README.md` - General usage
- `.env.example` - Configuration options
