#!/usr/bin/env bash
# scripts/dev/logs.sh — Tail and save logs from all services
# Usage: bash scripts/dev/logs.sh [--tail|--save]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

MODE="${1:---tail}"

log() { echo "[$(date '+%H:%M:%S')] [logs] $*"; }

case "$MODE" in
  --save)
    log "Saving all logs to $LOG_DIR..."

    # Docker container logs
    for svc in sparkle-db sparkle-redis minio sparkle-gateway sparkle-agent sparkle-api; do
      if docker ps --format '{{.Names}}' | grep -q "$svc"; then
        docker compose logs --no-color "$svc" > "$LOG_DIR/docker_${svc}.log" 2>&1 || true
        log "  Saved docker_${svc}.log"
      fi
    done

    # Backend logs
    if [ -d "$ROOT_DIR/backend/logs" ]; then
      cp -r "$ROOT_DIR/backend/logs/"*.log "$LOG_DIR/" 2>/dev/null || true
      log "  Saved backend logs"
    fi

    log "Logs saved to $LOG_DIR/"
    ;;

  --tail)
    log "Tailing logs from all running services (Ctrl+C to stop)..."
    echo ""

    # Build the list of running services
    SERVICES=()
    for svc in sparkle-db sparkle-redis minio sparkle-gateway sparkle-agent sparkle-api; do
      if docker ps --format '{{.Names}}' | grep -q "$svc"; then
        SERVICES+=("$svc")
      fi
    done

    if [ ${#SERVICES[@]} -eq 0 ]; then
      log "No running Docker services found."
      exit 0
    fi

    docker compose logs -f "${SERVICES[@]}" 2>&1 || true
    ;;

  *)
    echo "Usage: bash scripts/dev/logs.sh [--tail|--save]"
    echo "  --tail  Follow logs in real-time (default)"
    echo "  --save  Save all logs to artifacts/e2e/logs/"
    exit 1
    ;;
esac
