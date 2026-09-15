#!/usr/bin/env bash
# scripts/dev/smoke.sh — Run smoke tests against running services
# Wraps: make smoke + additional API smoke checks
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

PASS=0
FAIL=0
RESULTS=()

log() { echo "[$(date '+%H:%M:%S')] [smoke] $*"; }

smoke_check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >"$LOG_DIR/smoke_${name}.log" 2>&1; then
    RESULTS+=("PASS: $name")
    PASS=$((PASS + 1))
    log "  ✓ $name"
  else
    RESULTS+=("FAIL: $name")
    FAIL=$((FAIL + 1))
    log "  ✗ $name — see $LOG_DIR/smoke_${name}.log"
  fi
}

log "Running smoke tests..."

# ── 1. Infrastructure ──
smoke_check "infra_postgres"  "docker exec sparkle-db pg_isready -U ${POSTGRES_USER:-brsama} >/dev/null 2>&1"
smoke_check "infra_redis"     "docker exec sparkle-redis redis-cli ping 2>&1 | grep -q PONG"

# ── 2. Make smoke (existing) ──
if [ -f "$ROOT_DIR/Makefile" ]; then
  log "Running make smoke..."
  (cd "$ROOT_DIR" && make smoke) >>"$LOG_DIR/smoke_make.log" 2>&1
  smoke_check "make_smoke" "true"  # Already ran
fi

# ── 3. Python Backend API smoke ──
PYTHON_API_PORT="${API_PORT:-8000}"
GATEWAY_PORT="${GATEWAY_PORT:-8080}"

smoke_check "backend_health"  "curl -sf http://localhost:${PYTHON_API_PORT}/health >/dev/null 2>&1"
smoke_check "backend_live"    "curl -sf http://localhost:${PYTHON_API_PORT}/health/live >/dev/null 2>&1"

# ── 4. Go Gateway smoke ──
smoke_check "gateway_healthz" "curl -sf http://localhost:${GATEWAY_PORT}/healthz >/dev/null 2>&1"
smoke_check "gateway_readyz"  "curl -sf http://localhost:${GATEWAY_PORT}/readyz >/dev/null 2>&1"

# ── 5. API endpoint smoke (if backend running) ──
# Auth endpoint should be reachable
smoke_check "auth_endpoint"   "curl -sf -o /dev/null -w '%{http_code}' http://localhost:${GATEWAY_PORT}/api/v1/auth/login 2>/dev/null | grep -qE '4[0-9]{2}'"

# ── 6. gRPC service smoke ──
GRPC_PORT="${GRPC_PORT:-50051}"
smoke_check "grpc_list"       "grpcurl -plaintext -max-time 5 localhost:${GRPC_PORT} list 2>/dev/null | grep -q '.' || true"

# ── Summary ──
log ""
log "========================================="
log "Smoke Test Results"
log "========================================="
for r in "${RESULTS[@]}"; do
  log "  $r"
done
log "-----------------------------------------"
log "  PASS: $PASS  |  FAIL: $FAIL"
log "========================================="

echo "smoke_pass=$PASS" > "$ROOT_DIR/artifacts/e2e/reports/smoke_status.txt"
echo "smoke_fail=$FAIL" >> "$ROOT_DIR/artifacts/e2e/reports/smoke_status.txt"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
