#!/usr/bin/env bash
# production_readiness_check.sh — Phase 7 verification: pre-deploy checklist
#
# Usage: ./scripts/production_readiness_check.sh [--skip-flutter] [--skip-go]
#
# T7.3.5-7 — Production readiness verification

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

log_pass() { echo -e "  ${GREEN}✓${NC} $*"; ((PASS++)); }
log_fail() { echo -e "  ${RED}✗${NC} $*"; ((FAIL++)); }
log_warn() { echo -e "  ${YELLOW}!${NC} $*"; ((WARN++)); }
log_section() { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

SKIP_FLUTTER=false
SKIP_GO=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-flutter)
            SKIP_FLUTTER=true
            ;;
        --skip-go)
            SKIP_GO=true
            ;;
        *)
            log_warn "Unknown option ignored: $1"
            ;;
    esac
    shift
done

# ── 1. Infrastructure ────────────────────────────────────────────────

log_section "1. Infrastructure"

if docker compose --project-directory "$ROOT_DIR" ps sparkle_db 2>/dev/null | grep -q "running"; then
    log_pass "PostgreSQL is running"
else
    log_fail "PostgreSQL is NOT running"
fi

if docker compose --project-directory "$ROOT_DIR" ps redis 2>/dev/null | grep -q "running"; then
    log_pass "Redis is running"
else
    log_fail "Redis is NOT running"
fi

if docker compose --project-directory "$ROOT_DIR" ps minio 2>/dev/null | grep -q "running"; then
    log_pass "MinIO is running"
else
    log_warn "MinIO is not running (optional for some features)"
fi

# ── 2. Database Migrations ───────────────────────────────────────────

log_section "2. Database Migrations"

if command -v alembic &> /dev/null && [[ -d "$BACKEND_DIR" ]]; then
    CURRENT=$(cd "$BACKEND_DIR" && alembic current 2>/dev/null | head -1 || echo "unknown")
    if echo "$CURRENT" | grep -q "head"; then
        log_pass "Alembic at head: $CURRENT"
    else
        log_warn "Alembic not at head: $CURRENT"
    fi
else
    log_warn "Alembic not available, skipping migration check"
fi

# ── 3. Backend Health ───────────────────────────────────────────────

log_section "3. Backend Services"

if curl -sf --max-time 5 http://localhost:8000/health > /dev/null 2>&1; then
    log_pass "FastAPI health check OK"
else
    log_fail "FastAPI not responding on :8000"
fi

if curl -sf --max-time 5 http://localhost:8080/api/v1/health > /dev/null 2>&1; then
    log_pass "Gateway health check OK"
else
    log_fail "Gateway not responding on :8080"
fi

# ── 4. Security ─────────────────────────────────────────────────────

log_section "4. Security"

if grep -q "SECRET_KEY=change" "$BACKEND_DIR/.env" 2>/dev/null; then
    log_fail "SECRET_KEY is still set to default value"
else
    log_pass "SECRET_KEY is not default"
fi

if grep -q "minioadmin" "$BACKEND_DIR/.env" 2>/dev/null; then
    log_fail "MinIO credentials still using default"
else
    log_pass "MinIO credentials are not default"
fi

# Check CORS is not wildcard in production mode
if grep -q "CORS_ORIGINS=\[\"\\*\"\]" "$BACKEND_DIR/.env" 2>/dev/null; then
    log_warn "CORS origins is wildcard — ensure this is not production"
else
    log_pass "CORS origins are not wildcard"
fi

# ── 5. Monitoring ───────────────────────────────────────────────────

log_section "5. Monitoring & Observability"

if curl -sf --max-time 5 http://localhost:9090/-/healthy > /dev/null 2>&1; then
    log_pass "Prometheus is healthy"
else
    log_warn "Prometheus not reachable on :9090"
fi

if curl -sf --max-time 5 http://localhost:3000/api/health > /dev/null 2>&1; then
    log_pass "Grafana is healthy"
else
    log_warn "Grafana not reachable on :3000"
fi

# ── 6. Python Tests ─────────────────────────────────────────────────

log_section "6. Python Tests"

if command -v python3 &> /dev/null; then
    TEST_RESULT=$(cd "$BACKEND_DIR" && python3 -m pytest tests/unit/ -x -q --timeout=30 --co 2>/dev/null | tail -1 || echo "0 tests")
    TOTAL_TESTS=$(echo "$TEST_RESULT" | grep -oP '\d+' | head -1 || echo "0")
    if (( TOTAL_TESTS > 0 )); then
        log_pass "$TOTAL_TESTS tests collected"
    else
        log_warn "Could not collect test count"
    fi
else
    log_warn "python3 not available for test collection"
fi

# ── 7. Proto Contracts ──────────────────────────────────────────────

log_section "7. Proto & API Contracts"

if [[ -d "$ROOT_DIR/proto" ]]; then
    log_pass "Proto directory exists"
else
    log_warn "Proto directory not found"
fi

# ── 8. Deployment Artifacts ─────────────────────────────────────────

log_section "8. Deployment Artifacts"

if [[ -f "$ROOT_DIR/scripts/blue_green_switch.sh" ]]; then
    log_pass "Blue-green switch script exists"
else
    log_warn "Blue-green switch script not found"
fi

if [[ -f "$ROOT_DIR/scripts/chaos_drill.sh" ]]; then
    log_pass "Chaos drill script exists"
else
    log_warn "Chaos drill script not found"
fi

if [[ -f "$ROOT_DIR/monitoring/sparkle_t6_slo_alerts.yml" ]]; then
    log_pass "SLO alert rules exist"
else
    log_warn "SLO alert rules not found"
fi

# ── Summary ─────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}PASS${NC}: $PASS  ${RED}FAIL${NC}: $FAIL  ${YELLOW}WARN${NC}: $WARN"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if (( FAIL > 0 )); then
    echo -e "\n${RED}BLOCKED: $FAIL critical checks failed. Fix before deploying.${NC}"
    exit 1
else
    echo -e "\n${GREEN}READY: All critical checks passed.$NC"
    exit 0
fi
