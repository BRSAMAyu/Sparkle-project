#!/usr/bin/env bash
# scripts/dev/logs.sh — Tail and save logs from all services
# Usage: bash scripts/dev/logs.sh [--tail|--save]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/artifacts/e2e/logs"
mkdir -p "$LOG_DIR"

MODE="${1:---tail}"

# FIX-563：compose logs 用「服务名」、docker ps 按本仓分化后「容器名」探活。
# 旧清单混用且含 dash 形错名（sparkle-db/sparkle-redis 系初始 commit 既有债，P03-R2 登记）。
PAIRS=(
  "sparkle_db:sparkle_proj_db"
  "redis:sparkle_proj_redis"
  "minio:sparkle_proj_minio"
  "sparkle_gateway:sparkle_proj_gateway"
  "sparkle_agent:sparkle_proj_agent"
  "sparkle_api:sparkle_proj_api"
)

log() { echo "[$(date '+%H:%M:%S')] [logs] $*"; }

case "$MODE" in
  --save)
    log "Saving all logs to $LOG_DIR..."

    # Docker container logs
    for pair in "${PAIRS[@]}"; do
      svc="${pair%%:*}"; ctr="${pair##*:}"
      if docker ps --format '{{.Names}}' | grep -q "^${ctr}$"; then
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
    for pair in "${PAIRS[@]}"; do
      svc="${pair%%:*}"; ctr="${pair##*:}"
      if docker ps --format '{{.Names}}' | grep -q "^${ctr}$"; then
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
