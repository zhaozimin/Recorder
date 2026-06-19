# VoiceLog · 本地实时语音日志

DJI Mic Mini → 本地 Whisper 实时转写 → Markdown 笔记（可接 Obsidian）。
macOS 菜单栏小程序,后台常驻,无 Dock 图标,**不保留任何音频**。

## 文件清单
- `voicelog_menubar.py` — 主程序(采集 + VAD + 转写 + 术语纠错 + 幻觉过滤 + 菜单栏)
- `config.yaml` — 配置(模型/设备/时区/分句/术语偏置/纠错/掉线回退)
- `requirements.txt` — Python 依赖
- `claude_prompt.md` — 夜间让 Claude 整理日志/推文的提示词
- `install.sh` — 一键安装脚本
- `../launchd/com.six.voicelog.menubar.plist` — 开机自启配置

## 工作原理(一句话)
麦克风音频流 → Silero VAD 识别「一句话」的起止 → 该句结束就把这段音频(仅在内存中)交给
mlx-whisper(本地 large-v3)转成文字 → 术语纠错 + 幻觉过滤 → 追加写入当天笔记 → 音频缓冲立即释放,从不写盘。
**不是逐字流式**:whisper 是整句批处理,停顿约 700ms 判定一句结束后才落字(延迟 ~1-2 秒,日志场景的正确颗粒度)。

## 安装(在 Mac 上)
```bash
bash "$HOME/Claude/Projects/Voice recording and monitoring/voicelog/install.sh"
```
脚本会:选 ≥3.10 的 Python(系统自带 3.9 不合格)→ 建虚拟环境 `~/voicelog-venv` → 装依赖 → 装开机自启。

> 实测踩坑备忘(macOS 26 / M4 Pro):
> - Homebrew 的 `python@3.12` bottle 有 **libexpat ABI 断裂**,`ensurepip` 会挂 → 改用 **uv** 拉 hermetic CPython 3.12,自包含、免疫 brew 升级。
> - large-v3 经 HF 的 **Xet 客户端下载会卡死**;若 `mlx_whisper` 卡在 0%,改用 `aria2c` 直拉权重到本地目录,`config.yaml` 的 `model` 填该目录绝对路径即可绕开。
> - 匿名下载会被限速,建议 `hf auth login` 用一个免费 read token(仅下载时用,跑起来离线不需要)。

装完还需手动两步:① 先手动跑一次主程序触发并授予麦克风权限;② `launchctl load` 启用自启。详见 `install.sh` 末尾提示。

## 配置要点(`config.yaml`)
- `vault_path`:文字稿写哪。默认本项目「声音日志/」;接 Obsidian 改成 vault 路径。
- `model`:本地模型目录绝对路径(large-v3,最准);或填 HF 仓库名让它联网下。
- `input_device`:麦克风。`null`=系统默认,或填编号/名字片段(DJI 接收器真名是 `"Wireless Mic Rx"`)。
- `language`:`zh`,中英混说可留空自动检测。
- `timezone`:**留空=跟随系统本地(出差跟着走);或填 IANA 名(`Asia/Shanghai` 等)钉死**。决定时间戳与「当天」归属。
- `initial_prompt`:术语偏置表,抬高 `Claude/Obsidian/MCP…` 的先验(修同音/混说误识),顺带压繁体。
- `replace`:精确纠错(识别结果→正确写法)。ASCII 词按词边界匹配(`Cloud→Claude` 不误伤 iCloud/Cloudflare)。
- `drop_phrases`:额外要丢弃的「幻觉套话」(whisper 在噪声上冒的字幕水印)。
- `fallback_path`:vault 在外置盘上、盘掉线时,转写改写到这里(内置盘),**一个字都不丢**;菜单栏转 🟠 提示。

## 菜单栏图标
🎙 正常 · ⏸ 已暂停 · 🟠 外置盘掉线(写到备用盘) · ⚠️ 出错(看 `logs/err.log`)

## 夜间整理(可选,会用云端 Claude)
让 Claude 读当天 `声音日志/YYYY-MM-DD.md`,按 `claude_prompt.md` 生成「产品日志 / 开发者日志 / 推文」。
注意:这一步会把当天**文字**发给 Claude 云端;核心录音转写永远本地、永不上传。
