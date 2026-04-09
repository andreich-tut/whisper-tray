# -*- mode: python ; coding: utf-8 -*-

# PyInstaller spec file for WhisperTray
# This file tells PyInstaller how to build the Windows executable

import os

# Support environment variable overrides for CI builds
# WHISPER_TRAY_DEBUG=1 builds with console and debug settings
# WHISPER_TRAY_NAME sets the output name
_is_debug = os.environ.get('WHISPER_TRAY_DEBUG', '0') == '1'
_out_name = os.environ.get('WHISPER_TRAY_NAME', 'WhisperTray')

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
    'whisper_tray.tray.icon',
    'whisper_tray.tray.menu',
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

hidden_imports = whisper_tray_modules + third_party_imports

a = Analysis(
    ['whisper_tray/cli.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=['build/windows'],
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
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name=_out_name,
)
