"""供 pywebview 调用的桌面 API（备份 / 恢复 / 删除 / 状态）。"""

from __future__ import annotations

import os
import queue
import shutil
import threading
import time
import traceback
import webbrowser
from pathlib import Path
from typing import Any

from . import __version__
from .backup import BackupOptions, run_backup
from .backup_index import BackupEntry, delete_backup_dir, list_backup_entries
from .cursor_install import find_cursor_install_dir, read_cursor_version
from .paths import DEFAULT_BACKUP_ROOT, CursorPaths
from .process_check import (
    close_cursor_processes,
    cursor_is_running,
    launch_cursor,
    list_cursor_processes,
)
from .restore import RestoreOptions, run_restore, validate_backup_dir
from .sizing import format_bytes


def _default_backup_opts(backup_root: Path) -> BackupOptions:
    return BackupOptions(
        backup_root=backup_root,
        include_settings=True,
        include_keybindings=True,
        include_rules=False,
        include_state_vscdb_backup=False,
    )


def _default_restore_opts(backup_dir: Path) -> RestoreOptions:
    return RestoreOptions(
        backup_dir=backup_dir,
        include_settings=True,
        include_keybindings=True,
        include_rules=False,
    )


def _free_space_label(path: Path) -> str:
    try:
        usage = shutil.disk_usage(path if path.exists() else path.anchor or path)
        return format_bytes(usage.free)
    except OSError:
        return "未知"


def _entry_to_dict(entry: BackupEntry) -> dict[str, Any]:
    return {
        "id": str(entry.path),
        "path": str(entry.path),
        "timestamp": entry.display_time,
        "size": entry.size_label,
        "cursorVersion": entry.cursor_version or "未知",
        "chatCount": entry.item_count,
        "note": entry.note or ("完整会话快照" if entry.usable else None),
        "usable": entry.usable,
    }


