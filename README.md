# WhisperTray

A cross-platform system tray application for global speech-to-text using OpenAI's Whisper model. Hold a hotkey, speak, and release to instantly transcribe your voice to clipboard and paste into any text field.

**CPU-first design:** optimized for fast transcription on CPU. GPU acceleration is optional and opt-in.

## Features

- 🎤 **Global Hotkey Activation** — Press `Ctrl+Shift+Space` (configurable) from any application to start recording
- 📋 **Auto-Clipboard** — Transcribed text automatically copied to clipboard
- ⚡ **Auto-Paste** — Optional automatic paste into the focused text field (`Cmd+V` on macOS, `Ctrl+V` elsewhere)
- 🔊 **VAD Filter** — Built-in voice activity detection filters silence and background noise
- 🎨 **Status Indicator** — System tray icon changes color (green=idle, red=recording, orange=processing)
- 🪟 **Optional Overlay** — PySide6-powered on-screen overlay with shared state-driven copy, actionable error hints, and a shared Qt tray runtime when UI extras are installed
- 🚀 **CPU-Optimized** — `int8` quantization, greedy decoding, single worker thread — fast by default
- 💻 **Cross-Platform** — Windows, Linux, macOS
- 📦 **Standalone EXE** — Can be built as a portable executable (no Python required)

## Quick Start

### Option 1: Download Pre-built EXE (Windows, Recommended)

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
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install and run
pip install -e ".[dev]"
whisper-tray
```

To enable the optional on-screen overlay and the unified Qt tray runtime, install the UI extras:

```bash
pip install -e ".[dev,ui]"
```

## Usage

1. **Start** the application — the tray icon appears immediately (green = ready)
2. **Hold** `Ctrl+Shift+Space` to begin recording (icon turns red)
3. **Speak** clearly into your microphone
4. **Release** the hotkey to transcribe (icon flashes orange while processing)
5. Text is automatically copied to clipboard and pasted

When the overlay is enabled, both styles reflect the same shared app-state
model. Successful transcriptions enter a persistent `TRANSCRIBED` overlay state
that stays visible until WhisperTray no longer owns the clipboard, a new
recording starts, or an error replaces it.

### Tray Menu

| Option | Description |
|--------|-------------|
| **Language** | Set transcription language: English, Russian, or Auto-Detect |
| **Toggle Auto-Paste** | Enable/disable automatic pasting |
| **Overlay** | Enable the optional on-screen overlay, choose its corner and display target, tune ready auto-hide behavior, switch between compact or detailed view, and surface actionable recovery hints for failures. |
| **Exit** | Close the application |

### Icon Colors

| Color | Meaning |
|-------|---------|
| **Green** | Ready/idle |
| **Red** | Recording |
| **Orange (flashing)** | Processing/transcribing |

## Configuration

Create a `.env` file in the project root (or next to `WhisperTray.exe`):

```env
# Model settings — CPU-first defaults
MODEL_SIZE=small        # Options: tiny, base, small, medium, large, large-v3
DEVICE=cpu              # Options: cpu, cuda (GPU is opt-in)
COMPUTE_TYPE=int8       # Options: int8 (CPU), float16 (CUDA)
LANGUAGE=en             # Options: en, ru, or omit for auto-detect

# Decoding optimization
BEAM_SIZE=1             # 1 = greedy (fast), >1 = beam search (slower, better quality)
CONDITION_ON_PREVIOUS_TEXT=false  # false = treat each utterance independently (faster)

# VAD settings
VAD_THRESHOLD=0.5       # Voice activity detection sensitivity (0.0-1.0)
VAD_SILENCE_DURATION_MS=500  # Min silence (ms) to mark segment boundary
MIN_RECORDING_DURATION=0.3   # Min recording length (seconds) to process
SAMPLE_RATE=16000       # Audio sample rate (Hz)

# CPU threading
CPU_THREADS=4           # Limit CPU threads (sets OMP_NUM_THREADS + ONNX_NUM_THREADS)

# Hotkey settings
HOTKEY=ctrl,shift,space

# Behavior settings
AUTO_PASTE=true
PASTE_DELAY=0.1

# Optional overlay settings (requires pip install -e ".[ui]")
OVERLAY_ENABLED=false
OVERLAY_AUTO_HIDE_SECONDS=1.5  # 0 keeps the ready state visible
OVERLAY_POSITION=bottom-right  # top-left, top-right, bottom-left, bottom-right
OVERLAY_SCREEN=primary         # primary, cursor (follows the display under the pointer while visible)
OVERLAY_DENSITY=detailed       # detailed, compact

