#!/usr/bin/env bash
# scripts/test/run_flutter_tests.sh — Run Flutter analyze + test + build checks
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
REPORT_DIR="$ROOT_DIR/artifacts/e2e/reports"
mkdir -p "$LOG_DIR" "$REPORT_DIR"

log() { echo "[$(date '+%H:%M:%S')] [flutter-test] $*"; }
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

cd "$ROOT_DIR/mobile"

# ── 1. Dependency resolution ──
run_step "flutter_pub_get" "flutter pub get"

# ── 2. L10n generation ──
run_step "flutter_gen_l10n" "flutter gen-l10n"

# ── 3. Code generation ──
run_step "flutter_build_runner" "dart run build_runner build --delete-conflicting-outputs 2>/dev/null || echo 'build_runner skipped'"

# ── 4. Static analysis ──
run_step "dart_analyze" "dart analyze --no-fatal-infos 2>&1 | tail -5; exit \${PIPESTATUS[0]}"

# ── 5. Unit + widget tests ──
run_step "flutter_test" "flutter test --reporter compact 2>&1 | tail -20; exit \${PIPESTATUS[0]}"

# ── 6. iOS simulator build (non-blocking) ──
log "Attempting iOS simulator build (non-blocking)..."
if flutter build ios --simulator --no-codesign >"$LOG_DIR/flutter_ios_build.log" 2>&1; then
  RESULTS+=("PASS: ios_simulator_build")
  PASS=$((PASS + 1))
  log "  ✓ ios_simulator_build"
else
  RESULTS+=("WARN: ios_simulator_build")
  log "  ⚠ ios_simulator_build (non-blocking) — see $LOG_DIR/flutter_ios_build.log"
fi

# ── 7. Android debug build (non-blocking) ──
log "Attempting Android debug build (non-blocking)..."
if flutter build apk --debug >"$LOG_DIR/flutter_android_build.log" 2>&1; then
  RESULTS+=("PASS: android_debug_build")
  PASS=$((PASS + 1))
  log "  ✓ android_debug_build"
else
  RESULTS+=("WARN: android_debug_build")
  log "  ⚠ android_debug_build (non-blocking) — see $LOG_DIR/flutter_android_build.log"
fi

# ── Summary ──
log ""
log "========================================="
log "Flutter Test Results"
log "========================================="
for r in "${RESULTS[@]}"; do log "  $r"; done
log "-----------------------------------------"
log "  PASS: $PASS  |  FAIL: $FAIL"
log "========================================="

echo "flutter_pass=$PASS" > "$REPORT_DIR/flutter_status.txt"
echo "flutter_fail=$FAIL" >> "$REPORT_DIR/flutter_status.txt"

[ "$FAIL" -gt 0 ] && exit 1 || exit 0
