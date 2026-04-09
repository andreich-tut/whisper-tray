# Overlay UI Plan

**Last Updated:** 2026-04-09
**Status:** MVP Implemented, Runtime Overlay Controls Expanded, Unified Qt Tray Runtime Landed, Native Windows Polish Added, DPI-Aware Qt Startup Added, Startup Fallbacks Hardened, Build Wiring Added, Live Re-Anchoring Added, Tray Backend Selection Added, Windows QA Pending

## Current Progress

### Latest Checkpoint

- Overlay fallback behavior is now resilient when `PySide6` is missing at runtime
- Overlay startup now cleanly falls back when the Qt runtime fails to boot even
  if `PySide6` is installed
- Installing `.[ui]` now runs the tray and overlay on one shared Qt runtime
  instead of mixing `pystray` with a threaded Qt overlay
- Windows Qt startup now opts into per-monitor DPI awareness before
  `QApplication` boots when the host OS supports it
- Windows build wiring now includes the optional overlay backend when the UI
  extras are installed
- Qt tray startup failures now fall back to `pystray` without discarding the
  requested overlay, so the legacy threaded overlay backend can retry startup
- Visible overlays now re-anchor themselves while they are on screen so
  cursor-targeted placement and display geometry changes stay aligned
- Added an explicit tray backend selector so Windows QA can force `pystray`,
  force Qt, or keep the default auto-selection path
- Local verification is current through `77` passing tests
- The main remaining gap is still live Windows QA for focus, click-through,
  placement, and packaging behavior

### Completed on 2026-04-09

- Added a shared app state layer in `whisper_tray/state.py`
- Centralized user-visible states as:
  - `loading_model`
  - `ready`
  - `recording`
  - `processing`
  - `error`
- Added a presentation mapper so tray and future overlay UI can use the same copy and color model
- Refactored `WhisperTrayApp` to publish state transitions through one shared path
- Added an overlay controller seam in `whisper_tray/overlay/controller.py`
- Added overlay config fields:
  - `OVERLAY_ENABLED`
  - `OVERLAY_AUTO_HIDE_SECONDS`
  - `OVERLAY_POSITION`
  - `OVERLAY_SCREEN`
  - `OVERLAY_DENSITY`
- Added an optional `ui` dependency group with `PySide6`
- Updated tray rendering to consume the shared presentation model
- Added tests for state publishing, presentation mapping, and tray integration
- Implemented the first real `PySide6` overlay window backend
- Added a threaded overlay controller so shared state can drive Qt without
  replacing `pystray` yet
- Added fade-in and auto-hide behavior plus corner positioning for the overlay
- Deferred desktop-only imports so the app module and tests can run headlessly
- Exposed overlay enable and position controls in the tray menu
- Added runtime overlay restart logic so tray changes apply immediately
- Added fallback notifications when overlay support is requested without `PySide6`
- Added tray-managed ready auto-hide controls with a persistent "stay visible" mode
- Added compact vs detailed overlay density controls that rerender live
- Added display targeting so the overlay can follow either the primary monitor
  or the monitor under the cursor
- Added a more intentional overlay card layout with a state badge, accent rail,
  and richer typography spacing
- Added actionable error recovery copy so overlay failures suggest the next step
- Added native Win32 extended-window styling so the overlay stays click-through,
  topmost, and non-activating when supported
- Added a Windows DPI-awareness startup helper with safe API fallbacks before
  the Qt tray or overlay runtime boots
- Migrated the `.[ui]` runtime to a shared `QSystemTrayIcon` + overlay
  `QApplication` path with a safe `pystray` fallback when Qt is unavailable
- Fixed the overlay controller fallback so requests cleanly degrade when
  `PySide6` is not installed
- Hardened the overlay controller startup path so broken Qt runtime boots fall
  back to the no-op overlay instead of leaving the app in a half-enabled state
- Updated the Windows packaging path so overlay builds can bundle the optional
  `PySide6` backend
- Kept overlay requests alive when the unified Qt tray runtime falls back to
  `pystray`, preserving the legacy threaded overlay path as a retryable backup
- Added live overlay re-anchoring so visible cards stay aligned during
  cursor-display changes and monitor/taskbar geometry updates
