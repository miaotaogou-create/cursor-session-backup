"""先构建 React 界面，再打真正便携的单文件 exe（WebView2，无 tkinter）。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UI = ROOT / "ui"
RELEASE = ROOT / "release"
DIST_EXE = ROOT / "dist" / "CursorSessionBackup.exe"
OUT_EXE = RELEASE / "CursorSessionBackup.exe"
OLD_DIR = RELEASE / "CursorSessionBackup"


def _run(cmd: list[str], *, cwd: Path) -> None:
    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def build_ui() -> None:
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("未找到 npm，无法构建界面")
    if not (UI / "node_modules").is_dir():
        _run([npm, "install"], cwd=UI)
    _run([npm, "run", "build"], cwd=UI)
    if not (UI / "dist" / "index.html").is_file():
        raise SystemExit("ui/dist/index.html 未生成")


def main() -> int:
    build_ui()

    for path in (ROOT / "build", ROOT / "dist"):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    if OUT_EXE.exists():
        OUT_EXE.unlink()
    if OLD_DIR.exists():
        shutil.rmtree(OLD_DIR, ignore_errors=True)

    # 避免旧 Tcl 环境变量干扰（虽已不用 tk）
    env = dict(os.environ)
    for key in ("TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH"):
        env.pop(key, None)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(ROOT / "CursorSessionBackup.spec"),
    ]
    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=ROOT, check=False, env=env)
    if completed.returncode != 0:
        print("PyInstaller failed", file=sys.stderr)
        return completed.returncode
    if not DIST_EXE.is_file():
        print(f"Missing output: {DIST_EXE}", file=sys.stderr)
        return 1

    shutil.copy2(DIST_EXE, OUT_EXE)
    size_mb = OUT_EXE.stat().st_size / (1024 * 1024)
    print(f"OK: {OUT_EXE} ({size_mb:.1f} MB)")
    # 保留 bat 仅作兼容；日常请直接双击 exe
    launcher = RELEASE / "启动Cursor会话备份.bat"
    launcher.write_text(
        '@echo off\r\n'
        'rem 推荐直接双击 CursorSessionBackup.exe；本 bat 仅兼容旧快捷方式\r\n'
        'start "" "%~dp0CursorSessionBackup.exe"\r\n',
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
