"""检测 / 关闭 / 启动 Cursor 进程。"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .cursor_install import find_cursor_exe

# Windows 任务管理器里常见的进程名（不含 .exe 后缀，tasklist 对照用）
CURSOR_PROCESS_NAMES = (
    "Cursor",
    "cursor",
)

_CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


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
            creationflags=_CREATE_NO_WINDOW,
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


def close_cursor_processes(*, wait_seconds: float = 8.0) -> list[ProcessHit]:
    """请求结束 Cursor 进程；返回仍残留的进程（空列表表示已退出）。"""
    hits = list_cursor_processes()
    for hit in hits:
        subprocess.run(
            ["taskkill", "/PID", hit.pid, "/T", "/F"],
            capture_output=True,
            check=False,
            creationflags=_CREATE_NO_WINDOW,
        )
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if not cursor_is_running():
            return []
        time.sleep(0.4)
    return list_cursor_processes()


def launch_cursor(exe: Path | None = None) -> Path:
    target = exe or find_cursor_exe()
    if target is None or not target.is_file():
        raise FileNotFoundError("未找到 Cursor.exe，请手动启动")
    # 启动 GUI 程序不要带 CREATE_NO_WINDOW，否则窗口可能起不来
    subprocess.Popen([str(target)], cwd=str(target.parent))
    return target
