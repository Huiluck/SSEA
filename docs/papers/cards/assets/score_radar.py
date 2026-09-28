# -*- coding: utf-8 -*-
"""
论文分析卡片 · 六维评分雷达图生成器（仅依赖 Pillow）。

用法:
    python score_radar.py <输出png路径> <标题> <维度1=分值1> <维度2=分值2> ...
示例:
    python score_radar.py dream-rsi-radar.png "Dream-RSI 评分" 项目相关性=4 立场兼容性=3 \
        可搬运性=4 证据强度=4 组合价值=5 落地成本=3

分值为 1-5 整数；「落地成本」维度按反向口径打分：成本越低、分值越高。
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFont

# 配色（克制、可打印）
BG = (255, 255, 255)
GRID = (200, 200, 200)
AXIS = (170, 170, 170)
FILL = (52, 100, 170, 70)
LINE = (33, 71, 130)
TEXT = (40, 40, 40)
VAL = (180, 50, 45)


def load_font(size):
    for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(out_path, title, dims):
    labels = [d[0] for d in dims]
    values = [d[1] for d in dims]
    n = len(labels)

    size = 900
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)
    cx = cy = size // 2
    R = 270  # 雷达半径

    font_t = load_font(34)
    font_l = load_font(22)
    font_v = load_font(20)

    # 角度：从正上方开始，顺时针
    angles = [(-math.pi / 2 + 2 * math.pi * i / n) for i in range(n)]

    def pt(angle, r):
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    # 网格环（1-5）
    for ring in range(1, 6):
        r = R * ring / 5
        poly = [pt(a, r) for a in angles]
        draw.polygon(poly, outline=GRID)
    # 轴线
    for a in angles:
        draw.line([(cx, cy), pt(a, R)], fill=AXIS, width=1)

    # 数据多边形
    data_pts = [pt(a, R * v / 5) for a, v in zip(angles, values)]
    draw.polygon(data_pts, fill=FILL, outline=LINE)
    for p in data_pts:
        draw.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5],
                     fill=LINE, outline=BG)

    # 维度标签 + 分值
    for i, (a, label, v) in enumerate(zip(angles, labels, values)):
        lx, ly = pt(a, R + 46)
        bbox = draw.textbbox((0, 0), label, font=font_l)
        w = bbox[2] - bbox[0]
        cos_a = math.cos(a)
        anchor_x = lx - (w / 2 if abs(cos_a) < 0.3 else (w if cos_a > 0 else 0))
        draw.text((anchor_x, ly - 14), label, fill=TEXT, font=font_l)
        vx, vy = pt(a, R * v / 5)
        draw.text((vx + 8, vy - 26), str(v), fill=VAL, font=font_v)

    # 标题
    tb = draw.textbbox((0, 0), title, font=font_t)
    draw.text((cx - (tb[2] - tb[0]) / 2, 28), title, fill=TEXT, font=font_t)
    # 口径注记
    note = "分值 1-5；落地成本为反向口径（成本越低分越高）"
    nb = draw.textbbox((0, 0), note, font=font_v)
    draw.text((cx - (nb[2] - nb[0]) / 2, size - 48), note,
              fill=(120, 120, 120), font=font_v)

    img.convert("RGB").save(out_path, "PNG")


def main():
    out_path = sys.argv[1]
    title = sys.argv[2]
    dims = []
    for item in sys.argv[3:]:
        label, val = item.split("=")
        v = int(val)
        if not 1 <= v <= 5:
            raise ValueError("分值必须为 1-5: %s" % item)
        dims.append((label, v))
    render(out_path, title, dims)
    print("saved:", out_path)


if __name__ == "__main__":
    main()
