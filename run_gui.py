#!/usr/bin/env python3
"""启动图形界面（WebView2 + React）；崩溃时写旁路日志。"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _crash_log_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "CursorSessionBackup.crash.log"
    return Path(__file__).resolve().parent / "CursorSessionBackup.crash.log"


def main() -> None:
    try:
        from src.gui_webview import main as gui_main

        gui_main()
    except Exception:
        log = _crash_log_path()
        try:
            log.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
