"""最小自检：路径命名、体积格式、备份选项与跳过 .backup 的计划逻辑。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backup import BackupOptions, STATE_DB_BACKUP, build_plan  # noqa: E402
from src.backup_index import describe_backup  # noqa: E402
from src.paths import CursorPaths, new_backup_dir_name  # noqa: E402
from src.restore import validate_backup_dir  # noqa: E402
from src.sizing import format_bytes  # noqa: E402
from src.transfer import copy_tree  # noqa: E402


class SelfCheck(unittest.TestCase):
    def test_backup_dir_name(self) -> None:
        name = new_backup_dir_name(datetime(2026, 10, 27, 15, 30, 0))
        self.assertEqual(name, "cursor-sessions_20261027_153000")

    def test_format_bytes(self) -> None:
        self.assertEqual(format_bytes(500), "500 B")
        self.assertIn("KB", format_bytes(2048))

    def test_validate_backup_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            problems = validate_backup_dir(Path(tmp))
            self.assertTrue(any("globalStorage" in p for p in problems))

    def test_copy_tree_excludes_backup_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dst = Path(tmp) / "dst"
            gs = src / "globalStorage"
            gs.mkdir(parents=True)
            (gs / "state.vscdb").write_bytes(b"db")
            (gs / STATE_DB_BACKUP).write_bytes(b"bak")
            (gs / "other.txt").write_text("x", encoding="utf-8")
            copy_tree(gs, dst, exclude_files=[STATE_DB_BACKUP])
            self.assertTrue((dst / "state.vscdb").is_file())
            self.assertTrue((dst / "other.txt").is_file())
            self.assertFalse((dst / STATE_DB_BACKUP).exists())

    def test_build_plan_respects_skip_flag(self) -> None:
        # 用临时目录伪装路径，避免依赖本机真实体积扫描过久
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            user = base / "User"
            gs = user / "globalStorage"
            gs.mkdir(parents=True)
            (gs / "state.vscdb").write_bytes(b"a" * 100)
            (gs / STATE_DB_BACKUP).write_bytes(b"b" * 1000)
            ws = user / "workspaceStorage"
            ws.mkdir()
            projects = base / "projects"
            projects.mkdir()
            paths = CursorPaths(
                appdata_user=user,
                global_storage=gs,
                workspace_storage=ws,
                settings_json=user / "settings.json",
                keybindings_json=user / "keybindings.json",
                dot_cursor_projects=projects,
                rules_dir=base / "rules",
            )
            opts = BackupOptions(backup_root=base / "backup", include_state_vscdb_backup=False)
            plan = build_plan(paths, opts)
            gs_item = next(i for i in plan if i.key == "globalStorage")
            self.assertEqual(gs_item.estimated_bytes, 100)

    def test_describe_backup_reads_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cursor-sessions_20261027_181254"
            root.mkdir()
            gs = root / "globalStorage"
            gs.mkdir()
            (gs / "state.vscdb").write_bytes(b"db")
            (root / "backup-meta.json").write_text(
                '{"total_bytes": 1024, "cursor_version": "3.27.12", "items": ["globalStorage"]}',
                encoding="utf-8",
            )
            entry = describe_backup(root)
            self.assertEqual(entry.display_time, "2026-10-27 18:12:54")
            self.assertEqual(entry.cursor_version, "3.27.12")
            self.assertEqual(entry.size_bytes, 1024)
            self.assertTrue(entry.usable)

    def test_delete_clears_readonly(self) -> None:
        import os
        import stat

        from src.backup_index import delete_backup_dir

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cursor-sessions_20261027_120000"
            nested = root / "globalStorage"
            nested.mkdir(parents=True)
            fp = nested / "storage.json"
            fp.write_text("{}", encoding="utf-8")
            os.chmod(fp, stat.S_IREAD)
            delete_backup_dir(root)
            self.assertFalse(root.exists())

    def test_legacy_layout_validate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cursor-sessions_20261026_094955"
            gs = root / "AppData_Roaming_Cursor_User" / "globalStorage"
            gs.mkdir(parents=True)
            (gs / "storage.json").write_text("{}", encoding="utf-8")
            problems = validate_backup_dir(root)
            self.assertTrue(any("state.vscdb" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
