"""
PyInstaller hook for WhisperTray
Ensures all required modules and data files are bundled
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all submodules from key packages
hiddenimports = collect_submodules("faster_whisper")
hiddenimports += collect_submodules("sounddevice")
hiddenimports += collect_submodules("pynput")
hiddenimports += collect_submodules("pynput.keyboard")
hiddenimports += collect_submodules("pynput.mouse")
hiddenimports += collect_submodules("pystray")
hiddenimports += collect_submodules("PIL")
hiddenimports += collect_submodules("pyperclip")
hiddenimports += collect_submodules("pyautogui")
hiddenimports += collect_submodules("ctranslate2")
hiddenimports += collect_submodules("onnxruntime")

# Collect data files (including ONNX models)
datas = collect_data_files("faster_whisper", include_py_files=True)
