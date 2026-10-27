"""定位本机 Cursor 安装目录与可执行文件。"""

from __future__ import annotations

import json
import os
from pathlib import Path


def default_install_candidates() -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    return [
        local / "Programs" / "cursor" / "Cursor.exe",
        local / "Programs" / "Cursor" / "Cursor.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Cursor" / "Cursor.exe",
    ]


def find_cursor_exe() -> Path | None:
    for p in default_install_candidates():
        if p.is_file():
            return p
    return None


def find_cursor_install_dir() -> Path | None:
    exe = find_cursor_exe()
    return exe.parent if exe else None


def read_cursor_version(install_dir: Path | None = None) -> str | None:
    root = install_dir or find_cursor_install_dir()
    if root is None:
        return None
    # 常见：resources/app/product.json 或 package.json
    for rel in (
        Path("resources") / "app" / "product.json",
        Path("resources") / "app" / "package.json",
        Path("package.json"),
    ):
        fp = root / rel
        if not fp.is_file():
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for key in ("version", "cursorVersion", "appVersion"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None
