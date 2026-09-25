#!/usr/bin/env bash
# J-01 First-3-Minutes measurement runner (measurement infrastructure only).
#
# Reproduces the J-01 evidence: 5 personas x 2 routes against the REAL
# backend on the macOS desktop target, real wall-clock timings, screenshots.
# own_goal: one process per persona — every pass is a TRUE cold start.
# example:  one process, 5 persona passes with UI logout between.
#
# Prerequisites (verified 2026-09-25/26 on this machine):
#   * Go gateway :8080 healthy (curl localhost:8080/health)
#   * docker: sparkle_db / sparkle_redis / sparkle_minio up
#   * flutter macOS desktop enabled
#   * one-time worktree setup (gitignored artifacts):
#       make proto-gen
#       printf '#include "ephemeral/Flutter-Generated.xcconfig"\n' \
#         > mobile/macos/Flutter/Flutter-Debug.xcconfig
#       printf '#include "ephemeral/Flutter-Generated.xcconfig"\n' \
#         > mobile/macos/Flutter/Flutter-Release.xcconfig
#
# Usage: bash scripts/devtools/run_j01_first3_measurement.sh [repo-root]
set -euo pipefail

REPO="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
EVIDENCE="$REPO/v3/09_evidence/j01_first3"
LOGS="$EVIDENCE/logs"

mkdir -p "$LOGS" "$EVIDENCE/screenshots/own_goal" "$EVIDENCE/screenshots/example"

echo "== health check =="
curl -s -o /dev/null -w "gateway :8080 -> %{http_code}\n" --max-time 5 http://localhost:8080/health

cd "$REPO/mobile"

echo "== route own_goal: 5 personas, one cold process each =="
for i in 0 1 2 3 4; do
  echo "--- persona pass $i ---"
  flutter test integration_test/first3_measurement_test.dart -d macos \
    --dart-define=J01_ROUTE=own_goal \
    --dart-define=J01_PASS=$i \
    --dart-define=J01_SHOT_DEST="$EVIDENCE/screenshots/own_goal" \
    2>&1 | tee "$LOGS/run_own_goal_pass$i.log" || echo "pass $i had soft failures (see log)"
done

echo "== route example: one process, 5 persona passes (DEMO_MODE build flag) =="
# DEMO_MODE=true is the only way to reach an "example" experience today —
# the UI exposes no such entry. That dependency is itself a J-01 finding.
flutter test integration_test/first3_measurement_test.dart -d macos \
  --dart-define=J01_ROUTE=example \
  --dart-define=DEMO_MODE=true \
  --dart-define=J01_PASS=all \
  --dart-define=J01_SHOT_DEST="$EVIDENCE/screenshots/example" \
  2>&1 | tee "$LOGS/run_example.log" || echo "example run had soft failures (see log)"

echo "== done =="
grep -h "J01_SUMMARY " "$LOGS"/run_*.log >/dev/null && echo "summaries present"
