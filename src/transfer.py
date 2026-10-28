"""文件/目录拷贝（Windows 优先 robocopy），支持进度上报。"""

from __future__ import annotations

import shutil
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from .sizing import dir_size_bytes, format_bytes

# message, fraction(0..1 或 None 表示仅更新文案)
ProgressFn = Callable[[str, float | None], None]

_CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


def emit(progress: ProgressFn | None, message: str, fraction: float | None = None) -> None:
    if progress:
        progress(message, fraction)


def copy_file(
    src: Path,
    dst: Path,
    progress: ProgressFn | None = None,
    *,
    progress_span: tuple[float, float] | None = None,
) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    start, end = progress_span or (None, None)
    if start is not None and end is not None:
        emit(progress, f"复制文件: {src.name}", start)
    else:
        emit(progress, f"复制文件: {src} -> {dst}")
    shutil.copy2(src, dst)
    if start is not None and end is not None:
        emit(progress, f"已复制: {src.name}", end)


def copy_tree(
    src: Path,
    dst: Path,
    *,
    exclude_files: list[str] | None = None,
    progress: ProgressFn | None = None,
    progress_span: tuple[float, float] | None = None,
    expected_bytes: int | None = None,
) -> None:
    """复制目录树。exclude_files 为文件名列表（仅文件名，非路径）。"""
    if not src.exists():
        raise FileNotFoundError(f"源路径不存在: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    excludes = exclude_files or []

    if shutil.which("robocopy"):
        _robocopy(
            src,
            dst,
            excludes=excludes,
            progress=progress,
            progress_span=progress_span,
            expected_bytes=expected_bytes,
        )
        return

    emit(progress, f"robocopy 不可用，改用 shutil 复制: {src}")
    _shutil_copytree(
        src,
        dst,
        excludes=set(excludes),
        progress=progress,
        progress_span=progress_span,
        expected_bytes=expected_bytes,
    )


def _robocopy(
    src: Path,
    dst: Path,
    *,
    excludes: list[str],
    progress: ProgressFn | None,
    progress_span: tuple[float, float] | None,
    expected_bytes: int | None,
) -> None:
    cmd = [
        "robocopy",
        str(src),
        str(dst),
        "/E",
        "/COPY:DAT",
        "/R:2",
        "/W:2",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/nc",
        "/ns",
        "/np",
    ]
    if excludes:
        cmd.append("/XF")
        cmd.extend(excludes)

    start, end = progress_span or (0.0, 1.0)
    label = src.name
    emit(
        progress,
        f"正在复制 {label}"
        + (f"（约 {format_bytes(expected_bytes)}）" if expected_bytes else "")
        + (f"；排除 {', '.join(excludes)}" if excludes else ""),
        start,
    )

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_CREATE_NO_WINDOW,
    )

    stop = threading.Event()

    def poller() -> None:
        # ponytail: 用目标目录体积近似进度；robocopy 结束后会 snap 到 end
        while not stop.wait(0.35):
            if expected_bytes and expected_bytes > 0 and progress_span is not None:
                done = dir_size_bytes(dst)
                ratio = min(0.99, done / float(expected_bytes))
                frac = start + (end - start) * ratio
                emit(progress, f"正在复制 {label}… {format_bytes(done)} / {format_bytes(expected_bytes)}", frac)
            elif progress_span is not None:
                emit(progress, f"正在复制 {label}…", None)

    t = threading.Thread(target=poller, daemon=True)
    t.start()
    try:
        code = proc.wait()
    finally:
        stop.set()
        t.join(timeout=1.0)

    if code >= 8:
        raise RuntimeError(f"robocopy 失败 exit={code}\n源: {src}\n目标: {dst}")
    emit(progress, f"已完成: {label}", end)


def _shutil_copytree(
    src: Path,
    dst: Path,
    *,
    excludes: set[str],
    progress: ProgressFn | None,
    progress_span: tuple[float, float] | None,
    expected_bytes: int | None,
) -> None:
    start, end = progress_span or (0.0, 1.0)
    copied = 0
    files = [p for p in src.rglob("*") if p.is_file() and p.name not in excludes]
    total = expected_bytes or sum(p.stat().st_size for p in files) or 1
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if path.is_file() and path.name in excludes:
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            try:
                copied += path.stat().st_size
            except OSError:
                pass
            frac = start + (end - start) * min(1.0, copied / float(total))
            emit(progress, f"复制 {rel}", frac)


def move_aside(path: Path, stamp: str, progress: ProgressFn | None = None) -> Path | None:
    """将已有路径挪到同级 OLD_<stamp>_<原名>，便于回退。不存在则返回 None。"""
    if not path.exists():
        return None
    parent = path.parent
    aside = parent / f"OLD_{stamp}_{path.name}"
    n = 1
    while aside.exists():
        aside = parent / f"OLD_{stamp}_{path.name}_{n}"
        n += 1
    emit(progress, f"挪走现有数据以回退: {path.name}")
    path.rename(aside)
    return aside
