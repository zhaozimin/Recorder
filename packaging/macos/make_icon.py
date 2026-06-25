#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 读 voicelog/assets/logo_src.png(3D 写实彩色母版,自带深色背景)
[OUTPUT]: VoiceLog_iconmaster.png(1024 满铺圆角 squircle) + VoiceLog.iconset/* + VoiceLog.icns
[POS]: macOS 打包图标生成器;仅打包期运行,非运行依赖。一条命令重生 .icns。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

设计:新品牌图本身即成品(麦克风+无限符号 3D 渲染,深色影棚背景到边),
故管线由「白 logo 合成深色底」反转为「成品母版裁满铺圆角」。
Apple squircle 圆角半径 ≈ 0.2237 * 边长;在 2x 母版上裁切后降采样,圆角抗锯齿自然。
"""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "voicelog" / "assets" / "logo_src.png"
OUTDIR = Path(__file__).resolve().parent
MASTER = OUTDIR / "VoiceLog_iconmaster.png"
ICONSET = OUTDIR / "VoiceLog.iconset"
ICNS = OUTDIR / "VoiceLog.icns"

RADIUS_RATIO = 0.2237                     # Apple 连续曲率圆角比例
SPECS = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2),
         (256, 1), (256, 2), (512, 1), (512, 2)]


def squircle(img: Image.Image) -> Image.Image:
    """满铺圆角:整图裁成 squircle,角外透明。"""
    n = img.width
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, n - 1, n - 1], radius=round(RADIUS_RATIO * n), fill=255)
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def main() -> None:
    src = Image.open(SRC).convert("RGBA")
    if src.width != src.height:
        s = min(src.width, src.height)                       # 兜底:非方图居中裁方
        src = src.crop(((src.width - s) // 2, (src.height - s) // 2,
                        (src.width + s) // 2, (src.height + s) // 2))
    sq = squircle(src)                                       # 母版分辨率下的 squircle

    sq.resize((1024, 1024), Image.LANCZOS).save(MASTER)
    print("wrote", MASTER)

    ICONSET.mkdir(exist_ok=True)
    for base, scale in SPECS:
        px = base * scale
        name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
        sq.resize((px, px), Image.LANCZOS).save(ICONSET / name)
    subprocess.run(["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)], check=True)
    print("wrote", ICNS)


if __name__ == "__main__":
    main()
