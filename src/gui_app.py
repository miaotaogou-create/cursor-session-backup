"""高颜值 CustomTkinter 主界面：备份 / 恢复 / 删除。"""

from __future__ import annotations

import os
import shutil
import threading
import time
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import __version__
from . import gui_theme as T
from .backup import BackupOptions, build_plan, estimate_total, run_backup
from .backup_index import BackupEntry, delete_backup_dir, list_backup_entries
from .cursor_install import find_cursor_install_dir, read_cursor_version
from .gui_widgets import BackupCard, LogViewer, PathCard, ProgressPanel, TitleBar
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


def _free_space_label(path: Path) -> str:
    try:
        usage = shutil.disk_usage(path if path.exists() else path.anchor or path)
        return format_bytes(usage.free)
    except OSError:
        return "未知"


class SessionBackupApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.title(f"Cursor 会话备份  v{__version__}")
        self.geometry("920x760")
        self.minsize(840, 680)
        self.configure(fg_color=T.SLATE_100)
        self.overrideredirect(True)

        self.paths = CursorPaths.resolve()
        self.backup_root = DEFAULT_BACKUP_ROOT
        self._worker: threading.Thread | None = None
        self._cards: list[ctk.CTkFrame] = []
        self._op_started_at: float | None = None
        self._last_logged_frac = -1.0
        self._refresh_spinning = False

        self._build_shell()
        self.refresh_status()
        self.refresh_list()
        self.after(150, self._warm_estimate)

    def _build_shell(self) -> None:
        # 外层描边，模拟 shadow / rounded 容器
        shell = ctk.CTkFrame(
            self,
            fg_color=T.SLATE_50,
            corner_radius=18,
            border_width=1,
            border_color=T.SLATE_200,
        )
        shell.pack(fill="both", expand=True, padx=8, pady=8)

        TitleBar(
            shell,
            title=f"Cursor 会话备份 v{__version__}",
            on_close=self.destroy,
        ).pack(fill="x")

        body = ctk.CTkFrame(shell, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(16, 16))

        # —— 标题与状态药丸 ——
        hero = ctk.CTkFrame(body, fg_color="transparent")
        hero.pack(fill="x")
        left_hero = ctk.CTkFrame(hero, fg_color="transparent")
        left_hero.pack(side="left", fill="x", expand=True)
        title_row = ctk.CTkFrame(left_hero, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(
            title_row,
            text="Cursor 会话备份",
            font=ctk.CTkFont(family=T.FONT_UI_BOLD, size=24),
            text_color=T.SLATE_900,
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text="  Session Manager  ",
            font=ctk.CTkFont(family=T.FONT_UI, size=11),
            text_color=T.TEAL_700,
            fg_color=T.TEAL_50,
            corner_radius=8,
        ).pack(side="left", padx=10, pady=4)
        ctk.CTkLabel(
            left_hero,
            text="一键保存并快速还原 Cursor 历史会话、workspaceStorage 及配置",
            font=ctk.CTkFont(family=T.FONT_UI, size=13),
            text_color=T.SLATE_500,
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        self.status_pill = ctk.CTkLabel(
            hero,
            text="  ●  检测中…  ",
            font=ctk.CTkFont(family=T.FONT_UI, size=12),
            text_color=T.SLATE_700,
            fg_color=T.WHITE,
            corner_radius=16,
            padx=12,
            pady=8,
        )
        self.status_pill.pack(side="right", anchor="n")

        # —— 路径双卡 ——
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x", pady=(16, 8))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        install = find_cursor_install_dir()
        ver = read_cursor_version(install) or "?"
        self.install_card = PathCard(
            grid,
            title=f"已安装版本: v{ver}",
            path_text=str(install) if install else "(未检测到)",
            on_copy=lambda: self._copy_text(self.install_card.path_var.get()),
        )
        self.install_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        free = _free_space_label(self.backup_root)
        self.backup_card = PathCard(
            grid,
            title=f"备份目录: 剩余空间 {free}",
            path_text=str(self.backup_root),
            on_copy=lambda: self._copy_text(str(self.backup_root)),
            on_change=self._change_backup_root,
        )
        self.backup_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # —— 操作栏 ——
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", pady=(8, 8))
        self.btn_backup = ctk.CTkButton(
            actions,
            text="⬇  一键备份全部对话",
            height=42,
            corner_radius=12,
            fg_color=T.TEAL_700,
            hover_color=T.TEAL_800,
            text_color=T.WHITE,
            font=ctk.CTkFont(family=T.FONT_UI_BOLD, size=14),
            command=self.on_backup,
        )
        self.btn_backup.pack(side="left")
        ctk.CTkButton(
            actions,
            text="📂  打开备份文件夹",
            height=42,
            width=150,
            corner_radius=12,
            fg_color=T.WHITE,
            hover_color=T.SLATE_100,
            border_width=1,
            border_color=T.TEAL_700,
            text_color=T.TEAL_700,
            font=ctk.CTkFont(family=T.FONT_UI, size=13),
            command=self.open_backup_root,
        ).pack(side="left", padx=10)
        self.btn_refresh = ctk.CTkButton(
            actions,
            text="↻  刷新",
            height=42,
            width=88,
            corner_radius=12,
            fg_color=T.SLATE_200,
            hover_color=T.SLATE_300,
            text_color=T.SLATE_700,
            font=ctk.CTkFont(family=T.FONT_UI, size=13),
            command=self._refresh_all,
        )
        self.btn_refresh.pack(side="right")

        # —— 历史列表 ——
        list_head = ctk.CTkFrame(body, fg_color="transparent")
        list_head.pack(fill="x", pady=(10, 4))
        self.list_title = ctk.CTkLabel(
            list_head,
            text="历史对话备份 · 0 份",
            font=ctk.CTkFont(family=T.FONT_UI_BOLD, size=15),
            text_color=T.SLATE_900,
        )
        self.list_title.pack(side="left")
        ctk.CTkLabel(
            list_head,
            text="每条可删除或一键恢复",
            font=ctk.CTkFont(family=T.FONT_UI, size=12),
            text_color=T.SLATE_500,
        ).pack(side="right")

        self.list_host = ctk.CTkScrollableFrame(
            body,
            fg_color=T.SLATE_50,
            corner_radius=12,
            height=180,
        )
        self.list_host.pack(fill="both", expand=True, pady=(0, 8))

        self.progress = ProgressPanel(body)
        self.progress.pack(fill="x", pady=(4, 8))

        self.log = LogViewer(body)
        self.log.pack(fill="x")

    # ---------- 状态 ----------
    def _busy(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def _set_busy_ui(self, busy: bool, backup_loading: bool = False) -> None:
        state = "disabled" if busy else "normal"
        self.btn_backup.configure(state=state)
        self.btn_refresh.configure(state=state)
        if backup_loading and busy:
            self.btn_backup.configure(text="⏳  正在备份…")
        elif not busy:
            self.btn_backup.configure(text="⬇  一键备份全部对话")

    def _copy_text(self, text: str) -> None:
        if not text or text.startswith("("):
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log.append(f"已复制到剪贴板: {text}")

    def _change_backup_root(self) -> None:
        if self._busy():
            return
        chosen = filedialog.askdirectory(initialdir=str(self.backup_root), parent=self)
        if not chosen:
            return
        self.backup_root = Path(chosen)
        free = _free_space_label(self.backup_root)
        self.backup_card.set_title(f"备份目录: 剩余空间 {free}")
        self.backup_card.set_path(str(self.backup_root))
        self.refresh_list()

    def _refresh_all(self) -> None:
        if self._busy():
            return
        self.btn_refresh.configure(text="↻  …")
        self.refresh_status()
        self.refresh_list()
        self.after(400, lambda: self.btn_refresh.configure(text="↻  刷新"))

    def refresh_status(self) -> None:
        install = find_cursor_install_dir()
        ver = read_cursor_version(install)
        self.install_card.set_title(f"已安装版本: v{ver or '?'}")
        self.install_card.set_path(str(install) if install else "(未检测到)")
        free = _free_space_label(self.backup_root)
        self.backup_card.set_title(f"备份目录: 剩余空间 {free}")
        self.backup_card.set_path(str(self.backup_root))

        if cursor_is_running():
            n = len(list_cursor_processes())
            self.status_pill.configure(
                text=f"  ●  Cursor 运行中 | {n} 个活动进程  ",
                text_color=T.EMERALD_600,
            )
        else:
            self.status_pill.configure(
                text="  ●  Cursor 未运行  ",
                text_color=T.SLATE_500,
            )

    def refresh_list(self) -> None:
        for card in self._cards:
            card.destroy()
        self._cards.clear()
        entries = list_backup_entries(self.backup_root, compute_size_if_missing=False)
        self.list_title.configure(text=f"历史对话备份 · {len(entries)} 份")
        if not entries:
            empty = ctk.CTkFrame(
                self.list_host,
                fg_color=T.WHITE,
                corner_radius=14,
                border_width=1,
                border_color=T.SLATE_200,
            )
            empty.pack(fill="x", padx=4, pady=6)
            ctk.CTkLabel(
                empty,
                text="还没有备份。点上方「一键备份全部对话」开始。",
                font=ctk.CTkFont(family=T.FONT_UI, size=13),
                text_color=T.SLATE_500,
            ).pack(pady=28)
            self._cards.append(empty)
            return
        for entry in entries:
            card = BackupCard(
                self.list_host,
                entry,
                on_delete=self.on_delete,
                on_restore=self.on_restore,
            )
            card.pack(fill="x", padx=4, pady=6)
            self._cards.append(card)
        threading.Thread(target=self._fill_sizes_async, daemon=True).start()

    def _fill_sizes_async(self) -> None:
        try:
            entries = list_backup_entries(self.backup_root, compute_size_if_missing=True)
        except Exception:  # noqa: BLE001
            return
        self.after(0, lambda: self._apply_sized_entries(entries))

    def _apply_sized_entries(self, entries: list[BackupEntry]) -> None:
        if self._busy():
            return
        for card in self._cards:
            card.destroy()
        self._cards.clear()
        self.list_title.configure(text=f"历史对话备份 · {len(entries)} 份")
        for entry in entries:
            card = BackupCard(
                self.list_host,
                entry,
                on_delete=self.on_delete,
                on_restore=self.on_restore,
            )
            card.pack(fill="x", padx=4, pady=6)
            self._cards.append(card)

    def _warm_estimate(self) -> None:
        def work() -> None:
            try:
                total = estimate_total(build_plan(self.paths, _default_options(self.backup_root)))
                self.after(0, lambda: self.log.append(f"预计备份约 {format_bytes(total)}"))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.log.append(f"体积估算跳过: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    def open_backup_root(self) -> None:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        os.startfile(self.backup_root)  # noqa: S606

    # ---------- 进度回调 ----------
    def _make_progress_cb(self):
        def progress(msg: str, fraction: float | None = None) -> None:
            self.after(0, lambda m=msg, f=fraction: self._on_progress(m, f))

        return progress

    def _on_progress(self, msg: str, fraction: float | None) -> None:
        self.progress.set_progress(msg, fraction)
        if fraction is None or fraction in (0.0, 1.0) or "完成" in msg or "失败" in msg:
            self.log.append(msg)
        elif fraction is not None and abs(fraction - self._last_logged_frac) >= 0.08:
            self._last_logged_frac = fraction
            self.log.append(msg)

    def _elapsed(self) -> float | None:
        if self._op_started_at is None:
            return None
        return time.monotonic() - self._op_started_at

    # ---------- 业务操作 ----------
    def on_backup(self) -> None:
        if self._busy():
            return
        self.refresh_status()
        if not messagebox.askyesno(
            "一键备份",
            f"备份全部对话到：\n{self.backup_root}\\cursor-sessions_<时间戳>\n\n是否开始？",
            parent=self,
        ):
            return
        self._last_logged_frac = -1.0
        self._op_started_at = time.monotonic()
        self.progress.reset("备份进度")
        self._set_busy_ui(True, backup_loading=True)
        self.log.append("—— 开始备份 ——")
        progress = self._make_progress_cb()

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
        self._set_busy_ui(False)
        self.refresh_status()
        self.refresh_list()
        elapsed = self._elapsed()
        if error:
            self.progress.finish(False, "备份失败", elapsed)
            self.log.append("备份失败: " + "".join(traceback.format_exception_only(type(error), error)).strip())
            messagebox.showerror("备份失败", str(error), parent=self)
            return
        assert backup_dir is not None
        self.progress.finish(True, f"备份成功：{backup_dir.name}", elapsed)
        self.log.append(f"备份成功: {backup_dir}")
        messagebox.showinfo("备份成功", f"已保存：\n{backup_dir}", parent=self)

    def on_restore(self, path: Path) -> None:
        if self._busy():
            return
        problems = validate_backup_dir(path)
        if problems:
            messagebox.showerror(
                "这份备份不能恢复",
                "\n".join(problems) + "\n\n建议：用本工具重新「一键备份」一份完整备份。",
                parent=self,
            )
            return
        running = cursor_is_running()
        msg = (
            f"将恢复：{path.name}\n\n"
            "会先关闭 Cursor，把当前数据挪到 OLD_*，再写入备份，最后自动重新打开 Cursor。\n是否继续？"
        )
        if running:
            msg = "检测到 Cursor 正在运行。\n\n" + msg
        if not messagebox.askyesno("一键恢复", msg, parent=self):
            return
        self._last_logged_frac = -1.0
        self._op_started_at = time.monotonic()
        self.progress.reset("恢复进度")
        self._set_busy_ui(True)
        self.log.append("—— 开始恢复 ——")
        opts = _default_restore(path)
        progress = self._make_progress_cb()

        def work() -> None:
            try:
                if cursor_is_running():
                    progress("正在关闭 Cursor…", 0.01)
                    left = close_cursor_processes()
                    if left:
                        detail = ", ".join(f"{h.name}:{h.pid}" for h in left)
                        raise RuntimeError(f"无法关闭 Cursor：{detail}")
                    progress("Cursor 已退出", 0.05)
                result = run_restore(self.paths, opts, progress=progress)
                try:
                    launched = launch_cursor()
                    progress(f"已重新启动 Cursor：{launched}", 1.0)
                except Exception as launch_exc:  # noqa: BLE001
                    progress(f"恢复成功，但自动启动失败：{launch_exc}", 1.0)
                self.after(0, lambda: self._restore_done(result, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._restore_done(None, exc))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _restore_done(self, result, error: BaseException | None) -> None:
        self._set_busy_ui(False)
        self.refresh_status()
        elapsed = self._elapsed()
        if error:
            self.progress.finish(False, "恢复失败", elapsed)
            self.log.append("恢复失败: " + "".join(traceback.format_exception_only(type(error), error)).strip())
            messagebox.showerror("恢复失败", str(error), parent=self)
            return
        self.progress.finish(True, "恢复完成", elapsed)
        aside = "\n".join(result.aside_paths[:6]) if result.aside_paths else "(无)"
        messagebox.showinfo(
            "恢复成功",
            "已恢复："
            + ", ".join(result.restored)
            + "\n\n回退副本：\n"
            + aside
            + "\n\n请用原来的工程路径打开项目。",
            parent=self,
        )

    def on_delete(self, path: Path) -> None:
        if self._busy():
            return
        if not messagebox.askyesno(
            "删除备份",
            f"确定删除？\n{path.name}\n\n删除后无法找回。",
            parent=self,
        ):
            return
        self._last_logged_frac = -1.0
        self._op_started_at = time.monotonic()
        self.progress.reset("删除进度")
        self._set_busy_ui(True)
        self.log.append(f"—— 开始删除 {path.name} ——")
        progress = self._make_progress_cb()

        def work() -> None:
            try:
                delete_backup_dir(path, progress=progress)
                self.after(0, lambda: self._delete_done(path, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._delete_done(path, exc))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _delete_done(self, path: Path, error: BaseException | None) -> None:
        self._set_busy_ui(False)
        elapsed = self._elapsed()
        if error:
            self.progress.finish(False, "删除失败", elapsed)
            self.log.append("删除失败: " + "".join(traceback.format_exception_only(type(error), error)).strip())
            messagebox.showerror("删除失败", str(error), parent=self)
            return
        self.progress.finish(True, f"已删除：{path.name}", elapsed)
        self.log.append(f"已删除：{path}")
        self.refresh_list()


def main() -> None:
    app = SessionBackupApp()
    # 居中
    app.update_idletasks()
    w, h = 920, 760
    x = max(0, (app.winfo_screenwidth() - w) // 2)
    y = max(0, (app.winfo_screenheight() - h) // 2)
    app.geometry(f"{w}x{h}+{x}+{y}")
    app.mainloop()


if __name__ == "__main__":
    main()
