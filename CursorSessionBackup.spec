# -*- mode: python ; coding: utf-8 -*-
# 便携单文件：WebView2 + 内嵌 ui/dist，不再捆绑 tkinter/Tcl。

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

hidden = collect_submodules("src")
wv_datas, wv_binaries, wv_hidden = collect_all("webview")

ui_dist = Path("ui") / "dist"
if not (ui_dist / "index.html").is_file():
    raise SystemExit("缺少 ui/dist：请先在 ui 目录执行 npm run build")

icon_path = Path("assets") / "app.ico"
if not icon_path.is_file():
    raise SystemExit("缺少 assets/app.ico：请先执行 python assets/generate_icon.py")

a = Analysis(
    ["run_gui.py"],
    pathex=["."],
    binaries=list(wv_binaries),
    datas=list(wv_datas) + [(str(ui_dist), "ui")],
    hiddenimports=hidden + list(wv_hidden) + ["clr_loader", "pythonnet"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter", "customtkinter"],
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
    icon=str(icon_path),
)
