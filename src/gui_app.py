"""图形界面（标准库 tkinter）。"""

from __future__ import annotations

import os
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .backup import BackupOptions, build_plan, estimate_total, run_backup
from .paths import DEFAULT_BACKUP_ROOT, DEFAULT_RULES_DIR, CursorPaths, list_backup_dirs
from .process_check import cursor_is_running, list_cursor_processes
from .restore import RestoreOptions, run_restore, validate_backup_dir
from .sizing import format_bytes


class SessionBackupApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Cursor 会话备份 / 恢复  v{__version__}")
        self.geometry("780x620")
        self.minsize(700, 560)

        self.paths = CursorPaths.resolve()
        self._worker: threading.Thread | None = None

        self.backup_root_var = tk.StringVar(value=str(DEFAULT_BACKUP_ROOT))
        self.include_settings_var = tk.BooleanVar(value=True)
        self.include_keybindings_var = tk.BooleanVar(value=True)
        self.include_rules_var = tk.BooleanVar(value=False)
        self.include_vscdb_backup_var = tk.BooleanVar(value=False)
        self.estimate_var = tk.StringVar(value="尚未估算")
        self.process_var = tk.StringVar(value="")
        self.selected_backup_var = tk.StringVar(value="")

        self._build()
        self.refresh_process()
        self.refresh_backup_list()
        self.after(200, self.refresh_estimate)

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="备份根目录").grid(row=0, column=0, sticky="w")
        ent = ttk.Entry(root, textvariable=self.backup_root_var)
        ent.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(root, text="浏览…", command=self.pick_backup_root).grid(row=0, column=2, **pad)

        opts = ttk.LabelFrame(root, text="选项", padding=8)
        opts.grid(row=1, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Checkbutton(opts, text="包含 settings.json", variable=self.include_settings_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Checkbutton(opts, text="包含 keybindings.json", variable=self.include_keybindings_var).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Checkbutton(
            opts,
            text=f"包含规则笔记（{DEFAULT_RULES_DIR}）",
            variable=self.include_rules_var,
            command=self.refresh_estimate,
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(
            opts,
            text="包含 state.vscdb.backup（体积约再翻倍，默认不勾选）",
            variable=self.include_vscdb_backup_var,
            command=self.refresh_estimate,
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        info = ttk.Frame(root)
        info.grid(row=2, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Label(info, text="预估备份体积:").pack(side=tk.LEFT)
        ttk.Label(info, textvariable=self.estimate_var).pack(side=tk.LEFT, padx=6)
        ttk.Button(info, text="重新估算", command=self.refresh_estimate).pack(side=tk.LEFT)
        ttk.Button(info, text="刷新进程状态", command=self.refresh_process).pack(side=tk.LEFT, padx=8)
        ttk.Label(info, textvariable=self.process_var).pack(side=tk.LEFT, padx=6)

        actions = ttk.Frame(root)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)
        self.btn_backup = ttk.Button(actions, text="开始备份", command=self.on_backup)
        self.btn_backup.pack(side=tk.LEFT)
        ttk.Button(actions, text="打开备份根目录", command=self.open_backup_root).pack(side=tk.LEFT, padx=8)

        restore_box = ttk.LabelFrame(root, text="恢复", padding=8)
        restore_box.grid(row=4, column=0, columnspan=3, sticky="nsew", **pad)
        ttk.Label(restore_box, text="选择备份目录（cursor-sessions_*）").grid(row=0, column=0, sticky="w")
        self.backup_combo = ttk.Combobox(
            restore_box, textvariable=self.selected_backup_var, state="readonly", width=70
        )
        self.backup_combo.grid(row=1, column=0, sticky="ew", pady=4)
        btns = ttk.Frame(restore_box)
        btns.grid(row=1, column=1, sticky="e", padx=6)
        ttk.Button(btns, text="刷新列表", command=self.refresh_backup_list).pack(side=tk.TOP, fill=tk.X)
        ttk.Button(btns, text="手动选目录…", command=self.pick_backup_dir).pack(
            side=tk.TOP, fill=tk.X, pady=4
        )
        self.btn_restore = ttk.Button(
            restore_box, text="开始恢复（须先退出 Cursor）", command=self.on_restore
        )
        self.btn_restore.grid(row=2, column=0, columnspan=2, sticky="w", pady=6)
        tip = (
            "恢复会先把现有目标挪到同级 OLD_<时间戳>_*，再覆盖写入。\n"
            "恢复后请用备份时相同的工程路径打开项目。"
        )
        ttk.Label(restore_box, text=tip, foreground="#444").grid(
            row=3, column=0, columnspan=2, sticky="w"
        )
        restore_box.columnconfigure(0, weight=1)

        log_frame = ttk.LabelFrame(root, text="日志", padding=8)
        log_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", **pad)
        self.log = tk.Text(log_frame, height=14, wrap=tk.WORD)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.configure(yscrollcommand=scroll.set)

        root.columnconfigure(1, weight=1)
        root.rowconfigure(4, weight=1)
        root.rowconfigure(5, weight=2)

        self._append_log(f"Cursor User 目录: {self.paths.appdata_user}")
        self._append_log(f"globalStorage: {self.paths.global_storage}")

    def _append_log(self, message: str) -> None:
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_backup.configure(state=state)
        self.btn_restore.configure(state=state)

    def pick_backup_root(self) -> None:
        path = filedialog.askdirectory(
            initialdir=self.backup_root_var.get() or str(DEFAULT_BACKUP_ROOT)
        )
        if path:
            self.backup_root_var.set(path)
            self.refresh_backup_list()

    def pick_backup_dir(self) -> None:
        initial = self.backup_root_var.get() or str(DEFAULT_BACKUP_ROOT)
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            self.selected_backup_var.set(path)
            values = list(self.backup_combo["values"])
            if path not in values:
                values = [path] + values
                self.backup_combo["values"] = values

    def open_backup_root(self) -> None:
        root = Path(self.backup_root_var.get())
        root.mkdir(parents=True, exist_ok=True)
        os.startfile(root)  # noqa: S606

    def refresh_process(self) -> None:
        if cursor_is_running():
            hits = list_cursor_processes()
            self.process_var.set(
                "Cursor 正在运行: " + ", ".join(f"{h.name}:{h.pid}" for h in hits)
            )
        else:
            self.process_var.set("未检测到 Cursor 进程")

    def refresh_backup_list(self) -> None:
        root = Path(self.backup_root_var.get())
        dirs = [str(p) for p in list_backup_dirs(root)]
        self.backup_combo["values"] = dirs
        if dirs and not self.selected_backup_var.get():
            self.selected_backup_var.set(dirs[0])

    def refresh_estimate(self) -> None:
        def work() -> None:
            try:
                opts = self._backup_options()
                plan = build_plan(self.paths, opts)
                total = estimate_total(plan)
                lines = [f"{format_bytes(total)}（按当前选项）"]
                for item in plan:
                    if item.src.exists():
                        lines.append(f"  - {item.label}: {format_bytes(item.estimated_bytes)}")
                    else:
                        lines.append(f"  - {item.label}: 不存在")
                text = lines[0]
                detail = "\n".join(lines[1:])
                self.after(0, lambda: self.estimate_var.set(text))
                self.after(0, lambda: self._append_log("体积估算:\n" + detail))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.estimate_var.set(f"估算失败: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    def _backup_options(self) -> BackupOptions:
        return BackupOptions(
            backup_root=Path(self.backup_root_var.get()),
            include_settings=self.include_settings_var.get(),
            include_keybindings=self.include_keybindings_var.get(),
            include_rules=self.include_rules_var.get(),
            include_state_vscdb_backup=self.include_vscdb_backup_var.get(),
        )

    def _restore_options(self) -> RestoreOptions:
        selected = self.selected_backup_var.get().strip()
        if not selected:
            raise RuntimeError("请先选择要恢复的备份目录")
        return RestoreOptions(
            backup_dir=Path(selected),
            include_settings=self.include_settings_var.get(),
            include_keybindings=self.include_keybindings_var.get(),
            include_rules=self.include_rules_var.get(),
        )

    def on_backup(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self.refresh_process()
        root = Path(self.backup_root_var.get())
        if not root.drive:
            messagebox.showerror("错误", "请填写有效的备份根目录")
            return
        if not messagebox.askyesno(
            "确认备份",
            f"将备份到:\n{root / 'cursor-sessions_<时间戳>'}\n\n"
            "建议备份时尽量退出 Cursor，以免文件被锁。\n是否继续？",
        ):
            return
        self._set_busy(True)
        self._append_log("—— 开始备份 ——")

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
        self.refresh_backup_list()
        self.refresh_process()
        if error:
            self._append_log(
                "备份失败:\n" + "".join(traceback.format_exception_only(type(error), error))
            )
            messagebox.showerror("备份失败", str(error))
            return
        assert backup_dir is not None
        self.selected_backup_var.set(str(backup_dir))
        self._append_log(f"备份成功: {backup_dir}")
        messagebox.showinfo("备份成功", f"已保存到:\n{backup_dir}")

    def on_restore(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self.refresh_process()
        try:
            opts = self._restore_options()
        except RuntimeError as exc:
            messagebox.showerror("错误", str(exc))
            return
        problems = validate_backup_dir(opts.backup_dir)
        if problems:
            messagebox.showerror("备份无效", "\n".join(problems))
            return
        if cursor_is_running():
            messagebox.showerror(
                "请先退出 Cursor", "检测到 Cursor 仍在运行，禁止恢复以免损坏数据库。"
            )
            return
        if not messagebox.askyesno(
            "确认恢复",
            f"将从以下备份恢复并覆盖本机数据:\n{opts.backup_dir}\n\n"
            "覆盖前会把现有目录/文件挪到 OLD_* 以便回退。\n是否继续？",
        ):
            return
        self._set_busy(True)
        self._append_log("—— 开始恢复 ——")

        def progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._append_log(m))

        def work() -> None:
            try:
                result = run_restore(self.paths, opts, progress=progress)
                self.after(0, lambda: self._restore_done(result, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._restore_done(None, exc))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _restore_done(self, result, error: BaseException | None) -> None:
        self._set_busy(False)
        self.refresh_process()
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
            + "\n\n请重新打开 Cursor，并用原工程路径打开项目。",
        )


def main() -> None:
    app = SessionBackupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
