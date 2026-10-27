"""目录体积估算。"""

from __future__ import annotations

from pathlib import Path


def format_bytes(num: int) -> str:
    if num < 0:
        num = 0
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{num} B"


def dir_size_bytes(
    root: Path,
    *,
    skip_names: frozenset[str] | None = None,
) -> int:
    """递归统计文件大小；skip_names 按文件名精确跳过（如 state.vscdb.backup）。"""
    if not root.exists():
        return 0
    skip = skip_names or frozenset()
    total = 0
    if root.is_file():
        if root.name in skip:
            return 0
        try:
            return root.stat().st_size
        except OSError:
            return 0
    for dirpath, _dirnames, filenames in os_walk_safe(root):
        for name in filenames:
            if name in skip:
                continue
            fp = Path(dirpath) / name
            try:
                total += fp.stat().st_size
            except OSError:
                continue
    return total


def os_walk_safe(root: Path):
    import os

    yield from os.walk(root)
