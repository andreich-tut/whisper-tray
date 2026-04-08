Build a Windows system tray app called WhisperTray — a global speech-to-text tool using faster-whisper.

## Core flow
1. User holds a configurable hotkey (default: Ctrl+Shift+Space)
2. App records audio from the default microphone
3. On hotkey release — transcribe with faster-whisper
4. Result goes to clipboard AND is auto-pasted into the focused text field via Ctrl+V

## Stack
- faster-whisper (CUDA, float16, large-v3 by default)
- sounddevice for mic recording (16kHz, mono, float32)
- pynput for global hotkey detection
- pystray + Pillow for system tray icon
- pyperclip for clipboard
- pyautogui for paste simulation

## Config (top of file, easy to change)
- MODEL_SIZE, DEVICE, COMPUTE_TYPE, LANGUAGE
- HOTKEY (set of pynput keys)
- AUTO_PASTE toggle
- PASTE_DELAY (seconds before Ctrl+V fires)

## Tray icon behavior
- Gray circle = idle
- Red circle = recording (icon changes dynamically)
- Right-click menu: "Toggle auto-paste", "Exit"
- Tooltip shows current status

## Requirements file
Include requirements.txt with pinned versions.

## Error handling
- Ignore recordings shorter than 0.3 seconds
- Use faster-whisper built-in VAD filter (min_silence_duration_ms=500)
- Print errors to stdout, never crash the tray

## Startup
- Load model in a background thread so tray appears instantly
- Show "Loading model…" tooltip until ready
- Block hotkey handling until model is loaded

## File structure
whisper_tray/
  whisper_tray.py   # single-file app
  requirements.txt
  README.md         # setup steps (venv, CUDA, run)

Write complete, working code. No placeholders.