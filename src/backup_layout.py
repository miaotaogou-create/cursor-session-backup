"""识别新旧两种备份目录布局。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STATE_DB = "state.vscdb"


@dataclass(frozen=True)
class BackupLayout:
    """一份备份里各内容的实际路径。"""

    root: Path
    global_storage: Path | None
    workspace_storage: Path | None
    projects: Path | None
    settings_json: Path | None
    keybindings_json: Path | None
    rules_dir: Path | None
    legacy: bool


def resolve_backup_layout(backup_dir: Path) -> BackupLayout:
    """兼容本工具布局与旧脚本 AppData_Roaming_Cursor_User 布局。"""
    modern_gs = backup_dir / "globalStorage"
    legacy_user = backup_dir / "AppData_Roaming_Cursor_User"
    legacy_gs = legacy_user / "globalStorage"

    if modern_gs.is_dir():
        return BackupLayout(
            root=backup_dir,
            global_storage=modern_gs,
            workspace_storage=_dir_or_none(backup_dir / "workspaceStorage"),
            projects=_dir_or_none(backup_dir / "dot-cursor-projects")
            or _dir_or_none(backup_dir / "dot_cursor_projects"),
            settings_json=_file_or_none(backup_dir / "settings.json")
            or _file_or_none(legacy_user / "settings.json"),
            keybindings_json=_file_or_none(backup_dir / "keybindings.json")
            or _file_or_none(legacy_user / "keybindings.json"),
            rules_dir=_dir_or_none(backup_dir / "ZYL_dot_cursor"),
            legacy=False,
        )

    return BackupLayout(
        root=backup_dir,
        global_storage=_dir_or_none(legacy_gs),
        workspace_storage=_dir_or_none(legacy_user / "workspaceStorage"),
        projects=_dir_or_none(backup_dir / "dot_cursor_projects")
        or _dir_or_none(backup_dir / "dot-cursor-projects"),
        settings_json=_file_or_none(legacy_user / "settings.json"),
        keybindings_json=_file_or_none(legacy_user / "keybindings.json"),
        rules_dir=_dir_or_none(backup_dir / "ZYL_dot_cursor"),
        legacy=True,
    )


def backup_has_state_db(layout: BackupLayout) -> bool:
    return bool(layout.global_storage and (layout.global_storage / STATE_DB).is_file())


def _dir_or_none(path: Path) -> Path | None:
    return path if path.is_dir() else None


def _file_or_none(path: Path) -> Path | None:
    return path if path.is_file() else None
