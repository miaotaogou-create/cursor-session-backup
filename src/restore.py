"""从备份恢复 Cursor 会话相关数据。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .paths import CursorPaths
from .process_check import cursor_is_running, list_cursor_processes
from .transfer import ProgressFn, copy_file, copy_tree, move_aside

STATE_DB = "state.vscdb"


@dataclass
class RestoreOptions:
    backup_dir: Path
    include_settings: bool = True
    include_keybindings: bool = True
    include_rules: bool = False
    rules_dir: Path | None = None


@dataclass
class RestoreResult:
    restored: list[str] = field(default_factory=list)
    aside_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_backup_dir(backup_dir: Path) -> list[str]:
    """返回问题列表；空列表表示通过基础校验。"""
    problems: list[str] = []
    if not backup_dir.is_dir():
        return [f"备份目录不存在: {backup_dir}"]
    gs = backup_dir / "globalStorage"
    state = gs / STATE_DB
    if not gs.is_dir():
        problems.append("备份中缺少 globalStorage/")
    elif not state.is_file():
        problems.append("备份中缺少 globalStorage/state.vscdb")
    # workspace / projects 缺失时警告级，由 run_restore 记 warning
    return problems


def run_restore(
    paths: CursorPaths,
    options: RestoreOptions,
    progress: ProgressFn | None = None,
    now: datetime | None = None,
) -> RestoreResult:
    if cursor_is_running():
        hits = list_cursor_processes()
        detail = ", ".join(f"{h.name}(pid={h.pid})" for h in hits) or "Cursor"
        raise RuntimeError(f"请先完全退出 Cursor 再恢复。仍在运行: {detail}")

    problems = validate_backup_dir(options.backup_dir)
    if problems:
        raise RuntimeError("备份校验失败:\n- " + "\n- ".join(problems))

    now = now or datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    result = RestoreResult()

    def log(msg: str) -> None:
        if progress:
            progress(msg)

    pairs: list[tuple[str, Path, Path, bool]] = [
        ("globalStorage", options.backup_dir / "globalStorage", paths.global_storage, False),
        ("workspaceStorage", options.backup_dir / "workspaceStorage", paths.workspace_storage, False),
        ("dot-cursor-projects", options.backup_dir / "dot-cursor-projects", paths.dot_cursor_projects, False),
    ]
    if options.include_settings:
        pairs.append(("settings.json", options.backup_dir / "settings.json", paths.settings_json, True))
    if options.include_keybindings:
        pairs.append(
            ("keybindings.json", options.backup_dir / "keybindings.json", paths.keybindings_json, True)
        )
    if options.include_rules:
        rules_dst = options.rules_dir or paths.rules_dir
        pairs.append(("ZYL_dot_cursor", options.backup_dir / "ZYL_dot_cursor", rules_dst, False))

    for label, src, dst, is_file in pairs:
        if not src.exists():
            result.warnings.append(f"备份中无此项，跳过: {label}")
            log(result.warnings[-1])
            continue
        aside = move_aside(dst, stamp, progress=progress)
        if aside is not None:
            result.aside_paths.append(str(aside))
        if is_file:
            copy_file(src, dst, progress=progress)
        else:
            copy_tree(src, dst, progress=progress)
        result.restored.append(label)
        log(f"已恢复: {label} -> {dst}")

    if "globalStorage" not in result.restored:
        raise RuntimeError("恢复失败：未能恢复 globalStorage")

    log("恢复完成。请重新打开 Cursor，并用备份时相同的工程路径打开项目。")
    return result
