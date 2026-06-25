#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 读 voicelog/assets/logo_src.png(3D 写实彩色母版,自带深色背景)
[OUTPUT]: 生成 packaging/windows/VoiceLog.ico(多尺寸满铺圆角)
[POS]: Windows 打包图标生成器;仅打包期运行。供 PyInstaller(.exe)与 Inno Setup 使用。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

与 macOS 的 make_icon.py 同源:成品母版裁满铺圆角(Apple squircle 风),输出 .ico 多尺寸。
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "voicelog" / "assets" / "logo_src.png"
OUT = Path(__file__).resolve().parent / "VoiceLog.ico"

RADIUS_RATIO = 0.2237
SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    img = Image.open(SRC).convert("RGBA")
    if img.width != img.height:
        s = min(img.width, img.height)
        img = img.crop(((img.width - s) // 2, (img.height - s) // 2,
                        (img.width + s) // 2, (img.height + s) // 2))
    n = img.width
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, n - 1, n - 1], radius=round(RADIUS_RATIO * n), fill=255)
    sq = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    sq.paste(img, (0, 0), mask)
    sq.resize((256, 256), Image.LANCZOS).save(OUT, sizes=SIZES)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
