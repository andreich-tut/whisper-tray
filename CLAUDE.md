# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhisperTray is a Windows system tray application for global speech-to-text. Hold `Ctrl+Shift+Space` → speak → release → text is transcribed via faster-whisper and pasted into the focused window. Primarily targets Windows, but the core logic (config, audio, transcription) is platform-agnostic and can be developed/tested on Linux/macOS.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -e ".[dev]"        # core + dev tools
pip install -e ".[ui]"         # optional: PySide6 overlay and Qt tray
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

- **MANDATORY**: Before editing any code, read `prompts/CODESTYLE.md` and follow it as the canonical coding-style source for this repository.
- **MANDATORY**: If any Markdown file in this repo conflicts with `prompts/CODESTYLE.md`, or with checked-in tool config such as `pyproject.toml`, `.flake8`, `.pre-commit-config.yaml`, or `scripts/validate-build.py`, follow the canonical code-style guide and checked-in config.

The application is structured as independent subsystems coordinated by `app.py`:

- **`app.py`** — `WhisperTrayApp`: the central orchestrator. Wires together all subsystems, manages the recording state machine, and runs the tray event loop on the main thread.
- **`state.py`** — `AppState` enum + `AppStateSnapshot` / `AppStatePresentation` / `AppStatePresenter` / `AppStatePublisher`: the centralized pub/sub state machine. All UI components (tray, overlay) subscribe to `AppStatePublisher` and receive `AppStatePresentation` objects rather than reading raw state directly.
- **`config.py`** — `AppConfig` / `ModelConfig` / `HotkeyConfig` / `AudioConfig` / `OverlayConfig` / `UiConfig`: typed dataclasses reading from `.env` via `python-dotenv` or environment variables.
- **`audio/recorder.py`** — `AudioRecorder`: captures audio chunks via `sounddevice`.
- **`audio/transcriber.py`** — `Transcriber`: loads the `faster-whisper` model (CPU-first, optional CUDA), runs transcription with Silero VAD. Also handles PyInstaller-bundled ONNX asset resolution.
- **`input/hotkey.py`** — `HotkeyListener`: global keyboard listener via `pynput`. Uses an `_is_held` flag to prevent repeated triggers on key hold.
- **`tray/icon.py`** — `TrayIcon`: generates tray icon images (gray/red/yellow/green via Pillow).
- **`tray/menu.py`** — `TrayMenu`: builds the context menu with language, auto-paste, and overlay controls. Supports both pystray and Qt menus via `create_menu()` / `create_qt_menu()`.
- **`tray/runtime.py`** — `TrayRuntime` protocol with two backends: `PystrayTrayRuntime` (default) and `QtTrayRuntime` (requires PySide6, selected by `TRAY_BACKEND=qt` or auto when PySide6 is installed). The Qt runtime shares one `QApplication` with the overlay.
- **`overlay/controller.py`** — `OverlayController` protocol, `NullOverlayController` (no-op fallback), `ThreadedOverlayController` (proxies state to a UI thread via a command queue). Used by the pystray runtime.
- **`overlay/pyside_overlay.py`** — `PySide6OverlayRuntime` / `OverlayWindow`: the actual Qt overlay widget (frameless, always-on-top, corner-anchored). Optional; guarded by `find_spec("PySide6")`.
- **`clipboard.py`** — `ClipboardManager`: copies text via `pyperclip` and optionally auto-pastes via `pyautogui`.

### Threading model

- **Main thread**: tray event loop (pystray or Qt `QApplication.exec()`)
- **`model-loader` daemon thread**: loads the Whisper model, signals `threading.Event` on completion
- **`transcription-worker` daemon thread**: single worker consuming a `queue.Queue` of `(audio_data, language)` tuples; processes one utterance at a time to avoid backlog
- **`tray-processing-flash` daemon thread**: flashes the tray icon at 500 ms intervals while the worker is busy
- **`overlay-ui` daemon thread** (pystray path only): runs the `PySide6OverlayRuntime` event loop; not used when `QtTrayRuntime` owns the Qt app

### Configuration

All settings come from environment variables (loaded from `.env` if present).

| Var | Default | Notes |
|-----|---------|-------|
| `MODEL_SIZE` | `small` | tiny/base/small/medium/large/large-v3 |
| `DEVICE` | `cpu` | cpu or cuda |
| `COMPUTE_TYPE` | `int8` (cpu) / `float16` (cuda) | |
| `LANGUAGE` | auto-detect | e.g. `en`, `ru` |
| `HOTKEY` | `ctrl,shift,space` | comma-separated keys |
| `AUTO_PASTE` | `true` | |
| `PASTE_DELAY` | `0.1` | seconds |
| `BEAM_SIZE` | `1` | greedy by default for CPU speed |
| `OVERLAY_ENABLED` | `false` | requires `.[ui]` extras |
| `OVERLAY_POSITION` | `bottom-right` | top-left/top-right/bottom-left/bottom-right |
| `OVERLAY_SCREEN` | `primary` | primary or cursor |
| `OVERLAY_AUTO_HIDE_SECONDS` | `1.5` | 0 = stay visible |
| `OVERLAY_DENSITY` | `detailed` | compact or detailed |
| `TRAY_BACKEND` | `auto` | auto/pystray/qt |
| `CPU_THREADS` | — | sets OMP_NUM_THREADS + ONNX_NUM_THREADS |

## Plans

Plan files live in `plans/`. Name them:

```
YYYY-MM-DD-HHMM-<slug>.md
```

- **Datetime** — use the first git commit time for the file; use filesystem mtime if the file has never been committed. Local timezone, 24-hour clock, no separators between hour and minute.
- **Slug** — lowercase, hyphen-separated, no redundant words like `plan` or `prompt` (the directory already implies it). Keep it short: `overlay-ui`, `cpu-first-transcription`, `macos-m1-support`.

When a plan is superseded by a newer one, delete it. When a plan is fully implemented, keep it for history — do not delete it.

## Building Windows EXE

See `docs/DEPLOYMENT.md`. Quick build on Windows:

```bash
pyinstaller --clean --noconfirm packaging/windows/whisper_tray.spec
```

CI runs on `windows-latest` and tests Python 3.12+.
