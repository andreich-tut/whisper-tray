# macOS (M1) Support — Implementation Plan

## Overall Difficulty: Moderate (3-5 days of focused work)

The application code is **~90% cross-platform already**. The main work is in build/packaging and a few platform-specific details.

---

## What Works Out of the Box

| Component | Status |
|-----------|--------|
| `sounddevice` | ✅ Ships universal2 wheels with PortAudio dylib for M1 |
| `pyperclip` | ✅ Uses `pbcopy`/`pbpaste` natively on macOS |
| `pyautogui` | ✅ Cross-platform via Quartz |
| `faster-whisper` | ✅ Works via ONNX Runtime CPU (no CUDA/MPS) |
| `pynput` hotkey detection | ⚠️ Works, but has known M1 thread bugs if listener is created off main thread |
| `pystray` | ⚠️ Has macOS backend (`_darwin`), needs `pyobjc-framework-Cocoa` |

---

## Implementation Tasks

### 1. Paste Key: `Ctrl+V` → `Cmd+V` (Trivial)

**File:** `whisper_tray/clipboard.py` (line ~53)

Currently hardcoded to `Key.ctrl`. Needs platform detection:

```python
modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl
with self._keyboard_controller.pressed(modifier):
```

**Estimated effort:** 5 minutes

---

### 2. Default Device for macOS (Optional but Recommended)

**File:** `whisper_tray/config.py` (line ~31)

macOS has no CUDA. The transcriber has a fallback to CPU, but defaults should be platform-aware:

- Default `DEVICE=cpu` on macOS
- Default `COMPUTE_TYPE=int8` on macOS

Either make defaults platform-aware programmatically, or document in README.

**Estimated effort:** 10 minutes (code) or 5 minutes (docs-only)

---

### 3. Conditional macOS Dependencies

**File:** `pyproject.toml`

Add platform-specific dependencies:

```toml
"pyobjc-framework-Cocoa; sys_platform == 'darwin'",
"pyobjc-framework-Quartz; sys_platform == 'darwin'",
```

**Estimated effort:** 5 minutes

---

### 4. macOS Build Pipeline (Most Work)

**New file:** `.github/workflows/build-macos.yml`

- Use `runs-on: macos-14` (M1 runner)
- PyInstaller config that bundles for `.app` instead of `.exe`
- No CUDA DLL bundling (mac uses `.dylib`, sounddevice ships its own)
- Code signing / notarization (optional, for distribution)

**Estimated effort:** 2-3 hours

---

### 5. CI Matrix Update

**File:** `.github/workflows/ci.yml`

Add `macos-latest` to test matrix to ensure cross-platform tests pass.

**Estimated effort:** 30 minutes

---

### 6. Documentation

**Files:** `README.md`, `docs/`

Document:
- macOS support and setup instructions
- Performance limitations (CPU-only Whisper on M1)
- Recommended model sizes for macOS (`base` or `small`)
- Any known issues or workarounds

**Estimated effort:** 1 hour

---

## Performance Note

`faster-whisper` on M1 runs **CPU-only** (ONNX Runtime). The `large-v3` model will be noticeably slower than on an NVIDIA GPU.

Options:
- Default to `base` or `small` on macOS
- Document the limitation clearly
- (Future) Consider `whisper.cpp` with CoreML for M1 — major architectural change

---

## Files to Modify Summary

| File | Change | Effort |
|------|--------|--------|
| `whisper_tray/clipboard.py` | Platform-aware paste modifier | 5 min |
| `whisper_tray/config.py` | Platform-aware defaults (optional) | 10 min |
| `pyproject.toml` | Conditional pyobjc deps | 5 min |
| `.github/workflows/build-macos.yml` | New macOS build pipeline | 2-3 hours |
| `.github/workflows/ci.yml` | Add macos to test matrix | 30 min |
| `README.md` / `docs/` | Document macOS support & limitations | 1 hour |

---

## Bottom Line

**The code is nearly cross-platform ready.** The hardest parts are:
1. Setting up the macOS build/distribution pipeline (PyInstaller `.app` bundle)
2. The one-line paste key fix
3. Managing performance expectations for CPU-only Whisper on M1

No architectural refactoring needed — the modular structure makes this straightforward.
