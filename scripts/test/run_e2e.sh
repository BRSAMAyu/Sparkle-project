#!/usr/bin/env bash
# scripts/test/run_e2e.sh — Run Flutter integration tests on connected device
# Usage: DEVICE_ID=xxx bash scripts/test/run_e2e.sh [test_file]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
SCREENSHOT_DIR="$ROOT_DIR/artifacts/e2e/screenshots"
REPORT_DIR="$ROOT_DIR/artifacts/e2e/reports"
mkdir -p "$LOG_DIR" "$SCREENSHOT_DIR" "$REPORT_DIR"

log() { echo "[$(date '+%H:%M:%S')] [e2e] $*"; }

cd "$ROOT_DIR/mobile"

# ── 1. Detect device ──
DEVICE="${DEVICE_ID:-}"
if [ -z "$DEVICE" ]; then
  DEVICE=$(flutter devices 2>/dev/null | grep -E '(simulator|emulator|iphone|android)' | head -1 | awk '{print $1}' || true)
fi

if [ -z "$DEVICE" ]; then
  log "ERROR: No device found. Connect a simulator/emulator or set DEVICE_ID."
  log "  Available devices:"
  flutter devices 2>/dev/null || true
  exit 1
fi

log "Using device: $DEVICE"

# ── 2. Select test file(s) ──
TEST_TARGET="${1:-integration_test/}"
if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "integration_test/" ]; then
  TEST_TARGET="integration_test/"
fi

log "Running integration tests: $TEST_TARGET"

# ── 3. Set E2E test mode ──
export E2E_TEST_MODE="${E2E_TEST_MODE:-true}"
export LLM_PROVIDER="${LLM_PROVIDER:-mock}"

log "E2E_TEST_MODE=$E2E_TEST_MODE  LLM_PROVIDER=$LLM_PROVIDER"

# ── 4. Run tests ──
LOG_FILE="$LOG_DIR/flutter_e2e.log"
log "Running flutter test... (log: $LOG_FILE)"

if flutter test integration_test/ -d "$DEVICE" \
  --device-id="$DEVICE" \
  2>&1 | tee "$LOG_FILE"; then
  log "E2E tests PASSED."
  echo "e2e_pass=1" > "$REPORT_DIR/e2e_status.txt"
  echo "e2e_fail=0" >> "$REPORT_DIR/e2e_status.txt"
else
  EXIT_CODE=$?
  log "E2E tests FAILED (exit code: $EXIT_CODE)."
  echo "e2e_pass=0" > "$REPORT_DIR/e2e_status.txt"
  echo "e2e_fail=1" >> "$REPORT_DIR/e2e_status.txt"

  # ── 5. Collect screenshot if available ──
  if command -v xcrun >/dev/null 2>&1; then
    xcrun simctl io booted screenshot "$SCREENSHOT_DIR/e2e_failure.png" 2>/dev/null || true
  fi
  if command -v adb >/dev/null 2>&1; then
    adb exec-out screencap -p > "$SCREENSHOT_DIR/android/e2e_failure.png" 2>/dev/null || true
  fi

  exit 1
fi
