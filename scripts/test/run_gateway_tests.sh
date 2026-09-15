#!/usr/bin/env bash
# scripts/test/run_gateway_tests.sh — Run Go Gateway test suite
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
REPORT_DIR="$ROOT_DIR/artifacts/e2e/reports"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

log() { echo "[$(date '+%H:%M:%S')] [gateway-test] $*"; }
PASS=0; FAIL=0; RESULTS=()

run_step() {
  local name="$1"
  local cmd="$2"
  log "Running: $name"
  if eval "$cmd" >"$LOG_DIR/${name}.log" 2>&1; then
    RESULTS+=("PASS: $name")
    PASS=$((PASS + 1))
    log "  ✓ $name"
  else
    RESULTS+=("FAIL: $name")
    FAIL=$((FAIL + 1))
    log "  ✗ $name — tail:"
    tail -30 "$LOG_DIR/${name}.log" 2>/dev/null
  fi
}

cd "$ROOT_DIR/backend/gateway"

# ── 1. Build check ──
run_step "go_build" "go build ./..."

# ── 2. Vet ──
run_step "go_vet" "go vet ./..."

# ── 3. Tests ──
GO_TEST_ARGS="${GO_TEST_ARGS:--timeout 120s -count=1}"
run_step "go_test" "go test $GO_TEST_ARGS ./..."

# ── Summary ──
log ""
log "========================================="
log "Gateway Test Results"
log "========================================="
for r in "${RESULTS[@]}"; do log "  $r"; done
log "-----------------------------------------"
log "  PASS: $PASS  |  FAIL: $FAIL"
log "========================================="

echo "gateway_pass=$PASS" > "$REPORT_DIR/gateway_status.txt"
echo "gateway_fail=$FAIL" >> "$REPORT_DIR/gateway_status.txt"

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
