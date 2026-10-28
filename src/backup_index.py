"""历史备份列表与元数据。"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .backup_layout import backup_has_state_db, resolve_backup_layout
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
    usable: bool
    note: str | None = None


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
        size_label = "计算中…" if compute_size_if_missing is False else "未知"
    else:
        size_label = format_bytes(size_bytes)

    layout = resolve_backup_layout(path)
    usable = backup_has_state_db(layout)
    note = None
    if not usable:
        if layout.global_storage is None:
            note = "不完整：缺少会话库目录"
        else:
            note = "不完整：缺少 state.vscdb（无法恢复对话）"
    elif layout.legacy:
        note = "旧版备份格式"

    return BackupEntry(
        path=path,
        display_time=display,
        size_label=size_label,
        size_bytes=size_bytes,
        cursor_version=cursor_version,
        item_count=item_count,
        usable=usable,
        note=note,
    )


def list_backup_entries(backup_root: Path, *, compute_size_if_missing: bool = False) -> list[BackupEntry]:
    return [
        describe_backup(p, compute_size_if_missing=compute_size_if_missing)
        for p in list_backup_dirs(backup_root)
    ]


def _clear_readonly(func, path, _exc_info) -> None:
    # shutil.rmtree onerror：去掉只读后再删
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        raise


def delete_backup_dir(path: Path) -> None:
    if not path.is_dir():
        raise FileNotFoundError(str(path))
    if not path.name.startswith("cursor-sessions_"):
        raise RuntimeError(f"拒绝删除非本工具备份目录: {path}")

    # 先批量清只读，再 rmtree
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = Path(root) / name
            try:
                if fp.exists() and not os.access(fp, os.W_OK):
                    os.chmod(fp, stat.S_IWRITE)
            except OSError:
                continue

    shutil.rmtree(path, onerror=_clear_readonly)
    if path.exists():
        raise RuntimeError(f"删除未完成，目录仍在: {path}")
