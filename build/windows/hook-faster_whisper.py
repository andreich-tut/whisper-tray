"""
PyInstaller hook for faster-whisper.
Ensures ONNX model files and assets are bundled with the executable.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files (including ONNX models)
datas = collect_data_files("faster_whisper")

# Collect all submodules
hiddenimports = collect_submodules("faster_whisper")

# Also ensure onnxruntime is properly bundled
hiddenimports += [
    "onnxruntime",
    "onnxruntime.capi",
    "onnxruntime.capi._pybind_state",
    "onnxruntime.capi._pybind_state_gpu",
    "onnxruntime.capi._pybind_state_directml",
]
