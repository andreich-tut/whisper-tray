# No CUDA Installation Required - 2 Options

You can use WhisperTray **without installing CUDA Toolkit or cuDNN separately**. Here's how:

---

## Option 1: Auto-Bundle CUDA from pip Packages (Zero Extra Installs) ✅

**How it works**: When you run `pip install faster-whisper`, the CUDA DLLs are already downloaded as part of the `ctranslate2` package. The updated build script now finds and bundles them automatically.

### Steps:

1. **Ensure faster-whisper works with CUDA**:
   ```cmd
   python -c "from faster_whisper import WhisperModel; model = WhisperModel('tiny', device='cuda'); print('CUDA works!')"
   ```

   - If this works → CUDA DLLs are in your Python environment
   - If this fails → Install CUDA Toolkit (see Option 2)

2. **Rebuild with updated script**:
   ```cmd
   cd whisper_tray
   build.bat
   ```

3. **Verify CUDA DLLs were bundled**:
   ```cmd
   dir ..\dist\WhisperTray\_internal\cublas*.dll
   ```

   Should show: `cublas64_12.dll`, `cublasLt64_12.dll`, etc.

4. **Run `WhisperTray.exe`** - Done! 🎉

### What Changed:

The updated `build.bat` and `whisper_tray.spec` now:
- Search `ctranslate2` package for CUDA DLLs
- Search `onnxruntime` package for CUDA DLLs
- Search entire Python `site-packages` for CUDA DLLs
- Bundle them automatically into `_internal` folder

**No separate CUDA Toolkit installation needed!**

---

## Option 2: CPU Mode Only (Slowest, No GPU)

**Pros**: Zero dependencies, works everywhere
**Cons**: Much slower transcription (5-10x)

### Steps:

1. **Create `.env` file** next to `WhisperTray.exe`:
   ```
   DEVICE=cpu
   MODEL_SIZE=base
   ```

2. **Run `WhisperTray.exe`** - Done!

> **Note**: Use smaller models (`base` or `small`) for acceptable CPU performance.

---

## Troubleshooting

### "CUDA DLL missing" error after build

If Option 1 doesn't work:

1. Check if CUDA DLLs exist in Python environment:
   ```cmd
   python -c "import ctranslate2, os, glob; ct_dir = os.path.dirname(ctranslate2.__file__); print(glob.glob(os.path.join(ct_dir, '*.dll')))"
   ```

2. If DLLs exist → Build script should find them
3. If DLLs don't exist → Use Option 2 (CPU mode)

### Build says "CUDA not found - will use CPU mode"

This is expected if:
- System CUDA Toolkit not installed (normal)
- `ctranslate2` doesn't bundle CUDA DLLs (depends on version)

**Solution**: Use CPU mode - it will work, just slower.

---

## Summary

| Option | CUDA Install | Model Download | Speed | Setup Time |
|--------|-------------|----------------|-------|------------|
| **Auto-Bundle** | ❌ No (bundled from pip) | ✅ Yes (first run) | Fastest | 2 min |
| **CPU Mode** | ❌ No | ✅ Yes (first run) | Slow | 1 min |

**Recommendation**: Try **Auto-Bundle** first for best performance. If CUDA DLLs aren't found, fall back to **CPU mode**.