# Optional tray runtime selection
TRAY_BACKEND=auto              # auto, pystray, qt
```

`TRAY_BACKEND=auto` prefers the shared Qt tray runtime when `PySide6` is
installed. Set `TRAY_BACKEND=pystray` to keep the legacy tray loop even with
UI extras installed, or `TRAY_BACKEND=qt` to explicitly request the unified Qt
runtime and still fall back safely if Qt cannot start.

### Performance Presets

Quick presets for different use cases. Set these in your `.env` file:

| Preset | `MODEL_SIZE` | `DEVICE` | `COMPUTE_TYPE` | `BEAM_SIZE` | Best for |
|--------|-------------|----------|----------------|-------------|----------|
| **`fast`** | `base` | `cpu` | `int8` | `1` | Short commands, low latency |
| **`balanced`** (default) | `small` | `cpu` | `int8` | `1` | General-purpose use |
| **`accurate`** | `medium` | `cpu` | `int8` | `5` | Longer dictation, better quality |
| **`gpu`** | `large-v3` | `cuda` | `float16` | `5` | GPU-equipped machines |

Example — enable the `fast` preset:
```env
MODEL_SIZE=base
DEVICE=cpu
COMPUTE_TYPE=int8
BEAM_SIZE=1
```

### Model Size Recommendations

| Model | RAM/CPU | Speed | Accuracy |
|-------|---------|-------|----------|
| `tiny` | ~500MB | Fastest | Lower |
| `base` | ~700MB | Fast | Good |
| `small` | ~1GB | Medium | Better |
| `medium` | ~3GB | Slow | High |
| `large-v3` | ~10GB | Slowest | Best |

## Platform-Specific Notes

### macOS

- Uses `Cmd+V` for auto-paste (not `Ctrl+V`)
- Runs CPU-only (no CUDA/MPS). Use `base` or `small` model for best performance.
- Requires `pyobjc-framework-Cocoa` and `pyobjc-framework-Quartz` (installed automatically via conditional dependencies)

### Linux

- Works with PulseAudio/PipeWire for microphone input
- GPU acceleration requires NVIDIA GPU + CUDA Toolkit + cuDNN

### Windows

- Standalone EXE available via PyInstaller
- Python 3.14 builds require PyInstaller 6.15+
- GPU acceleration requires CUDA Toolkit 11.8+ and NVIDIA GPU

## Requirements

### Hardware

- **RAM**: 4GB+ system RAM (8GB+ for medium/large models)
- **Microphone**: Any working microphone
- **GPU** (optional): NVIDIA GPU with CUDA support for accelerated transcription

### Software

- **OS**: Windows 10/11, macOS 12+, or Linux
- **Python**: 3.12+ (for source mode)
- **CUDA Toolkit**: 11.8 or 12.x (optional, only for GPU acceleration)

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
- Code style guidelines, with [prompts/CODESTYLE.md](prompts/CODESTYLE.md) as the canonical style source

## Troubleshooting

**"Not enough memory" or "Unanticipated host error" (MME error 7)**
- Close memory-intensive applications
- Use a smaller model: `MODEL_SIZE=base` or `tiny`
- Restart the application after making changes

**Transcription is slow**
- Use the `fast` preset (see above): `MODEL_SIZE=base`, `BEAM_SIZE=1`
- Set `CPU_THREADS` to match your CPU core count
- If using GPU, ensure CUDA is properly installed

**Tray icon doesn't appear**
- The icon appears immediately, but the model loads in the background. Wait a few seconds for the tooltip to change from "Loading model..." to "Ready".
- Click the `^` arrow in the system tray to show hidden icons
- Check `whisper_tray.log` for error messages

**Hotkey not working**
- Check if hotkey is used by another application
- Change `HOTKEY` in `.env` file
- On macOS, ensure Accessibility permissions are granted

**Auto-paste not working on macOS**
- Ensure Accessibility permissions are granted for your terminal/app
- The app uses `Cmd+V` on macOS automatically

**No text output (empty transcription)**
- Check that your microphone is working and not muted
- Try lowering `VAD_THRESHOLD` (e.g., `0.3`) for quieter speech
- Try setting `LANGUAGE=en` (or your language) instead of auto-detect

For more troubleshooting steps, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## License

MIT License

## Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized Whisper inference
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [pystray](https://github.com/moses-palmer/pystray) - System tray support
- [pynput](https://github.com/moses-palmer/pynput) - Hotkey detection
