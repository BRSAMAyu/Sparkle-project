#!/usr/bin/env bash
# scripts/mobile/android_e2e.sh — Full Android Emulator E2E pipeline
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
REPORT_DIR="$ROOT_DIR/artifacts/e2e/reports"
SCREENSHOT_DIR="$ROOT_DIR/artifacts/e2e/screenshots/android"
mkdir -p "$LOG_DIR" "$REPORT_DIR" "$SCREENSHOT_DIR"

log() { echo "[$(date '+%H:%M:%S')] [android-e2e] $*"; }
PASS=0; FAIL=0; RESULTS=()

step() {
  local name="$1"; shift
  log "STEP: $name"
  if "$@" >"$LOG_DIR/android_e2e_${name}.log" 2>&1; then
    RESULTS+=("PASS: $name")
    PASS=$((PASS + 1))
    log "  ✓ $name"
  else
    RESULTS+=("FAIL: $name")
    FAIL=$((FAIL + 1))
    log "  ✗ $name — see $LOG_DIR/android_e2e_${name}.log"
    tail -40 "$LOG_DIR/android_e2e_${name}.log" 2>/dev/null
  fi
}

log "Starting Android E2E pipeline..."

# ── 1. Boot emulator ──
step "boot"   bash "$ROOT_DIR/scripts/mobile/android_boot.sh"

# ── 2. Build ──
step "build"  bash "$ROOT_DIR/scripts/mobile/android_build.sh"

# ── 3. Install ──
step "install" bash "$ROOT_DIR/scripts/mobile/android_install.sh"

# ── 4. Run integration tests ──
step "test"   bash "$ROOT_DIR/scripts/test/run_e2e.sh"

# ── 5. Screenshot ──
bash "$ROOT_DIR/scripts/mobile/android_screenshot.sh" "post_e2e" 2>/dev/null || true

# ── Summary ──
log ""
log "========================================="
log "Android E2E Results"
log "========================================="
for r in "${RESULTS[@]}"; do log "  $r"; done
log "-----------------------------------------"
log "  PASS: $PASS  |  FAIL: $FAIL"
log "========================================="

echo "android_pass=$PASS" > "$REPORT_DIR/android_status.txt"
echo "android_fail=$FAIL" >> "$REPORT_DIR/android_status.txt"

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
