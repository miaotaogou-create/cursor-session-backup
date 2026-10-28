"""从备份恢复 Cursor 会话相关数据。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .backup_layout import STATE_DB, backup_has_state_db, resolve_backup_layout
from .paths import CursorPaths
from .process_check import cursor_is_running, list_cursor_processes
from .sizing import dir_size_bytes
from .transfer import ProgressFn, copy_file, copy_tree, emit, move_aside


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
    layout = resolve_backup_layout(backup_dir)
    if layout.global_storage is None:
        problems.append("备份中缺少 globalStorage（含旧版 AppData_Roaming_Cursor_User/globalStorage）")
        return problems
    if not backup_has_state_db(layout):
        problems.append(
            f"备份不完整：找不到 {STATE_DB}。"
            "这份旧备份可能只拷了部分文件，无法恢复对话主库。"
        )
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

    layout = resolve_backup_layout(options.backup_dir)
    now = now or datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    result = RestoreResult()

    if layout.legacy:
        emit(progress, "检测到旧版备份目录结构，按兼容路径恢复", 0.02)

    pairs: list[tuple[str, Path | None, Path, bool]] = [
        ("globalStorage", layout.global_storage, paths.global_storage, False),
        ("workspaceStorage", layout.workspace_storage, paths.workspace_storage, False),
        ("dot-cursor-projects", layout.projects, paths.dot_cursor_projects, False),
    ]
    if options.include_settings:
        pairs.append(("settings.json", layout.settings_json, paths.settings_json, True))
    if options.include_keybindings:
        pairs.append(("keybindings.json", layout.keybindings_json, paths.keybindings_json, True))
    if options.include_rules:
        rules_dst = options.rules_dir or paths.rules_dir
        pairs.append(("ZYL_dot_cursor", layout.rules_dir, rules_dst, False))

    present = [(label, src, dst, is_file) for label, src, dst, is_file in pairs if src is not None and src.exists()]
    weights: list[int] = []
    for _label, src, _dst, is_file in present:
        assert src is not None
        if is_file:
            try:
                weights.append(max(src.stat().st_size, 1))
            except OSError:
                weights.append(1)
        else:
            weights.append(max(dir_size_bytes(src), 1024))
    total_w = float(sum(weights)) or 1.0
    cursor = 0.0
    emit(progress, "开始恢复…", 0.0)

    for (label, src, dst, is_file), weight in zip(present, weights, strict=True):
        assert src is not None
        # 挪走旧数据约占本段前 5%
        span_lo = cursor / total_w
        span_hi = (cursor + weight) / total_w
        aside_hi = span_lo + (span_hi - span_lo) * 0.05
        emit(progress, f"准备恢复 {label}", span_lo)
        aside = move_aside(dst, stamp, progress=progress)
        if aside is not None:
            result.aside_paths.append(str(aside))
        emit(progress, f"写入 {label}", aside_hi)
        if is_file:
            copy_file(src, dst, progress=progress, progress_span=(aside_hi, span_hi))
        else:
            copy_tree(
                src,
                dst,
                progress=progress,
                progress_span=(aside_hi, span_hi),
                expected_bytes=weight,
            )
        result.restored.append(label)
        emit(progress, f"已恢复: {label}", span_hi)
        cursor += weight

    for label, src, _dst, _is_file in pairs:
        if src is not None and src.exists():
            continue
        result.warnings.append(f"备份中无此项，跳过: {label}")
        emit(progress, result.warnings[-1])

    if "globalStorage" not in result.restored:
        raise RuntimeError("恢复失败：未能恢复 globalStorage")

    emit(progress, "恢复完成。请用备份时相同的工程路径打开项目。", 1.0)
    return result
