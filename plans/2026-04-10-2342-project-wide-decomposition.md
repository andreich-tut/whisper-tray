# Project-Wide Module Decomposition to Reach 150-200 LOC Targets

## Summary
Refactor the repo in behavior-preserving waves, starting with the largest production modules and immediately reshaping the matching tests around the new seams. Use `150` lines as the preferred target and `200` as the soft upper bound; if a file stays slightly above `200`, it must own one cohesive responsibility and have no obvious internal split left.

The decomposition should follow existing subsystem boundaries already visible in the codebase: app orchestration, workflow/background tasks, tray runtime, tray menu modeling, overlay runtime/window behavior, config parsing/validation, transcription runtime, and clipboard paste backends. Avoid “helper dumping”; every extracted file should represent a named responsibility with its own tests.

## Progress
- Status: in progress
- Current wave: `1` of `6`
- Completed in this pass:
  - Split `whisper_tray.config` into a facade package with focused env/defaults/model/hotkey/audio/overlay/ui helpers.
  - Split `whisper_tray.state_presentation` into `state_formatting.py`, `state_errors.py`, and `state_presenter.py`, while keeping the facade import stable.
  - Split `whisper_tray.clipboard` into a facade package plus `core.py`, `controller.py`, `windows.py`, and `pyautogui_fallback.py`.
  - Split the matching config/state/clipboard tests by production boundary.
  - Split `whisper_tray.audio.transcriber` into `audio/cuda.py`, `audio/fw_assets.py`, `audio/vad.py`, and a thinner orchestration module.
  - Split audio tests into recorder and transcriber-focused files.
  - Split `whisper_tray.tray.menu` into callback, state, and definition helpers while keeping the public `TrayMenu` facade stable.
  - Split `whisper_tray.tray.runtime` into protocol, pystray, Qt icon, Qt tray handle, Qt overlay host, and Qt runtime modules while keeping the facade import path stable.
- Current checkpoint:
  - Targeted validation completed for config/state/clipboard/audio/tray with `pytest`, `flake8`, and focused `mypy` checks.
  - Remaining turn budget is being held for a clean handoff before starting the larger overlay and app decompositions.
- Remaining execution order:
  - [ ] Split overlay runtime/window modules
  - [ ] Thin `app.py` and decompose the remaining app coordinators
  - [ ] Finish the wider test decomposition and cleanup pass

## Implementation Changes
### 1. App layer: make `WhisperTrayApp` a thin composition root
- Keep public surface unchanged: `WhisperTrayApp(config: AppConfig | None = None)` and `run()`.
- Reduce [`whisper_tray/app.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/app.py) to wiring, lazy coordinator access, and a minimal lifecycle.
- Move remaining app responsibilities into focused modules:
  - `app_runtime.py`: startup and shutdown flow, tray runtime preparation, background thread startup, overlay boot decision.
  - `app_callbacks.py`: hotkey and tray callback entrypoints that delegate to collaborators.
  - `app_facade.py` or equivalent only if needed for shared typed access to app-owned state used by coordinators.
- Keep [`whisper_tray/app_workflow.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/app_workflow.py) but split it further into:
  - `workflow/worker.py`: transcription queue loop, worker lifecycle.
  - `workflow/recording.py`: hotkey press/release flow, queue admission, idle-state decisions.
  - `workflow/clipboard_monitor.py`: clipboard ownership polling lifecycle.
  - `workflow/flash.py`: processing flash timer lifecycle.
- Split [`whisper_tray/app_ui.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/app_ui.py) into:
  - `ui/presentation.py`: presenter creation, snapshot building, state publication.
  - `ui/tray_updates.py`: tray icon/menu refresh and notifications.
  - `ui/overlay_runtime.py`: overlay settings build/apply and tray-runtime selection fallback.
- Split [`whisper_tray/app_actions.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/app_actions.py) into:
  - `actions/language.py`
  - `actions/overlay.py`
  - `actions/session.py` for exit and hotkey listener setup

