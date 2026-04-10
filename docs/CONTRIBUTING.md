# Contributing to WhisperTray

Developer-focused documentation for setting up, developing, and maintaining WhisperTray.

## Table of Contents

- [Project Architecture](#project-architecture)
- [Development Setup](#development-setup)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Code Style Guidelines](#code-style-guidelines)

---

## Project Architecture

### Directory Structure

```
whisper-tray/
├── whisper_tray/             # Main application package
│   ├── __init__.py
│   ├── __main__.py           # python -m whisper_tray entry point
│   ├── app.py                # Main application orchestrator
│   ├── cli.py                # CLI entry point
│   ├── config.py             # Configuration management
│   ├── clipboard.py          # Clipboard and paste operations
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── recorder.py       # Audio recording (sounddevice)
│   │   └── transcriber.py    # Whisper model + transcription
│   ├── input/
│   │   ├── __init__.py
│   │   └── hotkey.py         # Hotkey detection (pynput)
│   └── tray/
│       ├── __init__.py
│       ├── icon.py           # Tray icon management (pystray)
│       └── menu.py           # Context menu handlers
├── tests/                    # Test suite
├── build/                    # Build scripts and specs
│   ├── windows/
│   └── scripts/
├── docs/
│   ├── DEPLOYMENT.md         # Build and deployment guide
│   ├── CONTRIBUTING.md       # This file
│   └── plans/                # Planning documents
└── .github/workflows/        # CI/CD pipelines
    └── build-windows.yml     # Windows EXE build workflow
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `app.py` | Coordinates all subsystems, manages application lifecycle |
| `cli.py` | Command-line interface entry point |
| `config.py` | Type-safe configuration via dataclasses and environment variables |
| `clipboard.py` | Clipboard operations and paste simulation |
| `audio/recorder.py` | Microphone recording using sounddevice |
| `audio/transcriber.py` | Whisper model loading and transcription |
| `input/hotkey.py` | Global hotkey detection using pynput |
| `tray/icon.py` | System tray icon management using pystray |
| `tray/menu.py` | Context menu handlers and UI |

### Application Flow

1. **Startup**: Application loads configuration and initializes subsystems
2. **Model Loading**: Whisper model loads in background thread (non-blocking)
3. **Tray Ready**: System tray icon appears immediately (yellow while loading)
4. **Hotkey Active**: pynput listener monitors for hotkey combination
5. **Recording**: User holds hotkey → sounddevice captures audio chunks
6. **Transcription**: User releases hotkey → audio passed to Whisper model
7. **Output**: Result copied to clipboard, optionally auto-pasted
8. **Ready**: System returns to listening state

---

## Development Setup

### Prerequisites

- **Python**: 3.12+
- **OS**: Windows 10/11 (Linux/macOS for development only, no tray/hotkey testing)
- **Git**: For version control

### Quick Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd whisper-tray

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running the Application

```bash
# Via entry point
whisper-tray

# Or via module
python -m whisper_tray
```

### CUDA Setup (Optional)

For GPU-accelerated development:

1. Install CUDA Toolkit from [NVIDIA](https://developer.nvidia.com/cuda-toolkit)
2. Install cuDNN from [NVIDIA](https://developer.nvidia.com/cudnn)
3. Verify installation:
   ```bash
   nvcc --version
   ```

---

## Code Quality

### Running Quality Checks

```bash
# Format code
black whisper_tray/ tests/
isort whisper_tray/ tests/

# Lint
flake8 whisper_tray/ tests/

# Type check
mypy whisper_tray/

# Security scan
bandit -r whisper_tray/

# Run all checks (recommended before committing)
black whisper_tray/ tests/ && isort whisper_tray/ tests/ && flake8 whisper_tray/ tests/ && mypy whisper_tray/ && bandit -r whisper_tray/
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`:

```bash
# Run all hooks manually on all files
pre-commit run --all-files

# Run on staged files only (automatic)
pre-commit run
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=whisper_tray --cov-report=term-missing

# Run specific test file
pytest tests/test_config.py -v

# Run tests matching a pattern
pytest -k "hotkey"
```

### Test Structure

```
tests/
├── test_config.py      # Configuration tests
├── test_clipboard.py   # Clipboard operation tests
├── test_audio/         # Audio subsystem tests
├── test_input/         # Hotkey detection tests
└── test_tray/          # Tray icon tests
```

### Writing Tests

- Use `pytest` framework
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures for common setup
- Mock external dependencies (sounddevice, pynput, etc.)
- Test edge cases and error conditions

Example:

```python
def test_hotkey_debounce():
    """Test that rapid key presses don't trigger multiple recordings."""
    listener = HotkeyListener(
        hotkey={"ctrl", "shift", "space"},
        on_press=Mock(),
        on_release=Mock()
    )
    # Test implementation
```

---

## Code Style Guidelines

`prompts/CODESTYLE.md` is the canonical coding-style guide for WhisperTray.

Before editing code:

- Read `prompts/CODESTYLE.md` and follow its `Must`, `Prefer`, and `Legacy tolerated` guidance.
- Treat checked-in tool config as the source of truth for formatter, lint, type-check, security, secrets, and validation rules.
- If this file, another Markdown file, or an older example conflicts with `prompts/CODESTYLE.md`, `pyproject.toml`, `.flake8`, `.pre-commit-config.yaml`, or `scripts/validate-build.py`, follow the canonical style guide and checked-in config.

Key repo expectations, summarized:

- Keep configuration and environment parsing centralized in `config.py`.
- Preserve CPU-first defaults, cross-platform safety, and graceful fallback behavior.
- Do not block tray or hotkey responsiveness with long-running work.
- Prefer typed dataclasses, protocols, and explicit result objects at subsystem boundaries.
- Add or update deterministic pytest coverage for behavior changes.

For naming, logging, typing, fallback behavior, testing seams, and definition-of-done requirements, use `prompts/CODESTYLE.md` instead of duplicating local style rules here.

---

## Building Windows Executable

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete build instructions.

Quick build on Windows:

```bash
pyinstaller --clean --noconfirm packaging/windows/whisper_tray.spec
```

---

## Release Process

1. Update version in `pyproject.toml`
2. Create and push tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. GitHub Actions will:
   - Build Windows EXE
   - Create GitHub Release
   - Attach build artifacts
4. Verify release on GitHub

---

**Last updated:** 2026-04-09
