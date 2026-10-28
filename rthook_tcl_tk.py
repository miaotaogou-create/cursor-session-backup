"""冻结运行时：清掉污染的 TCL/TK 环境变量，再指向捆绑目录并写探针。"""

from __future__ import annotations

import os
import sys


def _boot() -> None:
    for key in ("TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH"):
        os.environ.pop(key, None)

    if not getattr(sys, "frozen", False):
        return

    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return

    tcl = os.path.join(base, "_tcl_data")
    tk = os.path.join(base, "_tk_data")
    init = os.path.join(tcl, "init.tcl")

    lines = [
        f"MEIPASS={base}",
        f"tcl_isdir={os.path.isdir(tcl)}",
        f"tk_isdir={os.path.isdir(tk)}",
        f"init_exists={os.path.isfile(init)}",
        f"init_size={os.path.getsize(init) if os.path.isfile(init) else -1}",
    ]
    if os.path.isdir(tcl):
        try:
            lines.append("tcl_top=" + ",".join(sorted(os.listdir(tcl))[:50]))
        except OSError as exc:
            lines.append(f"listdir_err={exc}")

    if os.path.isdir(tcl):
        os.environ["TCL_LIBRARY"] = tcl
    if os.path.isdir(tk):
        os.environ["TK_LIBRARY"] = tk

    lines.append(f"TCL_LIBRARY={os.environ.get('TCL_LIBRARY')}")
    lines.append(f"TK_LIBRARY={os.environ.get('TK_LIBRARY')}")

    try:
        log = os.path.join(os.path.dirname(sys.executable), "tcl_probe.txt")
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError:
        pass


_boot()
