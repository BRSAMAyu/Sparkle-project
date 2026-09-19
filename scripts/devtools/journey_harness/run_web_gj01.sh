#!/usr/bin/env bash
# GJ01 Web backend 一键运行：静态服务 Flutter Web 构建产物 → 跑 GJ01 journey。
# 用法： bash scripts/devtools/journey_harness/run_web_gj01.sh [port]
# 前置： mobile/build/web 已存在（flutter build web --release）；主栈网关 :8080 在跑。
# 注意：本机沙箱环境 dart2js 会被 OOM-kill（rc=137），构建需在沙箱外执行：
#   cd mobile && flutter build web --release --dart-define=API_BASE_URL=http://localhost:8080
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
PORT="${1:-8437}"
WEB_DIR="$REPO/mobile/build/web"

if [ ! -f "$WEB_DIR/index.html" ]; then
  echo "[run_web_gj01] 未找到 $WEB_DIR/index.html —— 先构建（见脚本头注释）"
  exit 2
fi

python3 "$HERE/serve_web.py" "$PORT" "$WEB_DIR" &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
sleep 1

PY11=/opt/homebrew/bin/python3.11
[ -x "$PY11" ] || PY11=python3
cd "$HERE"
"$PY11" run_journey.py --journey GJ01 --backend web --app-url "http://127.0.0.1:$PORT/"
