"""用 Edge WebView2 承载 React 界面（不再依赖 tkinter）。"""

from __future__ import annotations

import sys
from pathlib import Path

import webview

from . import __version__
from .gui_api import DesktopApi


def _ui_index() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "ui" / "index.html"
    # 开发：优先已构建的 ui/dist，其次源码提示
    root = Path(__file__).resolve().parents[1]
    built = root / "ui" / "dist" / "index.html"
    return built


def main() -> None:
    index = _ui_index()
    if not index.is_file():
        raise SystemExit(
            f"找不到界面文件：{index}\n请先在 ui 目录执行 npm install && npm run build"
        )

    api = DesktopApi()
    window = webview.create_window(
        title=f"Cursor 会话备份  v{__version__}",
        url=index.as_uri(),
        js_api=api,
        width=960,
        height=820,
        min_size=(840, 680),
        background_color="#F1F5F9",
        frameless=True,
        easy_drag=False,
    )
    api.bind_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
