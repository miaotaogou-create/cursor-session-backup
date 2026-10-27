"""备份 Cursor 会话相关数据。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .paths import CursorPaths, new_backup_dir_name
from .sizing import dir_size_bytes, format_bytes
from .transfer import ProgressFn, copy_file, copy_tree

STATE_DB = "state.vscdb"
STATE_DB_BACKUP = "state.vscdb.backup"


@dataclass
class BackupOptions:
    backup_root: Path
    include_settings: bool = True
    include_keybindings: bool = True
    include_rules: bool = False
    include_state_vscdb_backup: bool = False
    rules_dir: Path | None = None


@dataclass
class BackupPlanItem:
    key: str
    label: str
    src: Path
    dest_name: str
    is_file: bool
    required: bool
    estimated_bytes: int = 0


@dataclass
class BackupResult:
    backup_dir: Path
    items: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_bytes: int = 0


def build_plan(paths: CursorPaths, options: BackupOptions) -> list[BackupPlanItem]:
    skip = frozenset() if options.include_state_vscdb_backup else frozenset({STATE_DB_BACKUP})
    items: list[BackupPlanItem] = [
        BackupPlanItem(
            key="globalStorage",
            label="globalStorage（含 state.vscdb）",
            src=paths.global_storage,
            dest_name="globalStorage",
            is_file=False,
            required=True,
            estimated_bytes=dir_size_bytes(paths.global_storage, skip_names=skip),
        ),
        BackupPlanItem(
            key="workspaceStorage",
            label="workspaceStorage",
            src=paths.workspace_storage,
            dest_name="workspaceStorage",
            is_file=False,
            required=True,
            estimated_bytes=dir_size_bytes(paths.workspace_storage),
        ),
        BackupPlanItem(
            key="projects",
            label=".cursor/projects（Agent transcripts）",
            src=paths.dot_cursor_projects,
            dest_name="dot-cursor-projects",
            is_file=False,
            required=True,
            estimated_bytes=dir_size_bytes(paths.dot_cursor_projects),
        ),
    ]
    if options.include_settings:
        items.append(
            BackupPlanItem(
                key="settings",
                label="settings.json",
                src=paths.settings_json,
                dest_name="settings.json",
                is_file=True,
                required=False,
                estimated_bytes=dir_size_bytes(paths.settings_json),
            )
        )
    if options.include_keybindings:
        items.append(
            BackupPlanItem(
                key="keybindings",
                label="keybindings.json",
                src=paths.keybindings_json,
                dest_name="keybindings.json",
                is_file=True,
                required=False,
                estimated_bytes=dir_size_bytes(paths.keybindings_json),
            )
        )
    if options.include_rules:
        rules = options.rules_dir or paths.rules_dir
        items.append(
            BackupPlanItem(
                key="rules",
                label=f"规则笔记（{rules}）",
                src=rules,
                dest_name="ZYL_dot_cursor",
                is_file=False,
                required=False,
                estimated_bytes=dir_size_bytes(rules),
            )
        )
    return items


def estimate_total(plan: list[BackupPlanItem]) -> int:
    return sum(i.estimated_bytes for i in plan)


def run_backup(
    paths: CursorPaths,
    options: BackupOptions,
    progress: ProgressFn | None = None,
    now: datetime | None = None,
) -> BackupResult:
    now = now or datetime.now()
    plan = build_plan(paths, options)
    if not any(i.src.exists() for i in plan if i.required):
        raise RuntimeError("未找到任何必需的 Cursor 数据目录，请确认已安装并至少启动过一次 Cursor")

    # 关键：state.vscdb 必须在（若 globalStorage 存在）
    state_db = paths.global_storage / STATE_DB
    if paths.global_storage.exists() and not state_db.exists():
        raise RuntimeError(f"缺少关键文件: {state_db}")

    backup_root = options.backup_root
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / new_backup_dir_name(now)
    if backup_dir.exists():
        raise RuntimeError(f"备份目录已存在: {backup_dir}")
    backup_dir.mkdir(parents=True, exist_ok=False)

    def log(msg: str) -> None:
        if progress:
            progress(msg)

    result = BackupResult(backup_dir=backup_dir)
    exclude_gs = [] if options.include_state_vscdb_backup else [STATE_DB_BACKUP]

    for item in plan:
        if not item.src.exists():
            msg = f"跳过不存在: {item.src}"
            if item.required:
                result.warnings.append(f"必需项缺失: {item.src}")
            else:
                result.warnings.append(msg)
            log(msg)
            continue
        dest = backup_dir / item.dest_name
        try:
            if item.is_file:
                copy_file(item.src, dest, progress=progress)
            else:
                excludes = exclude_gs if item.key == "globalStorage" else None
                copy_tree(item.src, dest, exclude_files=excludes, progress=progress)
            result.items.append(item.dest_name)
            log(f"完成: {item.label}")
        except OSError as exc:
            # 文件被锁等
            raise RuntimeError(f"复制失败（可能被 Cursor 占用）: {item.src}\n{exc}") from exc

    # 再确认备份里有 state.vscdb
    backed_state = backup_dir / "globalStorage" / STATE_DB
    if "globalStorage" in result.items and not backed_state.exists():
        raise RuntimeError("备份完成校验失败：globalStorage 中缺少 state.vscdb")

    if not options.include_state_vscdb_backup:
        bad = backup_dir / "globalStorage" / STATE_DB_BACKUP
        if bad.exists():
            raise RuntimeError("备份校验失败：不应包含 state.vscdb.backup，但文件已出现")

    result.total_bytes = dir_size_bytes(backup_dir)
    _write_readme(backup_dir, paths, options, result, now)
    _write_manifest(backup_dir, paths, options, result, now)
    log(f"备份完成: {backup_dir}（{format_bytes(result.total_bytes)}）")
    return result


def _write_readme(
    backup_dir: Path,
    paths: CursorPaths,
    options: BackupOptions,
    result: BackupResult,
    now: datetime,
) -> None:
    lines = [
        "Cursor 会话备份",
        "================",
        f"备份时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"备份位置: {backup_dir}",
        f"体积: {format_bytes(result.total_bytes)}",
        "",
        "已包含",
        "------",
    ]
    for name in result.items:
        lines.append(f"- {name}")
    if result.warnings:
        lines.append("")
        lines.append("警告")
        lines.append("----")
        for w in result.warnings:
            lines.append(f"- {w}")
    lines.extend(
        [
            "",
            "源路径对照",
            "----------",
            f"globalStorage -> {paths.global_storage}",
            f"workspaceStorage -> {paths.workspace_storage}",
            f"dot-cursor-projects -> {paths.dot_cursor_projects}",
            f"settings.json -> {paths.settings_json}",
            f"keybindings.json -> {paths.keybindings_json}",
            f"ZYL_dot_cursor -> {options.rules_dir or paths.rules_dir}",
            "",
            f"是否包含 state.vscdb.backup: {'是' if options.include_state_vscdb_backup else '否（默认跳过）'}",
            "",
            "恢复提示",
            "--------",
            "1. 完全退出 Cursor（任务管理器确认无 Cursor 进程）",
            "2. 用本工具「恢复」选中本目录，或按同目录 RESTORE 说明手动覆盖",
            "3. 重新打开 Cursor，并用备份时相同的工程文件夹路径打开项目",
            "",
        ]
    )
    (backup_dir / "README-恢复说明.txt").write_text("\n".join(lines), encoding="utf-8")


def _write_manifest(
    backup_dir: Path,
    paths: CursorPaths,
    options: BackupOptions,
    result: BackupResult,
    now: datetime,
) -> None:
    from .cursor_install import read_cursor_version

    cursor_version = read_cursor_version()
    data = {
        "schema": 1,
        "tool": "cursor-session-backup",
        "created_at": now.isoformat(timespec="seconds"),
        "backup_dir": str(backup_dir),
        "items": result.items,
        "warnings": result.warnings,
        "total_bytes": result.total_bytes,
        "cursor_version": cursor_version,
        "options": {
            "include_settings": options.include_settings,
            "include_keybindings": options.include_keybindings,
            "include_rules": options.include_rules,
            "include_state_vscdb_backup": options.include_state_vscdb_backup,
        },
        "sources": {
            "globalStorage": str(paths.global_storage),
            "workspaceStorage": str(paths.workspace_storage),
            "dot_cursor_projects": str(paths.dot_cursor_projects),
            "settings_json": str(paths.settings_json),
            "keybindings_json": str(paths.keybindings_json),
            "rules_dir": str(options.rules_dir or paths.rules_dir),
        },
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (backup_dir / "backup-meta.json").write_text(
        json.dumps(
            {
                "created_at": now.isoformat(timespec="seconds"),
                "total_bytes": result.total_bytes,
                "cursor_version": cursor_version,
                "items": result.items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
