# WhisperTray

A Windows system tray application that provides global speech-to-text functionality using OpenAI's Whisper model. Hold a hotkey, speak, and release to instantly transcribe your voice to clipboard and paste into any text field.

## Features

- 🎤 **Global Hotkey Activation** - Press `Ctrl+Shift+Space` (configurable) from any application to start recording
- 📋 **Auto-Clipboard** - Transcribed text automatically copied to clipboard
- ⚡ **Auto-Paste** - Optional automatic paste into the focused text field
- 🔊 **VAD Filter** - Built-in voice activity detection filters silence and background noise
- 🎨 **Status Indicator** - System tray icon changes color (gray=idle, red=recording, green=LM Studio)
- 🚀 **GPU Accelerated** - CUDA support for fast transcription with faster-whisper
- 🔌 **LM Studio Support** - Optional mode to use LM Studio API instead of local model (no download needed)
- 📦 **Standalone EXE** - Can be built as a portable executable (no Python required)

> 📖 **Windows User?** See [DEPLOYMENT.md](DEPLOYMENT.md) for easy .exe building instructions.

## Requirements

### Hardware

#### Local Mode (faster-whisper)
- **GPU**: NVIDIA GPU with CUDA support (4GB+ VRAM recommended for large-v3 model)
- **RAM**: 8GB+ system RAM
- **Microphone**: Any working microphone

#### LM Studio Mode
- **RAM**: 4GB+ system RAM
- **Microphone**: Any working microphone
- **LM Studio**: Installed and running with a Whisper model loaded

### Software
- **OS**: Windows 10/11
- **Python**: 3.10, 3.11, or 3.12
- **CUDA Toolkit**: 11.8 or 12.x (matching your GPU drivers) - *Local mode only*
- **cuDNN**: Compatible with your CUDA version - *Local mode only*
- **LM Studio**: v0.2.0+ - *LM Studio mode only*

## Installation

### Option A: Local Mode (faster-whisper)

#### 1. Install CUDA (if not already installed)

