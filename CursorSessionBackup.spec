# -*- mode: python ; coding: utf-8 -*-
# 便携版单文件：无控制台窗口

from PyInstaller.utils.hooks import collect_all, collect_submodules

hidden = collect_submodules("src")
ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")

a = Analysis(
    ["run_gui.py"],
    pathex=["."],
    binaries=ctk_binaries,
    datas=ctk_datas,
    hiddenimports=hidden + list(ctk_hidden),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CursorSessionBackup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
