#!/usr/bin/env bash
# macOS backend journey：复用既有 mobile/integration_test/macos_journey_test.dart
# （访客全流程 finder 级驱动）。flutter test 失败/超时 => 非零退出。
# 用法： bash scripts/devtools/journey_harness/run_macos_journey.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"

PY11=/opt/homebrew/bin/python3.11
[ -x "$PY11" ] || PY11=python3
cd "$HERE"
"$PY11" run_journey.py --journey GJ01 --backend macos --macos-test-file integration_test/macos_journey_test.dart
