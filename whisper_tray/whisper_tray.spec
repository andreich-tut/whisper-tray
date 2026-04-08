# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import glob as glob_module
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Add project root to path for imports
spec_dir = os.path.dirname(os.path.realpath(sys.argv[0])) if hasattr(sys, 'argv') and sys.argv else os.getcwd()
sys.path.insert(0, spec_dir)

# Check if building debug version (with console)
# Pass --debug flag when building: pyinstaller whisper_tray.spec --debug
build_debug = '--debug' in sys.argv or 'DEBUG' in os.environ.get('PYINSTALLER_DEBUG', '')

# Collect faster-whisper data files (ONNX models, assets)
faster_whisper_datas = collect_data_files('faster_whisper')
faster_whisper_hiddenimports = collect_submodules('faster_whisper')

# ============================================================
# CUDA DLL Bundling (Required for faster-whisper GPU mode)
# ============================================================
binaries = []
cuda_dlls_found = False

def find_cuda_dlls():
    """Find CUDA DLLs from Python packages and system locations."""
    cuda_paths = []
    found_dll_files = []

    # Check CUDA_PATH environment variable
    cuda_path = os.environ.get('CUDA_PATH')
    if cuda_path:
        cuda_paths.append(os.path.join(cuda_path, 'bin'))

    # Check CUDA_PATH_V12_x and CUDA_PATH_V11_x
    for env_var in sorted(os.environ.keys()):
        if env_var.startswith('CUDA_PATH_V'):
            cuda_paths.append(os.path.join(os.environ[env_var], 'bin'))

    # Common system installation paths (updated for Windows 11)
    common_paths = [
        r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA',
        r'C:\Program Files\NVIDIA GPU Computing Toolkit',
        r'C:\CUDA',
    ]
    for base in common_paths:
        if os.path.exists(base):
            if os.path.isdir(base):
                for item in sorted(os.listdir(base)):
                    full_path = os.path.join(base, item)
                    if os.path.isdir(full_path):
                        bin_dir = os.path.join(full_path, 'bin')
                        if os.path.exists(bin_dir):
                            cuda_paths.append(bin_dir)

    # Check Python site-packages for bundled CUDA DLLs
    # ctranslate2 ships CUDA DLLs in its package
    try:
        import ctranslate2
        ct_dir = os.path.dirname(ctranslate2.__file__)
        cuda_paths.append(ct_dir)
        # Also check subdirectories
        for root, dirs, files in os.walk(ct_dir):
            if any(f.endswith('.dll') for f in files):
                cuda_paths.append(root)
    except ImportError:
        pass

    # Check onnxruntime for CUDA DLLs
    try:
        import onnxruntime
        ort_dir = os.path.dirname(onnxruntime.__file__)
        cuda_paths.append(ort_dir)
        for root, dirs, files in os.walk(ort_dir):
            if any(f.endswith('.dll') for f in files):
                cuda_paths.append(root)
    except ImportError:
        pass

    # Search entire site-packages for CUDA DLLs
    try:
        import site
        for site_pkg in site.getsitepackages():
            if os.path.exists(site_pkg):
                for root, dirs, files in os.walk(site_pkg):
                    cuda_dlls_in_dir = [f for f in files if f.startswith(('cublas', 'cudart', 'cudnn', 'cusolver', 'cusparse')) and f.endswith('.dll')]
                    if cuda_dlls_in_dir:
                        cuda_paths.append(root)
    except Exception:
        pass

    return cuda_paths

# Required CUDA DLLs for cuBLAS and cuDNN
required_cuda_dlls = [
    'cublas64_12.dll',
    'cublasLt64_12.dll',
    'cudart64_12.dll',
    'cudnn64_8.dll',
    'cudnn_adv_infer64_8.dll',
    'cudnn_cnn_infer64_8.dll',
    'cudnn_engines_precompiled64_8.dll',
    'cudnn_engines_runtime64_8.dll',
    'cudnn_ops_infer64_8.dll',
    'cudnn_ops_train64_8.dll',
    'cufft64_10.dll',
    'curand64_10.dll',
    'cusolver64_11.dll',
    'cusparse64_12.dll',
]

# Also check for v11 variants
required_cuda_dlls_v11 = [
    'cublas64_11.dll',
    'cublasLt64_11.dll',
    'cudart64_11.dll',
    'cudnn64_8.dll',
    'cufft64_10.dll',
    'curand64_10.dll',
    'cusolver64_11.dll',
    'cusparse64_11.dll',
]

# Additional CUDA DLLs that may be needed
additional_cuda_dlls = [
    'nvrtc64_12.dll',
    'nvrtc64_11.dll',
    'nvrtc-builtins64_12.dll',
    'nvrtc-builtins64_11.dll',
    'nvToolsExt64_1.dll',
    'onnxruntime_providers_cuda.dll',
    'onnxruntime_providers_shared.dll',
    'onnxruntime_providers_tensorrt.dll',
]

all_required_dlls = required_cuda_dlls + required_cuda_dlls_v11 + additional_cuda_dlls

cuda_paths = find_cuda_dlls()
found_dlls = set()

for cuda_path in cuda_paths:
    if not os.path.exists(cuda_path):
        continue
    for dll_name in all_required_dlls:
        dll_path = os.path.join(cuda_path, dll_name)
        if os.path.exists(dll_path) and dll_name not in found_dlls:
            binaries.append((dll_path, '.'))
            found_dlls.add(dll_name)
            print(f"[OK] Found CUDA DLL: {dll_path}")
            cuda_dlls_found = True

if cuda_dlls_found:
    print(f"[OK] Bundled {len(found_dlls)} CUDA DLLs")
