# Aggressive Core/Platform Decomposition

## Summary

The repo is already grouped by subsystem, but there are still three structural
leaks that make the next round of changes harder than they need to be:

- orchestration is still concentrated near the package root, especially
  `whisper_tray/app.py`
- adapter and backend code is still mixed into shared packages such as `tray`,
  `overlay`, `clipboard`, and `config`
- a few package-internal misc files are misplaced, including a duplicate
  `.env.example`, a package-local `requirements.txt`, and
  `whisper_tray/test_tray_icon.py`

This plan pushes the codebase toward a clear split:

- `app` for orchestration and lifecycle
- `core` for pure models, policies, and protocols
- `adapters` for third-party integrations
- `platform` for OS-specific code only

The current hotspots justify the split:

- `whisper_tray/app.py` at `431` LOC
- `whisper_tray/overlay/pyside_runtime.py` at `495` LOC
- `tests/test_tray.py` at `824` LOC
- `tests/test_overlay.py` at `614` LOC

## Progress

- status: in progress
- current slice: moved backend-neutral state, presentation, config, tray-menu,
  overlay-controller types, and runtime protocols under `whisper_tray/core/`
  with compatibility facades kept at the legacy import paths
- current slice: moved platform-aware config defaults into
  `whisper_tray/platform/defaults.py` and removed the duplicate package-local
  `.env.example`
- current slice: added `whisper_tray/adapters/` and `whisper_tray/platform/windows/`
  entry points, then switched app orchestration imports to the new adapter paths
- current slice: moved the standalone Windows tray test script to
  `scripts/windows/test_tray_icon.py` and replaced the package-local
  `whisper_tray/requirements.txt` with `requirements/legacy-runtime.txt`
- current slice: renamed `build/windows/` to `packaging/windows/`, moved the
  remaining Windows batch utilities under `scripts/windows/`, and moved the
  checked-in overlay mockups to `design/overlay/`
- current slice: converted `whisper_tray.app` from a single module into an
  `app/` package with `bootstrap.py` and `lifecycle.py`, while keeping the
  public import surface stable
- current slice: moved the existing session, UI, and workflow coordinators
  under `whisper_tray/app/` and left the old root modules as thin facades
- current slice: split `app/workflow.py` into `app/workflow/` package with
  `worker.py` (WorkerCoordinator), `recording.py` (RecordingCoordinator),
  `clipboard_monitor.py` (ClipboardMonitorCoordinator), and `flash.py`
  (FlashTimerCoordinator); `app/workflow/__init__.py` re-exports
  `AppWorkflowCoordinator` as a composing facade
- current slice: split `app/ui.py` into `app/ui/` package with
  `presentation.py` (PresentationCoordinator), `tray_updates.py`
  (TrayUpdatesCoordinator), and `overlay_runtime.py`
  (OverlayRuntimeCoordinator); `app/ui/__init__.py` re-exports
  `AppUiCoordinator` as a composing facade
- current slice: split `app/session.py` into `app/actions/` package with
  `language.py` (LanguageActions), `overlay.py` (OverlayActions), and
  `session.py` (SessionActions); `app/actions/__init__.py` re-exports
  `AppSessionActions` as a composing facade; `app/session.py` is now a thin
  re-export shim pointing to `app/actions`
- current slice: deleted root-level compatibility facades `app_workflow.py`,
  `app_ui.py`, and `app_actions.py` (no remaining callers); deleted
  `whisper_tray/types.py` and co-located the `Any` stubs with their owning
  boundary modules — pystray stubs in `app/lifecycle.py`, sounddevice stub
  in `audio/recorder.py`, pynput stubs in `input/hotkey.py`, and pystray icon
  stub in `tray/icon.py`
