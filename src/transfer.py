"""文件/目录拷贝（Windows 优先 robocopy）。"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

ProgressFn = Callable[[str], None]


def _log(progress: ProgressFn | None, message: str) -> None:
    if progress:
        progress(message)


def copy_file(src: Path, dst: Path, progress: ProgressFn | None = None) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    _log(progress, f"复制文件: {src} -> {dst}")
    shutil.copy2(src, dst)


def copy_tree(
    src: Path,
    dst: Path,
    *,
    exclude_files: list[str] | None = None,
    progress: ProgressFn | None = None,
) -> None:
    """复制目录树。exclude_files 为文件名列表（仅文件名，非路径）。"""
    if not src.exists():
        raise FileNotFoundError(f"源路径不存在: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    excludes = exclude_files or []

    if shutil.which("robocopy"):
        _robocopy(src, dst, excludes=excludes, progress=progress)
        return

    _log(progress, f"robocopy 不可用，改用 shutil 复制: {src}")
    _shutil_copytree(src, dst, excludes=set(excludes), progress=progress)


def _robocopy(
    src: Path,
    dst: Path,
    *,
    excludes: list[str],
    progress: ProgressFn | None,
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
    _log(progress, f"robocopy: {src} -> {dst}" + (f"（排除 {', '.join(excludes)}）" if excludes else ""))
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )
    # robocopy: 0–7 成功，>=8 失败
    if completed.returncode >= 8:
        detail = (completed.stdout or "") + (completed.stderr or "")
        raise RuntimeError(
            f"robocopy 失败 exit={completed.returncode}\n源: {src}\n目标: {dst}\n{detail.strip()}"
        )


def _shutil_copytree(
    src: Path,
    dst: Path,
    *,
    excludes: set[str],
    progress: ProgressFn | None,
) -> None:
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if path.is_file() and path.name in excludes:
            _log(progress, f"跳过: {rel}")
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def move_aside(path: Path, stamp: str, progress: ProgressFn | None = None) -> Path | None:
    """将已有路径挪到同级 OLD_<stamp>_<原名>，便于回退。不存在则返回 None。"""
    if not path.exists():
        return None
    parent = path.parent
    aside = parent / f"OLD_{stamp}_{path.name}"
    # 极少情况下重名，再加序号
    n = 1
    while aside.exists():
        aside = parent / f"OLD_{stamp}_{path.name}_{n}"
        n += 1
    _log(progress, f"挪走现有数据以回退: {path} -> {aside}")
    path.rename(aside)
    return aside
