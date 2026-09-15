#!/usr/bin/env bash
# scripts/test/run_prelaunch.sh — Master prelaunch engineering verification
# Runs all checks sequentially, generates PRELAUNCH_REPORT.md
# Usage: bash scripts/test/run_prelaunch.sh [--skip-mobile] [--skip-infra]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/artifacts/e2e"
LOG_DIR="$ARTIFACT_DIR/logs"
REPORT_DIR="$ARTIFACT_DIR/reports"

mkdir -p "$LOG_DIR" "$REPORT_DIR" \
  "$ARTIFACT_DIR/screenshots/ios" \
  "$ARTIFACT_DIR/screenshots/android" \
  "$ARTIFACT_DIR/videos/ios" \
  "$ARTIFACT_DIR/videos/android"

# Parse args
SKIP_MOBILE=false
SKIP_INFRA=false
for arg in "$@"; do
  case "$arg" in
    --skip-mobile) SKIP_MOBILE=true ;;
    --skip-infra)  SKIP_INFRA=true ;;
  esac
done

PASS=0
FAIL=0
SKIP=0
RESULTS=()
START_TIME=$(date +%s)

log() { echo "[$(date '+%H:%M:%S')] [prelaunch] $*"; }

run_step() {
  local name="$1"
  local cmd="$2"
  local required="${3:-true}"
  local timeout="${4:-300}"

  echo ""
  log "===== START: $name ====="
  echo "  Command: $cmd"

  local log_file="$LOG_DIR/${name}.log"
  local start step_start step_elapsed

  step_start=$(date +%s)

  if timeout "$timeout" bash -c "$cmd" >"$log_file" 2>&1; then
    step_elapsed=$(( $(date +%s) - step_start ))
    RESULTS+=("PASS: $name (${step_elapsed}s)")
    PASS=$((PASS + 1))
    log "  ✓ PASS: $name (${step_elapsed}s)"
    echo "PASS: $name" >> "$REPORT_DIR/prelaunch_status.txt"
  else
    step_elapsed=$(( $(date +%s) - step_start ))
    RESULTS+=("FAIL: $name (${step_elapsed}s)")
    FAIL=$((FAIL + 1))
    log "  ✗ FAIL: $name (${step_elapsed}s)"
    echo "FAIL: $name" >> "$REPORT_DIR/prelaunch_status.txt"
    if [ "$required" = "true" ]; then
      log "  Last 40 lines:"
      tail -40 "$log_file" 2>/dev/null
    fi
  fi
}

skip_step() {
  local name="$1"
  local reason="$2"
  RESULTS+=("SKIP: $name ($reason)")
  SKIP=$((SKIP + 1))
  log "  ⊘ SKIP: $name — $reason"
  echo "SKIP: $name" >> "$REPORT_DIR/prelaunch_status.txt"
}

# ── Clean previous state ──
rm -f "$REPORT_DIR/prelaunch_status.txt"
rm -f "$REPORT_DIR"/*_status.txt

log "Sparkle Prelaunch Engineering Verification"
log "============================================"
log ""

# ══════════════════════════════════════════════
# Phase 1: Infrastructure
# ══════════════════════════════════════════════

if [ "$SKIP_INFRA" = "false" ]; then
  log "── Phase 1: Infrastructure ──"
  run_step "dev_reset"      "bash $ROOT_DIR/scripts/dev/reset.sh"            "true"  120
  run_step "dev_up"          "bash $ROOT_DIR/scripts/dev/up.sh"              "true"  120
  run_step "healthcheck"    "bash $ROOT_DIR/scripts/dev/healthcheck.sh"      "true"   60
  run_step "smoke"          "bash $ROOT_DIR/scripts/dev/smoke.sh"            "true"   60
else
  skip_step "dev_reset"      "skipped by --skip-infra"
  skip_step "dev_up"          "skipped by --skip-infra"
  skip_step "healthcheck"    "skipped by --skip-infra"
  skip_step "smoke"          "skipped by --skip-infra"
fi

# ══════════════════════════════════════════════
# Phase 2: Backend Tests
# ══════════════════════════════════════════════

log "── Phase 2: Backend Tests ──"
run_step "backend_tests"   "bash $ROOT_DIR/scripts/test/run_backend_tests.sh"  "true" 300
run_step "gateway_tests"   "bash $ROOT_DIR/scripts/test/run_gateway_tests.sh"  "true" 300

# ══════════════════════════════════════════════
# Phase 3: Flutter Tests
# ══════════════════════════════════════════════

log "── Phase 3: Flutter Tests ──"
run_step "flutter_tests"   "bash $ROOT_DIR/scripts/test/run_flutter_tests.sh"  "true" 600

# ══════════════════════════════════════════════
# Phase 4: Mobile E2E
# ══════════════════════════════════════════════

if [ "$SKIP_MOBILE" = "false" ]; then
  log "── Phase 4: Mobile E2E ──"
  run_step "ios_e2e"       "bash $ROOT_DIR/scripts/mobile/ios_e2e.sh"         "false" 600
  run_step "android_e2e"   "bash $ROOT_DIR/scripts/mobile/android_e2e.sh"     "false" 600
else
  skip_step "ios_e2e"       "skipped by --skip-mobile"
  skip_step "android_e2e"   "skipped by --skip-mobile"
fi

# ══════════════════════════════════════════════
# Phase 5: Log Analysis
# ══════════════════════════════════════════════

log "── Phase 5: Log Analysis ──"

# Save all logs
bash "$ROOT_DIR/scripts/dev/logs.sh" --save 2>/dev/null || true

# Run analyzers
python3 "$ROOT_DIR/tool/e2e/analyze_flutter_log.py" "$LOG_DIR" >> "$LOG_DIR/flutter_analysis.log" 2>&1 || true
python3 "$ROOT_DIR/tool/e2e/analyze_backend_log.py" "$LOG_DIR" >> "$LOG_DIR/backend_analysis.log" 2>&1 || true

# ══════════════════════════════════════════════
# Phase 6: Report Generation
# ══════════════════════════════════════════════

log "── Phase 6: Report Generation ──"
python3 "$ROOT_DIR/tool/e2e/generate_e2e_report.py" >> "$LOG_DIR/report_gen.log" 2>&1 || true

# ══════════════════════════════════════════════
# Final Summary
# ══════════════════════════════════════════════

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))
MINUTES=$(( ELAPSED / 60 ))
SECONDS=$(( ELAPSED % 60 ))

echo ""
log "============================================"
log "PRELAUNCH VERIFICATION COMPLETE"
log "============================================"
for r in "${RESULTS[@]}"; do
  log "  $r"
done
log "--------------------------------------------"
log "  PASS: $PASS  |  FAIL: $FAIL  |  SKIP: $SKIP"
log "  Elapsed: ${MINUTES}m ${SECONDS}s"
log "============================================"
echo ""

log "Reports:"
log "  - artifacts/e2e/reports/PRELAUNCH_REPORT.md"
log "  - artifacts/e2e/reports/prelaunch_status.txt"
if [ -f "$REPORT_DIR/IOS_DEVICE_TEST_REPORT.md" ]; then
  log "  - artifacts/e2e/reports/IOS_DEVICE_TEST_REPORT.md"
fi
if [ -f "$REPORT_DIR/ANDROID_DEVICE_TEST_REPORT.md" ]; then
  log "  - artifacts/e2e/reports/ANDROID_DEVICE_TEST_REPORT.md"
fi
echo ""
log "Re-run: bash scripts/test/run_prelaunch.sh"
log "Re-run (fast, skip infra+mobile): bash scripts/test/run_prelaunch.sh --skip-infra --skip-mobile"

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
