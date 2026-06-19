#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VoiceLog · macOS 菜单栏实时语音日志
流程：DJI Mic Mini → sounddevice 实时采集 → Silero VAD 按句切 → mlx-whisper(本地 large-v3) 转写
      → 术语纠错 + 幻觉过滤 → 按配置时区写入当天笔记（外置盘掉线自动回退内置盘）
特点：音频转写后立即丢弃，绝不写盘；菜单栏小图标常驻，无 Dock、不抢前台。
配置见 config.yaml：模型/设备/时区/术语偏置(initial_prompt)/纠错表(replace)/掉线回退。
"""
import os
import re
import sys
import queue
import threading
import datetime
import subprocess
import traceback
from collections import deque
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import sounddevice as sd
import yaml
import rumps
import mlx_whisper
from silero_vad import load_silero_vad, VADIterator

# ---------------- 读取配置 ----------------
BASE = Path(__file__).resolve().parent
CFG = yaml.safe_load((BASE / "config.yaml").read_text(encoding="utf-8")) or {}

VERSION = "0.1.0"

SR = 16000
BLOCK = 512  # Silero v5 在 16k 采样率下要求每块正好 512 个采样
MODEL = CFG.get("model", "mlx-community/whisper-large-v3-turbo")
LANG = CFG.get("language") or None  # "zh" / "auto"(留空) 等
MAX_UTT_SEC = float(CFG.get("max_utterance_sec", 30))
MIN_SILENCE_MS = int(CFG.get("min_silence_ms", 700))
INPUT_DEVICE = CFG.get("input_device", None)  # None=系统默认；可填编号或名字片段(如 "DJI")
VAULT = Path(os.path.expanduser(CFG.get("vault_path", str(BASE.parent / "声音日志"))))
FALLBACK = Path(os.path.expanduser(CFG.get("fallback_path", "~/voicelog-fallback")))
REPLACE = CFG.get("replace") or {}
INITIAL_PROMPT = CFG.get("initial_prompt", "以下是简体中文普通话的日常口语记录。") or None
PREROLL = 8  # 句首预留约 0.25s，避免吃掉第一个字


def log_dir() -> Path:
    d = BASE / "logs"
    d.mkdir(exist_ok=True)
    return d


def append_err(msg: str) -> None:
    try:
        with (log_dir() / "err.log").open("a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now()}] {msg}")
    except Exception:
        pass


# ---------------- 时区 ----------------
# timezone 留空 = 跟随系统本地（macOS 开了自动时区，人飞到哪就记哪的时间）；
# 或填 IANA 名（"Asia/Shanghai" / "America/New_York" / "Europe/London"）钉死某个时区。
try:
    _TZ = ZoneInfo(CFG["timezone"]) if CFG.get("timezone") else None
except Exception:
    append_err(f"无效时区 {CFG.get('timezone')!r}，改用系统本地")
    _TZ = None


def now() -> datetime.datetime:
    """统一的“现在”：决定时间戳与当天笔记的归属日。跨时区出差时由 config.timezone 控制。"""
    return datetime.datetime.now(_TZ)


# 菜单栏「时区」子菜单里列出的快捷选项（空串=跟随系统本地）；可在 config.timezone_choices 自定义
TZ_CHOICES = CFG.get("timezone_choices") or [
    "", "Asia/Shanghai", "Asia/Tokyo", "Asia/Singapore",
    "Europe/London", "America/New_York", "America/Los_Angeles",
]


def set_timezone(tz: str) -> bool:
    """运行时切换时区：改全局 _TZ（立即影响后续 now()）并写回 config.yaml（重启也记住）。"""
    global _TZ
    try:
        _TZ = ZoneInfo(tz) if tz else None
    except Exception:
        append_err(f"切换时区失败：{tz!r}")
        return False
    try:  # 只替换 timezone 那一行，保留文件里其余注释
        cfg = BASE / "config.yaml"
        text = cfg.read_text(encoding="utf-8")
        new = re.sub(r"(?m)^timezone:.*$", f'timezone: "{tz}"', text)
        if new != text:
            cfg.write_text(new, encoding="utf-8")
    except Exception:
        append_err("写回时区失败：" + traceback.format_exc().splitlines()[-1])
    return True


# ---------------- 输出目录（运行时可改） ----------------
def choose_folder():
    """弹原生「选择文件夹」对话框，返回所选目录绝对路径；取消/失败返回 None。"""
    script = 'POSIX path of (choose folder with prompt "选择语音日志保存文件夹")'
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=120)
        return r.stdout.strip() or None
    except Exception:
        append_err("choose_folder: " + traceback.format_exc().splitlines()[-1])
        return None


def set_vault(path: str) -> bool:
    """运行时切换输出目录：改全局 VAULT（立即影响后续写入）并写回 config.yaml。"""
    global VAULT
    try:
        v = Path(os.path.expanduser(path))
        v.mkdir(parents=True, exist_ok=True)
        VAULT = v
    except Exception:
        append_err(f"设置保存目录失败：{path!r}")
        return False
    try:  # 只替换 vault_path 那一行，保留注释
        cfg = BASE / "config.yaml"
        text = cfg.read_text(encoding="utf-8")
        new = re.sub(r"(?m)^vault_path:.*$", f'vault_path: "{path}"', text)
        if new != text:
            cfg.write_text(new, encoding="utf-8")
    except Exception:
        append_err("写回 vault_path 失败：" + traceback.format_exc().splitlines()[-1])
    return True


def resolve_device(dev):
    """把 config 里的 input_device 解析成 sounddevice 能用的编号/None。"""
    if dev is None or dev == "":
        return None
    try:
        return int(dev)  # 直接是编号
    except (ValueError, TypeError):
        pass
    for i, d in enumerate(sd.query_devices()):  # 按名字片段匹配
        if d.get("max_input_channels", 0) > 0 and str(dev).lower() in d["name"].lower():
            return i
    append_err(f"未找到匹配输入设备：{dev}，改用系统默认")
    return None


# ---------------- 幻觉过滤 ----------------
# whisper 在静音/噪声上会“高置信度”吐出训练集里的字幕水印（实测 no_speech_prob 恒为 0、
# avg_logprob 还很高，概率信号根本识别不了）—— 唯一可靠的办法是套话黑名单 + 上游 VAD 门控。
_HALLUCINATIONS = {
    "优优独播剧场YoYo Television Series Exclusive",
    "请不吝点赞 订阅 转发 打赏支持明镜与点点栏目",
    "明镜与点点栏目",
    "字幕由Amara.org社区提供",
    "本字幕由观众提供",
    "请订阅我的频道",
    "谢谢观看",
    "谢谢大家",
    "下集再见",
}


def _norm(s: str) -> str:
    """归一化用于幻觉比对：只留字母数字汉字、转小写，抹掉空白与标点的差异。"""
    return "".join(ch.lower() for ch in s if ch.isalnum())


# 短套话（<8 归一字符）只做整句精确匹配，避免误杀真说的“谢谢大家…”；
# 长水印做子串匹配，容忍 whisper 前后多带的标点/空白。
_DROP_EXACT = {_norm(s) for s in _HALLUCINATIONS | set(CFG.get("drop_phrases") or [])}
_DROP_SUB = {d for d in _DROP_EXACT if len(d) >= 8}


def is_junk(text: str) -> bool:
    n = _norm(text)
    return bool(n) and (n in _DROP_EXACT or any(d in n for d in _DROP_SUB))


def apply_replace(text: str) -> str:
    """专名纠错。ASCII 词用词边界匹配，避免 Cloud→Claude 误伤 iCloud/Cloudflare 等更大的英文词。"""
    for k, v in REPLACE.items():
        if k.isascii() and k.strip():
            text = re.sub(rf"(?<![A-Za-z]){re.escape(k)}(?![A-Za-z])", v, text)
        else:
            text = text.replace(k, v)
    return text


# ---------------- 写入（外置盘掉线自动回退内置盘，绝不丢字） ----------------
def _ext_mount(p: Path):
    """p 若在外置卷 /Volumes/X 下，返回挂载点 /Volumes/X；内置路径返回 None。"""
    parts = p.parts
    return Path("/Volumes") / parts[2] if len(parts) >= 3 and parts[1] == "Volumes" else None


def _usable(base: Path) -> bool:
    """外置卷必须真的挂载着才算可用 —— 否则会在 /Volumes 下建幽灵目录并静默丢数据。"""
    m = _ext_mount(base)
    return m is None or m.is_mount()


def write_line(text: str) -> str:
    """把一行写进当天笔记；首选 vault，外置盘不可用时回退内置盘。返回实际落点标记。"""
    ts = now()
    line = f"- **{ts:%H:%M}** {text}\n"
    for base, tag in ((VAULT, "vault"), (FALLBACK, "fallback")):
        if not _usable(base):
            continue
        try:
            note = base / f"{ts:%Y-%m-%d}.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            if not note.exists():
                note.write_text(f"# {ts:%Y-%m-%d} 语音日志\n\n", encoding="utf-8")
            with note.open("a", encoding="utf-8") as f:
                f.write(line)
            return tag
        except Exception:
            append_err(f"写入 {base} 失败: " + traceback.format_exc().splitlines()[-1])
    return "lost"


# ---------------- 录音 + 转写线程 ----------------
class Recorder(threading.Thread):
    def __init__(self, state: dict):
        super().__init__(daemon=True)
        self.state = state
        self.q: queue.Queue = queue.Queue()
        self.muted = False
        self.vad = load_silero_vad()
        self.device = resolve_device(INPUT_DEVICE)

    def _callback(self, indata, frames, time_info, status):
        if status:
            self.state["status"] = str(status)
        if not self.muted:
            self.q.put(indata[:, 0].copy())  # 取单声道，拷贝出回调缓冲

    def run(self):
        while True:
            try:
                self._stream_loop()
            except Exception:
                self.state["err"] = traceback.format_exc().splitlines()[-1]
                append_err(traceback.format_exc())
                sd.sleep(3000)  # 设备掉线/出错 → 等 3 秒重连

    def _stream_loop(self):
        vad_iter = VADIterator(
            self.vad, sampling_rate=SR,
            min_silence_duration_ms=MIN_SILENCE_MS, speech_pad_ms=100,
        )
        preroll = deque(maxlen=PREROLL)
        buf, triggered = [], False
        self.state["err"] = ""
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                            blocksize=BLOCK, device=self.device,
                            callback=self._callback):
            self.state["live"] = True
            while True:
                x = self.q.get()
                preroll.append(x)
                flag = vad_iter(x, return_seconds=False)
                if flag and "start" in flag:
                    triggered = True
                    buf = list(preroll)
                elif triggered:
                    buf.append(x)

                end_now = bool(flag and "end" in flag)
                too_long = len(buf) * BLOCK > MAX_UTT_SEC * SR
                if triggered and (end_now or too_long):
                    triggered = False
                    utt = np.concatenate(buf) if buf else None
                    buf = []
                    if too_long and not end_now:
                        vad_iter.reset_states()  # 强制切句后重置，避免漏掉后续语音
                    if utt is not None:
                        self._transcribe(utt)

    def _transcribe(self, utt: np.ndarray):
        try:
            result = mlx_whisper.transcribe(
                utt, path_or_hf_repo=MODEL, language=LANG,
                initial_prompt=INITIAL_PROMPT,      # 简体偏置，压繁体
                condition_on_previous_text=False,   # 防复读式幻觉滚雪球
            )
            text = (result.get("text") or "").strip()
        except Exception:
            append_err("transcribe: " + traceback.format_exc())
            return
        if not text or is_junk(text):  # 空串 / 字幕水印幻觉 —— 直接丢弃，不污染日志
            return
        text = apply_replace(text)     # 专名纠错（ASCII 词按词边界，安全）

        sink = write_line(text)        # 外置盘掉线会自动回退内置盘
        if sink == "lost":
            return
        self.state["count"] += 1
        self.state["last"] = text
        self.state["sink"] = sink
        # utt 在此返回后即被回收 —— 音频从不落盘


# ---------------- 菜单栏 ----------------
class VoiceLogApp(rumps.App):
    def __init__(self):
        super().__init__("🎙", quit_button=None)
        self.state = {"count": 0, "last": "", "err": "", "live": False,
                      "status": "", "sink": "vault"}
        self.rec = Recorder(self.state)
        self.rec.start()

        self.count_item = rumps.MenuItem("今日已记：0 条")  # 存引用，标题会变
        self.toggle_item = rumps.MenuItem("暂停录音", callback=self.toggle)
        self.tz_menu = self._build_tz_menu()                # 「时区」子菜单，随时切换
        self.vault_item = rumps.MenuItem(self._vault_title(), callback=self.pick_vault)
        self.menu = [
            self.count_item,
            self.toggle_item,
            self.tz_menu,
            self.vault_item,
            rumps.MenuItem("打开今天的笔记", callback=self.open_note),
            None,  # 分隔线
            rumps.MenuItem(f"VoiceLog v{VERSION}"),  # 版本（无回调=不可点）
            rumps.MenuItem("退出", callback=self.quit_app),
        ]

    @staticmethod
    def _vault_title() -> str:
        parts = VAULT.parts
        short = "/".join(parts[-2:]) if len(parts) >= 2 else str(VAULT)
        return f"保存位置 …/{short}（点此更改）"

    def pick_vault(self, _):
        p = choose_folder()
        if not p or not set_vault(p):
            return
        self.vault_item.title = self._vault_title()

    @staticmethod
    def _tz_title(tz: str) -> str:
        return f"时区：{tz or '跟随系统'}"

    def _build_tz_menu(self):
        cur = CFG.get("timezone") or ""
        menu = rumps.MenuItem(self._tz_title(cur))
        for tz in TZ_CHOICES:
            item = rumps.MenuItem(tz or "跟随系统", callback=self.pick_tz)
            item.state = 1 if tz == cur else 0  # 当前时区打勾
            menu.add(item)
        return menu

    def pick_tz(self, sender):
        tz = "" if sender.title == "跟随系统" else sender.title
        if not set_timezone(tz):
            return
        for item in self.tz_menu.values():       # 重置勾选
            item.state = 1 if item.title == sender.title else 0
        self.tz_menu.title = self._tz_title(tz)  # 父项显示当前时区

    @rumps.timer(2)
    def tick(self, _):
        on_fallback = self.state.get("sink") == "fallback"
        tag = "（备用盘）" if on_fallback else ""
        self.count_item.title = f"今日已记：{self.state['count']} 条{tag}"
        if self.state["err"]:
            self.title = "⚠️"
        elif on_fallback:
            self.title = "🟠"  # 外置盘掉线，正写内置备用盘
        elif self.rec.muted:
            self.title = "⏸"
        else:
            self.title = "🎙"

    def toggle(self, sender):
        self.rec.muted = not self.rec.muted
        sender.title = "继续录音" if self.rec.muted else "暂停录音"

    def open_note(self, _):
        note = VAULT / f"{now():%Y-%m-%d}.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        if not note.exists():
            note.write_text("", encoding="utf-8")
        subprocess.run(["open", str(note)])

    def quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    VoiceLogApp().run()
