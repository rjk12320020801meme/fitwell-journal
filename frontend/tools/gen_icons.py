# -*- coding: utf-8 -*-
"""生成 PWA 图标（192/512）。
设计：深青绿圆角底 + 白色抽象哑铃（健身主题）。
运行：bundled Python（含 Pillow）直接执行本文件即可重新生成。
"""
from PIL import Image, ImageDraw

THEME = (15, 118, 110)      # 深青绿 #0F766E
THEME_DARK = (17, 94, 89)   # #115E59
WHITE = (255, 255, 255)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 圆角底（留 6% 透明边，视觉更柔和）
    pad = int(size * 0.04)
    radius = int(size * 0.22)
    d.rounded_rectangle([pad, pad, size - pad, size - pad],
                        radius=radius, fill=THEME)

    # 白色抽象哑铃：横杆 + 两端配重
    cx, cy = size // 2, size // 2
    bar_w = int(size * 0.34)   # 横杆长度
    bar_h = int(size * 0.09)   # 横杆粗细
    d.rounded_rectangle([cx - bar_w // 2, cy - bar_h // 2,
                         cx + bar_w // 2, cy + bar_h // 2],
                        radius=bar_h // 2, fill=WHITE)

    plate_w = int(size * 0.10)  # 配重块宽
    plate_h = int(size * 0.34)  # 配重块高
    for sign in (-1, 1):
        x = cx + sign * (bar_w // 2) - (plate_w if sign > 0 else 0)
        d.rounded_rectangle([x, cy - plate_h // 2,
                             x + plate_w, cy + plate_h // 2],
                            radius=plate_w // 2, fill=WHITE)
        # 靠外侧的小配重
        x2 = cx + sign * (bar_w // 2 + plate_w + int(size * 0.02)) - \
            (int(size * 0.06) if sign > 0 else 0)
        small_h = int(size * 0.20)
        d.rounded_rectangle([x2, cy - small_h // 2,
                             x2 + int(size * 0.06), cy + small_h // 2],
                            radius=int(size * 0.03), fill=WHITE)

    return img


def main() -> None:
    import os
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icons")
    for size in (192, 512):
        path = os.path.abspath(os.path.join(out_dir, f"icon-{size}.png"))
        draw_icon(size).save(path)
        print(f"saved {path}")


if __name__ == "__main__":
    main()
