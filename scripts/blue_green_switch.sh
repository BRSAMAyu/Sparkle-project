#!/usr/bin/env bash
# blue_green_switch.sh — Blue-Green deployment switcher for Sparkle
#
# Usage:
#   ./scripts/blue_green_switch.sh switch   # Switch active slot (blue↔green)
#   ./scripts/blue_green_switch.sh status   # Show current active slot
#   ./scripts/blue_green_switch.sh rollback # Rollback to previous slot
#   ./scripts/blue_green_switch.sh smoke    # Run smoke tests against active slot
#
# Environment:
#   ACTIVE_SLOT_FILE  — file storing current active slot (default: /tmp/sparkle_active_slot)
#   COMPOSE_FILE_BLUE — docker-compose file for blue slot
#   COMPOSE_FILE_GREEN — docker-compose file for green slot
#
# T6.2.1 + T6.2.2 — Blue-green switch with health check, smoke, and rollback

set -euo pipefail

ACTIVE_SLOT_FILE="${ACTIVE_SLOT_FILE:-/tmp/sparkle_active_slot}"
COMPOSE_FILE_BLUE="${COMPOSE_FILE_BLUE:-docker-compose.yml}"
COMPOSE_FILE_GREEN="${COMPOSE_FILE_GREEN:-docker-compose.green.yml}"
SLOTS=("blue" "green")
SMOKE_TIMEOUT=60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

get_current_slot() {
    if [[ -f "$ACTIVE_SLOT_FILE" ]]; then
        cat "$ACTIVE_SLOT_FILE"
    else
        echo "blue"
    fi
}

get_idle_slot() {
    local current
    current=$(get_current_slot)
    if [[ "$current" == "blue" ]]; then
        echo "green"
    else
        echo "blue"
    fi
}

get_compose_file() {
    local slot=$1
    if [[ "$slot" == "blue" ]]; then
        echo "$COMPOSE_FILE_BLUE"
    else
        echo "$COMPOSE_FILE_GREEN"
    fi
}

health_check() {
    local slot=$1
    local compose_file
    compose_file=$(get_compose_file "$slot")

    log_info "Running health check on $slot slot..."

    local gateway_url="http://localhost:8080/api/v1/health"
    local api_url="http://localhost:8000/health"

    # Check gateway
    if curl -sf --max-time 10 "$gateway_url" > /dev/null 2>&1; then
        log_info "Gateway healthy on $slot"
    else
        log_warn "Gateway not responding on $slot (may be expected if slot is down)"
        return 1
    fi

    # Check API
    if curl -sf --max-time 10 "$api_url" > /dev/null 2>&1; then
        log_info "API healthy on $slot"
    else
        log_warn "API not responding on $slot"
        return 1
    fi

    return 0
}

run_smoke() {
    local slot=$1
    log_info "Running smoke tests against $slot slot..."

    if command -v make &> /dev/null; then
        if make smoke 2>/dev/null; then
            log_info "Smoke tests passed on $slot"
            return 0
        else
            log_error "Smoke tests FAILED on $slot"
            return 1
        fi
    else
        # Basic smoke: health + version endpoint
        local ok=true
        for url in "http://localhost:8080/api/v1/health" "http://localhost:8000/health"; do
            if ! curl -sf --max-time 10 "$url" > /dev/null 2>&1; then
                log_error "Smoke FAILED: $url not responding"
                ok=false
            fi
        done
        if $ok; then
            log_info "Basic smoke tests passed on $slot"
            return 0
        else
            return 1
        fi
    fi
}

do_switch() {
    local current idle
    current=$(get_current_slot)
    idle=$(get_idle_slot)

    log_info "Current active: $current"
    log_info "Switching to: $idle"

    # 1. Bring up idle slot
    local idle_compose
    idle_compose=$(get_compose_file "$idle")
    if [[ -f "$idle_compose" ]]; then
        log_info "Starting $idle slot with $idle_compose..."
        docker compose -f "$idle_compose" up -d --wait 2>/dev/null || \
            docker compose -f "$idle_compose" up -d
    else
        log_info "No compose file for $idle slot, assuming containers already running"
    fi

    # 2. Health check idle slot
    log_info "Waiting for $idle slot to become healthy..."
    local attempts=0
    while (( attempts < SMOKE_TIMEOUT / 5 )); do
        if health_check "$idle"; then
            break
        fi
        log_info "Waiting... ($((attempts * 5))s)"
        sleep 5
        ((attempts++))
    done

    if ! health_check "$idle"; then
        log_error "Health check FAILED on $idle slot. Aborting switch."
        return 1
    fi

    # 3. Smoke test idle slot
    if ! run_smoke "$idle"; then
        log_error "Smoke tests FAILED on $idle slot. Aborting switch."
        return 1
    fi

    # 4. Switch active slot
    echo "$idle" > "$ACTIVE_SLOT_FILE"
    log_info "Active slot switched to: $idle"

    # 5. Optionally stop old slot (keep warm for quick rollback)
    log_info "Old slot ($current) kept running for quick rollback."
    log_info "Run './scripts/blue_green_switch.sh stop-old' to decommission."
}

do_rollback() {
    local current idle
    current=$(get_current_slot)
    idle=$(get_idle_slot)

    log_warn "ROLLBACK: Switching from $current back to $idle"

    if health_check "$idle"; then
        echo "$idle" > "$ACTIVE_SLOT_FILE"
        log_info "Rollback complete. Active: $idle"
    else
        log_error "Rollback FAILED: $idle slot is not healthy!"
        return 1
    fi
}

do_status() {
    local current
    current=$(get_current_slot)
    local idle
    idle=$(get_idle_slot)

    echo "Active slot: $current"
    echo "Idle slot:   $idle"

    echo ""
    echo "Health checks:"
    for slot in "${SLOTS[@]}"; do
        if health_check "$slot" 2>/dev/null; then
            echo "  $slot: ${GREEN}HEALTHY${NC}"
        else
            echo "  $slot: ${RED}DOWN${NC}"
        fi
    done
}

# ── Main ────────────────────────────────────────────────────────────

case "${1:-status}" in
    switch)
        do_switch
        ;;
    rollback)
        do_rollback
        ;;
    status)
        do_status
        ;;
    smoke)
        run_smoke "$(get_current_slot)"
        ;;
    stop-old)
        idle=$(get_idle_slot)
        idle_compose=$(get_compose_file "$idle")
        if [[ -f "$idle_compose" ]]; then
            log_info "Stopping $idle slot..."
            docker compose -f "$idle_compose" down
        fi
        ;;
    *)
        echo "Usage: $0 {switch|rollback|status|smoke|stop-old}"
        exit 1
        ;;
esac
