# Overlay UI Plan

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

### Phase 2: UI Framework Introduction

- Add `PySide6`
- Create a minimal `QApplication`
- Replace or wrap the existing tray entry point

### Phase 3: Overlay MVP

- Create a transparent overlay window
- Render the basic states
- Wire it to app events
- Add simple fade animations

### Phase 4: UX Polish

- Add positioning rules
- Support multi-monitor selection
- Improve typography and spacing
- Add error styling and recovery messaging

### Phase 5: Settings and Control

- Add tray menu options for:
  - Overlay enabled/disabled
  - Overlay position
  - Auto-hide duration
  - Compact vs detailed view

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
