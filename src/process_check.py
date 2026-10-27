"""检测 Cursor 相关进程是否仍在运行。"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


# Windows 任务管理器里常见的进程名（不含 .exe 后缀，tasklist 对照用）
CURSOR_PROCESS_NAMES = (
    "Cursor",
    "cursor",
)


@dataclass(frozen=True)
class ProcessHit:
    name: str
    pid: str


def list_cursor_processes() -> list[ProcessHit]:
    """返回仍在运行的 Cursor 进程列表；查不到 tasklist 时返回空（调用方自行提示）。"""
    try:
        completed = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except OSError:
        return []

    hits: list[ProcessHit] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # CSV: "name","pid","session","session#","mem"
        parts = [p.strip().strip('"') for p in line.split('","')]
        if not parts:
            continue
        raw_name = parts[0].strip('"')
        base = raw_name[:-4] if raw_name.lower().endswith(".exe") else raw_name
        if base in CURSOR_PROCESS_NAMES:
            pid = parts[1] if len(parts) > 1 else "?"
            hits.append(ProcessHit(name=raw_name, pid=pid))
    return hits


def cursor_is_running() -> bool:
    return bool(list_cursor_processes())
