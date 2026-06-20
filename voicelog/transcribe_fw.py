#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 faster_whisper.WhisperModel(CTranslate2 后端)、numpy；读 model/device 配置
[OUTPUT]: 对外提供 FasterWhisper 类(transcribe(wav_f32_16k, language, prompt) -> str)
[POS]: Windows/跨平台转写后端——与 macOS 的 mlx_whisper 对等。被 voicelog_win.py 注入到管线。
       接口契约与 mlx_whisper.transcribe 一致(吃 16k float32 单声道,吐文本),让管线对引擎无感。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md

设计:懒加载(首次转写才建模型,首启不卡)。有 N 卡走 cuda/float16,否则 cpu/int8(更快更省)。
"""
import numpy as np

DEFAULT_MODEL = "Systran/faster-whisper-large-v3"  # turbo 想更快可换 "deepdml/faster-whisper-large-v3-turbo-ct2"


class FasterWhisper:
    def __init__(self, model: str = DEFAULT_MODEL, device: str = "auto",
                 compute_type: str = "auto", download_root: str | None = None):
        self.model_name = model or DEFAULT_MODEL
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self._model = None
        self.last_err = ""

    # ---------------- 懒加载:首次转写时才付加载/下载代价 ----------------
    def _load(self):
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel
        # 设备/精度自适应:优先 cuda(float16),失败回退 cpu(int8)——int8 在 CPU 上最快且占内存小。
        tries = []
        if self.device in ("auto", "cuda"):
            tries.append(("cuda", "float16" if self.compute_type == "auto" else self.compute_type))
        tries.append(("cpu", "int8" if self.compute_type == "auto" else self.compute_type))
        last = None
        for dev, ct in tries:
            try:
                self._model = WhisperModel(self.model_name, device=dev,
                                           compute_type=ct, download_root=self.download_root)
                self.device, self.compute_type = dev, ct
                return self._model
            except Exception as e:
                last = e
        raise last  # cpu 都建不起来才真失败

    def ready(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except Exception:
            return False

    # ---------------- 转写:接口与 mlx_whisper.transcribe 对齐 ----------------
    def transcribe(self, wav: np.ndarray, language: str | None = None,
                   initial_prompt: str | None = None) -> str:
        try:
            model = self._load()
            audio = np.ascontiguousarray(wav, dtype=np.float32)
            segments, _ = model.transcribe(
                audio, language=language or None, initial_prompt=initial_prompt,
                beam_size=1,                      # 实时优先速度
                vad_filter=False,                 # 我们自己已用 silero 切句+三道门,不重复
                condition_on_previous_text=False, # 防复读式幻觉滚雪球(与 mac 端一致)
            )
            return "".join(s.text for s in segments).strip()
        except Exception as e:
            self.last_err = f"{type(e).__name__}: {e}"
            raise
