# -*- mode: python ; coding: utf-8 -*-
# ============================================================================
#  VoiceLog · Windows 打包配置 (PyInstaller, onedir → Inno Setup 出安装包)
#  入口 voicelog/voicelog_win.py(跨平台托盘版)。faster-whisper 转写 + pystray 托盘。
#  在 GitHub Actions windows-latest 上构建(见 .github/workflows/build-windows.yml)。
#  [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
# ============================================================================
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

SPEC_DIR = os.path.abspath(SPECPATH)                        # packaging/windows
PROJ = os.path.abspath(os.path.join(SPEC_DIR, "..", ".."))  # 仓库根
SRC = os.path.join(PROJ, "voicelog")

datas, binaries, hiddenimports = [], [], []
for pkg in ("faster_whisper", "ctranslate2", "silero_vad", "sounddevice",
            "speechbrain", "pystray", "PIL", "av"):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass  # av 等个别包缺失不致命

datas += [
    (os.path.join(SRC, "assets"), "assets"),
    (os.path.join(SRC, "config.example.yaml"), "."),
]

# 动态/懒加载导入:静态分析抓不到,显式补
hiddenimports += [
    "pystray._win32",                  # pystray 的 Windows 后端(按平台动态选,必须点名)
    "speechbrain.inference.speaker",   # speaker.py 函数内懒导入
    "transcribe_fw", "speaker", "i18n",
]
hiddenimports += collect_submodules("speechbrain")

a = Analysis(
    [os.path.join(SRC, "voicelog_win.py")],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["mlx", "mlx_whisper", "rumps", "AppKit", "Foundation", "objc",
              "PyObjCTools", "matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6",
              "IPython", "pytest", "notebook", "jupyter", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="VoiceLog",
          console=False, disable_windowed_traceback=False,
          icon=os.path.join(SPEC_DIR, "VoiceLog.ico"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="VoiceLog")
