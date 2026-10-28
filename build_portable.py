"""打包无控制台窗口的便携目录版（含 Tcl/Tk）。"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release"
DIST_DIR = ROOT / "dist" / "CursorSessionBackup"
OUT_DIR = RELEASE / "CursorSessionBackup"
OUT_EXE = OUT_DIR / "CursorSessionBackup.exe"


def main() -> int:
    for path in (ROOT / "build", ROOT / "dist"):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR, ignore_errors=True)
    RELEASE.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(ROOT / "CursorSessionBackup.spec"),
    ]
    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    if completed.returncode != 0:
        print("PyInstaller failed", file=sys.stderr)
        return completed.returncode
    if not (DIST_DIR / "CursorSessionBackup.exe").is_file():
        print(f"Missing output: {DIST_DIR}", file=sys.stderr)
        return 1

    shutil.copytree(DIST_DIR, OUT_DIR)
    init_tcl = OUT_DIR / "_internal" / "_tcl_data" / "init.tcl"
    # PyInstaller 6 onedir 通常把依赖放在 _internal
    candidates = [
        OUT_DIR / "_tcl_data" / "init.tcl",
        OUT_DIR / "_internal" / "_tcl_data" / "init.tcl",
    ]
    found = next((p for p in candidates if p.is_file()), None)
    if found is None:
        print("WARNING: init.tcl not found under release package", file=sys.stderr)
        # 列出一层便于排查
        for p in OUT_DIR.rglob("init.tcl"):
            print(" found elsewhere:", p)
            found = p
            break
    else:
        print(f"Tcl OK: {found}")

    if not OUT_EXE.is_file():
        print(f"Missing exe: {OUT_EXE}", file=sys.stderr)
        return 1

    # 根目录启动器，方便双击
    launcher = RELEASE / "启动Cursor会话备份.bat"
    launcher.write_text(
        '@echo off\r\nstart "" "%~dp0CursorSessionBackup\\CursorSessionBackup.exe"\r\n',
        encoding="utf-8",
    )
    print(f"OK: {OUT_EXE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
