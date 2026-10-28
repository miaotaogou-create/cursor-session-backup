"""现代化极简界面：一键备份 + 历史卡片（一键恢复 / 删除）。"""

from __future__ import annotations

import os
import threading
import traceback
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from . import __version__
from .backup import BackupOptions, build_plan, estimate_total, run_backup
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

# 浅色、克制的强调色（避免常见「紫渐变」套路）
ACCENT = "#0F766E"
ACCENT_HOVER = "#0D9488"
DANGER = "#B91C1C"
DANGER_HOVER = "#DC2626"
SURFACE = "#F4F6F8"
CARD = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"


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


class SessionBackupApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.title(f"Cursor 会话备份  v{__version__}")
        self.geometry("820x640")
        self.minsize(760, 560)
        self.configure(fg_color=SURFACE)

        self.paths = CursorPaths.resolve()
        self.backup_root = DEFAULT_BACKUP_ROOT
        self._worker: threading.Thread | None = None
        self._cards: list[ctk.CTkFrame] = []

        self._build()
        self.refresh_status()
        self.refresh_list()
        self.after(120, self._warm_estimate)

    def _build(self) -> None:
        pad = {"padx": 24, "pady": (18, 0)}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", **pad)
        ctk.CTkLabel(
            header,
            text="Cursor 会话备份",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=22),
            text_color=TEXT,
        ).pack(anchor="w")
        self.status_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=MUTED,
            anchor="w",
            justify="left",
        )
        self.status_label.pack(anchor="w", pady=(6, 0))
        self.path_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
            anchor="w",
        )
        self.path_label.pack(anchor="w", pady=(2, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(16, 8))
        ctk.CTkButton(
            actions,
            text="一键备份全部对话",
            height=42,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14),
            command=self.on_backup,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="打开备份文件夹",
            height=42,
            width=130,
            corner_radius=10,
            fg_color="#E2E8F0",
            hover_color="#CBD5E1",
            text_color=TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            command=self.open_backup_root,
        ).pack(side="left", padx=(10, 0))
        ctk.CTkButton(
            actions,
            text="刷新",
            height=42,
            width=80,
            corner_radius=10,
            fg_color="#E2E8F0",
            hover_color="#CBD5E1",
            text_color=TEXT,
            command=self._refresh_all,
        ).pack(side="right")

        list_head = ctk.CTkFrame(self, fg_color="transparent")
        list_head.pack(fill="x", padx=24, pady=(8, 4))
        self.list_title = ctk.CTkLabel(
            list_head,
            text="历史对话备份 · 0 份",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15),
            text_color=TEXT,
        )
        self.list_title.pack(side="left")
        ctk.CTkLabel(
            list_head,
            text="每条可删除或一键恢复",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
        ).pack(side="right")

        self.list_host = ctk.CTkScrollableFrame(
            self,
            fg_color=SURFACE,
            corner_radius=0,
        )
        self.list_host.pack(fill="both", expand=True, padx=18, pady=(0, 8))

        log_wrap = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12, border_width=1, border_color="#E2E8F0")
        log_wrap.pack(fill="x", padx=24, pady=(0, 20))
        ctk.CTkLabel(
            log_wrap,
            text="运行日志",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
        ).pack(anchor="w", padx=14, pady=(10, 0))
        self.log = ctk.CTkTextbox(
            log_wrap,
            height=110,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=CARD,
            text_color=TEXT,
            border_width=0,
        )
        self.log.pack(fill="x", padx=8, pady=(4, 10))

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _busy(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def _refresh_all(self) -> None:
        self.refresh_status()
        self.refresh_list()

    def refresh_status(self) -> None:
        install = find_cursor_install_dir()
        ver = read_cursor_version(install)
        if install:
            ver_s = f"  v{ver}" if ver else ""
            line1 = f"已安装{ver_s}    {install}"
        else:
            line1 = "未检测到安装目录（仍可备份 / 恢复本机会话）"
        if cursor_is_running():
            hits = list_cursor_processes()
            line1 += f"    ·  运行中（{len(hits)} 个进程）"
        else:
            line1 += "    ·  当前未运行"
        self.status_label.configure(text=line1)
        self.path_label.configure(text=f"备份目录  {self.backup_root}")

    def refresh_list(self) -> None:
        for card in self._cards:
            card.destroy()
        self._cards.clear()

        entries = list_backup_entries(self.backup_root, compute_size_if_missing=False)
        self.list_title.configure(text=f"历史对话备份 · {len(entries)} 份")

        if not entries:
            empty = ctk.CTkFrame(
                self.list_host,
                fg_color=CARD,
                corner_radius=12,
                border_width=1,
                border_color="#E2E8F0",
                height=88,
            )
            empty.pack(fill="x", padx=6, pady=6)
            ctk.CTkLabel(
                empty,
                text="还没有备份。点上方「一键备份全部对话」开始。",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=MUTED,
            ).pack(pady=28)
            self._cards.append(empty)
            return

        for entry in entries:
            self._cards.append(self._make_card(entry))

        # 后台补算体积（旧备份没有 manifest 时不再一直「未知」）
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
            self._cards.append(self._make_card(entry))

    def _make_card(self, entry: BackupEntry) -> ctk.CTkFrame:
        border = "#FECACA" if not entry.usable else "#E2E8F0"
        card = ctk.CTkFrame(
            self.list_host,
            fg_color=CARD,
            corner_radius=12,
            border_width=1,
            border_color=border,
        )
        card.pack(fill="x", padx=6, pady=6)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=16, pady=14)
        ctk.CTkLabel(
            left,
            text=entry.display_time,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=15),
            text_color=TEXT,
            anchor="w",
        ).pack(anchor="w")
        meta = f"{entry.size_label}"
        if entry.cursor_version:
            meta += f"    ·    Cursor {entry.cursor_version}"
        ctk.CTkLabel(
            left,
            text=meta,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))
        if entry.note:
            ctk.CTkLabel(
                left,
                text=entry.note,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=DANGER if not entry.usable else MUTED,
                anchor="w",
            ).pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=14, pady=14)
        ctk.CTkButton(
            right,
            text="删除",
            width=72,
            height=34,
            corner_radius=8,
            fg_color="#FEE2E2",
            hover_color="#FECACA",
            text_color=DANGER,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            command=lambda p=entry.path: self.on_delete(p),
        ).pack(side="left", padx=(0, 8))
        restore_btn = ctk.CTkButton(
            right,
            text="一键恢复",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=ACCENT if entry.usable else "#94A3B8",
            hover_color=ACCENT_HOVER if entry.usable else "#94A3B8",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13),
            command=lambda p=entry.path: self.on_restore(p),
        )
        restore_btn.pack(side="left")
        if not entry.usable:
            restore_btn.configure(state="disabled")
        return card

    def _warm_estimate(self) -> None:
        def work() -> None:
            try:
                total = estimate_total(build_plan(self.paths, _default_options(self.backup_root)))
                self.after(0, lambda: self._log(f"预计备份约 {format_bytes(total)}"))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._log(f"体积估算跳过: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    def open_backup_root(self) -> None:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        os.startfile(self.backup_root)  # noqa: S606

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
            messagebox.showerror("备份失败", str(error), parent=self)
            return
        assert backup_dir is not None
        self._log(f"备份成功: {backup_dir}")
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
            messagebox.showerror("恢复失败", str(error), parent=self)
            return
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
        try:
            delete_backup_dir(path)
            self._log(f"已删除：{path}")
            self.refresh_list()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("删除失败", str(exc), parent=self)


def main() -> None:
    app = SessionBackupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
