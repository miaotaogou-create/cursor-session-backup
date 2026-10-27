"""图形界面：一键备份、历史列表选择恢复。"""

from __future__ import annotations

import os
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .backup import BackupOptions, build_plan, estimate_total, run_backup
from .backup_index import delete_backup_dir, list_backup_entries
from .cursor_install import find_cursor_exe, find_cursor_install_dir, read_cursor_version
from .paths import DEFAULT_BACKUP_ROOT, DEFAULT_RULES_DIR, CursorPaths
from .process_check import (
    close_cursor_processes,
    cursor_is_running,
    launch_cursor,
    list_cursor_processes,
)
from .restore import RestoreOptions, run_restore, validate_backup_dir
from .sizing import format_bytes


class SessionBackupApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Cursor 会话备份助手  v{__version__}")
        self.geometry("900x680")
        self.minsize(820, 620)

        self.paths = CursorPaths.resolve()
        self._worker: threading.Thread | None = None
        self._path_by_iid: dict[str, Path] = {}

        self.backup_root_var = tk.StringVar(value=str(DEFAULT_BACKUP_ROOT))
        self.include_settings_var = tk.BooleanVar(value=True)
        self.include_keybindings_var = tk.BooleanVar(value=True)
        self.include_rules_var = tk.BooleanVar(value=False)
        self.include_vscdb_backup_var = tk.BooleanVar(value=False)
        self.auto_relaunch_var = tk.BooleanVar(value=True)
        self.status_install_var = tk.StringVar(value="")
        self.status_process_var = tk.StringVar(value="")
        self.estimate_var = tk.StringVar(value="尚未估算")
        self.list_summary_var = tk.StringVar(value="历史备份：0 份")

        self._build()
        self.refresh_status()
        self.refresh_backup_list()
        self.after(200, self.refresh_estimate)

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        # 顶部状态
        top = ttk.LabelFrame(root, text="Cursor 状态", padding=8)
        top.grid(row=0, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Label(top, textvariable=self.status_install_var).grid(row=0, column=0, sticky="w")
        ttk.Label(top, textvariable=self.status_process_var).grid(row=1, column=0, sticky="w", pady=(4, 0))
        top_btns = ttk.Frame(top)
        top_btns.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(top_btns, text="刷新状态", command=self.refresh_status).pack(side=tk.LEFT, padx=4)
        ttk.Button(top_btns, text="启动 Cursor", command=self.on_launch_cursor).pack(side=tk.LEFT, padx=4)
        top.columnconfigure(0, weight=1)

        # 备份根目录
        ttk.Label(root, text="备份根目录").grid(row=1, column=0, sticky="w")
        ttk.Entry(root, textvariable=self.backup_root_var).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(root, text="浏览…", command=self.pick_backup_root).grid(row=1, column=2, **pad)

        # 主操作
        actions = ttk.LabelFrame(root, text="操作面板", padding=10)
        actions.grid(row=2, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Button(actions, text="一键备份全部对话", command=self.on_backup).pack(side=tk.LEFT, padx=4)
        ttk.Label(actions, textvariable=self.estimate_var).pack(side=tk.LEFT, padx=12)
        ttk.Button(actions, text="重新估算体积", command=self.refresh_estimate).pack(side=tk.LEFT)
        ttk.Button(actions, text="打开备份目录", command=self.open_backup_root).pack(side=tk.RIGHT)

        # 高级选项
        opts = ttk.LabelFrame(root, text="高级选项（一般不用改）", padding=8)
        opts.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Checkbutton(opts, text="settings.json", variable=self.include_settings_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Checkbutton(opts, text="keybindings.json", variable=self.include_keybindings_var).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Checkbutton(
            opts,
            text=f"规则笔记 {DEFAULT_RULES_DIR}",
            variable=self.include_rules_var,
            command=self.refresh_estimate,
        ).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(
            opts,
            text="包含 state.vscdb.backup（体积约再翻倍）",
            variable=self.include_vscdb_backup_var,
            command=self.refresh_estimate,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(
            opts,
            text="恢复成功后自动重新启动 Cursor",
            variable=self.auto_relaunch_var,
        ).grid(row=1, column=2, sticky="w", pady=(4, 0))

        # 历史备份列表
        hist = ttk.LabelFrame(root, text="历史对话备份（点选后一键恢复）", padding=8)
        hist.grid(row=4, column=0, columnspan=3, sticky="nsew", **pad)
        head = ttk.Frame(hist)
        head.pack(fill=tk.X)
        ttk.Label(head, textvariable=self.list_summary_var).pack(side=tk.LEFT)
        ttk.Button(head, text="刷新列表", command=self.refresh_backup_list).pack(side=tk.RIGHT)

        tip = (
            "恢复前会尝试关闭 Cursor，并把当前数据挪到 OLD_* 以便回退；"
            "恢复后请尽量用备份时相同的工程路径打开项目。"
        )
        ttk.Label(hist, text=tip, foreground="#555", wraplength=820).pack(anchor="w", pady=(4, 6))

        cols = ("time", "size", "version", "path")
        tree = ttk.Treeview(hist, columns=cols, show="headings", height=8, selectmode="browse")
        tree.heading("time", text="备份时间")
        tree.heading("size", text="体积")
        tree.heading("version", text="Cursor 版本")
        tree.heading("path", text="目录")
        tree.column("time", width=150, anchor="w")
        tree.column("size", width=90, anchor="center")
        tree.column("version", width=100, anchor="center")
        tree.column("path", width=480, anchor="w")
        scroll = ttk.Scrollbar(hist, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree = tree
        tree.bind("<Double-1>", lambda _e: self.on_restore_selected())

        row_btns = ttk.Frame(hist)
        row_btns.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(row_btns, text="一键恢复选中备份", command=self.on_restore_selected).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(row_btns, text="删除选中备份", command=self.on_delete_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(row_btns, text="在资源管理器中打开", command=self.on_open_selected).pack(
            side=tk.LEFT, padx=4
        )

        # 日志
        log_frame = ttk.LabelFrame(root, text="日志", padding=8)
        log_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", **pad)
        self.log = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.configure(yscrollcommand=log_scroll.set)

        root.columnconfigure(1, weight=1)
        root.rowconfigure(4, weight=2)
        root.rowconfigure(5, weight=1)

    def _append_log(self, message: str) -> None:
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def _set_busy(self, busy: bool) -> None:
        # 简化：忙时禁用主按钮所在区域通过状态栏提示
        self.config(cursor="watch" if busy else "")

    def _busy(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def refresh_status(self) -> None:
        install = find_cursor_install_dir()
        exe = find_cursor_exe()
        ver = read_cursor_version(install)
        if install and exe:
            ver_s = f"  版本 {ver}" if ver else ""
            self.status_install_var.set(f"已安装{ver_s}    {install}")
        else:
            self.status_install_var.set("未检测到 Cursor 安装目录（仍可备份/恢复用户数据）")
        if cursor_is_running():
            hits = list_cursor_processes()
            self.status_process_var.set(
                "运行中: " + ", ".join(f"{h.name}:{h.pid}" for h in hits)
            )
        else:
            self.status_process_var.set("当前未运行 Cursor")

    def refresh_backup_list(self) -> None:
        root = Path(self.backup_root_var.get())
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._path_by_iid.clear()
        entries = list_backup_entries(root, compute_size_if_missing=False)
        self.list_summary_var.set(f"历史备份：{len(entries)} 份")
        for entry in entries:
            ver = entry.cursor_version or "-"
            iid = self.tree.insert(
                "",
                tk.END,
                values=(entry.display_time, entry.size_label, ver, str(entry.path)),
            )
            self._path_by_iid[iid] = entry.path
        if entries:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)

    def refresh_estimate(self) -> None:
        def work() -> None:
            try:
                opts = self._backup_options()
                plan = build_plan(self.paths, opts)
                total = estimate_total(plan)
                text = f"预计约 {format_bytes(total)}"
                detail = "\n".join(
                    f"  - {i.label}: {format_bytes(i.estimated_bytes)}"
                    if i.src.exists()
                    else f"  - {i.label}: 不存在"
                    for i in plan
                )
                self.after(0, lambda: self.estimate_var.set(text))
                self.after(0, lambda: self._append_log("体积估算:\n" + detail))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.estimate_var.set(f"估算失败: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    def pick_backup_root(self) -> None:
        path = filedialog.askdirectory(
            initialdir=self.backup_root_var.get() or str(DEFAULT_BACKUP_ROOT)
        )
        if path:
            self.backup_root_var.set(path)
            self.refresh_backup_list()

    def open_backup_root(self) -> None:
        root = Path(self.backup_root_var.get())
        root.mkdir(parents=True, exist_ok=True)
        os.startfile(root)  # noqa: S606

    def on_launch_cursor(self) -> None:
        try:
            path = launch_cursor()
            self._append_log(f"已启动: {path}")
            self.after(800, self.refresh_status)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("启动失败", str(exc))

    def _backup_options(self) -> BackupOptions:
        return BackupOptions(
            backup_root=Path(self.backup_root_var.get()),
            include_settings=self.include_settings_var.get(),
            include_keybindings=self.include_keybindings_var.get(),
            include_rules=self.include_rules_var.get(),
            include_state_vscdb_backup=self.include_vscdb_backup_var.get(),
        )

    def _selected_backup_path(self) -> Path | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self._path_by_iid.get(sel[0])

    def on_backup(self) -> None:
        if self._busy():
            return
        self.refresh_status()
        root = Path(self.backup_root_var.get())
        if not root.drive:
            messagebox.showerror("错误", "请填写有效的备份根目录")
            return
        if not messagebox.askyesno(
            "一键备份",
            f"将备份全部对话到:\n{root / 'cursor-sessions_<时间戳>'}\n\n"
            f"{self.estimate_var.get()}\n\n"
            "备份时 Cursor 可开可关；文件被锁会报错。是否开始？",
        ):
            return
        self._set_busy(True)
        self._append_log("—— 开始一键备份 ——")

        def progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._append_log(m))

        def work() -> None:
            try:
                result = run_backup(self.paths, self._backup_options(), progress=progress)
                self.after(0, lambda: self._backup_done(result.backup_dir, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._backup_done(None, exc))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _backup_done(self, backup_dir: Path | None, error: BaseException | None) -> None:
        self._set_busy(False)
        self.refresh_status()
        self.refresh_backup_list()
        if error:
            self._append_log(
                "备份失败:\n" + "".join(traceback.format_exception_only(type(error), error))
            )
            messagebox.showerror("备份失败", str(error))
            return
        assert backup_dir is not None
        self._append_log(f"备份成功: {backup_dir}")
        messagebox.showinfo("备份成功", f"已保存到:\n{backup_dir}")

    def on_restore_selected(self) -> None:
        if self._busy():
            return
        path = self._selected_backup_path()
        if path is None:
            messagebox.showwarning("未选择", "请先在列表中点选一份历史备份")
            return
        problems = validate_backup_dir(path)
        if problems:
            messagebox.showerror("备份无效", "\n".join(problems))
            return

        self.refresh_status()
        running = cursor_is_running()
        tip = (
            f"将恢复:\n{path}\n\n"
            "步骤：关闭 Cursor（如正在运行）→ 当前数据挪到 OLD_* → 写入备份 → "
            + ("自动重启 Cursor。" if self.auto_relaunch_var.get() else "请手动启动 Cursor。")
        )
        if running:
            tip = "检测到 Cursor 正在运行。\n\n" + tip
        if not messagebox.askyesno("一键恢复", tip):
            return

        self._set_busy(True)
        self._append_log("—— 开始一键恢复 ——")
        relaunch = self.auto_relaunch_var.get()
        opts = RestoreOptions(
            backup_dir=path,
            include_settings=self.include_settings_var.get(),
            include_keybindings=self.include_keybindings_var.get(),
            include_rules=self.include_rules_var.get(),
        )

        def progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._append_log(m))

        def work() -> None:
            try:
                if cursor_is_running():
                    progress("正在关闭 Cursor…")
                    left = close_cursor_processes()
                    if left:
                        detail = ", ".join(f"{h.name}:{h.pid}" for h in left)
                        raise RuntimeError(f"无法关闭 Cursor，仍在运行: {detail}")
                    progress("Cursor 已退出")
                result = run_restore(self.paths, opts, progress=progress)
                if relaunch:
                    try:
                        launched = launch_cursor()
                        progress(f"已重新启动: {launched}")
                    except Exception as launch_exc:  # noqa: BLE001
                        progress(f"恢复成功，但自动启动失败: {launch_exc}")
                self.after(0, lambda: self._restore_done(result, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._restore_done(None, exc))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _restore_done(self, result, error: BaseException | None) -> None:
        self._set_busy(False)
        self.refresh_status()
        if error:
            self._append_log(
                "恢复失败:\n" + "".join(traceback.format_exception_only(type(error), error))
            )
            messagebox.showerror("恢复失败", str(error))
            return
        aside = "\n".join(result.aside_paths) if result.aside_paths else "(无旧数据被挪走)"
        messagebox.showinfo(
            "恢复成功",
            "已恢复: "
            + ", ".join(result.restored)
            + "\n\n回退副本:\n"
            + aside
            + "\n\n请用备份时相同的工程路径打开项目。",
        )

    def on_delete_selected(self) -> None:
        path = self._selected_backup_path()
        if path is None:
            messagebox.showwarning("未选择", "请先选择要删除的备份")
            return
        if not messagebox.askyesno("删除备份", f"确定删除这份备份？\n{path}\n\n此操作不可恢复。"):
            return
        try:
            delete_backup_dir(path)
            self._append_log(f"已删除备份: {path}")
            self.refresh_backup_list()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("删除失败", str(exc))

    def on_open_selected(self) -> None:
        path = self._selected_backup_path()
        if path is None:
            messagebox.showwarning("未选择", "请先选择一份备份")
            return
        if path.is_dir():
            os.startfile(path)  # noqa: S606


def main() -> None:
    app = SessionBackupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
