"""极简界面：一键备份 + 历史列表（一键恢复 / 删除）。"""

from __future__ import annotations

import os
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

from . import __version__
from .backup import BackupOptions, estimate_total, build_plan, run_backup
from .backup_index import delete_backup_dir, list_backup_entries
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


def _default_options(backup_root: Path) -> BackupOptions:
    # 固定合理默认：会话 + 编辑器配置；不带规则笔记；跳过巨型 .backup
    return BackupOptions(
        backup_root=backup_root,
        include_settings=True,
        include_keybindings=True,
        include_rules=False,
        include_state_vscdb_backup=False,
    )


def _default_restore(backup_dir: Path) -> RestoreOptions:
    return RestoreOptions(
        backup_dir=backup_dir,
        include_settings=True,
        include_keybindings=True,
        include_rules=False,
    )


class SessionBackupApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Cursor 会话备份  v{__version__}")
        self.geometry("760x560")
        self.minsize(700, 480)

        self.paths = CursorPaths.resolve()
        self.backup_root = DEFAULT_BACKUP_ROOT
        self._worker: threading.Thread | None = None
        self._path_by_iid: dict[str, Path] = {}

        self.status_var = tk.StringVar(value="")
        self.hint_var = tk.StringVar(value="")
        self.list_summary_var = tk.StringVar(value="历史对话备份：0 份")

        self._build()
        self.refresh_status()
        self.refresh_list()
        self.after(100, self._warm_estimate)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, textvariable=self.status_var).pack(anchor="w")
        ttk.Label(root, textvariable=self.hint_var, foreground="#555").pack(anchor="w", pady=(2, 12))

        bar = ttk.Frame(root)
        bar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(bar, text="一键备份全部对话", command=self.on_backup).pack(side=tk.LEFT)
        ttk.Button(bar, text="打开备份文件夹", command=self.open_backup_root).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="刷新", command=self._refresh_all).pack(side=tk.RIGHT)

        box = ttk.LabelFrame(root, text="历史对话备份", padding=10)
        box.pack(fill=tk.BOTH, expand=True)

        head = ttk.Frame(box)
        head.pack(fill=tk.X)
        ttk.Label(head, textvariable=self.list_summary_var).pack(side=tk.LEFT)
        ttk.Label(
            head,
            text="选中后可删除或一键恢复；恢复会先关闭 Cursor，并把当前数据挪到 OLD_*。",
            foreground="#666",
        ).pack(side=tk.RIGHT)

        cols = ("time", "size", "version")
        tree = ttk.Treeview(box, columns=cols, show="headings", height=12, selectmode="browse")
        tree.heading("time", text="备份时间")
        tree.heading("size", text="体积")
        tree.heading("version", text="Cursor 版本")
        tree.column("time", width=180, anchor="w")
        tree.column("size", width=100, anchor="center")
        tree.column("version", width=120, anchor="center")
        scroll = ttk.Scrollbar(box, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(8, 8))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(8, 8))
        self.tree = tree
        tree.bind("<Double-1>", lambda _e: self.on_restore())

        btns = ttk.Frame(box)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="一键恢复", command=self.on_restore).pack(side=tk.LEFT)
        ttk.Button(btns, text="删除", command=self.on_delete).pack(side=tk.LEFT, padx=8)

        self.log = tk.Text(root, height=8, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=False, pady=(10, 0))

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def _busy(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def _refresh_all(self) -> None:
        self.refresh_status()
        self.refresh_list()

    def refresh_status(self) -> None:
        install = find_cursor_install_dir()
        ver = read_cursor_version(install)
        if install:
            ver_s = f" · v{ver}" if ver else ""
            base = f"已安装{ver_s}  {install}"
        else:
            base = "未检测到安装目录（仍可备份/恢复本机会话数据）"
        if cursor_is_running():
            hits = list_cursor_processes()
            run = "运行中 " + "/".join(h.pid for h in hits[:3])
        else:
            run = "未运行"
        self.status_var.set(f"{base}    |    Cursor：{run}")
        self.hint_var.set(f"备份位置：{self.backup_root}")

    def refresh_list(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._path_by_iid.clear()
        entries = list_backup_entries(self.backup_root, compute_size_if_missing=False)
        self.list_summary_var.set(f"历史对话备份：{len(entries)} 份")
        for entry in entries:
            iid = self.tree.insert(
                "",
                tk.END,
                values=(entry.display_time, entry.size_label, entry.cursor_version or "-"),
            )
            self._path_by_iid[iid] = entry.path
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[0])
            self.tree.focus(kids[0])

    def _warm_estimate(self) -> None:
        def work() -> None:
            try:
                total = estimate_total(build_plan(self.paths, _default_options(self.backup_root)))
                self.after(0, lambda: self._log(f"预计备份体积约 {format_bytes(total)}（首次估算）"))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._log(f"体积估算跳过: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    def open_backup_root(self) -> None:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        os.startfile(self.backup_root)  # noqa: S606

    def _selected(self) -> Path | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self._path_by_iid.get(sel[0])

    def on_backup(self) -> None:
        if self._busy():
            return
        self.refresh_status()
        if not messagebox.askyesno(
            "一键备份",
            f"备份全部对话到：\n{self.backup_root}\\cursor-sessions_<时间戳>\n\n是否开始？",
        ):
            return
        self._log("—— 开始备份 ——")

        def progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._log(m))

        def work() -> None:
            try:
                result = run_backup(
                    self.paths, _default_options(self.backup_root), progress=progress
                )
                self.after(0, lambda: self._backup_done(result.backup_dir, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._backup_done(None, exc))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _backup_done(self, backup_dir: Path | None, error: BaseException | None) -> None:
        self.refresh_status()
        self.refresh_list()
        if error:
            self._log("备份失败:\n" + "".join(traceback.format_exception_only(type(error), error)))
            messagebox.showerror("备份失败", str(error))
            return
        assert backup_dir is not None
        self._log(f"备份成功: {backup_dir}")
        messagebox.showinfo("备份成功", f"已保存：\n{backup_dir}")

    def on_restore(self) -> None:
        if self._busy():
            return
        path = self._selected()
        if path is None:
            messagebox.showwarning("提示", "请先在列表里选中一份备份")
            return
        problems = validate_backup_dir(path)
        if problems:
            messagebox.showerror("备份无效", "\n".join(problems))
            return
        running = cursor_is_running()
        msg = (
            f"将恢复这份备份：\n{path.name}\n\n"
            "会先关闭 Cursor，把当前数据挪到 OLD_*，再写入备份，最后自动重新打开 Cursor。\n是否继续？"
        )
        if running:
            msg = "检测到 Cursor 正在运行。\n\n" + msg
        if not messagebox.askyesno("一键恢复", msg):
            return
        self._log("—— 开始恢复 ——")
        opts = _default_restore(path)

        def progress(m: str) -> None:
            self.after(0, lambda x=m: self._log(x))

        def work() -> None:
            try:
                if cursor_is_running():
                    progress("正在关闭 Cursor…")
                    left = close_cursor_processes()
                    if left:
                        detail = ", ".join(f"{h.name}:{h.pid}" for h in left)
                        raise RuntimeError(f"无法关闭 Cursor：{detail}")
                    progress("Cursor 已退出")
                result = run_restore(self.paths, opts, progress=progress)
                try:
                    launched = launch_cursor()
                    progress(f"已重新启动 Cursor：{launched}")
                except Exception as launch_exc:  # noqa: BLE001
                    progress(f"恢复成功，但自动启动失败：{launch_exc}")
                self.after(0, lambda: self._restore_done(result, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._restore_done(None, exc))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _restore_done(self, result, error: BaseException | None) -> None:
        self.refresh_status()
        if error:
            self._log("恢复失败:\n" + "".join(traceback.format_exception_only(type(error), error)))
            messagebox.showerror("恢复失败", str(error))
            return
        aside = "\n".join(result.aside_paths[:6]) if result.aside_paths else "(无)"
        messagebox.showinfo(
            "恢复成功",
            "已恢复："
            + ", ".join(result.restored)
            + "\n\n回退副本：\n"
            + aside
            + "\n\n请用原来的工程路径打开项目。",
        )

    def on_delete(self) -> None:
        if self._busy():
            return
        path = self._selected()
        if path is None:
            messagebox.showwarning("提示", "请先选中要删除的备份")
            return
        if not messagebox.askyesno("删除备份", f"确定删除？\n{path.name}\n\n删除后无法找回。"):
            return
        try:
            delete_backup_dir(path)
            self._log(f"已删除：{path}")
            self.refresh_list()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("删除失败", str(exc))


def main() -> None:
    app = SessionBackupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
