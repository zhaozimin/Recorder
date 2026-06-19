#!/bin/bash
# VoiceLog 一键安装（在你的 Mac 上运行）
set -e

DIR="$HOME/Claude/Projects/Voice recording and monitoring"
VENV="$HOME/voicelog-venv"
PLIST="com.six.voicelog.menubar.plist"

echo "==> 0/3 选择 Python（要求 >= 3.10；系统自带的 3.9 不合格）"
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  p="$(command -v "$cand" 2>/dev/null)" || continue
  ver="$("$p" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null)" || continue
  if [ "$ver" -ge 310 ] 2>/dev/null; then PY="$p"; break; fi
done
if [ -z "$PY" ]; then
  echo "    未发现 >=3.10 的 Python。请先安装：brew install python@3.12"
  exit 1
fi
echo "    使用 $PY（$("$PY" --version 2>&1)）"

echo "==> 1/3 创建虚拟环境并安装依赖（首次会下载 mlx/torch 等，约几百 MB~1GB，请耐心）"
"$PY" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r "$DIR/voicelog/requirements.txt"

echo "==> 2/3 安装开机自启 (launchd)"
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$DIR/voicelog/logs"   # launchd 的 StandardOut/ErrorPath 父目录必须先存在，否则日志静默丢失
# 从模板生成 plist：把占位符替换成本机实际路径（仓库里不含写死的个人路径）
sed -e "s#__PYTHON__#$VENV/bin/python#g" \
    -e "s#__SCRIPT__#$DIR/voicelog/voicelog_menubar.py#g" \
    -e "s#__LOGDIR__#$DIR/voicelog/logs#g" \
    "$DIR/launchd/$PLIST.template" > "$HOME/Library/LaunchAgents/$PLIST"

echo ""
echo "==> 3/3 完成自动部分。还需你手动两步："
echo ""
echo "  ① 先手动跑一次以授予【麦克风】权限（首次会弹窗，去 系统设置→隐私与安全性→麦克风 打勾）："
echo "       source \"$VENV/bin/activate\" && python \"$DIR/voicelog/voicelog_menubar.py\""
echo "     右上角出现 🎙 后，对着麦说句话测试；确认 OK 后 Ctrl-C 退出。"
echo ""
echo "  ② 启用后台自启（以后开机自动常驻）："
echo "       launchctl load \"$HOME/Library/LaunchAgents/$PLIST\""
echo ""
echo "  （可选）让 Mac mini 永不休眠： sudo pmset -a sleep 0 disksleep 0"
echo ""
echo "完成后，文字稿会实时写进： $(grep vault_path "$DIR/voicelog/config.yaml" | head -1)"