else:
    print("[WARN] No CUDA DLLs found - executable will only work in CPU mode")
    print("       Install CUDA Toolkit if GPU acceleration is needed")

# Explicitly add Silero VAD ONNX file if collect_data_files missed it
import importlib.util
fw_spec = importlib.util.find_spec('faster_whisper')
if fw_spec and fw_spec.origin:
    fw_dir = os.path.dirname(fw_spec.origin)
    onnx_path = os.path.join(fw_dir, 'assets', 'silero_vad_v6.onnx')
    if os.path.exists(onnx_path):
        # Add to datas - will be placed in faster_whisper/assets/
        faster_whisper_datas.append((onnx_path, 'faster_whisper/assets'))
        print(f"[OK] Explicitly adding {onnx_path}")
    else:
        print(f"[WARN] ONNX file not found at {onnx_path}")

# Collect onnxruntime data files (CPU only to avoid CUDA dependency)
onnxruntime_datas = collect_data_files('onnxruntime')
onnxruntime_hiddenimports = collect_submodules('onnxruntime')

# Collect ctranslate2 data files and binaries (core inference engine)
try:
    ctranslate2_datas = collect_data_files('ctranslate2')
    ctranslate2_binaries = []
    # Try to collect dynamic libs from ctranslate2
    from PyInstaller.utils.hooks import collect_dynamic_libs
    ctranslate2_binaries = collect_dynamic_libs('ctranslate2')
    ctranslate2_hiddenimports = collect_submodules('ctranslate2')
    print(f"[OK] Collected ctranslate2: {len(ctranslate2_datas)} data files, {len(ctranslate2_binaries)} binaries")
except Exception as e:
    print(f"[WARN] Could not collect ctranslate2 files: {e}")
    ctranslate2_datas = []
    ctranslate2_binaries = []
    ctranslate2_hiddenimports = []

# Collect tokenizers (used by faster-whisper)
try:
    tokenizers_hiddenimports = collect_submodules('tokenizers')
    print(f"[OK] Collected tokenizers: {len(tokenizers_hiddenimports)} modules")
except Exception as e:
    print(f"[WARN] Could not collect tokenizers: {e}")
    tokenizers_hiddenimports = []

# Collect av (PyAV) data files and FFmpeg DLLs
try:
    av_datas = collect_data_files('av')
    av_hiddenimports = collect_submodules('av')
    print(f"[OK] Collected av (PyAV): {len(av_datas)} data files")
except Exception as e:
    print(f"[WARN] Could not collect av (PyAV) files: {e}")
    av_datas = []
    av_hiddenimports = []

# Collect sounddevice PortAudio DLL
# sounddevice ships PortAudio via _sounddevice_data package
try:
    from PyInstaller.utils.hooks import collect_dynamic_libs
    sounddevice_binaries = collect_dynamic_libs('_sounddevice_data')
    if sounddevice_binaries:
        print(f"[OK] Found sounddevice PortAudio DLLs: {[b[0] for b in sounddevice_binaries]}")
    else:
        print("[WARN] No PortAudio DLLs found in _sounddevice_data")
        sounddevice_binaries = []
except Exception as e:
    print(f"[WARN] Could not collect sounddevice binaries: {e}")
    sounddevice_binaries = []

# Exclude CUDA-related packages to reduce size and avoid missing DLL errors
excludes_list = [
    'onnxruntime.training',
    'onnxruntime.capi._pybind_state_gpu',
    'torch',
    'torchvision',
]

# Collect sounddevice data files
sounddevice_datas = collect_data_files('sounddevice')

# Build datas list
datas = (
    faster_whisper_datas
    + onnxruntime_datas
    + sounddevice_datas
    + ctranslate2_datas
    + av_datas
)

# Build binaries list (CUDA DLLs + ctranslate2 + sounddevice PortAudio)
binaries = binaries + ctranslate2_binaries + sounddevice_binaries

# Add .env file if it exists
env_path = os.path.join(spec_dir, '.env')
if os.path.exists(env_path):
    datas.append((env_path, '.'))

a = Analysis(
    ['whisper_tray.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pynput.keyboard._base',
        'pynput.mouse._base',
        'sounddevice',
        'faster_whisper',
        'faster_whisper.transcribe',
        'faster_whisper.vad',
        'pystray._win32',
        'pystray.platforms.windows',
        'pystray.platforms.windows._icon',
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageDraw',
        'pyperclip',
        'pyautogui',
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        'numpy',
        'wave',
        'ctypes',
        'queue',
        'threading',
        'json',
        'base64',
        'dotenv',
        'python_dotenv',
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi._pybind_state',
        'onnxruntime.capi.onnxruntime_providers_shared',
        'onnxruntime.capi.onnxruntime_providers_cuda',
        'ctypes.macholib',
        'comtypes',
        'ctranslate2',
        'tokenizers',
        'tokenizers.models',
        'tokenizers.decoders',
        'tokenizers.normalizers',
        'tokenizers.pre_tokenizers',
        'tokenizers.processors',
        'tokenizers.trainers',
        'huggingface_hub',
        'huggingface_hub.constants',
        'av',
        'av.audio',
        'av.audio.frame',
        'av.audio.stream',
        'av.dataset',
        'av.stream',
        '_sounddevice_data',
    ]
    + faster_whisper_hiddenimports
    + onnxruntime_hiddenimports
    + ctranslate2_hiddenimports
    + tokenizers_hiddenimports
    + av_hiddenimports,
    hookspath=[spec_dir],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'tkinter.ttk',
        'matplotlib',
        'scipy',
        'pytest',
        'nose',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WhisperTray',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=build_debug,  # Console only for debug builds
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
