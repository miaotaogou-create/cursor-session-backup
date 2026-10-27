"""历史备份列表与元数据。"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .paths import list_backup_dirs
from .sizing import dir_size_bytes, format_bytes

_NAME_RE = re.compile(r"^cursor-sessions_(\d{8})_(\d{6})$")


@dataclass(frozen=True)
class BackupEntry:
    path: Path
    display_time: str
    size_label: str
    size_bytes: int | None
    cursor_version: str | None
    item_count: int | None


def _parse_time_from_name(name: str) -> str | None:
    m = _NAME_RE.match(name)
    if not m:
        return None
    d, t = m.group(1), m.group(2)
    try:
        dt = datetime.strptime(d + t, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def describe_backup(path: Path, *, compute_size_if_missing: bool = False) -> BackupEntry:
    display = _parse_time_from_name(path.name) or path.name
    size_bytes: int | None = None
    cursor_version: str | None = None
    item_count: int | None = None

    for meta_name in ("backup-meta.json", "manifest.json"):
        meta = path / meta_name
        if not meta.is_file():
            continue
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if size_bytes is None and isinstance(data.get("total_bytes"), int):
            size_bytes = data["total_bytes"]
        if cursor_version is None and isinstance(data.get("cursor_version"), str):
            cursor_version = data["cursor_version"]
        if item_count is None and isinstance(data.get("items"), list):
            item_count = len(data["items"])

    if size_bytes is None and compute_size_if_missing and path.is_dir():
        size_bytes = dir_size_bytes(path)

    if size_bytes is None:
        size_label = "未知"
    else:
        size_label = format_bytes(size_bytes)

    return BackupEntry(
        path=path,
        display_time=display,
        size_label=size_label,
        size_bytes=size_bytes,
        cursor_version=cursor_version,
        item_count=item_count,
    )


def list_backup_entries(backup_root: Path, *, compute_size_if_missing: bool = False) -> list[BackupEntry]:
    return [
        describe_backup(p, compute_size_if_missing=compute_size_if_missing)
        for p in list_backup_dirs(backup_root)
    ]


def delete_backup_dir(path: Path) -> None:
    if not path.is_dir():
        raise FileNotFoundError(str(path))
    if not path.name.startswith("cursor-sessions_"):
        raise RuntimeError(f"拒绝删除非本工具备份目录: {path}")
    shutil.rmtree(path)