1. Download CUDA Toolkit from [NVIDIA](https://developer.nvidia.com/cuda-toolkit)
2. Download cuDNN from [NVIDIA](https://developer.nvidia.com/cudnn) (requires account)
3. Follow NVIDIA's installation instructions
4. Verify installation:
   ```bash
   nvcc --version
   ```

#### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip
```

#### 3. Install Dependencies

```bash
# Install with CUDA support
pip install -e ".[dev]"
```

> **Note**: If you encounter CUDA issues, try installing PyTorch with CUDA first:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu118
> ```

### Option B: LM Studio Mode (No Local Model Download)

#### 1. Install LM Studio

1. Download LM Studio from [https://lmstudio.ai](https://lmstudio.ai)
2. Install and launch LM Studio

#### 2. Download a Whisper Model in LM Studio

1. Click the "Download" button (magnet icon)
2. Search for a Whisper model (e.g., "whisper-large-v3")
3. Download your preferred model size

#### 3. Start the Local Server

1. Go to the "Server" tab in LM Studio
2. Select the downloaded Whisper model
3. Click "Start Server"
4. Note the server URL (default: `http://localhost:1234`)

#### 4. Set Up Python Environment and Install

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -e ".[dev]"
```

#### 5. Configure for LM Studio Mode

Create a `.env` file in the project root:

```bash
# Use LM Studio mode
WHISPERTRAY_MODE=lmstudio

# LM Studio server URL (adjust if needed)
LM_STUDIO_URL=http://localhost:1234
```

### Install Pre-commit Hooks (Optional but Recommended)

```bash
pre-commit install
```

## Building Windows Executable (.exe)

To create a standalone executable that doesn't require Python:

### Quick Build (on Windows)

1. **Copy** the `whisper-tray` folder to your Windows computer
2. **Open** the `whisper_tray` subfolder
3. **Double-click** `build.bat`
4. **Wait** for the build to complete
5. **Find** `WhisperTray.exe` in the `dist\` folder

### What This Does

- Installs all required dependencies
- Builds a standalone `.exe` file (~50-100MB)
- Creates output in `dist/WhisperTray.exe`
- No Python required on the target machine

### Configuration (Optional)

Create a `.env` file next to `WhisperTray.exe`:

```env
# For LM Studio mode (no model download needed)
WHISPERTRAY_MODE=lmstudio
LM_STUDIO_URL=http://localhost:1234

# OR for local mode (downloads Whisper model)
WHISPERTRAY_MODE=local
MODEL_SIZE=large-v3
```

For detailed build instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Usage

### Running the Application

```bash
# Activate virtual environment if not already active
venv\Scripts\activate

# Run WhisperTray
whisper-tray

# Or run directly
python -m whisper_tray.whisper_tray
```

### Basic Operation

1. **Start** the application - wait for "Ready" status in tray tooltip
2. **Hold** `Ctrl+Shift+Space` to begin recording (icon turns red)
3. **Speak** clearly into your microphone
4. **Release** the hotkey to transcribe
5. Text is automatically copied to clipboard and pasted

### Tray Menu Options

| Option | Description |
|--------|-------------|
| **Mode** | Select transcription mode: Local Whisper or LM Studio |
| **Language** | Set transcription language: English, Russian, or Auto-Detect |
| **Toggle auto-paste** | Enable/disable automatic pasting after transcription |
| **Exit** | Close the application |

### Icon Colors

| Color | Meaning |
|-------|---------|
| **Gray** | Idle (Local mode ready) |
| **Red** | Recording |
| **Green** | LM Studio mode ready |
| **Yellow** | Loading/Not ready |

## Configuration

### Using Environment Variables (Recommended)

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Transcription mode: "local" or "lmstudio"
WHISPERTRAY_MODE=local

# LM Studio settings (only used when WHISPERTRAY_MODE=lmstudio)
LM_STUDIO_URL=http://localhost:1234
LM_STUDIO_MODEL=

# Local model settings (only used when WHISPERTRAY_MODE=local)
MODEL_SIZE=large-v3
DEVICE=cuda
COMPUTE_TYPE=float16

# Hotkey settings
HOTKEY=ctrl,shift,space

# Behavior settings
AUTO_PASTE=true
PASTE_DELAY=0.1
```

### Editing Source Code (Alternative)

Edit `whisper_tray/whisper_tray.py` to customize settings:

```python
# Model settings
MODEL_SIZE = "large-v3"      # Options: tiny, base, small, medium, large-v3
DEVICE = "cuda"              # Options: cuda, cpu
COMPUTE_TYPE = "float16"     # Options: float16, int8, int8_float16
LANGUAGE = None              # None = auto-detect, or "en", "es", "fr", etc.

# Hotkey settings
HOTKEY = {Key.ctrl, Key.shift, Key.space}  # Custom hotkey combination

# Behavior settings
AUTO_PASTE = True            # Auto-paste transcription after copying
PASTE_DELAY = 0.1            # Seconds to wait before pasting
```

### Model Size Recommendations

| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~1GB | Fastest | Lower |
| `base` | ~1GB | Fast | Good |
| `small` | ~2GB | Medium | Better |
| `medium` | ~5GB | Slow | High |
| `large-v3` | ~10GB | Slowest | Best |

## Development

### Code Quality

```bash
# Format code
black whisper_tray/
isort whisper_tray/

# Lint
flake8 whisper_tray/

# Type check
mypy whisper_tray/

# Security scan
bandit -r whisper_tray/

# Run tests
pytest
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```bash
# Run all hooks manually
pre-commit run --all-files
```

### Building from Source

```bash
# Install build tools
pip install build

# Build distribution
python -m build

# Install local build
pip install dist/*.whl
```

### Building Windows Executable (.exe)

To create a standalone Windows executable that doesn't require Python:

#### 1. Install Build Dependencies

```bash
# Install pyinstaller and build dependencies
pip install -e ".[build]"
```

#### 2. Build the Executable

```bash
# Run the build script
python build_exe.py
```

This will create `dist/WhisperTray.exe` - a standalone executable that includes:
- All Python dependencies
- The application code
- Everything needed to run on Windows (no Python installation required)

#### 3. Distribute and Run

```bash
# Copy the executable to your desired location
# The .exe file is ~50-100MB (includes all dependencies)

# Optional: Create a .env file next to the .exe for configuration
# Copy .env.example to .env and adjust settings
```

#### Build Options

**For Local Mode (smaller .exe, downloads model on first run):**
```bash
# Default build - user can download model on first run
# Model size: ~3GB for large-v3
```

**For LM Studio Mode (no model download needed):**
```bash
# Create .env file next to WhisperTray.exe:
WHISPERTRAY_MODE=lmstudio
LM_STUDIO_URL=http://localhost:1234
```

#### Troubleshooting Builds

**"Module not found" errors:**
- Ensure all dependencies are installed: `pip install -e ".[build]"`
- Check the hiddenimports in `whisper_tray/whisper_tray.spec`

**Build succeeds but .exe doesn't run:**
- Run with `--console` flag to see errors (edit .spec file: `console=True`)
- Check Windows Defender - it may block unsigned executables
- Ensure Visual C++ Redistributable is installed on target machine

**Large .exe file:**
- This is normal - it includes Python and all dependencies
- Use UPX compression (enabled by default) to reduce size
- Consider using `--onefile` mode (already enabled in spec)

## Troubleshooting

### Common Issues

#### Local Mode Issues

**"CUDA out of memory"**
- Use a smaller model: `MODEL_SIZE = "base"` or `"small"`
- Close other GPU-intensive applications

**"No module named 'sounddevice'"**
- Run: `pip install -e ".[dev]"`
- Ensure virtual environment is activated

**Transcription is slow**
- Ensure CUDA is properly installed
- Check GPU utilization in Task Manager
- Try a smaller model size

#### LM Studio Mode Issues

**"LM Studio not available" or "Cannot connect"**
- Ensure LM Studio is running
- Check that the server is started in LM Studio (Server tab → Start Server)
- Verify the URL in your `.env` file matches LM Studio's server URL
- Check firewall settings - LM Studio server may be blocked

**"No models loaded in LM Studio"**
- Download a Whisper model in LM Studio first
- Load the model in the Server tab before starting WhisperTray

**Transcription fails or returns empty text**
- Ensure you have a Whisper model loaded (not just an LLM)
- Check LM Studio server logs for errors
- Try a different Whisper model variant

#### General Issues

**Hotkey not working**
- Run application as Administrator
- Check if hotkey is used by another application
- Change `HOTKEY` configuration

**Microphone not detected**
- Check Windows sound settings
- Ensure default recording device is set
- Test microphone in Windows Sound Control Panel

### Getting Help

1. Check this README for troubleshooting steps
2. Review error messages in the console output
3. Check `whisper_tray.log` for detailed logs
4. Verify CUDA installation with `nvcc --version` (local mode)
5. Check LM Studio server status (LM Studio mode)

## License

MIT License - See LICENSE file for details

## Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized Whisper inference
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [LM Studio](https://lmstudio.ai) - Local LLM and Whisper model server
- [pystray](https://github.com/moses-palmer/pystray) - System tray support
- [pynput](https://github.com/moses-palmer/pynput) - Hotkey detection