- current slice: migrated actual implementations from legacy directories into
  adapter modules — `adapters/audio/sounddevice_recorder.py` (AudioRecorder),
  `adapters/transcription/` (cuda, fw_assets, model_load, vad, transcriber),
  `adapters/hotkey/pynput_listener.py` (HotkeyListener),
  `adapters/clipboard/` (controller, pyautogui_fallback, core),
  `platform/windows/overlay_styles.py` (DPI/Win32 helpers),
  `platform/windows/send_input.py` (SendInput keyboard injection),
  `adapters/overlay/qt/runtime.py` (OverlayWindow, PySide6OverlayRuntime),
  `adapters/tray/icon.py` (TrayIcon), `adapters/tray/qt/icon.py`
  (pil_image_to_qicon), `adapters/tray/renderers.py`,
  `adapters/tray/qt/tray_handle.py`, `adapters/tray/pystray_runtime.py`,
  `adapters/tray/qt/overlay_host.py`, `adapters/tray/qt/runtime.py`; all
  legacy directories are now thin re-export facades pointing to adapters;
  test patch paths updated to target adapter modules, not legacy facades
- verification: `venv/bin/python -m pytest tests/ -q` — 108 passed, flake8
  clean, black/isort clean
- current slice: moved `create_overlay_controller` to `adapters/overlay/controller.py`,
  moved `pyside_presentation` content to `adapters/overlay/qt/presentation.py`, moved
  `TrayMenu` to `adapters/tray/menu.py`, inlined `_pyside6_is_available` in
  `core/protocols/tray.py`, updated all internal callers in `app/`, `adapters/`, and
  `core/` to import from canonical adapter/core paths, updated all test imports to
  point at adapter modules, then deleted all legacy facades:
  `audio/`, `input/`, `clipboard/`, `tray/`, `overlay/` packages; 108 passed, flake8
  clean, black/isort clean
- current slice: reorganised all tests into boundary-aligned directories;
  split test_tray.py into adapters/tray/test_menu.py, adapters/tray/test_qt_runtime.py,
  and app/test_tray_integration.py; split test_overlay.py into
  adapters/overlay/test_controller.py, adapters/overlay/test_qt_presentation.py,
  adapters/overlay/test_qt_runtime.py, and platform/windows/test_overlay_styles.py;
  moved all flat test files under tests/app/, tests/core/config/, tests/core/state/,
  tests/core/presentation/, tests/adapters/{audio,clipboard,hotkey,transcription}/,
  and tests/platform/windows/; all 108 tests pass, flake8/black/isort clean;
  core protocols (RecorderBackend, TranscriberBackend, ClipboardPasteBackend,
  HotkeyBackend) were already complete from the previous slice
- current slice: deleted the 5 legacy state sub-facades (state_models.py,
  state_presentation.py, state_presenter.py, state_errors.py, state_formatting.py)
  — no callers remained; state.py continues as the sole public re-export facade
  pointing at core/state/ and core/presentation/; deleted whisper_tray/whisper_tray.py
  (deprecated shim, no remaining callers); 108 passed, flake8 clean
- current slice: deleted 5 config sub-shims (config/audio.py, config/hotkey.py,
  config/model.py, config/overlay.py, config/ui.py) — config/__init__.py now imports
  directly from core/config/; moved app_constants.py to app/constants.py and updated
  3 callers (app/__init__.py, app/lifecycle.py, app/actions/overlay.py); 108 passed,
  flake8/isort clean
- status: complete — all plan goals achieved

## Target Structure

```text
whisper_tray/
  app/                  # composition root, lifecycle, actions, workflow
  core/                 # config schema, state models, presentation, protocols
  adapters/             # sounddevice, faster-whisper, pyperclip, pynput, pystray, Qt
  platform/             # windows/, darwin/, linux/ helpers only
  tray/                 # temporary public facade only
  overlay/              # temporary public facade only
  config/               # temporary public facade only
  state/                # temporary public facade only
```

### App

- move root app logic into `app/bootstrap.py` and `app/lifecycle.py`
- split `app_workflow.py` into:
  - `workflow/worker.py`
  - `workflow/recording.py`
  - `workflow/clipboard_monitor.py`
  - `workflow/flash.py`
- split `app_ui.py` into:
  - `ui/presentation.py`
  - `ui/tray_updates.py`
  - `ui/overlay_runtime.py`
- split `app_actions.py` into:
  - `actions/language.py`
  - `actions/overlay.py`
  - `actions/session.py`

### Core

- move `state_models.py`, `state_presenter.py`, `state_formatting.py`, and
  `state_errors.py` under `core/state/` and `core/presentation/`
