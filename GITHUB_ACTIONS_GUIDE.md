# Build Windows EXE from Linux via GitHub Actions

## 🚀 Quick Start

### Method 1: One-Click (Recommended)

```bash
./trigger-windows-build.sh
```

This script will:
- ✅ Check your GitHub setup
- ✅ Push your code
- ✅ Trigger the GitHub Actions workflow
- ✅ Show you where to download the `.exe`

---

### Method 2: Manual Push

```bash
git add -A
git commit -m "build: trigger windows build"
git push
```

The workflow **auto-triggers** on push to `main` or `master`.

---

### Method 3: GitHub Web Interface

1. Go to your repo on GitHub
2. Click **Actions** tab
3. Click **"Build Windows EXE"** workflow
4. Click **"Run workflow"** → **"Run workflow"** button
5. Wait ~5-10 minutes

---

## 📦 Download the Build

### Via GitHub CLI:
```bash
gh run list --workflow=build-windows.yml --limit 3
gh run download <run-id>
```

### Via Web Browser:
1. Go to **Actions** → **Build Windows EXE** → Latest run
2. Scroll to **"Artifacts"** section
3. Click **"WhisperTray-Windows"** to download
4. Extract the zip → Run `WhisperTray.exe`

---

## 🎯 What Gets Built

```
WhisperTray-Windows.zip
├── WhisperTray.exe           ← Release version (no console)
├── _internal/
│   └── faster_whisper/
│       └── assets/
│           └── silero_vad_v6.onnx  ← Auto-bundled ✅
└── ... (all dependencies)
```

Also creates: `WhisperTray-Windows-DEBUG.zip` (with console for debugging)

---

## 🏷️ Create a Release (Optional)

To create a permanent GitHub release:

```bash
# Tag a version
git tag v1.0.0
git push origin v1.0.0
```

This auto-creates a GitHub Release with the `.exe` attached!

---

## ⚙️ Workflow Triggers

The build runs on:

| Trigger | How |
|---------|-----|
| **Push to main/master** | Automatic |
| **Push tag (v*)** | Automatic + creates Release |
| **Pull Request** | Automatic (test only, no release) |
| **Manual** | Actions tab → Run workflow |

---

## 🔧 Customize the Build

Edit `.github/workflows/build-windows.yml` to:

- Change Python version (line 15)
- Add environment variables
- Change build settings
- Enable CUDA DLL bundling

---

## 📝 Build Logs

If the build fails:

1. Go to **Actions** → Failed run
2. Click **"Build WhisperTray for Windows"** job
3. Read the step-by-step logs
4. Fix the issue and push again

---

## 💡 Tips

- **Artifact retention:** 30 days (download before they expire)
- **Build time:** ~5-10 minutes
- **Cost:** Free (GitHub Actions free tier: 2000 min/month)
- **No Windows needed:** Everything runs in GitHub's cloud!

---

**Need help?** Check the workflow file or `BUILD_WINDOWS.md`
