# WhisperTray Project Context

## Project Overview

**WhisperTray** is a Windows system tray application that provides global speech-to-text functionality using OpenAI's Whisper model via the `faster-whisper` library.

### Core Functionality
1. User holds a configurable hotkey (default: `Ctrl+Shift+Space`)
2. App records audio from the default microphone
3. On hotkey release, audio is transcribed with faster-whisper
4. Result is copied to clipboard AND auto-pasted into the focused text field via `Ctrl+V`

### Tech Stack
- **faster-whisper**: Optimized Whisper inference (CUDA, float16, large-v3 model)
- **sounddevice**: Microphone recording (16kHz, mono, float32)
- **pynput**: Global hotkey detection
- **pystray + Pillow**: System tray icon with dynamic status indicators
- **pyperclip**: Clipboard operations
- **pyautogui**: Paste simulation

## Directory Structure

```
whisper-tray/
├── README.md                         # Primary user-facing documentation
├── QWEN.md                           # This file - AI assistant context
├── pyproject.toml                    # Project configuration
├── .claude/                          # Claude IDE settings
├── .github/workflows/                # CI/CD pipelines
│   └── build-windows.yml             # Windows EXE build workflow
├── prompts/                          # (Empty) Reserved for prompt templates
├── whisper_tray/                     # Main application package
│   ├── __init__.py
│   ├── __main__.py                   # python -m whisper_tray entry point
│   ├── app.py                        # Main application orchestrator
│   ├── cli.py                        # CLI entry point
│   ├── config.py                     # Configuration management
│   ├── clipboard.py                  # Clipboard and paste operations
│   ├── audio/
│   │   ├── recorder.py               # Audio recording (sounddevice)
│   │   └── transcriber.py            # Whisper model + transcription
│   ├── input/
│   │   └── hotkey.py                 # Hotkey detection (pynput)
│   └── tray/
│       ├── icon.py                   # Tray icon management (pystray)
│       └── menu.py                   # Context menu handlers
├── tests/                            # Test suite
├── build/                            # Build scripts and specs
│   ├── windows/
│   └── scripts/
└── docs/
    ├── DEPLOYMENT.md                 # Build and deployment guide
    └── CONTRIBUTING.md               # Developer documentation
```

## Configuration (Defined in `whisper_tray/config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_SIZE` | `large-v3` | Whisper model variant |
| `DEVICE` | `cuda` | Inference device |
| `COMPUTE_TYPE` | `float16` | CUDA compute precision |
| `LANGUAGE` | (auto-detect) | Speech language |
| `HOTKEY` | `Ctrl+Shift+Space` | Recording trigger |
| `AUTO_PASTE` | `True` | Enable auto-paste feature |
| `PASTE_DELAY` | (configurable) | Seconds before Ctrl+V fires |

## Tray Icon Behavior

- **Gray circle**: Idle state
- **Red circle**: Recording state (dynamic icon change)
- **Right-click menu**: "Toggle auto-paste", "Exit"
- **Tooltip**: Shows current status (e.g., "Loading model…", "Ready", "Recording")

## Error Handling Requirements

- Ignore recordings shorter than 0.3 seconds
- Use faster-whisper built-in VAD filter (`min_silence_duration_ms=500`)
- Print errors to stdout, never crash the tray

## Startup Sequence

1. Load model in a background thread (tray appears instantly)
2. Show "Loading model…" tooltip until ready
3. Block hotkey handling until model is fully loaded

## Development Conventions

- **MANDATORY**: Before editing any code, read `prompts/CODESTYLE.md` and follow the coding style guide.
- **Modular architecture**: Logic separated into domain-specific modules
- **Configuration**: Type-safe dataclasses in `config.py`
- **Pinned dependencies**: `requirements.txt` with exact versions
- **No placeholders**: Write complete, working code
- **Graceful degradation**: Handle errors without crashing
- **Testable design**: Each module can be tested independently

### Code Quality Tools

| Tool | Purpose | Command |
|------|---------|---------|
| **black** | Code formatting | `black whisper_tray/` |
| **isort** | Import sorting | `isort whisper_tray/` |
| **flake8** | Linting | `flake8 whisper_tray/` |
| **mypy** | Type checking | `mypy whisper_tray/` |
| **bandit** | Security scanning | `bandit -r whisper_tray/` |
| **pytest** | Testing | `pytest` |
| **validate-build** | Build validation | `python scripts/validate-build.py` |
| **pre-commit** | Git hooks | `pre-commit run --all-files` |

### Setup Commands

```bash
# Install pre-commit hooks (run once)
pip install pre-commit
pre-commit install

# Install project with dev dependencies
pip install -e ".[dev]"

# Run all quality checks
black whisper_tray/ tests/ && isort whisper_tray/ tests/ && flake8 whisper_tray/ tests/ && mypy whisper_tray/ && bandit -r whisper_tray/
```

## Building and Running

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Run the application
whisper-tray
# Or
python -m whisper_tray
```

### CUDA Requirements
- NVIDIA GPU with CUDA support
- CUDA Toolkit installed
- cuDNN libraries

## Related Files

- `README.md`: Primary user-facing documentation
- `docs/DEPLOYMENT.md`: Build and deployment instructions
- `docs/CONTRIBUTING.md`: Developer documentation
- `.claude/settings.json`: IDE-specific permissions configuration

## Qwen Added Memories
- Always run `python scripts/check.py` after making changes to the project to ensure all code quality checks pass.
- After running checks successfully, always suggest the user to make a commit using the commit-name skill.
