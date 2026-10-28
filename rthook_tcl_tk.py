"""冻结运行时强制指向捆绑的 Tcl/Tk 数据目录。"""

from __future__ import annotations

import os
import sys


def _boot() -> None:
    if not getattr(sys, "frozen", False):
        return
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
    tcl = os.path.join(base, "_tcl_data")
    tk = os.path.join(base, "_tk_data")
    if os.path.isdir(tcl):
        os.environ["TCL_LIBRARY"] = tcl
    if os.path.isdir(tk):
        os.environ["TK_LIBRARY"] = tk


_boot()
