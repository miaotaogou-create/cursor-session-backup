"""本机 Cursor 相关路径解析。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_BACKUP_ROOT = Path(r"C:\ZYL\backup")
DEFAULT_RULES_DIR = Path(r"C:\ZYL\.cursor")


@dataclass(frozen=True)
class CursorPaths:
    """当前用户下的 Cursor 数据路径。"""

    appdata_user: Path
    global_storage: Path
    workspace_storage: Path
    settings_json: Path
    keybindings_json: Path
    dot_cursor_projects: Path
    rules_dir: Path

    @classmethod
    def resolve(cls, rules_dir: Path | None = None) -> "CursorPaths":
        appdata = Path(os.environ.get("APPDATA", ""))
        if not appdata.parts:
            raise RuntimeError("未找到 APPDATA 环境变量")
        user = appdata / "Cursor" / "User"
        home = Path.home()
        return cls(
            appdata_user=user,
            global_storage=user / "globalStorage",
            workspace_storage=user / "workspaceStorage",
            settings_json=user / "settings.json",
            keybindings_json=user / "keybindings.json",
            dot_cursor_projects=home / ".cursor" / "projects",
            rules_dir=Path(rules_dir) if rules_dir else DEFAULT_RULES_DIR,
        )


def new_backup_dir_name(now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"cursor-sessions_{stamp}"


def list_backup_dirs(backup_root: Path) -> list[Path]:
    """列出备份根目录下形如 cursor-sessions_* 的子目录（新在前）。"""
    if not backup_root.is_dir():
        return []
    dirs = [
        p
        for p in backup_root.iterdir()
        if p.is_dir() and p.name.startswith("cursor-sessions_")
    ]
    dirs.sort(key=lambda p: p.name, reverse=True)
    return dirs