- Added `TRAY_BACKEND` so runtime selection can be pinned to `auto`,
  `pystray`, or `qt` without code changes

### Implemented and user-visible with `.[ui]`

- Setting `OVERLAY_ENABLED=true` now renders a live on-screen overlay when
  `PySide6` is installed
- Overlay requests still safely fall back to a no-op controller when `PySide6`
  is unavailable
- Overlay requests now also safely fall back when the Qt runtime fails during
  startup
- Ready-state auto-hide can now be tuned from the tray, including a persistent
  "stay visible" mode
- The overlay can now switch between detailed and compact presentation density
  at runtime
- The overlay can now target either the primary display or the display under
  the cursor for multi-monitor setups
- Installing `.[ui]` now runs the tray and overlay on one shared Qt event loop
- `pystray` remains available as the fallback runtime when Qt is unavailable
- Visible overlays now keep themselves pinned to the active target display even
  when cursor-driven placement or screen geometry changes mid-state
- Windows QA can now compare the unified Qt tray path against the legacy
  `pystray` tray path without reinstalling dependencies

### Verified on 2026-04-09

- Full repository test suite passed with `venv/bin/python -m pytest -q`
- Current result: 77 tests passed
- Headless test support improved by deferring desktop-only imports until runtime
- Added overlay-focused tests for the native Windows style helper, Qt-missing
  fallback behavior, and broken-runtime startup fallback behavior
- Added overlay-focused tests for the Windows DPI-awareness startup helper
- Added tray tests for Qt runtime selection and backend-neutral menu state sync
- Added helper coverage for overlay anchor-coordinate math used during live
  re-anchoring
- Added config and runtime coverage for explicit tray backend selection

### Next Recommended Step

- Validate the unified Qt tray + overlay runtime on Windows and tune
  focus/click-through behavior
- Decide whether `TRAY_BACKEND=auto` should stay Qt-first long term after the
  Windows QA pass

## Overview

This document describes a practical path for adding an on-screen overlay UI to WhisperTray so the app can show model loading, recording, audio processing, and error states without relying on tray-only feedback.

## Goals

- Show clear status feedback directly on screen.
- Keep the current transcription pipeline reusable.
- Avoid blocking the global hotkey flow.
- Preserve Windows-first behavior while keeping the design portable enough for future cross-platform work.

## Recommended Direction

Use `PySide6` as the UI layer and move the tray implementation to `QSystemTrayIcon`.

Why this is the cleanest option:

- `pystray` is fine for a simple tray icon, but it is not a strong foundation for overlay windows.
- Qt gives us a tray icon, transparent windows, animations, timers, and signal/slot communication in one framework.
- The current core modules can stay mostly intact: `audio`, `transcriber`, `hotkey`, `clipboard`, and most of the state machine in `app.py`.

## UI States

The overlay should support these first-class states:

- `loading_model`
- `ready`
- `recording`
- `processing`
- `error`
- `disabled` or `paused` as an optional future state

Each state should define:

- Primary text
- Secondary text
- Color theme
- Optional animation
- Optional timeout or auto-hide behavior

## MVP Overlay Behavior

For the first version, keep the overlay intentionally small:

- A compact pill or card near the bottom-right corner of the main display
- Transparent background around the component
- Always-on-top window
- Click-through behavior if possible on Windows
- Fade in on status change
- Fade out after a short timeout for `ready`
- Persistent display for `loading_model`, `recording`, and `processing`

Example state copy:

- `Loading model...`
- `Listening...`
- `Processing speech...`
- `Ready`
- `Model failed to load`

## Architecture

Introduce a small UI-facing state layer between the app logic and the presentation:

### 1. App State Publisher

Create a simple state publisher that emits structured events such as:

- `model_loading_started`
- `model_ready`
- `recording_started`
- `recording_stopped`
- `transcription_started`
- `transcription_finished`
- `transcription_failed`

This can be implemented with:

- Qt signals if the app moves fully to Qt
- A thread-safe queue if we want a staged migration

### 2. Presentation Model

Add a thin presenter that converts internal events into UI state:

- Internal event: `model_ready`
- UI state: `ready`
- Overlay text: `Ready`
- Tray state: green icon + ready title

