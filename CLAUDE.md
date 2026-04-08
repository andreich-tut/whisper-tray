# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhisperTray is a Windows system tray application for global speech-to-text. Hold `Ctrl+Shift+Space` → speak → release → text is transcribed via faster-whisper and pasted into the focused window. Primarily targets Windows, but the core logic (config, audio, transcription) is platform-agnostic and can be developed/tested on Linux/macOS.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -e ".[dev]"
pre-commit install
```

## Commands

```bash
# Run application
whisper-tray
python -m whisper_tray

# Tests
pytest                                    # all tests with coverage
pytest tests/test_config.py -v            # single file
pytest -k "hotkey"                        # by pattern

# Formatting & linting (run before committing)
black whisper_tray/ tests/
isort whisper_tray/ tests/
flake8 whisper_tray/ tests/
mypy whisper_tray/
bandit -r whisper_tray/

# Or all at once
black whisper_tray/ tests/ && isort whisper_tray/ tests/ && flake8 whisper_tray/ tests/ && mypy whisper_tray/ && bandit -r whisper_tray/
```

## Architecture

The application is structured as independent subsystems coordinated by `app.py`:

- **`app.py`** — `WhisperTrayApp`: the central orchestrator. Wires together all subsystems, manages the recording state machine, and runs the pystray event loop on the main thread.
- **`config.py`** — `AppConfig` / `ModelConfig` / `HotkeyConfig` / `AudioConfig`: typed dataclasses that read from `.env` via `python-dotenv` or environment variables directly.
- **`audio/recorder.py`** — `AudioRecorder`: captures audio chunks via `sounddevice`.
- **`audio/transcriber.py`** — `Transcriber`: loads the `faster-whisper` model (CUDA with automatic CPU fallback), runs transcription with Silero VAD. Also handles PyInstaller-bundled ONNX asset resolution.
- **`input/hotkey.py`** — `HotkeyListener`: global keyboard listener via `pynput`. Uses an `_is_held` flag to prevent repeated triggers on key hold.
- **`tray/icon.py`** — `TrayIcon`: generates tray icon images (gray/red/yellow via Pillow) and tooltips.
- **`tray/menu.py`** — `TrayMenu`: builds the pystray context menu with language selection and auto-paste toggle.
- **`clipboard.py`** — `ClipboardManager`: copies text via `pyperclip` and optionally auto-pastes via `pyautogui`.

### Threading model

- **Main thread**: pystray icon loop (blocks)
- **Dedicated background thread**: Whisper model loading (signals completion via `threading.Event`)
- **Per-transcription daemon threads**: spawned on hotkey release to avoid blocking the keyboard listener

### Configuration

All settings come from environment variables (loaded from `.env` if present). Key vars: `MODEL_SIZE`, `DEVICE`, `COMPUTE_TYPE`, `LANGUAGE`, `HOTKEY`, `AUTO_PASTE`, `PASTE_DELAY`. See README for full reference.

## Building Windows EXE

See `docs/DEPLOYMENT.md`. Quick build on Windows:

```bash
pyinstaller --clean --noconfirm build/windows/whisper_tray.spec
```

CI runs on `windows-latest` and tests Python 3.10–3.12.
