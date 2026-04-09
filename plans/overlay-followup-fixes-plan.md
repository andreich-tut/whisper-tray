# Overlay Follow-Up Fix Plan

**Last Updated:** 2026-04-10
**Status:** Planned

## Summary

This plan captures the next round of overlay and tray fixes based on recent UX
findings:

- The overlay can still land on the primary display when cursor-targeting
  should place it on another monitor.
- Mutually exclusive tray options behave like independent checkboxes instead of
  a single-choice group.
- The rounded overlay card shows visual artifacts around the accent rail.
- The overlay does not show the recognized text or reflect clipboard ownership
  after transcription completes.

## Recommended Direction

Treat this as a focused polish pass, not a rewrite.

The best implementation path is:

- Keep the existing presenter-driven state model.
- Add one explicit post-transcription state instead of overloading `READY`.
- Fix exclusivity in both tray backends, not only `pystray`.
- Replace the accent rail composition with a single clipped visual surface so
  the rounded card renders cleanly on all DPIs.
- Make transcript visibility clipboard-aware so the overlay can honestly say
  whether the text is still the latest WhisperTray-owned clipboard content.

## Suggested Improvements Beyond The Original Analysis

### 1. Multi-monitor placement should avoid silent primary-screen fallback

The current logic is correct only when `QGuiApplication.screenAt(QCursor.pos())`
returns a screen. When it returns `None`, cursor-targeted placement quietly
drops back to the primary display.

Recommended improvement:

- Preserve the last successfully resolved target screen while the overlay is
  visible.
- When cursor lookup fails, prefer:
  - last resolved cursor screen
  - screen containing the current overlay anchor
  - primary screen
- Keep `primary` as the final fallback, not the first practical fallback for
  cursor mode.

This should reduce "overlay jumped to the wrong monitor" behavior during
display sleep/wake, transient geometry changes, or Qt cursor lookup gaps.

### 2. Tray option exclusivity should be backend-neutral

The original diagnosis is right for `pystray`, but the Qt tray path needs the
same UX treatment.

Recommended improvement:

- `pystray`: add `radio=True` to language, position, display, ready auto-hide,
  and density groups.
- Qt: use exclusive `QActionGroup`s for the same groups instead of plain
  independent checkable actions.

That keeps both runtimes visually and behaviorally aligned.

### 3. The accent rail should be painted as part of one rounded surface

The current structure uses a separate child frame for the accent rail inside a
rounded card. That is fragile because the accent and the card are rendered as
different surfaces with different borders.

Recommended improvement:

- Replace the child accent-frame approach with one of:
  - a custom-painted card using `QPainterPath` and clipped rounded geometry
  - a single-surface background treatment that includes the rail visually
- Prefer custom painting if needed for crisp Windows rendering and DPI safety

This is more robust than trying to tune multiple border radii in stylesheets.

### 4. Transcript feedback should be a first-class state, not a transient side effect

The overlay should distinguish:

- `READY`: idle and waiting for input
- `TRANSCRIBED`: the latest recognition result is available

Recommended improvement:

- Add `AppState.TRANSCRIBED`
- Extend the state snapshot with transcript payload data
- Show the recognized text in the overlay primary/secondary fields
- Show whether the result was copied only or copied and auto-pasted
- Keep the transcript visible until:
  - a new recording starts
  - an error replaces it
  - the clipboard no longer matches the last WhisperTray-owned text

This is a better fit than forcing `READY` to carry temporary transcript UI.

## Proposed Implementation Plan

## Phase 1: Fix monitor targeting reliability

### Goal

Make cursor-targeted overlays reliably stay on the intended monitor.

### Changes

- Update `resolve_overlay_screen()` in
  `whisper_tray/overlay/pyside_overlay.py` to support richer fallback logic.
- Track the last resolved screen inside `OverlayWindow`.
- Update `_reposition()` to reuse the last good screen before falling back to
  the primary display.
- Keep live re-anchoring behavior intact.

### Tests

- Add unit coverage for:
  - cursor mode using cursor screen when present
  - cursor mode reusing last resolved screen when cursor lookup fails
  - fallback to primary only when no better candidate exists

## Phase 2: Make tray groups truly single-choice

### Goal

Ensure users see single-selection behavior for settings that are logically
radio groups.

### Changes

- Update `whisper_tray/tray/menu.py`:
  - `create_menu()` should mark mutually exclusive submenu items as radio items
  - `create_qt_menu()` should create exclusive action groups for the same sets
- Keep overlay enable and auto-paste as real toggles

### Tests

- Extend `tests/test_tray.py` to assert:
  - `pystray` menu items in exclusive groups carry `radio=True`
  - Qt grouped actions are registered in an exclusive grouping mechanism
  - checked-state refresh still works after menu state changes

## Phase 3: Rebuild the card surface to remove border artifacts

### Goal

Make the overlay card look intentional and stable at different scales.

### Changes

- Refactor `OverlayWindow` in `whisper_tray/overlay/pyside_overlay.py`
- Remove the separate `overlayAccent` frame or make it purely decorative after
  a clipped container is introduced
- Render the rounded card and accent as a unified visual surface
- Re-check drop shadow and transparency after the structure change

### QA focus

- top-left and bottom-right positions
- compact and detailed density
- Windows high-DPI rendering
- no visible seam between accent and body

## Phase 4: Add clipboard-aware transcript state

### Goal

Show users what WhisperTray just recognized and whether that text is still the
clipboard content WhisperTray owns.

### Changes

- Update `whisper_tray/state.py`:
  - add `AppState.TRANSCRIBED`
  - extend `AppStateSnapshot` with transcript-related fields
  - add presentation rules for copied vs pasted outcomes
- Update `whisper_tray/app.py`:
  - publish a transcribed snapshot after successful recognition
  - replace the current immediate `READY` transition after successful work
  - transition back to `READY` when the transcript should no longer be shown
- Update `whisper_tray/clipboard.py`:
  - remember the last WhisperTray-copied text
  - add a way to detect whether the clipboard still matches it
  - expose enough result metadata for the presenter

### UX recommendation

- Detailed overlay:
  - badge: `Copied` or `Pasted`
  - primary: truncated transcript
  - secondary: clipboard or paste status
  - hint: "Shown until clipboard changes" or similar
- Compact overlay:
  - one-line transcript preview with ellipsis

### Tests

- Add state presenter tests for `TRANSCRIBED`
- Add app tests for successful transcription publishing transcript payload
- Add clipboard tests for ownership tracking and state reset when contents change

## File Impact

- `whisper_tray/overlay/pyside_overlay.py`
- `whisper_tray/tray/menu.py`
- `whisper_tray/state.py`
- `whisper_tray/app.py`
- `whisper_tray/clipboard.py`
- `tests/test_overlay.py`
- `tests/test_tray.py`
- `tests/test_state.py`
- `tests/test_clipboard.py`

## Risks And Notes

- Clipboard-change detection may be trickier on headless test environments than
  on a live desktop session. Keep the first implementation simple and mockable.
- If exact clipboard ownership tracking becomes too invasive, land the
  `TRANSCRIBED` state first and make "hide when clipboard changes" a follow-up.
- Qt action grouping will likely require a small update to the existing fake Qt
  test helpers.
- Custom painting is the safest fix for the accent seam, but it is also the
  part most likely to need visual QA on real Windows hardware.

## Recommended Delivery Order

1. Tray exclusivity
2. Multi-monitor placement reliability
3. Transcript state and clipboard ownership
4. Rounded-card rendering polish

This order gives the fastest user-visible wins first while keeping the
presentation-model change isolated before the visual refactor.
