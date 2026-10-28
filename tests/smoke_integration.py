"""端到端冒烟：在临时目录上走备份 → 校验 → 恢复 → 删除（不碰真实 Cursor 数据）。"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backup import BackupOptions, run_backup
from src.backup_index import delete_backup_dir, describe_backup, list_backup_entries
from src.paths import CursorPaths, list_backup_dirs
from src.restore import run_restore, validate_backup_dir
from src.sizing import format_bytes


class _Prog:
    def __init__(self, name: str) -> None:
        self.name = name
        self.last = -1.0
        self.updates = 0

    def __call__(self, message: str, fraction: float | None = None) -> None:
        self.updates += 1
        if fraction is None:
            print(f"  [{self.name}] {message}")
            return
        if fraction - self.last >= 0.15 or fraction in (0.0, 1.0):
            self.last = fraction
            print(f"  [{self.name}] {int(fraction * 100):3d}%  {message}")


def _write_fake_cursor(home: Path) -> CursorPaths:
    user = home / "AppData" / "Roaming" / "Cursor" / "User"
    gs = user / "globalStorage"
    ws = user / "workspaceStorage" / "ws1"
    projects = home / ".cursor" / "projects" / "demo" / "agent-transcripts"
    gs.mkdir(parents=True)
    ws.mkdir(parents=True)
    projects.mkdir(parents=True)

    # ~8MB，足够让进度回调多跳几档，又不至于太慢
    (gs / "state.vscdb").write_bytes(os.urandom(6 * 1024 * 1024))
    (gs / "state.vscdb.backup").write_bytes(os.urandom(4 * 1024 * 1024))
    (gs / "storage.json").write_text('{"ok":true}', encoding="utf-8")
    (ws / "state.vscdb").write_bytes(b"workspace-db")
    (projects / "a.jsonl").write_text('{"role":"user"}\n', encoding="utf-8")
    (user / "settings.json").write_text('{"editor.fontSize":14}', encoding="utf-8")
    (user / "keybindings.json").write_text("[]", encoding="utf-8")

    return CursorPaths(
        appdata_user=user,
        global_storage=gs,
        workspace_storage=user / "workspaceStorage",
        settings_json=user / "settings.json",
        keybindings_json=user / "keybindings.json",
        dot_cursor_projects=home / ".cursor" / "projects",
        rules_dir=home / "rules",
    )


def main() -> int:
    print("=== smoke_integration ===")
    with tempfile.TemporaryDirectory(prefix="csb_smoke_") as tmp:
        tmp_p = Path(tmp)
        src_home = tmp_p / "src_home"
        dst_home = tmp_p / "dst_home"
        backup_root = tmp_p / "backups"
        backup_root.mkdir()

        src = _write_fake_cursor(src_home)
        print("[1] 假数据已准备")

        # —— 备份 ——
        print("[2] 备份…")
        opts = BackupOptions(
            backup_root=backup_root,
            include_settings=True,
            include_keybindings=True,
            include_rules=False,
            include_state_vscdb_backup=False,
        )
        result = run_backup(src, opts, progress=_Prog("backup"))
        backup_dir = result.backup_dir
        print(f"    备份目录: {backup_dir}")
        print(f"    体积: {format_bytes(result.total_bytes)}  项: {result.items}")

        assert "globalStorage" in result.items
        assert (backup_dir / "globalStorage" / "state.vscdb").is_file()
        assert not (backup_dir / "globalStorage" / "state.vscdb.backup").exists(), "不应包含 .backup"
        assert (backup_dir / "manifest.json").is_file()
        print("[2] OK 备份校验通过（已跳过 state.vscdb.backup）")

        # —— 列表 / 元数据 ——
        entries = list_backup_entries(backup_root, compute_size_if_missing=True)
        assert len(entries) == 1
        assert entries[0].usable is True
        assert entries[0].size_bytes and entries[0].size_bytes > 0
        print(f"[3] OK 列表: {entries[0].display_time}  {entries[0].size_label}")

        problems = validate_backup_dir(backup_dir)
        assert not problems, problems
        print("[4] OK validate_backup_dir")

        # —— 恢复到另一套假路径 ——
        print("[5] 恢复…")
        dst = _write_fake_cursor(dst_home)
        # 先弄脏一点，确认会被 OLD_* 挪走再覆盖
        (dst.global_storage / "state.vscdb").write_bytes(b"OLD-CONTENT")
        from src.restore import RestoreOptions

        # 冒烟用假路径，不真正动 Cursor；本机若正开着 Cursor，跳过进程门禁
        from unittest.mock import patch

        with patch("src.restore.cursor_is_running", return_value=False):
            restored = run_restore(
                dst,
                RestoreOptions(backup_dir=backup_dir),
                progress=_Prog("restore"),
            )
        assert "globalStorage" in restored.restored
        data = (dst.global_storage / "state.vscdb").read_bytes()
        assert data == (src.global_storage / "state.vscdb").read_bytes()
        assert any("OLD_" in p for p in restored.aside_paths)
        print(f"[5] OK 恢复成功，OLD 回退 {len(restored.aside_paths)} 处")

        # —— 只读文件删除 ——
        print("[6] 删除（含只读）…")
        ro = backup_dir / "globalStorage" / "storage.json"
        if ro.is_file():
            os.chmod(ro, stat.S_IREAD)
        delete_backup_dir(backup_dir, progress=_Prog("delete"))
        assert not backup_dir.exists()
        assert list_backup_dirs(backup_root) == []
        print("[6] OK 删除完成")

        # —— 不完整备份识别 ——
        print("[7] 不完整旧备份识别…")
        bad = backup_root / "cursor-sessions_20260101_000000"
        legacy_gs = bad / "AppData_Roaming_Cursor_User" / "globalStorage"
        legacy_gs.mkdir(parents=True)
        fp = legacy_gs / "storage.json"
        fp.write_text("{}", encoding="utf-8")
        os.chmod(fp, stat.S_IREAD)
        entry = describe_backup(bad)
        assert entry.usable is False
        assert entry.note and "state.vscdb" in entry.note
        problems = validate_backup_dir(bad)
        assert any("state.vscdb" in p for p in problems)
        delete_backup_dir(bad, progress=_Prog("delete-bad"))
        assert not bad.exists()
        print("[7] OK 不完整备份可识别且可删除")

    print("=== 全部冒烟通过 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
