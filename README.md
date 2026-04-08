# WhisperTray

A Windows system tray application that provides global speech-to-text functionality using OpenAI's Whisper model. Hold a hotkey, speak, and release to instantly transcribe your voice to clipboard and paste into any text field.

## Features

- 🎤 **Global Hotkey Activation** - Press `Ctrl+Shift+Space` (configurable) from any application to start recording
- 📋 **Auto-Clipboard** - Transcribed text automatically copied to clipboard
- ⚡ **Auto-Paste** - Optional automatic paste into the focused text field
- 🔊 **VAD Filter** - Built-in voice activity detection filters silence and background noise
- 🎨 **Status Indicator** - System tray icon changes color (gray=idle, red=recording)
- 🚀 **GPU Accelerated** - CUDA support for fast transcription with faster-whisper
- 📦 **Standalone EXE** - Can be built as a portable executable (no Python required)

## Quick Start

### Option 1: Download Pre-built EXE (Recommended)

1. Go to **Releases** page and download the latest `WhisperTray-Windows.zip`
2. Extract and run `WhisperTray.exe`
3. No Python installation required!

### Option 2: Run from Source

```bash
# Clone the repository
git clone <your-repo-url>
cd whisper-tray

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install and run
pip install -e ".[dev]"
whisper-tray
```

## Usage

1. **Start** the application - wait for "Ready" status in tray tooltip
2. **Hold** `Ctrl+Shift+Space` to begin recording (icon turns red)
3. **Speak** clearly into your microphone
4. **Release** the hotkey to transcribe
5. Text is automatically copied to clipboard and pasted

### Tray Menu

| Option | Description |
|--------|-------------|
| **Language** | Set transcription language: English, Russian, or Auto-Detect |
| **Toggle auto-paste** | Enable/disable automatic pasting |
| **Exit** | Close the application |

### Icon Colors

| Color | Meaning |
|-------|---------|
| **Gray** | Ready |
| **Red** | Recording |
| **Yellow** | Loading/Not ready |

## Configuration

Create a `.env` file in the project root (or next to `WhisperTray.exe`):

```env
# Model settings
MODEL_SIZE=large-v3     # Options: tiny, base, small, medium, large-v3
DEVICE=cuda             # Options: cuda, cpu
COMPUTE_TYPE=float16    # Options: float16, int8, int8_float16
LANGUAGE=en             # Options: en, ru, or omit for auto-detect

# Hotkey settings
HOTKEY=ctrl,shift,space

# Behavior settings
AUTO_PASTE=true
PASTE_DELAY=0.1
```

### Model Size Recommendations

| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~1GB | Fastest | Lower |
| `base` | ~1GB | Fast | Good |
| `small` | ~2GB | Medium | Better |
| `medium` | ~5GB | Slow | High |
| `large-v3` | ~10GB | Slowest | Best |

## Requirements

### Hardware

- **GPU**: NVIDIA GPU with CUDA support (4GB+ VRAM recommended for large-v3)
- **RAM**: 8GB+ system RAM
- **Microphone**: Any working microphone

### Software

- **OS**: Windows 10/11
- **Python**: 3.10, 3.11, or 3.12 (for source mode)
- **CUDA Toolkit**: 11.8 or 12.x (optional, for GPU acceleration)

## Building Windows Executable

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete build instructions, including:
- Building on Windows locally
- Building on Linux via GitHub Actions
- CUDA bundling options
- Troubleshooting

## Development

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for:
- Project architecture overview
- Setting up development environment
- Running tests and quality checks
- Code style guidelines

## Troubleshooting

**"CUDA out of memory"**
- Use a smaller model: `MODEL_SIZE=base` or `small`
- Close other GPU-intensive applications

**Hotkey not working**
- Run application as Administrator
- Check if hotkey is used by another application
- Change `HOTKEY` in `.env` file

**Transcription is slow**
- Ensure CUDA is properly installed (if using GPU mode)
- Try a smaller model size
- Check GPU utilization in Task Manager

**No tray icon appears**
- Click the `^` arrow in the system tray to show hidden icons
- Check `whisper_tray.log` for error messages

For more troubleshooting steps, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## License

MIT License

## Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized Whisper inference
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [pystray](https://github.com/moses-palmer/pystray) - System tray support
- [pynput](https://github.com/moses-palmer/pynput) - Hotkey detection