- move backend-neutral tray menu model, definition, and state under
  `core/tray_menu/`
- move `OverlayController`, `OverlaySettings`, overlay commands, and runtime
  protocols under `core/overlay/`
- keep config dataclasses and validation in `core/config/`
- move environment loading into `app/config_loader.py`

### Adapters

- move `audio/recorder.py` to `adapters/audio/sounddevice_recorder.py`
- move `audio/transcriber.py`, `cuda.py`, `fw_assets.py`, and `vad.py` to
  `adapters/transcription/`
- move `input/hotkey.py` to `adapters/hotkey/pynput_listener.py`
- move `clipboard/core.py`, `controller.py`, and `pyautogui_fallback.py` to
  `adapters/clipboard/`
- move pystray and Qt tray runtime and rendering modules to `adapters/tray/`
- place Qt-specific tray code under `adapters/tray/qt/`
- move Qt overlay window and runtime code from `overlay/pyside_runtime.py` to
  `adapters/overlay/qt/`

### Platform

- move `clipboard/windows.py` to `platform/windows/send_input.py`
- move Windows DPI and style helpers from `overlay/pyside_platform.py` to
  `platform/windows/overlay_styles.py`
- move platform-aware defaults from `config/defaults.py` to `platform/defaults.py`

## Interfaces And Migration Order

- add internal protocols in `core/protocols/` or subsystem-local protocol
  modules:
  - `RecorderBackend`
  - `TranscriberBackend`
  - `ClipboardPasteBackend`
  - `HotkeyBackend`
  - `TrayRuntime`
  - `OverlayRuntime`
- keep public imports stable for one migration phase with re-export facades:
  - `whisper_tray.app.WhisperTrayApp`
  - `whisper_tray.config.*`
  - `whisper_tray.state.*`
  - `whisper_tray.tray.runtime.*`
  - `whisper_tray.overlay.*`
- remove `whisper_tray/types.py` by moving optional-library typing aliases next
  to the owning adapter

Migration order:

1. Create `core` protocols and types, plus thin facades at the current import
   paths.
2. Thin the app layer into `app/` without changing behavior.
3. Move tray, overlay, clipboard, and transcription integrations into
   `adapters/`.
4. Pull Win32 and platform-default logic into `platform/`.
5. Split tests to match the new boundaries, then delete obsolete facades only
   if no internal imports remain.

## Repo Layout Cleanup

- keep only the root `.env.example`; delete `whisper_tray/.env.example` after
  merging any remaining differences
- move `whisper_tray/test_tray_icon.py` to `scripts/windows/test_tray_icon.py`
- remove `whisper_tray/requirements.txt`; if it still matters, replace it with
  `requirements/legacy-runtime.txt` at repo root and document why it exists
- rename `build/windows/` to `packaging/windows/`
- rename `build/scripts/` to `scripts/windows/`
- move checked-in mockups from `artifacts/` to `design/overlay/` if they are
  design references; otherwise stop tracking generated artifacts

## Test Plan

- replace flat tests with boundary-aligned directories:
  - `tests/app/`
  - `tests/core/state/`
  - `tests/adapters/tray/`
  - `tests/adapters/overlay/`
  - `tests/platform/windows/`
  - `tests/support/` only for fakes reused in at least three files
- split `tests/test_tray.py` into menu model, pystray runtime, Qt runtime, and
  app integration slices
- split `tests/test_overlay.py` into controller, geometry and presentation,
  Qt runtime, and Windows helper slices

Acceptance coverage to keep:

- pystray startup and Qt fallback
- overlay disabled and missing-PySide fallback
- hotkey press and release gating
- single-worker transcription queue behavior
- clipboard ownership reset after external clipboard changes
- Windows `SendInput` and fallback paste ordering
- config and env loading plus platform-default behavior
- CUDA probe and CPU fallback

## Assumptions

- this plan intentionally chooses the aggressive architecture split instead of a
  minimal cleanup pass
- no user-facing behavior, CLI names, environment variables, or default
  semantics change in this refactor
- the repo should not switch to a `src/` layout in the same pass
- root AI and tooling files such as `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, and
  prompt docs stay where they are
- this plan is added alongside the earlier decomposition plans instead of
  replacing them
