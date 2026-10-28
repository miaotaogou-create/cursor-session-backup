"""生成资源管理器 / 任务栏用的多尺寸 app.ico（对齐界面青绿主题）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
TEAL_BG = (17, 94, 89)
TEAL_ACCENT = (13, 148, 136)
WHITE = (248, 250, 252)
EDGE = (45, 212, 191)
SIZES = (16, 32, 48, 64, 128, 256)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = max(1, size // 16)
    d.rounded_rectangle(
        (m, m, size - m - 1, size - m - 1), radius=size // 5, fill=TEAL_BG
    )
    pad = size // 5
    d.rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=size // 8,
        fill=TEAL_ACCENT,
    )

    cx = size // 2
    top = int(size * 0.28)
    bot = int(size * 0.72)
    rx = int(size * 0.22)
    ry = max(2, int(size * 0.08))
    d.rectangle((cx - rx, top, cx + rx, bot), fill=WHITE)
    d.ellipse((cx - rx, bot - ry, cx + rx, bot + ry), fill=WHITE)
    d.ellipse((cx - rx, top - ry, cx + rx, top + ry), fill=WHITE)
    line_w = max(1, size // 32)
    for y in (int(size * 0.42), int(size * 0.56)):
        d.ellipse(
            (cx - rx, y - ry // 2, cx + rx, y + ry // 2),
            outline=TEAL_ACCENT,
            width=line_w,
        )
    d.rounded_rectangle(
        (m, m, size - m - 1, size - m - 1),
        radius=size // 5,
        outline=EDGE,
        width=max(1, size // 32),
    )
    return img


def main() -> None:
    images = [draw_icon(s) for s in SIZES]
    ico = ROOT / "app.ico"
    images[-1].save(ico, format="ICO", sizes=[(s, s) for s in SIZES])
    images[-1].save(ROOT / "app_256.png", format="PNG")
    print(f"OK: {ico} ({ico.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
