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


if __name__ == "__main__":
    unittest.main()
