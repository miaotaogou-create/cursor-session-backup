"""打包无控制台窗口的便携单文件 exe。"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "release"
DIST_EXE = ROOT / "dist" / "CursorSessionBackup.exe"
OUT_EXE = RELEASE / "CursorSessionBackup.exe"


def main() -> int:
    for path in (ROOT / "build", ROOT / "dist"):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
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
    if not DIST_EXE.is_file():
        print(f"Missing output: {DIST_EXE}", file=sys.stderr)
        return 1
    shutil.copy2(DIST_EXE, OUT_EXE)
    print(f"OK: {OUT_EXE}")
    print(f"Size: {OUT_EXE.stat().st_size / (1024 * 1024):.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
