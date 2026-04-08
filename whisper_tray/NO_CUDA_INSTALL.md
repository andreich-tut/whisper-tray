# No CUDA Installation Required - 3 Options

You can use WhisperTray **without installing CUDA Toolkit or cuDNN separately**. Here's how:

---

## Option 1: LM Studio Mode (Recommended - Easiest) ✅

**Pros**: No CUDA, no model download, runs anywhere  
**Cons**: Requires LM Studio running in background

### Steps:

1. **Download LM Studio**: https://lmstudio.ai (free)
2. **Install a Whisper model**:
   - Open LM Studio → Click "Download" (magnet icon)
   - Search "whisper-large-v3" → Download
3. **Start the server**:
   - Go to "Server" tab
   - Select the Whisper model
   - Click "Start Server" (default: `http://localhost:1234`)
4. **Create `.env` file** next to `WhisperTray.exe`:
   ```
   WHISPERTRAY_MODE=lmstudio
   LM_STUDIO_URL=http://localhost:1234
   ```
5. **Run `WhisperTray.exe`** - Done! 🎉

---

## Option 2: Auto-Bundle CUDA from pip Packages (Zero Extra Installs) ✅

**How it works**: When you run `pip install faster-whisper`, the CUDA DLLs are already downloaded as part of the `ctranslate2` package. The updated build script now finds and bundles them automatically.

### Steps:

1. **Ensure faster-whisper works with CUDA**:
   ```cmd
   python -c "from faster_whisper import WhisperModel; model = WhisperModel('tiny', device='cuda'); print('CUDA works!')"
   ```
   
   - If this works → CUDA DLLs are in your Python environment
   - If this fails → Install CUDA Toolkit (see Option 3)

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

## Option 3: CPU Mode Only (Slowest, No GPU)

**Pros**: Zero dependencies, works everywhere  
**Cons**: Much slower transcription (5-10x)

### Steps:

1. **Create `.env` file** next to `WhisperTray.exe`:
   ```
   WHISPERTRAY_MODE=local
   DEVICE=cpu
   MODEL_SIZE=base
   ```

2. **Run `WhisperTray.exe`** - Done!

> **Note**: Use smaller models (`base` or `small`) for acceptable CPU performance.

---

## Troubleshooting

### "CUDA DLL missing" error after build

If Option 2 doesn't work:

1. Check if CUDA DLLs exist in Python environment:
   ```cmd
   python -c "import ctranslate2, os, glob; ct_dir = os.path.dirname(ctranslate2.__file__); print(glob.glob(os.path.join(ct_dir, '*.dll')))"
   ```

2. If DLLs exist → Build script should find them
3. If DLLs don't exist → Use Option 1 (LM Studio) or Option 3 (CPU)

### Build says "CUDA not found - will use CPU mode"

This is expected if:
- System CUDA Toolkit not installed (normal)
- `ctranslate2` doesn't bundle CUDA DLLs (depends on version)

**Solution**: Use Option 1 (LM Studio) for easiest setup.

---

## Summary

| Option | CUDA Install | Model Download | Speed | Setup Time |
|--------|-------------|----------------|-------|------------|
| **LM Studio** | ❌ No | ✅ Yes (in LM Studio) | Fast | 5 min |
| **Auto-Bundle** | ❌ No (bundled from pip) | ✅ Yes (first run) | Fastest | 2 min |
| **CPU Mode** | ❌ No | ✅ Yes (first run) | Slow | 1 min |

**Recommendation**: Start with **LM Studio mode** (easiest), then try **Auto-Bundle** if you want maximum performance.
