# -*- mode: python ; coding: utf-8 -*-
# 便携版：目录模式（onedir），可靠捆绑 Tcl/Tk，避免单文件丢 init.tcl

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

hidden = collect_submodules("src")
ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")

tcl_root = Path(sys.base_prefix) / "tcl"
extra_datas = []
if (tcl_root / "tcl8.6").is_dir():
    extra_datas.append((str(tcl_root / "tcl8.6"), "_tcl_data"))
if (tcl_root / "tk8.6").is_dir():
    extra_datas.append((str(tcl_root / "tk8.6"), "_tk_data"))
if (tcl_root / "tcl8").is_dir():
    extra_datas.append((str(tcl_root / "tcl8"), "tcl8"))

a = Analysis(
    ["run_gui.py"],
    pathex=["."],
    binaries=ctk_binaries,
    datas=ctk_datas + extra_datas,
    hiddenimports=hidden + list(ctk_hidden),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthook_tcl_tk.py"],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CursorSessionBackup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CursorSessionBackup",
)
