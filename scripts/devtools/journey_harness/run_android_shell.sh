#!/usr/bin/env bash
# Android backend GJ01 最小壳：boot AVD → 装 APK → 启动 App → 截图/logcat 证据。
# 基线边界（诚实声明）：只验证 App 可启动并留证，UI 步进 unsupported（Flutter
# 语义树需无障碍激活，uiautomator 不可见）。任何一步失败都非零退出。
# 用法： bash scripts/devtools/journey_harness/run_android_shell.sh [apk路径]
#   不传 apk 时自动构建 debug APK（耗时约 5-15 分钟）。
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
APK="${1:-$REPO/mobile/build/app/outputs/flutter-apk/app-debug.apk}"

if [ ! -f "$APK" ]; then
  echo "[run_android_shell] 未找到 APK，开始构建 debug APK..."
  (cd "$REPO/mobile" && flutter build apk --debug --dart-define=API_BASE_URL=http://10.0.2.2:8080)
fi

PY11=/opt/homebrew/bin/python3.11
[ -x "$PY11" ] || PY11=python3
cd "$HERE"
"$PY11" run_journey.py --journey GJ01 --backend android --apk "$APK" --avd "${AVD_NAME:-Medium_Phone_API_36.1}"
