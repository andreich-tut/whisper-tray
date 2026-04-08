# WhisperTray - Quick Build Card

## 🚀 Fastest Way (On Windows)

```bash
cd whisper_tray
build.bat          # Release version (no console)
# OR
build_console.bat  # Debug version (shows console)
```

Find your EXE in: `..\dist\WhisperTray\` or `..\dist\WhisperTray_DEBUG\`

## 📋 What Gets Built

```
dist/WhisperTray/
├── WhisperTray.exe          ← Run this!
└── _internal/
    └── faster_whisper/
        └── assets/
            └── silero_vad_v6.onnx  ← Auto-bundled ✅
```

## 🔧 If Build Fails

| Error | Fix |
|-------|-----|
| `Python not found` | Install Python 3.10+ from python.org |
| `silero_vad_v6.onnx failed` | Rebuild - spec file now includes it explicitly |
| `cublas64_*.dll not found` | Copy CUDA DLLs or use `DEVICE=cpu` |
| Module errors | `pip install --upgrade -r requirements.txt` |

## 🎯 Usage

1. Run `WhisperTray.exe`
2. Wait for tray icon (gray = ready)
3. Hold `Ctrl+Space` to record
4. Release to transcribe & auto-paste

## 📝 Log File

Check `whisper_tray.log` next to the EXE for detailed error messages.

---

**Full guide:** See `BUILD_WINDOWS.md`
