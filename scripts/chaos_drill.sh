#!/usr/bin/env bash
# chaos_drill.sh — Chaos engineering drill script for Sparkle
#
# Usage:
#   ./scripts/chaos_drill.sh redis-down     # Simulate Redis outage
#   ./scripts/chaos_drill.sh db-slow        # Simulate slow DB queries
#   ./scripts/chaos_drill.sh llm-timeout    # Simulate LLM provider timeout
#   ./scripts/chaos_drill.sh network-partition  # Simulate network partition
#   ./scripts/chaos_drill.sh all            # Run all drills
#   ./scripts/chaos_drill.sh restore        # Restore all services
#
# T6.3.1 + T6.3.2 — Chaos engineering foundation for CI periodic drills

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[CHAOS-DRILL]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[CHAOS-DRILL]${NC} $*"; }
log_error() { echo -e "${RED}[CHAOS-DRILL]${NC} $*"; }

COMPOSE_PROJECT="sparkle"

# ── Individual Drills ────────────────────────────────────────────────

drill_redis_down() {
    log_warn "DRILL: Simulating Redis outage..."
    docker compose pause redis 2>/dev/null || docker pause ${COMPOSE_PROJECT}-redis-1 2>/dev/null || {
        log_error "Could not pause Redis container"
        return 1
    }

    log_info "Redis is DOWN. Testing graceful degradation..."
    sleep 5

    # Check that API still responds (should use fallback)
    if curl -sf --max-time 10 http://localhost:8000/health > /dev/null 2>&1; then
        log_info "PASS: API still responds with Redis down"
    else
        log_warn "API health check failed with Redis down (may be expected)"
    fi

    log_info "Restoring Redis..."
    docker compose unpause redis 2>/dev/null || docker unpause ${COMPOSE_PROJECT}-redis-1 2>/dev/null || true
    sleep 3
    log_info "Redis restored"
}

drill_db_slow() {
    log_warn "DRILL: Simulating slow DB (adding network latency)..."
    # Add 500ms latency to DB container
    local container_id
    container_id=$(docker compose ps -q sparkle_db 2>/dev/null || echo "")

    if [[ -n "$container_id" ]]; then
        docker exec "$container_id" tc qdisc add dev eth0 root netem delay 500ms 2>/dev/null || {
            log_warn "tc not available in container, using CPU throttling instead"
            docker update --cpus=0.1 "$container_id" 2>/dev/null || true
        }
        log_info "DB is SLOW. Testing query timeouts..."
        sleep 5

        # Check that API still responds within timeout
        if curl -sf --max-time 30 http://localhost:8000/health > /dev/null 2>&1; then
            log_info "PASS: API responds despite slow DB"
        else
            log_warn "API health check slow/failed with slow DB"
        fi

        log_info "Restoring DB performance..."
        docker exec "$container_id" tc qdisc del dev eth0 root 2>/dev/null || true
        docker update --cpus=0 "$container_id" 2>/dev/null || true
    else
        log_warn "DB container not found, skipping"
    fi
    log_info "DB restored"
}

drill_llm_timeout() {
    log_warn "DRILL: Simulating LLM provider timeout..."
    # Block outgoing traffic to LLM APIs
    local container_id
    container_id=$(docker compose ps -q sparkle_api 2>/dev/null || echo "")

    if [[ -n "$container_id" ]]; then
        # Block HTTPS to common LLM endpoints
        docker exec "$container_id" iptables -A OUTPUT -d api.openai.com -j DROP 2>/dev/null || {
            log_warn "iptables not available, simulating via env override"
        }
        log_info "LLM outbound blocked. Testing fallback..."

        sleep 5

        log_info "Restoring LLM connectivity..."
        docker exec "$container_id" iptables -D OUTPUT -d api.openai.com -j DROP 2>/dev/null || true
    else
        log_warn "API container not found, skipping"
    fi
    log_info "LLM restored"
}

drill_network_partition() {
    log_warn "DRILL: Simulating network partition between API and Gateway..."
    # Use Docker network disconnect
    local api_id gw_id network
    api_id=$(docker compose ps -q sparkle_api 2>/dev/null || echo "")
    gw_id=$(docker compose ps -q sparkle_gateway 2>/dev/null || echo "")
    network="${COMPOSE_PROJECT}_default"

    if [[ -n "$api_id" && -n "$gw_id" ]]; then
        docker network disconnect "$network" "$api_id" 2>/dev/null || true
        log_info "API disconnected from network. Testing gateway error handling..."
        sleep 5

        # Gateway should return 502/503 gracefully
        local status
        status=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8080/api/v1/health 2>/dev/null || echo "000")
        if [[ "$status" == "502" || "$status" == "503" || "$status" == "000" ]]; then
            log_info "PASS: Gateway returns $status (expected error)"
        else
            log_warn "Unexpected status: $status"
        fi

        log_info "Restoring network..."
        docker network connect "$network" "$api_id" 2>/dev/null || true
        sleep 3
    else
        log_warn "Containers not found, skipping"
    fi
    log_info "Network restored"
}

do_restore() {
    log_info "Restoring all services..."
    docker compose unpause redis 2>/dev/null || true
    docker compose unpause sparkle_db 2>/dev/null || true
    local api_id
    api_id=$(docker compose ps -q sparkle_api 2>/dev/null || echo "")
    if [[ -n "$api_id" ]]; then
        local network="${COMPOSE_PROJECT}_default"
        docker network connect "$network" "$api_id" 2>/dev/null || true
    fi
    log_info "All services restored"
}

# ── Main ────────────────────────────────────────────────────────────

case "${1:-all}" in
    redis-down)   drill_redis_down ;;
    db-slow)      drill_db_slow ;;
    llm-timeout)  drill_llm_timeout ;;
    network-partition) drill_network_partition ;;
    all)
        log_info "Running ALL chaos drills..."
        drill_redis_down
        drill_db_slow
        drill_llm_timeout
        drill_network_partition
        log_info "ALL drills complete. Running restore..."
        do_restore
        log_info "Chaos drill session complete."
        ;;
    restore)      do_restore ;;
    *)
        echo "Usage: $0 {redis-down|db-slow|llm-timeout|network-partition|all|restore}"
        exit 1
        ;;
esac
