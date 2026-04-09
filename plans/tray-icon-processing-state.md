# Tray Icon Processing State (Flashing Animation)

**Date:** 2026-04-09  
**Status:** Planned

## Overview

Add visual feedback during audio transcription by implementing a flashing tray icon that alternates between green (ready) and orange (processing) every 500ms.

## Problem

Currently, the tray icon has no visual state during transcription processing, which can take several seconds (especially on CPU). Users have no feedback that their audio is being processed.

## Current States

- **Light green**: Ready/idle
- **Tomato (red)**: Recording
- **Yellow**: Model loading

## Proposed States

- **Flashing green ↔ orange**: Processing/transcribing audio

## Implementation Plan

### 1. Update `TrayIcon` class (`whisper_tray/tray/icon.py`)

- Add `is_processing: bool` parameter to:
  - `get_icon_image()`
  - `update_icon()`
  - `get_tooltip()`
- Return orange icon when `is_processing=True`
- Update tooltip to show "Processing..." when `is_processing=True`

### 2. Update `WhisperTrayApp` class (`whisper_tray/app.py`)

- Add `_is_processing: bool = False` state
- Add `_flash_timer: Optional[threading.Thread]` for toggling icon
- Add `_flash_event: threading.Event()` for clean shutdown
- Add `_flash_icon()` method that toggles between processing/idle icons every 500ms
- Start flash timer in `_on_hotkey_released()` before spawning transcription thread
- Stop flash timer in `_process_transcription()` after transcription completes
- Update `_update_tray_icon()` to pass `is_processing` state

### 3. Flash Timer Logic

```python
def _start_flash_timer(self) -> None:
    """Start background thread that flashes the icon."""
    self._is_processing = True
    self._flash_event.clear()
    
    def flash_loop():
        while not self._flash_event.is_set():
            # Toggle between processing and idle icon
            self._update_tray_icon()
            self._flash_event.wait(0.5)  # 500ms interval
    
    self._flash_timer = threading.Thread(target=flash_loop, daemon=True)
    self._flash_timer.start()

def _stop_flash_timer(self) -> None:
    """Stop the flash timer."""
    self._is_processing = False
    self._flash_event.set()
    if self._flash_timer:
        self._flash_timer.join(timeout=1.0)
```

### 4. Integration Points

- **`_on_hotkey_released()`**: Call `_start_flash_timer()` after stopping recording
- **`_process_transcription()`**: Call `_stop_flash_timer()` after transcription completes
- **`_update_tray_icon()`**: Pass `is_processing=self._is_processing` to `TrayIcon.update_icon()`

### 5. Files to Modify

- `whisper_tray/tray/icon.py` - Add processing state support
- `whisper_tray/app.py` - Add flash timer logic and state management

## Color Choice

- **Orange** (`"orange"`) for processing state - indicates intermediate/active work
- **Light green** (`"lightgreen"`) for ready/idle state
- Flash interval: 500ms

## Edge Cases

- Handle model not ready (don't flash, keep yellow)
- Handle transcription errors (stop flash, return to green)
- Handle short recordings (<0.3s) - don't start flash
- Clean up flash timer on app exit

## Testing

- Verify icon flashes during transcription
- Verify icon returns to green after transcription completes
- Verify no flashing during recording (stays red)
- Verify no flashing when model not ready (stays yellow)
- Test with short recordings (should not flash)
