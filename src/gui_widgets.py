"""可复用界面组件（标题栏、路径卡、备份卡、进度、日志）。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from . import gui_theme as T
from .backup_index import BackupEntry


class BrandBar(ctk.CTkFrame):
    """深青色品牌条（不用自定义拖拽/三键，避免无边框窗口递归崩溃；系统标题栏负责窗控）。"""

    def __init__(self, master, title: str) -> None:
        super().__init__(master, height=40, fg_color=T.TEAL_800, corner_radius=12)
        self.pack_propagate(False)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=14)
        ctk.CTkLabel(
            left,
            text="▣  " + title,
            font=ctk.CTkFont(family=T.FONT_UI_BOLD, size=13),
            text_color=T.WHITE,
        ).pack(side="left", pady=8)

        mid = ctk.CTkFrame(self, fg_color="#0F766E", corner_radius=10, height=24)
        mid.pack(side="left", padx=16)
        ctk.CTkLabel(
            mid,
            text="  本地安全存储 · 无网络上传  ",
            font=ctk.CTkFont(family=T.FONT_UI, size=11),
            text_color="#CCFBF1",
        ).pack(padx=6, pady=2)


class PathCard(ctk.CTkFrame):
    """白底路径信息卡。"""

    def __init__(
        self,
        master,
        title: str,
        path_text: str,
        *,
        on_copy: Callable[[], None],
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.WHITE,
            corner_radius=14,
            border_width=1,
            border_color=T.SLATE_200,
        )
        self.path_var = tk.StringVar(value=path_text)
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(family=T.FONT_UI_BOLD, size=12),
            text_color=T.SLATE_700,
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=14, pady=(12, 6))

        row = ctk.CTkFrame(self, fg_color=T.SLATE_50, corner_radius=8)
        row.pack(fill="x", padx=12, pady=(0, 12))
        entry = ctk.CTkEntry(
            row,
            textvariable=self.path_var,
            font=ctk.CTkFont(family=T.FONT_MONO, size=12),
            fg_color=T.SLATE_50,
            border_width=0,
            text_color=T.SLATE_700,
            state="readonly",
        )
        entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ctk.CTkButton(
            row,
            text="复制",
            width=52,
            height=28,
            corner_radius=8,
            fg_color=T.SLATE_200,
            hover_color=T.SLATE_300,
            text_color=T.SLATE_700,
            font=ctk.CTkFont(family=T.FONT_UI, size=12),
            command=on_copy,
        ).pack(side="right", padx=(0, 4), pady=6)
        if on_change is not None:
            ctk.CTkButton(
                row,
                text="更改",
                width=52,
                height=28,
                corner_radius=8,
                fg_color=T.TEAL_50,
                hover_color="#CCFBF1",
                text_color=T.TEAL_700,
                font=ctk.CTkFont(family=T.FONT_UI, size=12),
                command=on_change,
            ).pack(side="right", padx=(0, 6), pady=6)

    def set_title(self, title: str) -> None:
        self.title_label.configure(text=title)

    def set_path(self, path: str) -> None:
        self.path_var.set(path)


class BackupCard(ctk.CTkFrame):
    """单条历史备份卡片。"""

    def __init__(
        self,
        master,
        entry: BackupEntry,
        *,
        on_delete: Callable[[Path], None],
        on_restore: Callable[[Path], None],
    ) -> None:
        border = "#FECACA" if not entry.usable else T.SLATE_200
        super().__init__(
            master,
            fg_color=T.WHITE,
            corner_radius=14,
            border_width=1,
            border_color=border,
        )
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=14)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(anchor="w", fill="x")
        ctk.CTkLabel(
            title_row,
            text=entry.display_time,
            font=ctk.CTkFont(family=T.FONT_MONO, size=15, weight="bold"),
            text_color=T.SLATE_900,
        ).pack(side="left")
        badge_fg = "#ECFDF5" if entry.usable else T.ROSE_50
        badge_tx = T.EMERALD_600 if entry.usable else T.ROSE_600
        badge_text = "已校验" if entry.usable else "不可用"
        ctk.CTkLabel(
            title_row,
            text=f"  {badge_text}  ",
            font=ctk.CTkFont(family=T.FONT_UI, size=11),
            text_color=badge_tx,
            fg_color=badge_fg,
            corner_radius=8,
        ).pack(side="left", padx=10)

        meta_parts = [entry.size_label]
        if entry.cursor_version:
            meta_parts.append(f"Cursor {entry.cursor_version}")
        if entry.usable:
            meta_parts.append("完整会话快照")
        elif entry.note:
            meta_parts.append(entry.note)
        ctk.CTkLabel(
            left,
            text=" · ".join(meta_parts),
            font=ctk.CTkFont(family=T.FONT_UI, size=12),
            text_color=T.SLATE_500,
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="right")
        ctk.CTkButton(
            right,
            text="删除",
            width=72,
            height=34,
            corner_radius=10,
            fg_color=T.ROSE_50,
            hover_color="#FFE4E6",
            text_color=T.ROSE_600,
            font=ctk.CTkFont(family=T.FONT_UI, size=13),
            command=lambda: on_delete(entry.path),
        ).pack(side="left", padx=(0, 8))
        restore = ctk.CTkButton(
            right,
            text="一键恢复",
            width=104,
            height=34,
            corner_radius=10,
            fg_color=T.TEAL_700 if entry.usable else T.SLATE_300,
            hover_color=T.TEAL_800 if entry.usable else T.SLATE_300,
            text_color=T.WHITE,
            font=ctk.CTkFont(family=T.FONT_UI_BOLD, size=13),
            command=lambda: on_restore(entry.path),
            state="normal" if entry.usable else "disabled",
        )
        restore.pack(side="left")


class ProgressPanel(ctk.CTkFrame):
    """任务进度卡。"""

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.WHITE,
            corner_radius=14,
            border_width=1,
            border_color=T.SLATE_200,
        )
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 4))
        self.title = ctk.CTkLabel(
            head,
            text="任务进度",
            font=ctk.CTkFont(family=T.FONT_UI_BOLD, size=13),
            text_color=T.SLATE_700,
        )
        self.title.pack(side="left")
        self.status = ctk.CTkLabel(
            head,
            text="  就绪  ",
            font=ctk.CTkFont(family=T.FONT_UI, size=11),
            text_color=T.TEAL_700,
            fg_color=T.TEAL_50,
            corner_radius=8,
        )
        self.status.pack(side="right")

        self.bar = ctk.CTkProgressBar(
            self,
            height=14,
            corner_radius=8,
            progress_color=T.TEAL_700,
            fg_color=T.SLATE_100,
        )
        self.bar.pack(fill="x", padx=16, pady=8)
        self.bar.set(0)

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=16, pady=(0, 12))
        self.detail = ctk.CTkLabel(
            foot,
            text="空闲",
            font=ctk.CTkFont(family=T.FONT_UI, size=12),
            text_color=T.SLATE_500,
            anchor="w",
        )
        self.detail.pack(side="left")
        self.elapsed = ctk.CTkLabel(
            foot,
            text="",
            font=ctk.CTkFont(family=T.FONT_MONO, size=12),
            text_color=T.SLATE_500,
        )
        self.elapsed.pack(side="right")

    def reset(self, title: str) -> None:
        self.title.configure(text=title)
        self.status.configure(text="  运行中  ", text_color=T.TEAL_700, fg_color=T.TEAL_50)
        self.bar.set(0)
        self.detail.configure(text="准备中…")
        self.elapsed.configure(text="")

    def set_progress(self, message: str, fraction: float | None = None) -> None:
        self.detail.configure(text=message)
        if fraction is None:
            return
        frac = max(0.0, min(1.0, float(fraction)))
        self.bar.set(frac)
        self.status.configure(
            text=f"  {int(round(frac * 100))}%  ",
            text_color=T.TEAL_700,
            fg_color=T.TEAL_50,
        )

    def finish(self, ok: bool, message: str, elapsed_s: float | None = None) -> None:
        self.bar.set(1.0 if ok else self.bar.get())
        if ok:
            self.status.configure(text="  完成  ", text_color=T.EMERALD_600, fg_color="#ECFDF5")
        else:
            self.status.configure(text="  失败  ", text_color=T.ROSE_600, fg_color=T.ROSE_50)
        self.detail.configure(text=message)
        if elapsed_s is not None:
            self.elapsed.configure(text=f"耗时 {elapsed_s:.1f}s")


class LogViewer(ctk.CTkFrame):
    """深色终端风格日志。"""

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.SLATE_950,
            corner_radius=14,
            border_width=1,
            border_color=T.SLATE_800,
        )
        self._auto_scroll = True
        self._lines = 0

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 4))
        self.title = ctk.CTkLabel(
            head,
            text=">_  运行日志 (0 行)",
            font=ctk.CTkFont(family=T.FONT_MONO, size=12),
            text_color=T.SLATE_300,
        )
        self.title.pack(side="left")

        btns = ctk.CTkFrame(head, fg_color="transparent")
        btns.pack(side="right")
        self.auto_btn = ctk.CTkButton(
            btns,
            text="自动滚动:开",
            width=90,
            height=26,
            corner_radius=8,
            fg_color=T.SLATE_800,
            hover_color=T.SLATE_700,
            text_color=T.SLATE_200,
            font=ctk.CTkFont(size=11),
            command=self._toggle_auto,
        )
        self.auto_btn.pack(side="left", padx=3)
        ctk.CTkButton(
            btns,
            text="复制",
            width=48,
            height=26,
            corner_radius=8,
            fg_color=T.SLATE_800,
            hover_color=T.SLATE_700,
            text_color=T.SLATE_200,
            font=ctk.CTkFont(size=11),
            command=self.copy_all,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btns,
            text="清空",
            width=48,
            height=26,
            corner_radius=8,
            fg_color=T.SLATE_800,
            hover_color=T.SLATE_700,
            text_color=T.SLATE_200,
            font=ctk.CTkFont(size=11),
            command=self.clear,
        ).pack(side="left", padx=3)

        self.box = ctk.CTkTextbox(
            self,
            height=120,
            font=ctk.CTkFont(family=T.FONT_MONO, size=12),
            fg_color=T.SLATE_950,
            text_color="#E2E8F0",
            border_width=0,
            activate_scrollbars=True,
        )
        self.box.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        tb = self.box._textbox  # noqa: SLF001
        tb.tag_configure("ok", foreground="#4ADE80")
        tb.tag_configure("skip", foreground="#FBBF24")
        tb.tag_configure("info", foreground="#38BDF8")
        tb.tag_configure("err", foreground="#FB7185")
        tb.tag_configure("plain", foreground="#CBD5E1")
        self.box.configure(state="disabled")

    def _toggle_auto(self) -> None:
        self._auto_scroll = not self._auto_scroll
        self.auto_btn.configure(text="自动滚动:开" if self._auto_scroll else "自动滚动:关")

    def clear(self) -> None:
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.configure(state="disabled")
        self._lines = 0
        self.title.configure(text=">_  运行日志 (0 行)")

    def copy_all(self) -> None:
        text = self.box.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)

    def append(self, message: str) -> None:
        from datetime import datetime

        stamp = datetime.now().strftime("%H:%M:%S")
        level, tag = self._classify(message)
        line = f"{stamp} [{level}] {message}\n"
        self.box.configure(state="normal")
        self.box.insert("end", line, tag)
        self.box.configure(state="disabled")
        self._lines += 1
        self.title.configure(text=f">_  运行日志 ({self._lines} 行)")
        if self._auto_scroll:
            self.box.see("end")

    @staticmethod
    def _classify(message: str) -> tuple[str, str]:
        m = message.lower()
        if "失败" in message or "error" in m or "无法" in message:
            return "错误", "err"
        if "跳过" in message:
            return "跳过", "skip"
        if "完成" in message or "成功" in message or "已恢复" in message or "已删除" in message:
            return "成功", "ok"
        if "开始" in message or "正在" in message or "已重新启动" in message or "预计" in message:
            return "信息", "info"
        return "信息", "plain"
