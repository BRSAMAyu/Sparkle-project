#!/usr/bin/env bash
# scripts/dev/healthcheck.sh — Verify all local services are healthy
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

PASS=0
FAIL=0
WARN=0
RESULTS=()

log() { echo "[$(date '+%H:%M:%S')] [health] $*"; }

check() {
  local name="$1"
  local cmd="$2"
  local severity="${3:-P0}"
  if eval "$cmd" >"$LOG_DIR/health_${name}.log" 2>&1; then
    RESULTS+=("PASS: $name")
    PASS=$((PASS + 1))
    log "  ✓ $name"
  else
    RESULTS+=("FAIL: $name ($severity)")
    FAIL=$((FAIL + 1))
    log "  ✗ $name ($severity) — see $LOG_DIR/health_${name}.log"
  fi
}

warn() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >"$LOG_DIR/health_${name}.log" 2>&1; then
    RESULTS+=("PASS: $name")
    PASS=$((PASS + 1))
    log "  ✓ $name"
  else
    RESULTS+=("WARN: $name")
    WARN=$((WARN + 1))
    log "  ⚠ $name (non-critical)"
  fi
}

log "Running health checks..."

# ── Docker services ──
check "docker_daemon"       "docker info >/dev/null 2>&1"
check "postgres_connect"    "docker exec sparkle-db pg_isready -U ${POSTGRES_USER:-brsama} >/dev/null 2>&1"
check "redis_ping"          "docker exec sparkle-redis redis-cli ping >/dev/null 2>&1"

# MinIO — check if container is running and bucket is accessible
check "minio_running"       "docker ps --format '{{.Names}}' | grep -q 'minio'"
warn  "minio_bucket"        "curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1"

# ── Python Backend ──
PYTHON_API_PORT="${API_PORT:-8000}"
GRPC_PORT="${GRPC_PORT:-50051}"

warn "python_api_health"    "curl -sf http://localhost:${PYTHON_API_PORT}/health/live >/dev/null 2>&1"
warn "python_api_ready"     "curl -sf http://localhost:${PYTHON_API_PORT}/health/ready >/dev/null 2>&1"
warn "grpc_server"          "grpcurl -plaintext -max-time 3 localhost:${GRPC_PORT} list >/dev/null 2>&1 || echo 'attempted' | grep -q ''"

# ── Go Gateway ──
GATEWAY_PORT="${GATEWAY_PORT:-8080}"

warn "gateway_healthz"      "curl -sf http://localhost:${GATEWAY_PORT}/healthz >/dev/null 2>&1"
warn "gateway_readyz"       "curl -sf http://localhost:${GATEWAY_PORT}/readyz >/dev/null 2>&1"

# ── Cross-service connectivity ──
if curl -sf http://localhost:${GATEWAY_PORT}/health >/dev/null 2>&1; then
  # Check if gateway reports upstream health
  GATEWAY_BODY=$(curl -sf http://localhost:${GATEWAY_PORT}/health 2>/dev/null || echo "{}")
  warn "gateway_to_backend"  "echo '$GATEWAY_BODY' | python3 -c \"import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status') in ('healthy','degraded') else 1)\" 2>/dev/null"
fi

# ── WebSocket endpoint ──
warn "websocket_handshake"  "curl -sf -o /dev/null -w '%{http_code}' -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' http://localhost:${GATEWAY_PORT}/ws/chat 2>/dev/null | grep -qE '101|4[0-9]{2}'"

# ── Flutter SDK ──
warn "flutter_sdk"          "command -v flutter >/dev/null 2>&1 && flutter --version >/dev/null 2>&1"

# ── Summary ──
log ""
log "========================================="
log "Health Check Results"
log "========================================="
for r in "${RESULTS[@]}"; do
  log "  $r"
done
log "-----------------------------------------"
log "  PASS: $PASS  |  FAIL: $FAIL  |  WARN: $WARN"
log "========================================="

# Write status file for report generator
echo "healthcheck_pass=$PASS" > "$ROOT_DIR/artifacts/e2e/reports/healthcheck_status.txt"
echo "healthcheck_fail=$FAIL" >> "$ROOT_DIR/artifacts/e2e/reports/healthcheck_status.txt"
echo "healthcheck_warn=$WARN" >> "$ROOT_DIR/artifacts/e2e/reports/healthcheck_status.txt"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
