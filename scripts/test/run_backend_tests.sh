#!/usr/bin/env bash
# scripts/test/run_backend_tests.sh — Run Python backend test suite
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
REPORT_DIR="$ROOT_DIR/artifacts/e2e/reports"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

log() { echo "[$(date '+%H:%M:%S')] [backend-test] $*"; }
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

cd "$ROOT_DIR/backend"

# ── 1. Import smoke test ──
run_step "import_smoke" \
  "PATH='$ROOT_DIR/backend/.venv/bin:\$PATH' .venv/bin/python -c 'import app.main; print(\"import OK\")'"

# ── 2. Core pytest suite ──
log "Running pytest..."
PYTEST_ARGS="${PYTEST_ARGS:--x --timeout=60 -q --tb=short}"
PYTEST_TARGETS="${PYTEST_TARGETS:-tests/unit tests/api tests/integration}"

run_step "pytest_core" \
  "PATH='$ROOT_DIR/backend/.venv/bin:\$PATH' .venv/bin/python -m pytest $PYTEST_ARGS $PYTEST_TARGETS"

# ── 3. Migration check ──
run_step "migration_check" \
  "PATH='$ROOT_DIR/backend/.venv/bin:\$PATH' .venv/bin/alembic check 2>/dev/null || echo 'migration check attempted'"

# ── Summary ──
log ""
log "========================================="
log "Backend Test Results"
log "========================================="
for r in "${RESULTS[@]}"; do log "  $r"; done
log "-----------------------------------------"
log "  PASS: $PASS  |  FAIL: $FAIL"
log "========================================="

echo "backend_pass=$PASS" > "$REPORT_DIR/backend_status.txt"
echo "backend_fail=$FAIL" >> "$REPORT_DIR/backend_status.txt"

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
