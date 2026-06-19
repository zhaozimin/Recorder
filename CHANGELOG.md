# Changelog

版本规则：小改 +0.1，大改 +1.0。

## v0.1.0 — 2026-06-18
首个版本。本地实时语音日志,音频绝不写盘。
- DJI Mic Mini → sounddevice 采集 → Silero VAD 按句切 → 本地 Whisper(large-v3 via MLX) 转写 → Markdown 笔记
- 菜单栏常驻(无 Dock):今日计数、暂停/继续、打开今天笔记、退出
- 术语偏置(`initial_prompt`) + 词边界纠错(`replace`,Cloud→Claude 不误伤 iCloud) + 幻觉过滤(字幕水印套话)
- **时区实时切换**(菜单栏子菜单,即时生效并写回配置)
- **输出目录实时选择**(菜单栏原生文件夹选择框)
- 外置盘掉线自动回退内置盘,菜单栏 🟠 提示,绝不丢字
- 跨环境部署:uv hermetic CPython(绕开 Homebrew libexpat ABI 坑)、aria2 续传下载模型(绕开 hf_xet 卡死)
