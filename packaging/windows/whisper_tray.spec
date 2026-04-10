# -*- mode: python ; coding: utf-8 -*-

# PyInstaller spec file for WhisperTray
# This file tells PyInstaller how to build the Windows executable

import os
from importlib.util import find_spec

# Support environment variable overrides for CI builds
# WHISPER_TRAY_DEBUG=1 builds with console and debug settings
# WHISPER_TRAY_NAME sets the output name
_is_debug = os.environ.get('WHISPER_TRAY_DEBUG', '0') == '1'
_out_name = os.environ.get('WHISPER_TRAY_NAME', 'WhisperTray')
_has_pyside6 = find_spec('PySide6') is not None

block_cipher = None

# All whisper_tray modules that need to be bundled
whisper_tray_modules = [
    'whisper_tray',
    'whisper_tray.app',
    'whisper_tray.cli',
    'whisper_tray.config',
    'whisper_tray.clipboard',
    'whisper_tray.audio.recorder',
    'whisper_tray.audio.transcriber',
    'whisper_tray.input.hotkey',
    'whisper_tray.overlay',
    'whisper_tray.overlay.controller',
    'whisper_tray.tray.icon',
    'whisper_tray.tray.menu',
    'whisper_tray.state',
]

# Third-party modules that need explicit importing
third_party_imports = [
    'sounddevice',
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'pystray',
    'PIL',
    'pyperclip',
    'pyautogui',
    'numpy',
    'dotenv',
]

if _has_pyside6:
    whisper_tray_modules.append('whisper_tray.overlay.pyside_overlay')
    third_party_imports.extend([
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ])

hidden_imports = whisper_tray_modules + third_party_imports

# Get the project root directory
# PyInstaller runs from project root, so we use that as our base
project_root = os.getcwd()

a = Analysis(
    [os.path.join(project_root, 'whisper_tray', 'cli.py')],
    pathex=[project_root],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[os.path.join(project_root, 'packaging', 'windows')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    block_cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    name=_out_name,
    debug=_is_debug,
    bootloader_ignore_signals=False,
    strip=False,
    # Keep Windows builds uncompressed; UPX can trigger early DLL load failures.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=_is_debug,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=_out_name,
)