### 2. Config: separate env loading, defaults, parsing, and validation
- Keep public surface unchanged: [`whisper_tray/config.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/config.py) should remain the import facade for `AppConfig`, `ModelConfig`, `HotkeyConfig`, `AudioConfig`, `OverlayConfig`, and `UiConfig`.
- Move internals into:
  - `config/env.py`: `.env` candidate resolution and dotenv loading.
  - `config/defaults.py`: platform-aware default functions and preset definitions.
  - `config/model.py`, `config/hotkey.py`, `config/audio.py`, `config/overlay.py`, `config/ui.py`: one dataclass per file plus validation.
  - `config/logging.py`: config logging helpers if still needed after the split.
- Replace legacy `Optional[...]` with `| None` in touched config code.
- Keep env var names and current default semantics exactly the same.

### 3. Transcription and clipboard: isolate runtime-dependent branches
- Split [`whisper_tray/audio/transcriber.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/audio/transcriber.py) into:
  - `audio/cuda.py`: CUDA availability probing and fallback decision.
  - `audio/fw_assets.py`: faster-whisper asset discovery/copy logic.
  - `audio/vad.py`: VAD asset detection and transcribe kwargs construction.
  - `audio/transcriber.py`: thin `Transcriber` orchestration only.
- Preserve `Transcriber` public API: constructor, `load_model()`, `transcribe()`, `is_ready`, and `device`.
- Split [`whisper_tray/clipboard.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/clipboard.py) into:
  - `clipboard/core.py`: `ClipboardManager` and clipboard ownership logic.
  - `clipboard/windows.py`: Win32 `SendInput` paste helpers.
  - `clipboard/controller.py`: pynput-based paste path and unavailable-controller fallback.
  - `clipboard/pyautogui_fallback.py`: optional PyAutoGUI paste path.
- Preserve `ClipboardManager` public API and `PasteAttemptResult`.

### 4. Tray: separate runtime backends from menu definition
- Keep [`whisper_tray/tray/menu.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/tray/menu.py) as a thin facade or builder entrypoint only.
- Split menu concerns into:
  - `tray/menu_callbacks.py`: callback wrappers and checked-state closures.
  - `tray/menu_definition.py`: shared `MenuEntry` tree construction.
  - `tray/menu_state.py`: getter normalization and checked helpers if still needed.
- Split [`whisper_tray/tray/runtime.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/tray/runtime.py) into:
  - `tray/runtime_protocol.py`: `TrayRuntime` and backend-selection helper.
  - `tray/pystray_runtime.py`
  - `tray/qt_runtime.py`
  - `tray/qt_tray_handle.py`
  - `tray/qt_overlay_host.py`
  - `tray/qt_icon.py` for PIL-to-`QIcon` conversion
- Preserve public imports for `PystrayTrayRuntime`, `QtTrayRuntime`, `TrayRuntime`, and `should_use_qt_tray`.

### 5. Overlay: split pure presentation logic from Qt widget/runtime code
- Keep current public import paths stable through [`whisper_tray/overlay/__init__.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/overlay/__init__.py) and [`whisper_tray/overlay/controller.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/overlay/controller.py).
- Split [`whisper_tray/overlay/pyside_runtime.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/overlay/pyside_runtime.py) into:
  - `overlay/pyside_window.py`: `OverlayWindow`
  - `overlay/pyside_animation.py`: fade/hide behavior
  - `overlay/pyside_markup.py`: hotkey keycap markup
  - `overlay/pyside_runtime.py`: queue polling runtime only
- Keep pure helpers in `pyside_platform.py` and `pyside_presentation.py`, but split either file again if any stays above target:
  - platform: DPI awareness, Win32 styles, platform feature flags
  - presentation: theme, layout, geometry, screen resolution, reposition policy
- Remove stale imports from tests that still point at `pyside_overlay` if those functions now live elsewhere; keep compatibility re-exports during the transition.

