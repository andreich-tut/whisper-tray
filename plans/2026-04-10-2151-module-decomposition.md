# Decompose Oversized Modules Into Focused Components

## Summary
Refactor the codebase in small, behavior-preserving phases, starting with production modules only. The goal is to move oversized files toward a soft cap of around 150 lines by splitting them along existing subsystem boundaries, not by scattering helpers arbitrarily. Prioritize modules where multiple responsibilities are currently mixed: app orchestration, tray menu backend adaptation, overlay runtime and platform behavior, and state presentation logic.

## Implementation Changes
- Start with `whisper_tray/app.py` and split it into role-based collaborators while keeping `WhisperTrayApp` as the public orchestrator.
  Public surface to preserve: `WhisperTrayApp(config: AppConfig | None = None)` and `run()`.
  Extract private responsibilities into focused modules or classes:
  - Recording and transcription workflow: hotkey press or release handling, queue admission, worker loop, flash lifecycle.
  - UI runtime coordination: tray runtime preparation, overlay application, tray icon or menu refresh, user notifications.
  - Session or config actions: language changes, overlay setting changes, auto-paste toggles, startup and shutdown wiring.
  Result: `app.py` becomes thin orchestration that wires these collaborators together.

- Split `whisper_tray/tray/menu.py` by separating menu definition from backend-specific rendering.
  Public surface to preserve: one high-level tray menu builder used by the app.
  Extract:
  - Menu model or constants: language options, overlay positions or screens or densities, checked-state helpers.
  - `pystray` renderer: translates the menu model into `pystray.Menu`.
  - Qt renderer: translates the same model into `QMenu` and sync logic.
  Result: one source of truth for menu structure, two backend adapters, no duplicated menu-shape logic.

- Split `whisper_tray/overlay/pyside_overlay.py` into platform helpers, presentation or theme or layout logic, and Qt runtime or window code.
  Public surface to preserve: the overlay runtime factory used by `create_overlay_controller(...)`.
  Extract:
  - Windows or native helpers: DPI awareness, Win32 style application, platform feature flags.
  - Geometry or screen resolution helpers: screen selection, coordinate resolution, reposition fallback.
  - Theme or layout tokens: `OverlayTheme`, `OverlayLayout`, density or error sizing rules, color-theme resolution.
  - Qt window or runtime: `OverlayWindow`, runtime startup loop, command consumption.
  Result: the Qt-specific runtime file becomes readable, and non-Qt logic becomes directly unit-testable.

- Split `whisper_tray/state.py` into state model or publisher and presentation formatting.
  Public surface to preserve: `AppState`, `AppStateSnapshot`, `AppStatePresentation`, `AppStatePresenter`, `AppStatePublisher`, `format_hotkey(...)`.
  Extract:
  - Core state types and publisher.
  - Presentation formatting helpers: transcript formatting, error copy, density-aware secondary or hint rules.
  Result: state transport and UI copy logic stop evolving in the same file.

- Defer second-wave modules until after the first four are stable.
  Candidates: `whisper_tray/tray/runtime.py`, `whisper_tray/audio/transcriber.py`, `whisper_tray/config.py`, `whisper_tray/clipboard.py`.
  Rule for wave two: only split when there is a clean seam such as platform fallback, config parsing versus validation, or backend or resource loading. Avoid extracting tiny helpers just to satisfy line count.

## API and Type Expectations
- Preserve current import ergonomics for the app layer by re-exporting moved public classes or functions where needed.
- Do not change configuration names, environment variable behavior, tray callback signatures, or overlay controller or runtime protocols as part of the decomposition.
- If new internal dataclasses or protocols are introduced, keep them internal unless they replace an already shared boundary.
- Prefer dependency injection at extracted boundaries so tests can target components without booting tray, Qt, clipboard, or whisper backends.

## Test Plan
- Keep existing behavior coverage green while moving code. Treat this as a no-feature-change refactor.
- Add or update focused unit tests for newly extracted pure logic:
  - Queue admission and idle-state decisions from app workflow helpers.
  - Menu model rendering parity across `pystray` and Qt adapters.
  - Overlay screen or geometry or theme or layout resolution helpers.
  - State presentation formatting for ready, processing, transcribed, and error snapshots.
- Only split test files when a production refactor naturally creates a clearer matching test module. Do not do a separate test-file decomposition pass in phase one.
- After each phase, run the relevant targeted pytest files for the module being decomposed before moving to the next phase.

## Assumptions
- The 150-line preference is a strong design target, but not a hard rule when a cohesive file remains slightly above that size after a clean split.
- Production modules are the priority. Oversized test files are deferred unless touched by the refactor.
- The refactor should be phased, with the order: `app.py` first, then `tray/menu.py`, then `overlay/pyside_overlay.py`, then `state.py`.
- Behavior, config semantics, and optional-backend fallback behavior must remain unchanged during the decomposition.
