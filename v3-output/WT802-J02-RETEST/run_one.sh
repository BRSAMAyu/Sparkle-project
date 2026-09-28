#!/usr/bin/env bash
# wt802 J-02 retest — single timed-run executor with wt801 mutual-avoidance gate.
# Usage: bash run_one.sh <name> <J02_PASS> <J02_LEGS>
# Gate: refuses to start while a bench/e08 process is active (protocol: timed
# runs mutually pollute API timings). Never touches wt801 processes/artifacts.
set -euo pipefail

NAME="${1:?name}"
PASS="${2:?J02_PASS}"
LEGS="${3:?J02_LEGS}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_ID="$(cat /tmp/wt802_run_id.txt)"
EVID="$REPO/v3-output/WT802-J02-RETEST/evidence/$RUN_ID"

# ── wt801 mutual-avoidance gate (bench families: e08/q06/any wt801 worker) ──
if pgrep -f 'bench_ai_stack|q06_perf_bench|wt801|e08' >/dev/null 2>&1; then
  echo "[wt802] GATE BLOCKED: wt801 bench still active ($(pgrep -f 'bench_ai_stack|q06_perf_bench|wt801|e08' | tr '\n' ' '))"
  exit 42
fi
echo "[wt802] gate clear — starting timed run $NAME (PASS=$PASS LEGS=$LEGS) $(date '+%H:%M:%S')"

cd "$REPO/mobile"
flutter test integration_test/j02_fastpath_journey_test.dart -d macos \
  --dart-define=J02_PASS="$PASS" \
  --dart-define=J02_LEGS="$LEGS" \
  --dart-define=J02_SHOT_DEST="$EVID/screenshots" \
  --reporter expanded 2>&1 | tee "$EVID/logs/run_macos_$NAME.log"
rc=${PIPESTATUS[0]}
echo "[wt802] run $NAME finished rc=$rc $(date '+%H:%M:%S')"
exit "$rc"
