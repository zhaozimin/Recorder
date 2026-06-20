#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 读 voicelog/assets/icon.png(白色透明 logo)
[OUTPUT]: 生成 packaging/windows/VoiceLog.ico(多尺寸:深色圆角方 + 白 logo)
[POS]: Windows 打包资源生成器;仅打包期运行。供 PyInstaller(.exe 图标)与 Inno Setup 使用。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

与 macOS 的 make_icon.py 同源设计(深色 squircle + 白 logo),但输出 .ico 多尺寸。
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "voicelog" / "assets" / "icon.png"
OUT = Path(__file__).resolve().parent / "VoiceLog.ico"

BASE = 256
SS = 4
N = BASE * SS
TOP, BOT = (0x28, 0x28, 0x2d), (0x15, 0x15, 0x17)


def main() -> None:
    mask = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, N - 1, N - 1], radius=int(N * 0.22), fill=255)
    grad = Image.new("RGB", (1, N))
    for y in range(N):
        t = y / (N - 1)
        grad.putpixel((0, y), tuple(round(TOP[i] + (BOT[i] - TOP[i]) * t) for i in range(3)))
    canvas = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    canvas.paste(grad.resize((N, N)).convert("RGBA"), (0, 0), mask)
    logo = Image.open(SRC).convert("RGBA")
    lw = int(N * 0.66)
    lh = round(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    canvas.alpha_composite(logo, ((N - lw) // 2, (N - lh) // 2))
    master = canvas.resize((BASE, BASE), Image.LANCZOS)
    master.save(OUT, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