### 6. State and presentation: keep facade, split copy rules
- [`whisper_tray/state.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/state.py) is already a good facade; keep it thin.
- Split [`whisper_tray/state_presentation.py`](/Users/andreich/dev-ai/whisper-tray/whisper_tray/state_presentation.py) into:
  - `state_formatting.py`: `format_hotkey`, transcript wrapping/truncation
  - `state_errors.py`: `ErrorPresentation` and `describe_error`
  - `state_presenter.py`: `AppStatePresenter`
- Preserve exports from `state.py` so import ergonomics do not change.

### 7. Tests: decompose by production boundary, not by assertion style
- Replace oversized umbrella tests with smaller modules aligned to runtime seams.
- Split [`tests/test_tray.py`](/Users/andreich/dev-ai/whisper-tray/tests/test_tray.py) into:
  - `tests/test_tray_menu.py`
  - `tests/test_tray_runtime_pystray.py`
  - `tests/test_tray_runtime_qt.py`
  - `tests/test_app_ui.py` for tray-update fan-out if those behaviors stay app-facing
- Split [`tests/test_overlay.py`](/Users/andreich/dev-ai/whisper-tray/tests/test_overlay.py) into:
  - `tests/test_overlay_controller.py`
  - `tests/test_overlay_platform.py`
  - `tests/test_overlay_geometry.py`
  - `tests/test_overlay_runtime.py`
- Consider splitting [`tests/test_config.py`](/Users/andreich/dev-ai/whisper-tray/tests/test_config.py) into `test_config_env.py`, `test_config_model.py`, and `test_config_overlay.py` once config modules are separated.
- Keep fakes local to the test module that uses them unless the same fake is needed in at least three files; only then promote to `tests/support/`.

## Public APIs and Compatibility
- Preserve these import surfaces during the refactor:
  - `from whisper_tray.config import ...`
  - `from whisper_tray.state import ...`
  - `from whisper_tray.tray.runtime import ...`
  - `from whisper_tray.overlay...` imports currently used by the app and tests
- Use facade modules and re-exports while moving implementations so callers do not have to change all at once.
- Do not rename environment variables, config fields, tray callback signatures, overlay controller types, or `Transcriber` / `ClipboardManager` entrypoints in this decomposition pass.

## Execution Order
1. Split `config.py`, `state_presentation.py`, and `clipboard.py` first.
2. Split `audio/transcriber.py` next.
3. Split tray menu and tray runtime modules.
4. Split overlay runtime/window modules.
5. Thin `app.py`, then finish decomposing `app_ui.py`, `app_workflow.py`, and `app_actions.py` around the now-stable boundaries.
6. After each production split, immediately split the corresponding tests before moving to the next subsystem.
7. End with a cleanup pass that removes temporary compatibility shims only if the resulting files still stay under the target size.

## Test Plan
- After each wave, run only the closest targeted pytest modules first, then a broader regression slice.
- Minimum targeted checks by subsystem:
  - config: `tests/test_config.py`
  - state/presentation: `tests/test_state.py`
  - clipboard/transcriber: `tests/test_clipboard.py`, `tests/test_audio.py`
  - tray: `tests/test_tray.py`
  - overlay: `tests/test_overlay.py`
  - app integration: `tests/test_app.py`
- Final acceptance criteria:
  - no production module above `200` LOC unless explicitly justified by a single cohesive responsibility
  - no test module above `200` LOC unless it is a deliberate fixture/support file
  - all current pytest coverage remains green
  - behavior remains unchanged for tray startup, overlay fallback, hotkey flow, transcription queueing, clipboard ownership reset, and config/env parsing

## Assumptions and Defaults
- “Whole project” includes tests, so test decomposition is part of the same plan rather than a follow-up.
- The target is readability and responsibility isolation, not achieving an arbitrary number at the cost of scattered abstractions.
- Slightly exceeding `150` lines is acceptable; exceeding `200` requires a documented reason.
- Temporary re-export facades are allowed during the transition and should be removed only when they are no longer needed to preserve stable imports.