This keeps business logic out of the window code.

### 3. Overlay Window

Build a dedicated overlay widget:

- Frameless
- Transparent
- Topmost
- Non-activating if possible
- Optional click-through on Windows using native window flags

The overlay widget should only render state. It should not own transcription logic.

### 4. Tray Integration

If we adopt Qt, replace `pystray` with `QSystemTrayIcon`.

Benefits:

- One event loop for tray + overlay
- Better long-term maintainability
- Easier coordination between background work and UI updates

## Implementation Phases

### Phase 1: State Extraction

- Introduce a shared app status enum or dataclass
- Centralize all state transitions in one place
- Keep the existing tray behavior working

**Progress:** Completed on 2026-04-09

### Phase 2: UI Framework Introduction

- Add `PySide6`
- Create a minimal `QApplication`
- Replace or wrap the existing tray entry point

**Progress:** Complete for `.[ui]` installs

- Optional `PySide6` dependency group added
- Runtime overlay seam added
- A shared `QApplication` now hosts both the tray icon and overlay when
  `PySide6` is installed
- `pystray` remains the fallback backend when Qt is unavailable

### Phase 3: Overlay MVP

- Create a transparent overlay window
- Render the basic states
- Wire it to app events
- Add simple fade animations

**Progress:** Mostly Complete

- Transparent `PySide6` overlay window implemented
- Shared app state now drives overlay rendering
- Fade-in and ready-state auto-hide implemented
- Corner positioning implemented through `OVERLAY_POSITION`
- Windows-specific polish and QA still pending
- Native no-activate and click-through Win32 styling is now implemented

### Phase 4: UX Polish

- Add positioning rules
- Support multi-monitor selection
- Improve typography and spacing
- Add error styling and recovery messaging

**Progress:** Partially Complete

- Overlay placement now supports primary-display and cursor-display targeting
- Typography, spacing, and actionable error recovery messaging are now in place
- Native Win32 click-through and non-activating styling is now in place
- Visible overlays now keep re-anchoring while shown so cursor-display targeting
  and taskbar-safe geometry updates stay in sync without waiting for a new state
- Windows-specific visual and interaction QA is still pending

### Phase 5: Settings and Control

- Add tray menu options for:
  - Overlay enabled/disabled
  - Overlay position
  - Auto-hide duration
  - Compact vs detailed view

**Progress:** Partially Complete

- Tray menu now supports runtime overlay enable/disable
- Tray menu now supports corner selection for the overlay
- Tray menu now supports display targeting for multi-monitor overlay placement
- Tray menu now supports ready-state auto-hide presets
- Tray menu now supports compact vs detailed overlay presentation density
- README and tests now cover the new runtime overlay controls

## Windows-Specific Details

Important Windows topics for the overlay:

- Per-monitor DPI awareness
- Transparent layered windows
- Click-through behavior
- Avoid stealing focus while updating
- Correct placement above taskbar and full-screen apps

These are all feasible, but they should be treated as explicit QA targets.

## Risks

- Adding Qt changes packaging size and startup characteristics.
- PyInstaller config will need updates for Qt plugins.
- Mixing `pystray` and Qt in the same final architecture is possible, but not ideal.
- Overlay polish usually takes longer than the raw window implementation.

## Recommended Migration Strategy

Do not build a serious overlay on top of `pystray` as the long-term UI foundation.

Recommended path:

1. Fix the current tray update issues.
2. Extract app state transitions.
3. Introduce Qt for UI.
4. Migrate tray UI from `pystray` to `QSystemTrayIcon`.
5. Add the overlay window on top of the shared Qt event loop.

## Rough Estimate

- Tray fix and state extraction: small task
- Overlay prototype: small to medium task
- Polished Windows-ready MVP: medium task

For a practical engineering plan, expect:

- A quick prototype in less than a day
- A solid MVP in a few days
- A polished release version after additional QA, packaging, and Windows-specific tuning

## Success Criteria

The overlay work is successful when:

- The user can tell at a glance whether the app is loading, listening, processing, or ready
- The overlay never blocks typing or steals focus
- Tray and overlay states stay consistent
- The app still feels lightweight and reliable