class DesktopApi:
    """js_api 对象：方法名会暴露给 window.pywebview.api。"""

    def __init__(self) -> None:
        self.paths = CursorPaths.resolve()
        self.backup_root = DEFAULT_BACKUP_ROOT
        self._events: queue.Queue[dict[str, Any]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._busy = False
        self._op_started_at: float | None = None
        self._window = None  # 由启动器注入
        # pywebview 的 window.maximized 创建后不随窗态更新，需自管
        self._maximized = False

    def bind_window(self, window) -> None:
        self._window = window
        self._maximized = bool(getattr(window, "maximized", False))

        def _on_maximized() -> None:
            self._maximized = True
            self._emit("windowMaximized", maximized=True)

        def _on_restored() -> None:
            self._maximized = False
            self._emit("windowMaximized", maximized=False)

        try:
            window.events.maximized += _on_maximized
            window.events.restored += _on_restored
        except Exception:
            pass

    def _emit(self, kind: str, **payload: Any) -> None:
        self._events.put({"kind": kind, **payload})

    def _busy_guard(self) -> dict[str, Any] | None:
        if self._busy:
            return {"ok": False, "error": "已有任务在进行中"}
        return None

    # —— 只读 ——
    def get_version(self) -> str:
        return __version__

    def get_snapshot(self) -> dict[str, Any]:
        install = find_cursor_install_dir()
        procs = list_cursor_processes()
        backups = [_entry_to_dict(e) for e in list_backup_entries(self.backup_root)]
        return {
            "appVersion": __version__,
            "systemInfo": {
                "cursorVersion": read_cursor_version() or "未知",
                "installPath": str(install) if install else "(未找到 Cursor)",
                "isRunning": bool(procs),
                "processCount": len(procs),
                "backupDirectory": str(self.backup_root),
                "diskFreeSpace": _free_space_label(self.backup_root),
            },
            "backups": backups,
            "busy": self._busy,
        }

    def poll_events(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        while True:
            try:
                out.append(self._events.get_nowait())
            except queue.Empty:
                break
        return out

    # —— 窗控 ——
    def window_minimize(self) -> None:
        if self._window is not None:
            self._window.minimize()

    def window_toggle_maximize(self) -> dict[str, Any]:
        if self._window is None:
            return {"ok": False, "maximized": False}
        if self._maximized:
            self._window.restore()
            self._maximized = False
        else:
            self._window.maximize()
            self._maximized = True
        return {"ok": True, "maximized": self._maximized}

    def window_is_maximized(self) -> bool:
        return self._maximized

    def window_close(self) -> None:
        if self._window is not None:
            self._window.destroy()

    def window_begin_drag(self) -> None:
        """用 Win32 HTCAPTION 原生拖窗，避免 pywebview JS 拖拽在缩放下光标错位抖动。"""
        if self._window is None:
            return
        try:
            import ctypes

            from System import Func, Type
            from webview.platforms.winforms import BrowserView

            form = BrowserView.instances.get(self._window.uid)
            if form is None:
                return

            def _drag() -> None:
                handle = form.Handle
                hwnd = int(handle.ToInt64()) if hasattr(handle, "ToInt64") else int(handle.ToInt32())
                ctypes.windll.user32.ReleaseCapture()
                # WM_NCLBUTTONDOWN + HTCAPTION：系统原生拖动，光标不跳
                ctypes.windll.user32.SendMessageW(hwnd, 0x00A1, 2, 0)

            form.Invoke(Func[Type](_drag))
        except Exception:
            pass

    # —— 路径 / 文件夹 ——
    def open_backup_folder(self) -> dict[str, Any]:
        path = self.backup_root
        try:
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(path)  # type: ignore[attr-defined]
            return {"ok": True}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}

    def pick_backup_directory(self) -> dict[str, Any]:
        import webview

        if self._window is None:
            return {"ok": False, "error": "窗口未就绪"}
        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=str(self.backup_root) if self.backup_root.exists() else None,
        )
        if not result:
            return {"ok": False, "cancelled": True}
        chosen = Path(result[0])
        self.backup_root = chosen
        self._emit("log", level="info", message=f"备份目录已修改为: {chosen}")
        return {"ok": True, "path": str(chosen), "snapshot": self.get_snapshot()}

    def set_backup_directory(self, path: str) -> dict[str, Any]:
        text = (path or "").strip()
        if not text:
            return {"ok": False, "error": "路径不能为空"}
        self.backup_root = Path(text)
        try:
            self.backup_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        self._emit("log", level="info", message=f"备份目录已修改为: {self.backup_root}")
        return {"ok": True, "snapshot": self.get_snapshot()}

    def open_external(self, url: str) -> None:
        webbrowser.open(url)

    # —— 任务 ——
    def start_backup(self) -> dict[str, Any]:
        blocked = self._busy_guard()
        if blocked:
            return blocked
        self._busy = True
        self._op_started_at = time.monotonic()
        self._emit("op", state="backing-up", percent=0, message="正在初始化备份...", op="backup")
        self._emit("log", level="info", message="开始创建完整会话备份...")

        def work() -> None:
            try:

                def progress(message: str, fraction: float | None = None) -> None:
                    pct = int(round((fraction or 0) * 100)) if fraction is not None else None
                    payload: dict[str, Any] = {
                        "kind": "op",
                        "state": "backing-up",
                        "message": message,
                        "op": "backup",
                    }
                    if pct is not None:
                        payload["percent"] = pct
                    self._events.put(payload)
                    if message:
                        self._emit("log", level="info", message=message)

                result = run_backup(
                    self.paths,
                    _default_backup_opts(self.backup_root),
                    progress=progress,
                )
                elapsed = time.monotonic() - (self._op_started_at or time.monotonic())
                self._emit(
                    "op",
                    state="completed",
                    percent=100,
                    message="备份完成",
                    op="backup",
                    elapsed=f"{elapsed:.1f}s",
                )
                self._emit(
                    "log",
                    level="success",
                    message=f"会话备份创建成功：{result.backup_dir}",
                )
                self._emit("toast", message="一键备份已成功完成！")
                self._emit("snapshot", snapshot=self.get_snapshot())
            except Exception as exc:  # noqa: BLE001
                self._emit("op", state="error", message="备份失败", op="backup")
                self._emit(
                    "log",
                    level="error",
                    message="备份失败: "
                    + "".join(traceback.format_exception_only(type(exc), exc)).strip(),
                )
                self._emit("toast", message=f"备份失败：{exc}")
            finally:
                self._busy = False
                self._emit("snapshot", snapshot=self.get_snapshot())

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()
        return {"ok": True}

    def start_restore(self, backup_path: str) -> dict[str, Any]:
        blocked = self._busy_guard()
        if blocked:
            return blocked
        path = Path(backup_path)
        problems = validate_backup_dir(path)
        if problems:
            return {"ok": False, "error": "\n".join(problems)}

        self._busy = True
        self._op_started_at = time.monotonic()
        self._emit(
            "op",
            state="restoring",
            percent=0,
            message="正在准备恢复...",
            op="restore",
        )
        self._emit("log", level="info", message=f"开始从备份恢复: {path.name}")

        def work() -> None:
            try:

                def progress(message: str, fraction: float | None = None) -> None:
                    pct = int(round((fraction or 0) * 100)) if fraction is not None else None
                    payload: dict[str, Any] = {
                        "kind": "op",
                        "state": "restoring",
                        "message": message,
                        "op": "restore",
                    }
                    if pct is not None:
                        payload["percent"] = pct
                    self._events.put(payload)
                    level = "info"
                    low = message.lower()
                    if "跳过" in message:
                        level = "skip"
                    elif "失败" in message or "error" in low:
                        level = "error"
                    elif "完成" in message or "成功" in message or "已恢复" in message:
                        level = "success"
                    self._emit("log", level=level, message=message)

                if cursor_is_running():
                    progress("正在关闭 Cursor…", 0.01)
                    left = close_cursor_processes()
                    if left:
                        detail = ", ".join(f"{h.name}:{h.pid}" for h in left)
                        raise RuntimeError(f"无法关闭 Cursor：{detail}")
                    progress("Cursor 已退出", 0.05)

                result = run_restore(
                    self.paths, _default_restore_opts(path), progress=progress
                )
                try:
                    launched = launch_cursor()
                    progress(f"已重新启动 Cursor：{launched}", 1.0)
                except Exception as launch_exc:  # noqa: BLE001
                    progress(f"恢复成功，但自动启动失败：{launch_exc}", 1.0)

                elapsed = time.monotonic() - (self._op_started_at or time.monotonic())
                self._emit(
                    "op",
                    state="completed",
                    percent=100,
                    message="恢复完成",
                    op="restore",
                    elapsed=f"{elapsed:.1f}s",
                )
                self._emit(
                    "log",
                    level="success",
                    message="恢复完成。请用备份时相同的工程路径打开项目。 已恢复: "
                    + ", ".join(result.restored),
                )
                self._emit("toast", message="历史会话已成功恢复！")
            except Exception as exc:  # noqa: BLE001
                self._emit("op", state="error", message="恢复失败", op="restore")
                self._emit(
                    "log",
                    level="error",
                    message="恢复失败: "
                    + "".join(traceback.format_exception_only(type(exc), exc)).strip(),
                )
                self._emit("toast", message=f"恢复失败：{exc}")
            finally:
                self._busy = False
                self._emit("snapshot", snapshot=self.get_snapshot())

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()
        return {"ok": True}

    def delete_backup(self, backup_path: str) -> dict[str, Any]:
        blocked = self._busy_guard()
        if blocked:
            return blocked
        path = Path(backup_path)
        self._busy = True
        self._op_started_at = time.monotonic()
        self._emit("op", state="deleting", percent=0, message="正在删除备份...", op="delete")
        self._emit("log", level="info", message=f"—— 开始删除 {path.name} ——")

        def work() -> None:
            try:

                def progress(message: str, fraction: float | None = None) -> None:
                    pct = int(round((fraction or 0) * 100)) if fraction is not None else None
                    payload: dict[str, Any] = {
                        "kind": "op",
                        "state": "deleting",
                        "message": message,
                        "op": "delete",
                    }
                    if pct is not None:
                        payload["percent"] = pct
                    self._events.put(payload)

                delete_backup_dir(path, progress=progress)
                elapsed = time.monotonic() - (self._op_started_at or time.monotonic())
                self._emit(
                    "op",
                    state="completed",
                    percent=100,
                    message=f"已删除：{path.name}",
                    op="delete",
                    elapsed=f"{elapsed:.1f}s",
                )
                self._emit("log", level="info", message=f"已删除备份记录: {path.name}")
                self._emit("toast", message="备份已从列表中删除")
            except Exception as exc:  # noqa: BLE001
                self._emit("op", state="error", message="删除失败", op="delete")
                self._emit("log", level="error", message=f"删除失败: {exc}")
                self._emit("toast", message=f"删除失败：{exc}")
            finally:
                self._busy = False
                self._emit("snapshot", snapshot=self.get_snapshot())

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()
        return {"ok": True}
